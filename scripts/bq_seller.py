#!/usr/bin/env python3
"""Search HubSpot Contact rows in BigQuery and emit matching PalmStreet uids.

Standalone lookup tool — NOT part of any skill. The seller-audit skill takes a
PalmStreet uid as input and runs the audit; this script is the upstream
"resolve identity → uid" step you invoke when the user gives you anything
other than a uid (email, name, username, phone, contact link, etc.).

Typical workflow:
    python scripts/bq_seller.py --query "frankie@example.com"
    # → uid on stdout
    # → invoke the seller-audit skill with that uid

The audit pipeline itself uses `skills/seller-audit/scripts/bq_query_seller.py
--uid <uid>` for the per-seller detail extraction; that script is a skill
component and not interchangeable with this one.

Output:
- stdout: tab-separated rows, one per matching contact. Column 1 is the
  PalmStreet uid (suitable for `xargs -I{} python skills/seller-audit/scripts/bq_query_seller.py --uid {}`).
  Contacts WITHOUT a `palmstreet_userid` are surfaced on stderr instead of
  stdout (`# no_uid …`) so they don't pollute the uid stream.
- file: raw matched rows are dumped to `outputs/seller_query_<slug>.json` for
  inspection; the path is logged on stderr (`# Found N record(s). Raw rows: …`).
"""

import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery

_SCRIPT_DIR = Path(__file__).resolve().parent       # <repo>/scripts
_PROJECT_ROOT = _SCRIPT_DIR.parent                  # <repo>

OUTPUT_DIR = _PROJECT_ROOT / "outputs"
TABLE = "`plantstory.hubspot.Contact`"

SEARCH_FIELDS = [
    "VId",
    "firstname",
    "lastname",
    "company",
    "email",
    "phone",
    "hs_calculated_phone_number",
    "palmstreet_username",
    "palmstreet_userid",
    "website",
    "social_media",
    "categories",
    "aloy_category",
    "app__date",   # used for ORDER BY tiebreak (most recent app first)
    "createdate",  # used for ORDER BY tiebreak when app__date is null
]
SEARCH_SELECT_COLS = ", ".join(SEARCH_FIELDS)


# ----------------------------------------------------------------------------
# Helpers (small, intentionally duplicated from bq_query_seller.py to keep
# each script self-contained — these scripts are independently invokable and
# adding a shared module would force callers to set PYTHONPATH)
# ----------------------------------------------------------------------------


def get_client(project: str | None):
    try:
        return bigquery.Client(project=project)
    except DefaultCredentialsError as exc:
        raise DefaultCredentialsError(
            "No Application Default Credentials found. Run "
            "`gcloud auth application-default login` in the sandbox."
        ) from exc


def rows_to_dicts(results):
    rows = []
    for row in results:
        item = dict(row)
        for key, value in item.items():
            if hasattr(value, "isoformat"):
                item[key] = value.isoformat()
            elif isinstance(value, bytes):
                item[key] = value.decode("utf-8", errors="replace")
            elif isinstance(value, Decimal):
                item[key] = float(value)
        rows.append(item)
    return rows


