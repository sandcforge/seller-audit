#!/usr/bin/env python3
"""Pull a single HubSpot Contact by PalmStreet uid → emit Applicant Summary YAML.

The output YAML (per `skills/seller-audit/references/extract-hubspot.md`,
section "Output: Applicant Summary YAML") is written to **stdout only** —
nothing is persisted to disk. The orchestrator captures stdout and feeds it
straight into the seller-investigate Task prompt; no intermediate file is
required.

For free-form search (resolving an email/name/username/VId to a PalmStreet
uid), use the standalone lookup tool at `scripts/bq_seller.py --query "<term>"`
(in the project-root scripts/ directory, NOT this skill). The previous
`--query` and `--vid` modes on this script were removed.
"""

import argparse
import re
import sys
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path

import yaml

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery

TABLE = "`plantstory.hubspot.Contact`"

# Whitelist of audit-relevant columns. Do NOT change to SELECT *: Contact has
# 400+ columns and the extra marketing/automation fields bloat the result
# without helping the audit.
#
# Every column listed below either populates a field in the Applicant Summary
# YAML or is needed for query plumbing (currently just `app__date` and
# `createdate` for the dup-row ORDER BY in query_by_uid). HubSpot internal
# status columns (sales_stage, approval_date, rejection_reason, contact_owner,
# record sources, etc.) used to be selected and emitted under an
# `internal_status` block — they were dropped because verdict has no consumer.
DETAIL_FIELDS = [
    "VId",
    "firstname", "lastname", "company",
    "email", "phone", "hs_calculated_phone_number",
    "website", "social_media",
    "palmstreet_username", "palmstreet_userid",
    "categories", "aloy_category",
    "inv__count__new_", "avg__plant_price", "price_range",
    "ppw_shipping_volume", "selling_experience",
    "referred_by", "referring_friend",
    "app__date", "createdate",  # plumbing only — used by query_by_uid ORDER BY
]
DETAIL_SELECT_COLS = ", ".join(DETAIL_FIELDS)


# ----------------------------------------------------------------------------
# Helpers
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


def _str_or_none(value) -> str | None:
    """Return value as str if non-empty, else None. Empty strings → None."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _int_or_none(value) -> int | None:
    """Coerce to int; return None for null/empty/unparseable."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))  # tolerate "200.0" stored as string
    except (ValueError, TypeError):
        return None


