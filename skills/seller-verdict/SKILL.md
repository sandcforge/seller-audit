---
name: seller-verdict
description: "Issue a final APPROVE/REJECT/REVIEW verdict for a PalmStreet seller based on structured investigation data. This is the Verdict Agent component of the seller audit pipeline. Receives investigation YAML from seller-investigate, applies category-specific SOP rules, and produces a formatted Markdown report. Does NOT use Chrome or visit URLs. Typically invoked by the seller-audit orchestrator."
---

# Seller Verdict (Verdict Agent)

Receive structured investigation data, apply SOP verdict logic, and produce a formatted audit report.

## Role Boundaries

- **DO:** Read investigation YAML, apply your category SOP (`references/sop-{category}.md` — verdict decision rules), classify tier/risk, look up decision matrix, generate report
- **DO NOT:** Use Chrome, visit URLs, read seller-investigate's references (scrape-*.md, loop-react.md, sop-*.md investigation SOPs, url-normalization.md), or do any investigation

## Input (read by file path)

The orchestrator passes you a **work directory path** (e.g. `outputs/<uid>/<NN>/`). Read your inputs from disk:

- **`<work_dir>/applicant.yaml`** — Applicant Summary YAML produced by Step 1. Top-level keys: `seller`, `online_assets`, `business_claims`. Used for the category-mismatch check and as the source of identity / claimed numbers.
- **`<work_dir>/investigation.yaml`** — Observed-data investigation produced by Step 2 (seller-investigate). Schema in `../seller-audit/references/schema-investigation.md`. The investigator self-validates this file against the schema before returning, so you can trust the structural shape — focus on interpreting the content.

Use the `Read` tool to load both files. Verify `investigation.investigation_summary.sop_applied` matches the actual category before proceeding.

## Step 1: Load Category SOP (verdict decision rules)

