#!/usr/bin/env python3
"""
Query seller info from BigQuery (plantstory.hubspot.Contact).
Run this on your local machine where gcloud auth is configured.

Usage:
    python bq_query_seller.py --email "xxx@gmail.com"
    python bq_query_seller.py --vid 215124027166
    python bq_query_seller.py --userid "5rx1mjs3..."
"""

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

# Paths (script now lives inside the skill):
#   <project_root>/skills/seller-audit/scripts/bq_query_seller.py  ← this file
#   <project_root>/skills/seller-audit/assets/bq-reader-key.json    ← GCP key
#   <project_root>/outputs/                                         ← where JSONs go
_SCRIPT_DIR = Path(__file__).resolve().parent          # .../skills/seller-audit/scripts
_SKILL_DIR = _SCRIPT_DIR.parent                        # .../skills/seller-audit
_PROJECT_ROOT = _SKILL_DIR.parent.parent               # .../seller-audit (project root)

KEY_PATH = _SKILL_DIR / "assets" / "bq-reader-key.json"
OUTPUT_DIR = _PROJECT_ROOT / "outputs"
TABLE = "`plantstory.hubspot.Contact`"

# Audit-relevant whitelist. Keeps JSON small so the agent doesn't drown in
# marketing/automation fields. Every column below has been verified to exist
# in plantstory.hubspot.Contact.
FIELDS = [
    # Identity
    "VId",
    "firstname", "lastname", "company",
    "email", "phone", "hs_calculated_phone_number",
    # Online assets provided in the application
    "website", "social_media",
    "palmstreet_username", "palmstreet_userid",
    # Business claims
    "categories", "aloy_category",
    "inv__count__new_", "avg__plant_price", "price_range",
    "ppw_shipping_volume", "selling_experience",
    # Internal status
    "sales_stage", "approval_date", "rejection_reason",
    "metabase_status", "aloy_activation_pending",
    "hubspot_owner_id",
    "hs_object_source_label", "hs_latest_source",
    "self_reported_lead_source__typeform_",
    "recent_expo_name", "notes_last_contacted",
    # Timestamps (used for filtering / ordering in batch queries)
    "app__date", "createdate",
]
SELECT_COLS = ", ".join(FIELDS)


def get_client():
    if KEY_PATH.exists():
        creds = service_account.Credentials.from_service_account_file(str(KEY_PATH))
        return bigquery.Client(credentials=creds, project=creds.project_id)
    # fallback to application default credentials (gcloud auth)
    return bigquery.Client()


def query_by_email(client, email):
    q = f"""
    SELECT {SELECT_COLS}
    FROM {TABLE}
    WHERE LOWER(email) = LOWER(@email)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("email", "STRING", email)]
    )
    return client.query(q, job_config=job_config).result()


def query_by_vid(client, vid):
    q = f"""
    SELECT {SELECT_COLS}
    FROM {TABLE}
    WHERE VId = @vid
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("vid", "INT64", int(vid))]
    )
    return client.query(q, job_config=job_config).result()


def query_by_userid(client, userid):
    q = f"""
    SELECT {SELECT_COLS}
    FROM {TABLE}
    WHERE palmstreet_userid = @userid
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("userid", "STRING", userid)]
    )
    return client.query(q, job_config=job_config).result()


def rows_to_dicts(results):
    rows = []
    for row in results:
        d = dict(row)
        # convert non-serializable types
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif isinstance(v, bytes):
                d[k] = v.decode("utf-8", errors="replace")
            elif isinstance(v, Decimal):
                d[k] = float(v)
        rows.append(d)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Query seller info from BigQuery")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--email", help="Seller email address")
    group.add_argument("--vid", help="HubSpot VId")
    group.add_argument("--userid", help="PalmStreet user ID")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    args = parser.parse_args()

    client = get_client()

    if args.email:
        results = query_by_email(client, args.email)
        identifier = args.email.replace("@", "_at_")
    elif args.vid:
        results = query_by_vid(client, args.vid)
        identifier = args.vid
    else:
        results = query_by_userid(client, args.userid)
        identifier = args.userid

    rows = rows_to_dicts(results)

    if not rows:
        print(f"No results found.")
        sys.exit(1)

    print(f"Found {len(rows)} record(s).")

    # Save to JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output) if args.output else OUTPUT_DIR / f"seller_{identifier}.json"
    with open(out_path, "w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"Saved to {out_path}")

    # Print key fields summary
    for row in rows:
        print(f"\n--- {row.get('firstname', '')} {row.get('lastname', '')} ---")
        for key in ["email", "phone", "website", "social_media",
                     "palmstreet_username", "palmstreet_userid",
                     "categories", "aloy_category", "inv__count__new_",
                     "avg__plant_price", "selling_experience",
                     "sales_stage", "approval_date", "rejection_reason"]:
            if key in row and row[key]:
                print(f"  {key}: {row[key]}")


if __name__ == "__main__":
    main()
