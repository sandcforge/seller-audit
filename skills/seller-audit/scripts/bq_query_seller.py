#!/usr/bin/env python3
"""Unified seller query tool for BigQuery (plantstory.hubspot.Contact).

Modes:
1. Search mode: provide a free-form query string and return matching VId rows.
2. Detail mode: provide a VId and return the full whitelisted seller record.
"""

import argparse
import json
import re
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

DETAIL_FIELDS = [
    "VId",
    "firstname", "lastname", "company",
    "email", "phone", "hs_calculated_phone_number",
    "website", "social_media",
    "palmstreet_username", "palmstreet_userid",
    "categories", "aloy_category",
    "inv__count__new_", "avg__plant_price", "price_range",
    "ppw_shipping_volume", "selling_experience",
    "sales_stage", "approval_date", "rejection_reason",
    "metabase_status", "aloy_activation_pending",
    "hubspot_owner_id",
    "hs_object_source_label", "hs_latest_source",
    "self_reported_lead_source__typeform_",
    "recent_expo_name", "notes_last_contacted",
    "app__date", "createdate",
]
DETAIL_SELECT_COLS = ", ".join(DETAIL_FIELDS)

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
    "sales_stage",
    "app__date",
    "createdate",
]
SEARCH_SELECT_COLS = ", ".join(SEARCH_FIELDS)


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


def query_by_vid(client, vid: str):
    sql = f"""
    SELECT {DETAIL_SELECT_COLS}
    FROM {TABLE}
    WHERE VId = @vid
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("vid", "INT64", int(vid))]
    )
    return rows_to_dicts(client.query(sql, job_config=job_config).result())


def print_search_results(rows):
    for row in rows:
        name = f"{row.get('firstname') or ''} {row.get('lastname') or ''}".strip() or "Unknown"
        category = row.get("aloy_category") or row.get("categories") or ""
        print(
            f"VId={row.get('VId')} | {name} | {row.get('email') or ''} | "
            f"{row.get('palmstreet_username') or ''} | {category} | "
            f"{row.get('sales_stage') or ''} | app_date={row.get('app__date') or ''}"
        )


def print_detail_result(rows):
    for row in rows:
        print(f"\n--- {row.get('firstname', '')} {row.get('lastname', '')} ---")
        for key in [
            "email",
            "phone",
            "website",
            "social_media",
            "palmstreet_username",
            "palmstreet_userid",
            "categories",
            "aloy_category",
            "inv__count__new_",
            "avg__plant_price",
            "selling_experience",
            "sales_stage",
            "approval_date",
            "rejection_reason",
        ]:
            if row.get(key):
                print(f"  {key}: {row[key]}")


def default_output_path(args) -> Path:
    if args.output:
        return Path(args.output)
    if args.query:
        return OUTPUT_DIR / f"seller_query_{slugify(args.query, 'query')}.json"
    return OUTPUT_DIR / f"seller_{args.vid}.json"


def main():
    parser = argparse.ArgumentParser(description="Unified seller query tool")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--query", help="Free-form search string. Returns matching VId rows.")
    mode_group.add_argument("--vid", help="HubSpot VId. Returns the full seller record.")
    parser.add_argument("--limit", type=int, default=20, help="Max search results for --query mode.")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument(
        "--project",
        help="Override the GCP project when using sandbox gcloud credentials.",
    )
    args = parser.parse_args()

    client = get_client(args.project)

    if args.query:
        rows = search_by_query(client, args.query, args.limit)
    else:
        rows = query_by_vid(client, args.vid)

    if not rows:
        print("No results found.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = default_output_path(args)
    with open(out_path, "w") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)

    print(f"Found {len(rows)} record(s).")
    print(f"Saved to {out_path}")

    if args.query:
        print_search_results(rows)
    else:
        print_detail_result(rows)


if __name__ == "__main__":
    main()
