#!/usr/bin/env python3
"""
Audit Report Renderer

Reads three YAMLs from the per-attempt work directory:
  - applicant.yaml      (Step 1)
  - investigation.yaml  (Step 2)
  - verdict.yaml        (Step 3 — written by the verdict subagent; top-level
                          fields are the assessment itself: verdict, tier, risk,
                          investigation_steps, special_notes, *_justification)

Produces three deliverables in one call:
  1. <work_dir>/audit.md
  2. INSERT into plantstory.risk_control.seller_application_audit
  3. <work_dir>/_meta.json + outputs/<uid>/latest symlink updates

Supports all four category SOPs: General, Plants, Shiny, Beauty, Collectibles.
"""

import json
import os
import re
import subprocess
import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone


# Path to the upstream applicant-data lookup script. The investigation carries only
# the palmstreet_userid join key — render_report refetches the full applicant
# record (name / email / phone / online_assets / business_claims) from BigQuery
# at verdict time so the investigation stays slim and observed-data-only.
_REPO_ROOT_FROM_THIS_FILE = Path(__file__).resolve().parents[3]
BQ_QUERY_SELLER_SCRIPT = (
    _REPO_ROOT_FROM_THIS_FILE / 'skills' / 'seller-audit' / 'scripts' / 'bq_query_seller.py'
)


def fetch_applicant(uid: str) -> Dict[str, Any]:
    """Re-fetch the Applicant Summary YAML for a uid by invoking
    bq_query_seller.py. Returns the parsed dict (top-level keys: seller,
    online_assets, business_claims). Raises RuntimeError on lookup failure.

    The investigation schema deliberately does NOT carry these blocks; the
    palmstreet_userid join key on the investigation is the single source we use to
    re-derive applicant data here.
    """
    if not BQ_QUERY_SELLER_SCRIPT.exists():
        raise RuntimeError(
            f'bq_query_seller.py not found at {BQ_QUERY_SELLER_SCRIPT}. '
            f'Cannot refetch applicant data for uid={uid!r}.'
        )
    try:
        result = subprocess.run(
            [sys.executable, str(BQ_QUERY_SELLER_SCRIPT), '--uid', uid],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f'bq_query_seller.py failed for uid={uid!r}: '
            f'exit={e.returncode} stderr={e.stderr.strip()}'
        ) from e
    parsed = yaml.safe_load(result.stdout)
    if not isinstance(parsed, dict) or 'seller' not in parsed:
        raise RuntimeError(
            f'bq_query_seller.py returned unexpected output for uid={uid!r}: '
            f'{result.stdout[:200]!r}'
        )
    return parsed


# Decision Matrices (hardcoded from SOPs)

VALID_VERDICTS = ('APPROVE', 'REJECT', 'REVIEW')


def get_verdict(assessment: Dict[str, Any]) -> str:
    """Return the agent-supplied verdict, validated.

    The verdict agent decides — generate_report.py is pure rendering. This
    function only enforces the tri-state contract and surfaces a clean error
    if the assessment is malformed.

    Routing tags (ESCALATE_TO_MADDY, FLAG_TO_JAMES, ESCALATE_TO_ME_S_TIER, etc.)
    are NOT verdict values. The agent must put those in `assessment.special_notes`
    and supply one of APPROVE / REJECT / REVIEW here.
    """
    raw = assessment.get('verdict')
    if raw is None:
        raise ValueError(
            f'assessment.verdict is required — pick one of {VALID_VERDICTS}. '
            'Put any escalation tag (ESCALATE_TO_MADDY, FLAG_TO_JAMES, etc.) '
            'into assessment.special_notes.'
        )
    verdict = str(raw).strip().upper()
    if verdict not in VALID_VERDICTS:
        raise ValueError(
            f'assessment.verdict must be one of {VALID_VERDICTS}; got '
            f'{raw!r}. If you intended an escalation route, set '
            'assessment.verdict to APPROVE/REJECT/REVIEW and put the route '
            '(e.g. "Escalate to Maddy for VIP onboarding") in '
            'assessment.special_notes.'
        )
    return verdict


