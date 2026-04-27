#!/usr/bin/env python3
"""Validate ``investigation.yaml`` against ``schema-investigation.md``.

This script is invoked by the seller-investigate subagent after it writes
``<work_dir>/investigation.yaml`` and BEFORE it returns control to the
orchestrator. The investigator must keep retrying (read errors → fix YAML →
re-validate) until validation passes or the per-attempt retry budget is
exhausted, at which point it must still return a *schema-compliant* YAML
(usually a near-empty shell with ``early_exit_reason`` set to
``"schema_validation_failed_after_<N>_retries"``).

The orchestrator does NOT re-validate. The investigator owns the schema —
that's the contract.

Usage:
    python skills/seller-audit/scripts/validate_investigation.py \\
        --file <work_dir>/investigation.yaml

Exit code:
    0 — validation passed (no errors)
    1 — validation failed (errors printed to stderr, one per line)
    2 — script-level error (file missing, YAML parse error, etc.)

Output (stderr):
    On failure, one line per error with the JSON-pointer-style path and a
    short message, e.g.:
        platforms[0].metrics.followers: must be int or null, got str ('1.5K')
        investigation_summary.total_platforms_checked: must equal len(platforms[]) (got 3, expected 5)
    On success: a single line ``✓ schema valid: <N> platforms``.

The schema is enforced in code (not from the .md) for two reasons:
    1. The .md is the human-readable contract; this script is the executable
       contract. They MUST agree — when you change one, change the other.
    2. .md → code parsing would force every CI run to re-derive the schema
       from prose, which is brittle. Code is cheap to read; one source of
       truth per artifact (.md for humans, .py for the validator).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, List, Tuple

import yaml


# ---------------------------------------------------------------------------
# Schema constants — keep in sync with
# skills/seller-audit/references/schema-investigation.md
# ---------------------------------------------------------------------------

VALID_PLATFORMS = {
    'instagram', 'whatnot', 'facebook', 'ebay', 'etsy',
    'poshmark', 'tiktok', 'mercari', 'website', 'collx', 'other',
}
VALID_ATTRIBUTIONS = {
    'provided_by_seller', 'constructed_from_username',
    'found_in_bio', 'found_via_websearch',
}
VALID_STATUSES = {'active', '404', 'login_blocked', 'private'}
VALID_ACCOUNT_TYPES = {'business', 'personal', 'marketplace', None}

# Per-platform required keys (with their type-or-null contracts).
# Tuple form: (key, allowed_types, allow_null)
# A `tuple` for allowed_types means "any of these"; `None` for allow_null means
# the field must be non-null.
PLATFORM_FIELDS: List[Tuple[str, tuple, bool]] = [
    ('platform', (str,), False),
    ('url', (str,), False),
    ('redirected_from', (str,), True),
    ('attribution', (str,), False),
    ('status', (str,), False),
    ('account_type', (str,), True),
    ('metrics', (dict,), False),
    ('bio', (str,), True),
    ('bio_links', (list,), False),
    ('categories_observed', (list,), False),
    ('badges', (list,), False),
    ('location', (str,), True),
    ('member_since', (str,), True),
    ('risks', (list,), False),
    ('raw_metrics_text', (str,), True),
]

METRICS_FIELDS: List[Tuple[str, tuple, bool]] = [
    ('followers', (int,), True),
    ('following', (int,), True),
    ('items_sold', (int,), True),
    ('items_listed', (int,), True),
    ('reviews_count', (int,), True),
    ('rating', (int, float), True),
    ('feedback_pct', (int, float), True),
    ('likes', (int,), True),
]

INVESTIGATION_SUMMARY_FIELDS: List[Tuple[str, tuple, bool]] = [
    ('total_platforms_checked', (int,), False),
    ('total_platforms_active', (int,), False),
    ('total_followers', (int,), True),
    ('total_items_sold', (int,), True),
    ('highest_rating', (int, float), True),
    ('actual_category', (str,), True),
    ('risk_flags', (list,), False),
    ('china_connection_signals', (list,), False),
    ('investigation_iterations', (int,), False),
    ('early_exit_reason', (str,), True),
    ('sop_applied', (str,), False),
    ('audit_timestamp', (str,), False),
]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_field(
    obj: Any,
    key: str,
    allowed_types: tuple,
    allow_null: bool,
    path: str,
    errors: List[str],
) -> None:
    """Validate a single field's presence and type at ``<path>.<key>``."""
    if not isinstance(obj, dict):
        errors.append(f'{path}: must be a mapping, got {type(obj).__name__}')
        return
    if key not in obj:
        errors.append(f'{path}.{key}: missing required field')
        return
    value = obj[key]
    if value is None:
        if not allow_null:
            type_names = ' or '.join(t.__name__ for t in allowed_types)
            errors.append(f'{path}.{key}: must be {type_names}, got null')
        return
    # bool is a subclass of int in Python — reject it where we expect a real int
    # to avoid `followers: True` slipping past the type check.
    if int in allowed_types and isinstance(value, bool):
        errors.append(
            f'{path}.{key}: must be int or null, got bool ({value!r})'
        )
        return
    if not isinstance(value, allowed_types):
        type_names = ' or '.join(t.__name__ for t in allowed_types)
        errors.append(
            f'{path}.{key}: must be {type_names} or null, got '
            f'{type(value).__name__} ({value!r})'
        )


def _validate_metrics(metrics: Any, path: str, errors: List[str]) -> None:
    if not isinstance(metrics, dict):
        errors.append(f'{path}: must be a mapping, got {type(metrics).__name__}')
        return
    for key, allowed_types, allow_null in METRICS_FIELDS:
        _check_field(metrics, key, allowed_types, allow_null, path, errors)