def slugify(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return cleaned or fallback


def _str_or_none(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


# ----------------------------------------------------------------------------
# Search
# ----------------------------------------------------------------------------


def search_by_query(client, query: str, limit: int):
    lowered = query.strip().lower()
    wildcard = f"%{lowered}%"
    digits = re.sub(r"\D", "", query)
    digits_wildcard = f"%{digits}%" if digits else None

    sql = f"""
    SELECT {SEARCH_SELECT_COLS}
    FROM {TABLE}
    WHERE
      CAST(VId AS STRING) = @query
      OR LOWER(COALESCE(email, '')) LIKE @wildcard
      OR LOWER(COALESCE(company, '')) LIKE @wildcard
      OR LOWER(COALESCE(firstname, '')) LIKE @wildcard
      OR LOWER(COALESCE(lastname, '')) LIKE @wildcard
      OR LOWER(CONCAT(COALESCE(firstname, ''), ' ', COALESCE(lastname, ''))) LIKE @wildcard
      OR LOWER(COALESCE(palmstreet_username, '')) LIKE @wildcard
      OR LOWER(COALESCE(palmstreet_userid, '')) LIKE @wildcard
      OR LOWER(COALESCE(website, '')) LIKE @wildcard
      OR LOWER(COALESCE(social_media, '')) LIKE @wildcard
      OR LOWER(COALESCE(categories, '')) LIKE @wildcard
      OR LOWER(COALESCE(aloy_category, '')) LIKE @wildcard
      OR (@digits_wildcard IS NOT NULL AND REGEXP_REPLACE(COALESCE(phone, ''), r'[^0-9]', '') LIKE @digits_wildcard)
      OR (@digits_wildcard IS NOT NULL AND REGEXP_REPLACE(COALESCE(hs_calculated_phone_number, ''), r'[^0-9]', '') LIKE @digits_wildcard)
    ORDER BY
      CASE
        WHEN CAST(VId AS STRING) = @query THEN 0
        WHEN LOWER(COALESCE(email, '')) = @query THEN 1
        WHEN LOWER(COALESCE(palmstreet_userid, '')) = @query THEN 2
        WHEN LOWER(COALESCE(palmstreet_username, '')) = @query THEN 3
        WHEN LOWER(CONCAT(COALESCE(firstname, ''), ' ', COALESCE(lastname, ''))) = @query THEN 4
        ELSE 5
      END,
      app__date DESC,
      createdate DESC
    LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query", "STRING", lowered),
            bigquery.ScalarQueryParameter("wildcard", "STRING", wildcard),
            bigquery.ScalarQueryParameter("digits_wildcard", "STRING", digits_wildcard),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )
    return rows_to_dicts(client.query(sql, job_config=job_config).result())


def print_search_uids(rows):
    """Tab-separated, uid-first. Stdout for rows with a uid; stderr for those
    without (so the uid stream is clean for `| xargs`-style piping).
    """
    for row in rows:
        uid = _str_or_none(row.get("palmstreet_userid"))
        name = f"{row.get('firstname') or ''} {row.get('lastname') or ''}".strip() or "Unknown"
        category = row.get("aloy_category") or row.get("categories") or ""
        if uid:
            print(
                f"{uid}\t{name}\t{row.get('email') or ''}\t"
                f"{row.get('palmstreet_username') or ''}\t{category}\t"
                f"vid={row.get('VId')}\tapp_date={row.get('app__date') or ''}"
            )
        else:
            print(
                f"# no_uid\tVId={row.get('VId')}\t{name}\t{row.get('email') or ''}",
                file=sys.stderr,
            )


def default_output_path(args) -> Path:
    if args.output:
        return Path(args.output)
    return OUTPUT_DIR / f"seller_query_{slugify(args.query, 'query')}.json"


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Search HubSpot Contact rows in BigQuery → emit "
        "matching PalmStreet uids on stdout. After resolving a uid, invoke "
        "the seller-audit skill (or run skills/seller-audit/scripts/bq_query_seller.py --uid <uid> "
        "directly) for the per-seller audit.",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Free-form search string (email, name, username, vid, phone, "
        "URL fragment, category, etc.).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max search results.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Override the path for the raw rows JSON dump.",
    )
    parser.add_argument(
        "--project",
        help="Override the GCP project when using sandbox gcloud credentials.",
    )
    args = parser.parse_args()

    client = get_client(args.project)
    rows = search_by_query(client, args.query, args.limit)
    if not rows:
        print("No results found.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = default_output_path(args)
    with open(out_path, "w") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    print(f"# Found {len(rows)} record(s). Raw rows: {out_path}", file=sys.stderr)
    print_search_uids(rows)


if __name__ == "__main__":
    main()