def render_investigation_steps(steps: List[Dict[str, Any]]) -> str:
    """Render investigation steps as markdown.

    The canonical step schema is {heading, url, status, findings, signals}.
    For robustness against agent drift we also accept a `body` alias for
    `findings` (a shape some subagents have produced) — without this fallback
    the entire step body silently disappears and the report renders
    `Status: unknown` placeholders only. New code should use `findings`.
    """
    if not steps:
        return ''

    output = '## Investigation Steps\n\n'

    for i, step in enumerate(steps, 1):
        heading = step.get('heading', f'Step {i}')
        url = step.get('url') or ''
        # findings is the canonical key; accept `body` as a fallback for
        # subagents that used the alternate shape.
        findings = step.get('findings') or step.get('body') or ''
        signals = step.get('signals') or []
        # If status is missing, default based on whether we have any content:
        # an empty step is genuinely "unknown"; a step with findings/url is
        # reasonably "active" unless the agent says otherwise.
        status = step.get('status')
        if not status:
            status = 'active' if (findings or url) else 'unknown'

        output += f'**Step {i} — {heading}**\n'

        if url:
            output += f'URL: `{url}`\n'

        output += f'Status: `{status}`\n'

        if findings:
            output += f'\n{findings}\n'

        if signals:
            output += '\n'
            for signal in signals:
                output += f'- {signal}\n'

        output += '\n'

    return output


def _normalize_bullets(value: Any, max_bullets: int = 3) -> List[str]:
    """Normalize a justification field into a list of 1–3 bullet strings.

    Accepts either:
      - a list of strings (preferred): each item becomes its own bullet
      - a single string: returned as a one-element list

    Empty / whitespace-only entries are dropped. Result is capped at
    max_bullets to keep the Conclusion section terse — long-form context
    belongs in special_notes or Investigation Steps, not stacked here.
    """
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, (list, tuple)):
        out: List[str] = []
        for item in value:
            if item is None:
                continue
            s = str(item).strip()
            if s:
                out.append(s)
        return out[:max_bullets]
    # Unknown type — coerce to string as last resort.
    s = str(value).strip()
    return [s] if s else []


def render_conclusion_section(assessment: Dict[str, Any], investigation: Dict[str, Any]) -> str:
    """Render the top-level Conclusion section.

    Layout:
      1. Final Verdict (from assessment.verdict — APPROVE/REJECT/REVIEW)
         + 1–3 bullets summarizing the audit
      2. Special Notes (from assessment.special_notes — onboarding actions,
         escalation routes, REVIEW checklists, context). May be empty.
      3. Quality Tier + 1–3 bullets of tier justification
      4. Risk Level + 1–3 bullets of risk justification

    The three justification fields (verdict_justification, tier_justification,
    risk_justification) accept EITHER a single string (rendered as one bullet,
    backwards compatible) OR a list of 1–3 strings (each rendered as its own
    bullet). Lists are capped at 3 entries.
    """
    verdict = get_verdict(assessment)
    tier = assessment.get('tier', 'F')
    risk = assessment.get('risk', 'HIGH')
    category = assessment.get('category_used', 'general')

    tier_bullets = _normalize_bullets(assessment.get('tier_justification'))
    risk_bullets = _normalize_bullets(assessment.get('risk_justification'))
    verdict_bullets = _normalize_bullets(assessment.get('verdict_justification'))

    # Bullets under "Final Verdict" — prefer explicit verdict_justification,
    # otherwise lean on the risk justification (it usually drives the call),
    # falling back to tier justification.
    headline_bullets = verdict_bullets or risk_bullets or tier_bullets

    output = '## Conclusion\n\n'

    # 1. Final Verdict
    output += f'1. **Final Verdict: {verdict}** _(Category: {category.title()})_\n'
    for bullet in headline_bullets:
        output += f'   - {bullet}\n'
    output += '\n'

    # 2. Special Notes — single field carrying onboarding actions, escalation
    # routes (e.g. "Escalate to Maddy for VIP onboarding"), REVIEW checklists,
    # or any context the agent wants to surface. Replaces the old Action Items
    # section.
    special_notes = (assessment.get('special_notes') or '').strip()
    output += '2. **Special Notes:**\n'
    if special_notes:
        output += f'   - {special_notes}\n'
    else:
        output += '   - _None_\n'
    output += '\n'

    # 3. Quality Tier
    output += f'3. **Quality Tier: {tier}**\n'
    for bullet in tier_bullets:
        output += f'   - {bullet}\n'
    output += '\n'

    # 4. Risk Level
    output += f'4. **Risk Level: {risk}**\n'
    for bullet in risk_bullets:
        output += f'   - {bullet}\n'
    output += '\n'

    return output


