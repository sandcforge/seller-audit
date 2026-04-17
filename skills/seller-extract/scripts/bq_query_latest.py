#!/usr/bin/env python3
"""Fetch the latest N applicants from BigQuery ordered by app__date desc."""
import json
import sys
from decimal import Decimal
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _SKILL_DIR.parent.parent
KEY_PATH = _SKILL_DIR / "assets" / "bq-reader-key.json"
TABLE = "`plantstory.hubspot.Contact`"

FIELDS = [
    "VId", "firstname", "lastname", "company",
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
SELECT_COLS = ", ".join(FIELDS)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else _PROJECT_ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    creds = service_account.Credentials.from_service_account_file(str(KEY_PATH))
    client = bigquery.Client(credentials=creds, project=creds.project_id)

    q = f"""
    SELECT {SELECT_COLS}
    FROM {TABLE}
    WHERE app__date IS NOT NULL
    ORDER BY app__date DESC
    LIMIT {n}
    """
    rows = []
    for row in client.query(q).result():
        d = dict(row)
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif isinstance(v, bytes):
                d[k] = v.decode("utf-8", errors="replace")
            elif isinstance(v, Decimal):
                d[k] = float(v)
        rows.append(d)

    manifest = []
    for idx, r in enumerate(rows, 1):
        name = f"{r.get('firstname') or ''} {r.get('lastname') or ''}".strip().replace(' ', '_').replace('/', '_') or 'Unknown'
        vid = r.get('VId')
        fname = f"{idx:02d}_{vid}_{name}.json"
        fpath = out_dir / fname
        with open(fpath, "w") as f:
            json.dump(r, f, indent=2, ensure_ascii=False)
        manifest.append({
            "idx": idx,
            "vid": vid,
            "name": f"{r.get('firstname') or ''} {r.get('lastname') or ''}".strip(),
            "email": r.get('email'),
            "category": r.get('aloy_category') or r.get('categories'),
            "app_date": r.get('app__date'),
            "file": fname,
        })
        print(f"[{idx}] VId={vid} | {manifest[-1]['name']} | {manifest[-1]['email']} | {manifest[-1]['category']} | app_date={manifest[-1]['app_date']}")

    with open(out_dir / "_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(rows)} applicants to {out_dir}")


if __name__ == "__main__":
    main()