Based on `investigation.investigation_summary.actual_category` (what was observed across storefronts — NOT the applicant's claim, which is fetched separately from BQ), read this skill's verdict SOP. Each file is scoped to verdict only — the matching investigation data points live in seller-investigate's references and are not your concern.
- Plants / Flowers / Gardening → `references/sop-plants.md`
- Jewelry / Coins / Crystals → `references/sop-shiny.md`
- Beauty / Makeup / Skincare → `references/sop-beauty.md`
- Collectibles / Trading Cards → `references/sop-collectibles.md`
- All other → `references/sop-general.md`

Confirm the seller's actual category matches the SOP you opened. If not, STOP and load the correct one.

## Step 2: Classify Tier

Apply the SOP's tier classification rules using metrics from the investigation YAML:
- `investigation_summary.total_followers` for follower-based tiers
- `investigation_summary.total_items_sold` for sales-based tiers
- Platform-specific metrics from `platforms[]` entries
- Applicant-claimed data (refetched from BQ at verdict time) — note whether investigation verified these

**Flexible tier adjustment:** When near a threshold boundary, adjust by ONE level based on quality signals. Document justification.

## Step 3: Assess Risk

Apply the SOP's risk assessment rules. Use:
- `investigation_summary.risk_flags` — primary risk input
- `investigation_summary.china_connection_signals`
- `platforms[].risks` — per-platform risk signals
- Category-specific risk criteria from the SOP

## Step 4: Render Report (MANDATORY — script path only)

**You MUST run `generate_report.py --work-dir <work_dir>`. Do NOT hand-write the Markdown report.**

This step has THREE equally required deliverables, all produced by one script call:
1. `<work_dir>/audit.md` — the Markdown report
2. An INSERT into the BigQuery table `plantstory.risk_control.seller_application_audit`
3. `outputs/<uid>/latest` symlink refreshed to point at this attempt + `<work_dir>/_meta.json` updated with `completed_at`, `last_completed_step: "verdict"`, and `verdict`

If you skip the script and write the `.md` yourself, all three side effects are silently lost and the audit is incomplete — even if the local file looks fine. There is no manual workaround for the BQ insert; only the script writes that row, and only the script refreshes the symlink.

### How to invoke

**Write your assessment to `<work_dir>/verdict.yaml`, then call the script with `--work-dir`.** The script reads `applicant.yaml` + `investigation.yaml` + `verdict.yaml` from the same directory automatically — your only output is `verdict.yaml`.

`verdict.yaml` top-level fields ARE the assessment itself — there is NO outer `assessment:` wrapper.

Step 1 — compose the assessment as a Python dict:
```python
assessment = {
    "verdict": "APPROVE",                # or REJECT / REVIEW — see Step 5 below
    "tier": "A",                          # S / A / B / F
    "risk": "LOW",                        # HIGH / MEDIUM / LOW
    "category_used": "general",           # plants / shiny / beauty / collectibles / general
    # Each justification field accepts EITHER a single string (rendered
    # as one bullet) OR a list of 1–3 strings (rendered as separate
    # bullets under the Conclusion heading). A list of 1–3 short bullets
    # reads best. Lists longer than 3 are truncated to 3. Keep each
    # bullet short and standalone (one fact / signal / threshold).
    "tier_justification": [
        "2,000 items sold with 5.0 rating across 185 reviews exceeds the >500-sold Professional threshold.",
        "<1d average ship time and consistent branding (Whatnot @jessnelson77 ↔ TikTok @fitlifejess) reinforce the tier.",
    ],
    "risk_justification": [
        "No fraud signals: matching email, cross-platform identity, authentic lifestyle content.",
        "No dropshipping or China-connection indicators.",
    ],
    "verdict_justification": [           # optional bullets under Final Verdict
        "A-tier seller with low risk → APPROVE under the general-category SOP.",
    ],
    "investigation_steps": [
        # Each step MUST use these exact keys. `body` / `description` etc.
        # will silently disappear from the rendered report.
        {
            "heading": "Whatnot Profile Verification",
            "url": "https://www.whatnot.com/user/jessnelson77",
            "status": "active",                  # active | 404 | login_blocked | private | evaluated
            "findings": "1–3 sentences describing what was observed on this page.",
            "signals": [
                "What this finding tells us (positive or negative)",
                "Multiple signals are fine"
            ]
        },
        # ... more steps
    ],
    "special_notes": "..."                # optional — actions / escalation / context
}
```

Step 2 — write `verdict.yaml` to the work directory using the `Write` tool (NOT heredocs / `echo` — quoting will fail):
```python
# Path: <work_dir>/verdict.yaml
# Content: yaml.safe_dump(assessment, sort_keys=False, allow_unicode=True)
# IMPORTANT: top-level fields are the assessment fields themselves —
# do NOT wrap in `{"assessment": assessment}`.
```

Step 3 — run the script:
```bash
python skills/seller-verdict/scripts/generate_report.py --work-dir <work_dir>
```

After the call, verify all THREE side effects in stderr:
- `✓ wrote .../audit.md`
- `✓ inserted row into plantstory.risk_control.seller_application_audit (vid=<vid>)`
- `✓ refreshed .../latest → <NN>`

If any confirmation is missing, the step is NOT complete — do not report success to the orchestrator. Re-run after fixing the underlying error (most often a missing/invalid `verdict`, a malformed `verdict.yaml`, or a missing `applicant.yaml`/`investigation.yaml` in the work directory).

The script:
- Reads `applicant.yaml` + `investigation.yaml` + `verdict.yaml` from the work directory
- Renders the Markdown report (Conclusion + Investigation Steps)
- Writes the .md to the work directory and inserts the BQ row
- Refreshes `outputs/<uid>/latest` symlink and updates `_meta.json` on success
- Warns if the report exceeds 90 lines
- Does NOT apply decision logic — that is your job

### Step 5: Common errors → fixes

The script raises `ValueError` on malformed input. Each error message is
self-contained, but here are the cases that have caused retry loops in the
past — fix in your assessment JSON, do not work around them:

| Error symptom | Cause | Fix |
|---|---|---|
| `assessment.verdict is required` | You forgot the field, or set it to `null`/`""` | Add `"verdict": "APPROVE"` (or REJECT / REVIEW). Pick exactly one. |
| `assessment.verdict must be one of ('APPROVE','REJECT','REVIEW'); got 'ESCALATE_TO_MADDY'` (or similar) | You used a routing tag as the verdict | The verdict is tri-state. Move the routing tag into `special_notes` (see table below). |
| `palmstreet_userid is required in investigation.seller` | The investigation is missing the join key | Add `seller.palmstreet_userid` to the investigation. The script uses it to derive the BQ row's `user_id` column and as the audit filename root. |
| `work_dir <path> is missing required artifacts` | One of `applicant.yaml`, `investigation.yaml`, or `verdict.yaml` is not in the work directory | Step 1 should have written `applicant.yaml`; Step 2 should have written `investigation.yaml`; you should have just written `verdict.yaml`. Re-check the work directory listing before running the script. |
| `bq_query_seller.py failed for uid=...` | uid doesn't exist in HubSpot, or BQ permissions issue | Verify the uid exists via `python scripts/bq_seller.py --query "<known email>"`. If correct, check ADC creds. |

**Routing tags belong in `special_notes`, not in `verdict`.** Common cases:

| If the SOP says... | `verdict` is... | `special_notes` says... |
|---|---|---|
| Tier S Plants → ESCALATE_TO_MADDY | `APPROVE` | `"Escalate to Maddy for VIP onboarding (White Glove)"` |
| Beauty VIP referral or Tier S → ESCALATE_TO_RAJ | `APPROVE` | `"Escalate to Raj (VIP/S-Tier)"` |
| Beauty pure influencer → FLAG_TO_JAMES | `REVIEW` | `"Flag to James — Affiliate candidate (no stock)"` |
| Collectibles Tier S → ESCALATE_TO_ME_S_TIER | `APPROVE` | `"Escalate to User (S Tier)"` |
| Collectibles non-US REVIEW → Forward to Kay | `REVIEW` | `"Forward to Kay (international)"` |
| Plants Tier A → CONTACT_SELLER tag | `APPROVE` | `"Tag: CONTACT_SELLER"` |
| Plants Tier B → ROOKIE_SELLER tag | `APPROVE` | `"Tag: ROOKIE_SELLER"` |
| Missing link / MISSING_INFO | `REVIEW` | `"Request More Info (Link) — Follow up applicant"` |

If you're unsure whether something is a verdict or a tag, ask: "is this one
of APPROVE/REJECT/REVIEW?" — if not, it's `special_notes` material.

**Escape hatches (rarely needed — the normal flow above does NOT use any of these):**
- `--vid <vid>` overrides the BQ insert's `vid` column. Defaults to `applicant.seller.hubspot_id`. Use only when you need to insert under a different vid (e.g. cleaning up a row that was originally inserted with a wrong vid).
- `--no-md` skips writing `<work_dir>/audit.md`. Use when you only want the BQ row, not the local markdown.
- `--no-bq` skips the INSERT into `plantstory.risk_control.seller_application_audit`. ONLY for dry runs explicitly requested by the user. Default audits MUST persist to BQ.

The report format is specified in `references/output-format.md` — that document is for reference only. Do NOT use it as a recipe to hand-write the report; always go through the script.

## General Rules

1. **Total followers:** Sum across ALL platforms. Do not evaluate each in isolation.
2. **User-provided data:** Applicant-claimed data (`inventory_count`, `average_price`, etc.) is read by `generate_report.py` from `<work_dir>/applicant.yaml` (the file written by Step 1 of the orchestrator). The investigation itself does NOT carry these fields.
3. **Category mismatch:** Compare `investigation.investigation_summary.actual_category` (what was observed) against the applicant's claimed category (refetched from BQ). Use the ACTUAL category's SOP, not the claimed one. Flag the mismatch in `special_notes`.
4. **Collectibles:** NEVER reject outright. Downgrade all would-be REJECTs to REVIEW.
5. **raw_metrics_text sanity check:** Before finalizing tier, spot-check a few `raw_metrics_text` entries against their parsed metric values. If "1.5K" was parsed as 15000, fix it.
6. **No hallucinated numbers.** Every quantitative claim in the report ("Audited N platforms", "M followers", "K items sold", etc.) must trace back to a specific field in the investigation YAML. Do NOT recompute counts from the investigator's prose narrative or `early_exit_reason`. In particular: "Audited N platforms with M active" must use `investigation_summary.total_platforms_checked` and `total_platforms_active` verbatim — nothing else. If those fields contradict the narrative, trust the fields and note the discrepancy in Special Notes.
7. **Null is not zero.** If `total_followers` or `total_items_sold` is `null`, report it as "not observed" or omit the claim — do not render as "0 followers" or "0 sales", which implies a negative signal that wasn't actually measured.
8. **Verdict lives in the Conclusion section, not as a final step.** The report is structured as Conclusion (Final Verdict / Special Notes / Quality Tier / Risk Level — in that numbered order) → Investigation Steps. Do NOT append a `Step N — Verdict: Apply [Category] SOP` row at the end of Investigation Steps — that pattern is deprecated. `generate_report.py` produces this layout automatically.
9. **UNABLE_TO_AUDIT signal.** If `investigation.investigation_summary.early_exit_reason` starts with the literal prefix `"unable_to_audit:"`, the investigation could not proceed (BQ + HubSpot UI both down, Chrome unavailable, zero usable input data, etc.). In that case: emit `verdict: REVIEW`, set `tier` and `risk` to `"N/A"`, and put the reason verbatim into `special_notes` along with `"Audit incomplete — manual follow-up required."`. Do NOT default to REJECT just because there are no platforms — the failure mode is data availability, not seller quality.

## Decision Shortcuts

For common patterns that speed up verdict, read:
> `references/shortcuts.md`
