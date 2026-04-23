#!/usr/bin/env python3
"""Return the N most recent seller applications (VId + name) from BigQuery.

Ordered by app__date DESC, then createdate DESC as tie-breaker. Defaults to 3.
"""

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _SKILL_DIR.parent.parent

OUTPUT_DIR = _PROJECT_ROOT / "outputs"
TABLE = "`plantstory.hubspot.Contact`"

FIELDS = [
    "VId",
    "firstname",
    "lastname",
    "company",
    "email",
    "palmstreet_username",
    "aloy_category",
    "categories",
    "sales_stage",
    "app__date",
    "createdate",
]
SELECT_COLS = ", ".join(FIELDS)


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


def query_latest(client, limit: int):
    sql = f"""
    SELECT {SELECT_COLS}
    FROM {TABLE}
    WHERE app__date IS NOT NULL
    ORDER BY app__date DESC, createdate DESC
    LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    )
    return rows_to_dicts(client.query(sql, job_config=job_config).result())


def print_rows(rows):
    for i, row in enumerate(rows, 1):
        name = f"{row.get('firstname') or ''} {row.get('lastname') or ''}".strip() or "Unknown"
        company = row.get("company") or ""
        category = row.get("aloy_category") or row.get("categories") or ""
        print(
            f"{i}. VId={row.get('VId')} | {name}"
            + (f" ({company})" if company else "")
            + f" | {row.get('email') or ''} | {category} | "
            f"stage={row.get('sales_stage') or ''} | app_date={row.get('app__date') or ''}"
        )


def main():
    parser = argparse.ArgumentParser(description="Latest seller applications")
    parser.add_argument("--limit", "-n", type=int, default=3, help="How many rows (default 3)")
    parser.add_argument("--output", "-o", help="Optional JSON output path")
    parser.add_argument("--project", help="Override GCP project")
    args = parser.parse_args()

    client = get_client(args.project)
    rows = query_latest(client, args.limit)

    if not rows:
        print("No results found.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output) if args.output else OUTPUT_DIR / f"latest_applications_{args.limit}.json"
    with open(out_path, "w") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)

    print(f"Found {len(rows)} record(s). Saved to {out_path}\n")
    print_rows(rows)


if __name__ == "__main__":
    main()