def _validate_platform(platform: Any, idx: int, errors: List[str]) -> None:
    path = f'platforms[{idx}]'
    if not isinstance(platform, dict):
        errors.append(f'{path}: must be a mapping, got {type(platform).__name__}')
        return
    for key, allowed_types, allow_null in PLATFORM_FIELDS:
        _check_field(platform, key, allowed_types, allow_null, path, errors)
    # Enum checks (only if the field is a string at all — type errors above
    # already flagged it otherwise).
    if isinstance(platform.get('platform'), str) and platform['platform'] not in VALID_PLATFORMS:
        errors.append(
            f"{path}.platform: must be one of {sorted(VALID_PLATFORMS)}, "
            f"got {platform['platform']!r}"
        )
    if isinstance(platform.get('attribution'), str) and platform['attribution'] not in VALID_ATTRIBUTIONS:
        errors.append(
            f"{path}.attribution: must be one of {sorted(VALID_ATTRIBUTIONS)}, "
            f"got {platform['attribution']!r}"
        )
    if isinstance(platform.get('status'), str) and platform['status'] not in VALID_STATUSES:
        errors.append(
            f"{path}.status: must be one of {sorted(VALID_STATUSES)}, "
            f"got {platform['status']!r}"
        )
    if 'account_type' in platform and platform['account_type'] not in VALID_ACCOUNT_TYPES:
        errors.append(
            f"{path}.account_type: must be one of "
            f"{sorted([v for v in VALID_ACCOUNT_TYPES if v])} or null, "
            f"got {platform['account_type']!r}"
        )
    # url must be a full https URL (the schema is explicit on this — bare
    # domains and http:// have produced bad audits before).
    url = platform.get('url')
    if isinstance(url, str) and not url.startswith('https://'):
        errors.append(f'{path}.url: must start with https://, got {url!r}')
    # Nested metrics block.
    if isinstance(platform.get('metrics'), dict):
        _validate_metrics(platform['metrics'], f'{path}.metrics', errors)


def _validate_seller(seller: Any, errors: List[str]) -> None:
    path = 'seller'
    if not isinstance(seller, dict):
        errors.append(f'{path}: must be a mapping, got {type(seller).__name__}')
        return
    uid = seller.get('palmstreet_userid')
    if not uid or not isinstance(uid, str):
        errors.append(
            f'{path}.palmstreet_userid: required non-empty string '
            f'(join key for the BQ refetch), got {uid!r}'
        )


def _validate_investigation_summary(
    summary: Any, platforms: list, errors: List[str]
) -> None:
    path = 'investigation_summary'
    if not isinstance(summary, dict):
        errors.append(f'{path}: must be a mapping, got {type(summary).__name__}')
        return
    for key, allowed_types, allow_null in INVESTIGATION_SUMMARY_FIELDS:
        _check_field(summary, key, allowed_types, allow_null, path, errors)
    # Cross-field consistency: total_platforms_checked must equal len(platforms[]).
    total_checked = summary.get('total_platforms_checked')
    if isinstance(total_checked, int) and isinstance(platforms, list):
        if total_checked != len(platforms):
            errors.append(
                f'{path}.total_platforms_checked: must equal len(platforms[]) '
                f'(got {total_checked}, expected {len(platforms)})'
            )
    # total_platforms_active must equal count of status=="active" entries.
    total_active = summary.get('total_platforms_active')
    if isinstance(total_active, int) and isinstance(platforms, list):
        observed_active = sum(
            1 for p in platforms
            if isinstance(p, dict) and p.get('status') == 'active'
        )
        if total_active != observed_active:
            errors.append(
                f'{path}.total_platforms_active: must equal count of '
                f'platforms[].status=="active" (got {total_active}, '
                f'expected {observed_active})'
            )
    # investigation_iterations bound: 1..5 inclusive (per loop-react.md).
    iters = summary.get('investigation_iterations')
    if isinstance(iters, int) and not (0 <= iters <= 5):
        errors.append(
            f'{path}.investigation_iterations: must be 0..5 inclusive, got {iters}'
        )


def validate(data: Any) -> List[str]:
    """Run all checks and return a list of error strings (empty == valid)."""
    errors: List[str] = []
    if not isinstance(data, dict):
        errors.append(f'<root>: must be a mapping, got {type(data).__name__}')
        return errors

    # Top-level required keys.
    for key in ('seller', 'platforms', 'investigation_summary'):
        if key not in data:
            errors.append(f'<root>.{key}: missing required top-level block')

    if 'seller' in data:
        _validate_seller(data['seller'], errors)

    platforms = data.get('platforms')
    if 'platforms' in data:
        if not isinstance(platforms, list):
            errors.append(
                f'platforms: must be a list, got {type(platforms).__name__}'
            )
            platforms = []
        else:
            for idx, platform in enumerate(platforms):
                _validate_platform(platform, idx, errors)

    if 'investigation_summary' in data:
        _validate_investigation_summary(
            data['investigation_summary'], platforms or [], errors
        )

    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Validate <work_dir>/investigation.yaml against '
        'schema-investigation.md. Run by the seller-investigate subagent '
        'after writing the file and before returning to the orchestrator.'
    )
    parser.add_argument(
        '--file',
        type=Path,
        required=True,
        help='Path to investigation.yaml',
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f'✗ file not found: {args.file}', file=sys.stderr)
        return 2

    try:
        data = yaml.safe_load(args.file.read_text(encoding='utf-8'))
    except yaml.YAMLError as e:
        print(f'✗ YAML parse error in {args.file}: {e}', file=sys.stderr)
        return 2

    errors = validate(data)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(
            f'✗ schema validation failed: {len(errors)} error(s)',
            file=sys.stderr,
        )
        return 1

    platforms = data.get('platforms') or []
    print(f'✓ schema valid: {len(platforms)} platform(s)', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