def _float_or_none(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _normalize_multi_category(value: str | None) -> str | None:
    """Convert a multi-category string into the schema's ' / ' form.

    Both `aloy_category` and `categories` columns can carry multiple values:
    - aloy_category uses semicolons: 'collectible_toy;disney_loungefly'
    - categories sometimes uses semicolons ('Plant;Crystal'), sometimes
      commas as free text ('Toys, Cards, Coins, Memorabilia')

    extract-hubspot.md Rule 4: join multi-category claims with ' / ' so
    investigate's category-mismatch check sees the full claim.
    """
    s = _str_or_none(value)
    if s is None:
        return None
    parts = [p.strip() for p in re.split(r"[;,]", s) if p.strip()]
    return " / ".join(parts) if parts else None


def _coalesce_referrer(row: dict) -> str | None:
    """COALESCE(referred_by, referring_friend) per
    extract-hubspot.md Rule 6. Prefer the newer `referred_by`; fall back to
    the older `referring_friend` only when `referred_by` is null/empty.
    """
    primary = _str_or_none(row.get("referred_by"))
    if primary:
        return primary
    return _str_or_none(row.get("referring_friend"))


def _category_claimed(row: dict) -> str | None:
    """Prefer `aloy_category` if set, else fall back to Typeform `categories`,
    per extract-hubspot.md mapping table. Both columns can carry multi-value
    strings — normalize via `_normalize_multi_category` so the output always
    matches the ' / ' schema rule regardless of which source we used.
    """
    aloy = _normalize_multi_category(row.get("aloy_category"))
    if aloy:
        return aloy
    return _normalize_multi_category(row.get("categories"))


def _full_name(row: dict) -> str:
    first = _str_or_none(row.get("firstname")) or ""
    last = _str_or_none(row.get("lastname")) or ""
    return f"{first} {last}".strip()


def row_to_applicant_summary(row: dict) -> dict:
    """Map a BQ Contact row → Applicant Summary YAML dict.

    Schema source of truth: skills/seller-audit/references/extract-hubspot.md
    (section "Output: Applicant Summary YAML"). Field-level rules:
    - Every field present (None for unknown — yaml.safe_dump renders that as
      `null`).
    - Numbers are int/float, not strings.
    - URLs are NOT auto-prefixed with https:// here — the schema requires it,
      but we don't risk corrupting a malformed URL silently. LLM should
      verify on read; investigate's normalize_urls.py also enforces it.
    - phone_area_code_location is left null: this script doesn't carry an
      area-code → city/region table. LLM can enrich downstream.
    """
    summary = OrderedDict()
    summary["seller"] = OrderedDict([
        ("name", _full_name(row)),
        ("company", _str_or_none(row.get("company"))),
        ("hubspot_id", str(row.get("VId")) if row.get("VId") is not None else None),
        ("palmstreet_userid", _str_or_none(row.get("palmstreet_userid"))),
        ("palmstreet_username", _str_or_none(row.get("palmstreet_username"))),
        ("email", _str_or_none(row.get("email"))),
        ("phone",
            _str_or_none(row.get("phone"))
            or _str_or_none(row.get("hs_calculated_phone_number"))),
        # Not derivable from this script — left null for LLM enrichment.
        ("phone_area_code_location", None),
    ])
    summary["online_assets"] = OrderedDict([
        ("website", _str_or_none(row.get("website"))),
        ("social_media", _str_or_none(row.get("social_media"))),
    ])
    summary["business_claims"] = OrderedDict([
        ("category", _category_claimed(row)),
        ("inventory_count", _int_or_none(row.get("inv__count__new_"))),
        ("average_price", _float_or_none(row.get("avg__plant_price"))),
        ("price_range", _str_or_none(row.get("price_range"))),
        ("shipping_volume", _str_or_none(row.get("ppw_shipping_volume"))),
        ("selling_experience", _str_or_none(row.get("selling_experience"))),
        ("referred_by", _coalesce_referrer(row)),
    ])
    # NOTE: `internal_status` (sales_stage, approval_date, rejection_reason,
    # contact_owner, record_source, etc.) is intentionally NOT emitted —
    # verdict has no consumer for those fields. The BQ columns are still
    # SELECTed (see DETAIL_FIELDS) because we use app__date/createdate for
    # dup-row tiebreaking, but they don't reach the YAML. If you need them
    # for ad-hoc inspection, use `bq_seller.py --query` to dump raw rows.
    return summary


def _ordered_dict_representer(dumper, data):
    """Make yaml.safe_dump preserve OrderedDict insertion order so the rendered
    YAML matches the schema's declared field order (much easier to eyeball).
    """
    return dumper.represent_mapping(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items()
    )


yaml.SafeDumper.add_representer(OrderedDict, _ordered_dict_representer)


def dump_yaml(summary: dict) -> str:
    return yaml.safe_dump(
        summary,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10_000,  # avoid line-wrapping long URLs
    )


# ----------------------------------------------------------------------------
# Query
# ----------------------------------------------------------------------------


def query_by_uid(client, uid: str):
    """Look up a contact by PalmStreet uid. ~80 uids in BQ map to multiple
    Contact rows; pick the most recent application (then fall back to the
    most recent createdate) and warn on stderr.
    """
    sql = f"""
    SELECT {DETAIL_SELECT_COLS}
    FROM {TABLE}
    WHERE palmstreet_userid = @uid
    ORDER BY app__date DESC NULLS LAST, createdate DESC NULLS LAST
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("uid", "STRING", uid)]
    )
    return rows_to_dicts(client.query(sql, job_config=job_config).result())


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Render the Applicant Summary YAML for a single seller "
        "looked up by PalmStreet uid. YAML is written to stdout only "
        "(no file persisted). For free-form search, use bq_seller.py.",
    )
    parser.add_argument(
        "--uid",
        required=True,
        help="PalmStreet uid (palmstreet_userid).",
    )
    parser.add_argument(
        "--project",
        help="Override the GCP project when using sandbox gcloud credentials.",
    )
    args = parser.parse_args()

    client = get_client(args.project)
    rows = query_by_uid(client, args.uid)
    if not rows:
        print(
            f"No HubSpot Contact found with palmstreet_userid={args.uid!r}. "
            f"If you only have an email/name/VId, search first with "
            f"`bq_seller.py --query <term>`.",
            file=sys.stderr,
        )
        sys.exit(1)
    if len(rows) > 1:
        print(
            f"# WARNING: {len(rows)} HubSpot Contact rows share "
            f"palmstreet_userid={args.uid!r}. Using the most recent "
            f"(VId={rows[0].get('VId')}, app__date={rows[0].get('app__date')}). "
            f"Other VIds: "
            f"{[r.get('VId') for r in rows[1:]]}",
            file=sys.stderr,
        )

    summary = row_to_applicant_summary(rows[0])
    sys.stdout.write(dump_yaml(summary))


if __name__ == "__main__":
    main()