def render_report(input_data: Dict[str, Any]) -> str:
    """Render complete markdown report."""
    investigation = input_data.get('investigation', {})
    assessment = input_data.get('assessment', {})

    investigation_seller = investigation.get('seller', {}) or {}
    # PalmStreet user id is the join key for the applicant refetch and the
    # primary seller identifier in the local filename. Required — no fallback.
    uid = investigation_seller.get('palmstreet_userid')
    if not uid:
        raise ValueError(
            'palmstreet_userid is required in investigation.seller — '
            'update investigation.yaml to include it.'
        )

    # Resolve applicant data: prefer caller-provided block, otherwise refetch
    # from BigQuery. Identity fields (name/email/phone/online_assets/business_claims)
    # live exclusively in the applicant payload, never in the investigation.
    applicant = input_data.get('applicant')
    if applicant is None:
        applicant = fetch_applicant(uid)
        # Stash the fetched applicant so downstream callers (build_row) reuse
        # it without a second BQ round-trip.
        input_data['applicant'] = applicant

    # Section 1: Conclusion (verdict, special notes, tier, risk)
    output = render_conclusion_section(assessment, investigation)

    output += '---\n\n'

    # Section 2: Investigation Steps (chronological narrative)
    investigation_steps = assessment.get('investigation_steps', [])
    output += render_investigation_steps(investigation_steps)

    # NOTE: special_notes is rendered inside the Conclusion section (item #2).
    # No second copy at the report tail — that duplicated content under the
    # old Action Items + trailing Special Notes layout.

    return output


# ---------------------------------------------------------------------------
# Persistence helpers: write Markdown to outputs/ and INSERT a row into BQ.
# Both are on by default; main() exposes --no-md / --no-bq to skip them.
# ---------------------------------------------------------------------------

# BQ target (matches plantstory.risk_control.seller_application_audit, 17 cols)
BQ_PROJECT = 'plantstory'
BQ_TABLE_FQN = 'plantstory.risk_control.seller_application_audit'


def _repo_root() -> Path:
    """Resolve the seller-audit repo root.

    The script lives at <repo>/skills/seller-verdict/scripts/generate_report.py,
    so three parents up from this file is the repo root regardless of cwd.
    """
    return Path(__file__).resolve().parents[3]


def _classify_step(step: Dict[str, Any]) -> str:
    """Classify an investigation step into search / parse / browse / other.

    Heuristic: heading keywords + presence of URL.
    Used to populate the BQ action-count columns.
    """
    heading = (step.get('heading') or '').lower()
    url = step.get('url') or ''

    if 'search' in heading or 'google' in heading or 'websearch' in heading:
        return 'search'
    if 'parse' in heading or 'extract' in heading or 'analyze' in heading:
        return 'parse'
    if url or 'visit' in heading or 'browse' in heading or 'load' in heading:
        return 'browse'
    return 'other'


def _flatten_applicant_data(applicant: Dict[str, Any]) -> Dict[str, str]:
    """Build the flat ``applicant_data`` dict written to BigQuery.

    The BQ ``applicant_data`` column is consumed by downstream systems that
    expect a flat, application-form-shaped payload (Typeform-ish field names,
    all values as strings, "" for missing).

    Source: the Applicant Summary YAML refetched from BigQuery via
    bq_query_seller.py. Top-level keys: seller / online_assets / business_claims.

    Mapping (applicant source → applicant_data field):
      seller.name (split on first space) → first_name / last_name
      seller.email                       → email
      seller.phone                       → phone
      seller.hubspot_id                  → hubspot (HubSpot Contact VId, stringified)
      business_claims.category           → products (applicant's claim)
      business_claims.inventory_count    → inventory_size
      business_claims.selling_experience → experience_years
      business_claims.referred_by        → referred_by (already coalesced upstream
                                           by bq_query_seller.py: prefer Contact.referred_by,
                                           fall back to Contact.referring_friend)
      online_assets.website              → business_website
      online_assets.social_media         → social_url
      [not captured upstream today]      → social_followers (emit "")

    Notes:
    - Empty values are emitted as "" (not None) to match the consumer's shape.
    - Numbers are stringified (inventory_size: "45", not 45).
    - ``palmstreet_userid`` is intentionally NOT included here — it lives in
      its own BQ column (``user_id``) and in ``full_data``.
    """
    seller = applicant.get('seller', {}) or {}
    business_claims = applicant.get('business_claims', {}) or {}
    online_assets = applicant.get('online_assets', {}) or {}

    name = (seller.get('name') or '').strip()
    if name:
        first, _, last = name.partition(' ')
    else:
        first, last = '', ''

    def _s(v: Any) -> str:
        """None / null → "" ; everything else → str(v)."""
        return '' if v is None else str(v)

    return {
        'first_name': _s(first),
        'last_name': _s(last),
        'email': _s(seller.get('email')),
        'phone': _s(seller.get('phone')),
        'hubspot': _s(seller.get('hubspot_id')),
        'business_website': _s(online_assets.get('website')),
        'social_url': _s(online_assets.get('social_media')),
        # social_followers stays "" until the upstream form starts capturing
        # it — platforms[].metrics.followers is *observed*, not *claimed*,
        # so it can't substitute here.
        'social_followers': '',
        'referred_by': _s(business_claims.get('referred_by')),
        'products': _s(business_claims.get('category')),
        'inventory_size': _s(business_claims.get('inventory_count')),
        'experience_years': _s(business_claims.get('selling_experience')),
    }


def _summarize(
    report_md: str,
    max_chars: int = 600,
    assessment: Optional[Dict[str, Any]] = None,
    investigation: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the BQ ``context_summary`` blurb.

    Preferred path (when called with assessment+investigation): synthesize a 1-2
    sentence summary from structured fields — verdict, platform counts, and
    the agent's tier_justification / verdict_justification. This replaces the
    old behavior of scraping a `> [summary]` blockquote from the rendered
    markdown, which was removed when the header table + summary quote came
    out of the report layout.

    Fallback (when called positionally with just report_md): match an
    optional leading blockquote, otherwise return the first ~max_chars. Kept
    for back-compat with any older callers.
    """
    if assessment is not None:
        verdict = get_verdict(assessment)
        inv = (investigation or {}).get('investigation_summary') if investigation else None
        platforms_checked = (inv or {}).get('total_platforms_checked')
        active_platforms = (inv or {}).get('total_platforms_active')
        parts: List[str] = []
        if platforms_checked is not None and active_platforms is not None:
            parts.append(
                f'Audited {platforms_checked} platform'
                f'{"s" if platforms_checked != 1 else ""} '
                f'with {active_platforms} active.'
            )
        parts.append(f'Verdict: **{verdict}**.')
        # Pull the most informative justification into the BQ context_summary.
        # Each *_justification field may be a string or a list — _normalize_bullets
        # handles both. Join multi-bullet lists into a single sentence-style blob.
        for key in ('verdict_justification', 'tier_justification', 'risk_justification'):
            bullets = _normalize_bullets(assessment.get(key))
            if bullets:
                parts.append(' '.join(bullets))
                break
        return ' '.join(parts)[:max_chars]

    m = re.search(r'^>\s*(.+?)(?:\n\n|---)', report_md, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()[:max_chars]
    return report_md[:max_chars].strip()


def build_row(
    input_data: Dict[str, Any],
    report_md: str,
    vid_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble a row matching the seller_application_audit BQ schema."""
    investigation = input_data.get('investigation', {}) or {}
    assessment = input_data.get('assessment', {}) or {}
    investigation_seller = investigation.get('seller', {}) or {}

    # PalmStreet uid → user_id column. The investigation's seller block carries ONLY
    # palmstreet_userid (the join key); all other applicant fields come from
    # the refetched applicant payload below.
    uid = investigation_seller.get('palmstreet_userid')
    if not uid:
        raise ValueError(
            'palmstreet_userid is required in investigation.seller — '
            'update investigation.yaml to include it.'
        )

    # Applicant data is refetched from BigQuery in render_report and stashed on
    # input_data; if a caller invoked build_row directly without going through
    # render_report, refetch here.
    applicant = input_data.get('applicant')
    if applicant is None:
        applicant = fetch_applicant(uid)
        input_data['applicant'] = applicant
    applicant_seller = applicant.get('seller', {}) or {}

    vid = vid_override or applicant_seller.get('hubspot_id') or ''
    if not vid:
        raise ValueError('vid is required (applicant.seller.hubspot_id missing)')

    verdict = get_verdict(assessment)
    steps = assessment.get('investigation_steps', []) or []

    # Classify steps for the action-count columns.
    counts = {'search': 0, 'parse': 0, 'browse': 0, 'other': 0}
    failed: List[Dict[str, Any]] = []
    for step in steps:
        counts[_classify_step(step)] += 1
        status = (step.get('status') or '').lower()
        # Treat anything that isn't an obvious success as "failed" for the
        # failed_actions JSON column. Keep the entry small — heading + status.
        if status and status not in ('active', 'success', 'ok', '200'):
            failed.append({
                'heading': step.get('heading'),
                'url': step.get('url'),
                'status': step.get('status'),
            })

    # full_data captures everything the verdict had access to: the slim
    # observed-data investigation, the refetched applicant block, and the agent's
    # assessment. This is the canonical record for downstream consumers.
    full_data = {
        'investigation': investigation,
        'applicant': applicant,
        'assessment': assessment,
    }

    return {
        'vid': str(vid),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'verdict': verdict,
        'quality_tier': assessment.get('tier'),
        'risk_level': assessment.get('risk'),
        'md_report': report_md,
        'total_actions': len(steps),
        # JSON columns: insert_rows_json wants the value pre-serialized as a
        # JSON string for STRING-typed JSON columns in legacy tables. Modern
        # JSON-typed columns accept native dicts/lists. We serialize to be
        # safe across both — BigQuery will round-trip it.
        'failed_actions': json.dumps(failed),
        'search_actions': counts['search'],
        'parse_actions': counts['parse'],
        'browse_actions': counts['browse'],
        'other_actions': counts['other'],
        'applicant_data': json.dumps(_flatten_applicant_data(applicant)),
        'full_data': json.dumps(full_data),
        'context_summary': _summarize(report_md, assessment=assessment, investigation=investigation),
        'user_id': uid,
        # NOTE: the `note` BQ column is reserved for human-entered annotations
        # and is intentionally NOT written by this script. Do not add it back —
        # special_notes from the assessment already lives in md_report and
        # full_data. Auto-populating `note` would clobber manual edits.
    }


def write_md(out_path: Path, report_md: str) -> Path:
    """Write the rendered report to ``<work_dir>/audit.md`` (overwrite)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding='utf-8')
    return out_path


def _update_latest_symlink(work_dir: Path) -> Path:
    """Atomically point ``outputs/<uid>/latest`` at the current attempt.

    ``work_dir`` is ``outputs/<uid>/<NN>``. We write a relative symlink so the
    ``outputs/`` tree is portable. Writes go through a tempfile + ``os.replace``
    for atomicity (``os.replace`` swaps the symlink in one syscall).

    Returns the symlink path.
    """
    parent = work_dir.parent  # outputs/<uid>
    target = work_dir.name    # e.g. "00" — relative, not absolute
    final = parent / 'latest'
    tmp = parent / f'.latest.{os.getpid()}'
    # Clean up any stale tmp from a prior crashed run.
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    os.symlink(target, tmp)
    os.replace(tmp, final)  # atomic swap
    return final


def _update_meta(work_dir: Path, *, last_completed_step: str, verdict: Optional[str]) -> None:
    """Update ``<work_dir>/_meta.json`` after a successful step.

    Best-effort: a missing or unreadable _meta.json is logged but does not
    fail the audit. The file was created by ``allocate_attempt.py``; if it's
    gone, the work directory was constructed by hand or _meta got deleted —
    rare enough that we don't fight for it.
    """
    meta_path = work_dir / '_meta.json'
    try:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(
            f'⚠️  could not update {meta_path}: {e} '
            f'(continuing — meta is bookkeeping only)',
            file=sys.stderr,
        )
        return
    meta['last_completed_step'] = last_completed_step
    meta['verdict'] = verdict
    meta['completed_at'] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')


def write_bq(row: Dict[str, Any]) -> None:
    """INSERT one row into plantstory.risk_control.seller_application_audit.

    Append-only: same vid may produce multiple rows over time, distinguished
    by created_at. On insert error, dumps the row to outputs/ as a backup
    and re-raises.
    """
    try:
        from google.cloud import bigquery  # lazy import — only needed if writing
    except ImportError as e:
        raise RuntimeError(
            'google-cloud-bigquery not installed; run `source ./activate.sh` '
            'or pass --no-bq to skip BQ write'
        ) from e

    client = bigquery.Client(project=BQ_PROJECT)
    errors = client.insert_rows_json(BQ_TABLE_FQN, [row])
    if errors:
        # Persist the row locally so we don't lose the audit on a transient
        # schema/permission error.
        backup = _repo_root() / 'outputs' / f'audit_{row["vid"]}.bq.json'
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(json.dumps(row, indent=2, default=str), encoding='utf-8')
        raise RuntimeError(f'BQ insert failed: {errors} (row backed up to {backup})')


def _load_work_dir_inputs(work_dir: Path) -> Dict[str, Any]:
    """Read the three YAMLs that drive the report from a per-attempt work directory.

    Expected layout (created by allocate_attempt.py + Steps 1–3 of the
    seller-audit pipeline):

        <work_dir>/applicant.yaml        # Step 1 output (BQ → YAML)
        <work_dir>/investigation.yaml    # Step 2 output (investigate; self-validated)
        <work_dir>/verdict.yaml          # Step 3 input authored by the verdict
                                         # subagent — top-level fields ARE the
                                         # assessment itself (verdict, tier, risk,
                                         # *_justification, investigation_steps,
                                         # special_notes).

    Returns a dict with top-level keys ``applicant``, ``investigation``,
    ``assessment`` for downstream rendering.
    """
    applicant_path = work_dir / 'applicant.yaml'
    investigation_path = work_dir / 'investigation.yaml'
    verdict_path = work_dir / 'verdict.yaml'

    missing = [
        p.name for p in (applicant_path, investigation_path, verdict_path)
        if not p.exists()
    ]
    if missing:
        raise RuntimeError(
            f'work_dir {work_dir} is missing required artifacts: {missing}. '
            f'Expected applicant.yaml (Step 1), investigation.yaml (Step 2), and '
            f'verdict.yaml (Step 3).'
        )

    applicant = yaml.safe_load(applicant_path.read_text(encoding='utf-8'))
    investigation = yaml.safe_load(investigation_path.read_text(encoding='utf-8'))
    verdict = yaml.safe_load(verdict_path.read_text(encoding='utf-8'))

    if not isinstance(verdict, dict):
        raise RuntimeError(
            f'{verdict_path}: top-level must be a YAML mapping with the '
            f'assessment fields (verdict, tier, risk, ...). Got '
            f'{type(verdict).__name__}.'
        )

    return {
        'applicant': applicant,
        'investigation': investigation,
        'assessment': verdict,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Render the audit report from a per-attempt work directory. '
        'Reads applicant.yaml + investigation.yaml + verdict.yaml, writes '
        'audit.md, INSERTs a row into BigQuery, refreshes the outputs/<uid>/latest '
        'symlink, and updates _meta.json — all three side effects are required '
        'for a successful audit. Use --no-md / --no-bq to skip pieces during '
        'local debugging.'
    )
    parser.add_argument(
        '--work-dir',
        type=Path,
        required=True,
        help='Per-attempt work directory (e.g. outputs/<uid>/<NN>). The script '
        'reads applicant.yaml + investigation.yaml + verdict.yaml from this '
        'directory, writes audit.md to this directory, refreshes the '
        'outputs/<uid>/latest symlink, and updates _meta.json on success.',
    )
    parser.add_argument('--no-md', action='store_true', help='Skip writing audit.md')
    parser.add_argument('--no-bq', action='store_true', help=f'Skip INSERT into {BQ_TABLE_FQN}')
    parser.add_argument('--vid', help='Override vid (defaults to applicant.seller.hubspot_id)')

    args = parser.parse_args()

    work_dir = args.work_dir.resolve()
    data = _load_work_dir_inputs(work_dir)

    report = render_report(data)
    print(report)

    # Check length
    line_count = len(report.split('\n'))
    if line_count > 90:
        print(f'\n⚠️ Warning: Report exceeds 90 lines ({line_count} lines)', file=sys.stderr)

    # Side effects: md file + BQ insert. Both default-on.
    needs_row = not (args.no_md and args.no_bq)
    if needs_row:
        try:
            row = build_row(data, report, vid_override=args.vid)
        except ValueError as e:
            print(f'⚠️  Skipping md/bq writes: {e}', file=sys.stderr)
            return

        if not args.no_md:
            md_path = write_md(work_dir / 'audit.md', report)
            print(f'✓ wrote {md_path}', file=sys.stderr)

        if not args.no_bq:
            try:
                write_bq(row)
                print(f'✓ inserted row into {BQ_TABLE_FQN} (vid={row["vid"]})', file=sys.stderr)
            except Exception as e:
                print(f'✗ BQ insert failed: {e}', file=sys.stderr)
                sys.exit(2)

        # Refresh latest symlink + meta only on full success. We reach this
        # point only when the requested side effects (md / BQ) all succeeded
        # — so updating _meta to "verdict completed" is honest.
        symlink_path = _update_latest_symlink(work_dir)
        print(f'✓ refreshed {symlink_path} → {work_dir.name}', file=sys.stderr)
        _update_meta(
            work_dir,
            last_completed_step='verdict',
            verdict=row['verdict'],
        )


if __name__ == '__main__':
    main()
