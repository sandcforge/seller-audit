---
name: seller-verdict
description: "Issue a final APPROVE/REJECT/REVIEW verdict for a PalmStreet seller based on structured investigation data. This is the Verdict Agent component of the seller audit pipeline. Receives handoff YAML from seller-investigate, applies category-specific SOP rules, and produces a formatted Markdown report. Does NOT use Chrome or visit URLs. Typically invoked by the seller-audit orchestrator."
---

# Seller Verdict (Verdict Agent)

Receive structured investigation data, apply SOP verdict logic, and produce a formatted audit report.

## Role Boundaries

- **DO:** Read handoff YAML, apply SOP Part B, classify tier/risk, look up decision matrix, generate report
- **DO NOT:** Use Chrome, visit URLs, read scraping guides, read SOP Part A, or do any investigation

## Input

Structured YAML from seller-investigate, following the schema in:
> `../seller-audit/references/handoff-schema.md`

Verify `sop_applied` matches the actual category before proceeding.

## Step 1: Load Category SOP (Part B Only)

Based on `handoff.investigation_summary.actual_category` (what was observed across storefronts — NOT the applicant's claim, which is fetched separately from BQ), read Part B (Verdict Decision) of the relevant SOP:
- Plants / Flowers / Gardening → `../seller-audit/references/sop-plants.md` Part B
- Jewelry / Coins / Crystals → `../seller-audit/references/sop-shiny.md` Part B
- Beauty / Makeup / Skincare → `../seller-audit/references/sop-beauty.md` Part B
- Collectibles / Trading Cards → `../seller-audit/references/sop-collectibles.md` Part B
- All other → `../seller-audit/references/sop-general.md` Part B

**Do NOT read Part A** — that was for the Scraper Agent.

If you are reading a Part B file, confirm the seller's actual category matches. If not, STOP and load the correct SOP.

## Step 2: Classify Tier

Apply the SOP's tier classification rules using metrics from the handoff YAML:
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

## Step 4: Render Verdict (MANDATORY — script path only)

**You MUST run `render_verdict.py`. Do NOT hand-write the Markdown report.**

This step has two equally required deliverables:
1. The Markdown report at `outputs/audit_<palmstreet_userid>.md`
2. An INSERT into the BigQuery table `plantstory.risk_control.seller_application_audit`

`render_verdict.py` does **both** in one call. If you skip the script and write the `.md` yourself, the BQ row is silently lost and the audit is incomplete — even if the local file looks fine. There is no manual workaround for the BQ insert; only the script writes that row.

### How to invoke (use `--input <path>`, NOT `echo | stdin`)

**Always write the input to a file first, then pass the path.** Piping JSON
through `echo '...' | python ... --input -` looks convenient but breaks on
quoting — single-quotes inside the JSON, multi-line values, and nested arrays
all turn into shell parsing failures. Reaching for stdin is the #1 reason
this step gets retried.

```python
# 1. Compose the input as a Python dict and serialize it cleanly:
import json
input_data = {
    "handoff": {...},      # paste the slim handoff dict
    "assessment": {
        "verdict": "APPROVE",                # or REJECT / REVIEW — see Step 5 below
        "tier": "A",                          # S / A / B / F
        "risk": "LOW",                        # HIGH / MEDIUM / LOW
        "category_used": "general",           # plants / shiny / beauty / collectibles / general
        # Each justification field accepts EITHER a single string (legacy —
        # rendered as one bullet) OR a list of 1–3 strings (preferred —
        # rendered as separate bullets under the Conclusion heading). Lists
        # longer than 3 are truncated to 3. Keep each bullet short and
        # standalone (one fact / signal / threshold).
        "tier_justification": [
            "2,000 items sold with 5.0 rating across 185 reviews exceeds the >500-sold Professional threshold.",
            "<1d average ship time and consistent branding (Whatnot @jessnelson77 ↔ TikTok @fitlifejess) reinforce the tier.",
        ],
        "risk_justification": [
            "No fraud signals: matching email, cross-platform identity, authentic lifestyle content.",
            "No dropshipping or China-connection indicators.",
        ],
        "verdict_justification": [           # optional bullets under Final Verdict
            "A-tier seller with low risk → APPROVE under SOP-General Part B.",
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
}

# 2. Write to outputs/ (use the Write tool, not heredocs):
input_path = f"outputs/verdict_input_{palmstreet_userid}.json"
# Write tool → input_path with json.dumps(input_data, indent=2)

# 3. Then run:
#    python skills/seller-verdict/scripts/render_verdict.py --input outputs/verdict_input_<uid>.json
```

After the call, verify both side effects in stderr:
- `✓ wrote .../outputs/audit_<uid>.md`
- `✓ inserted row into plantstory.risk_control.seller_application_audit (vid=<vid>)`

If either confirmation is missing, the step is NOT complete — do not report success to the orchestrator. Re-run after fixing the underlying error (most often a missing `palmstreet_userid`, a missing/invalid `verdict`, or a malformed `assessment` payload).

The script:
- Renders the Markdown report (Conclusion + Investigation Steps)
- Writes the .md and inserts the BQ row
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
| `palmstreet_userid is required in handoff.seller` | The handoff is missing the join key | Add `seller.palmstreet_userid` to the handoff. The script needs it to refetch the applicant from BQ. |
| `bq_query_seller.py failed for uid=...` | uid doesn't exist in HubSpot or BQ permissions issue | Verify the uid exists via `python scripts/bq_seller.py --query "<known email>"`. If correct, check ADC creds. |

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
- `--no-md` skips writing `outputs/audit_<palmstreet_userid>.md`. Use when you only want the BQ row, not the local markdown.
- `--no-bq` skips the INSERT into `plantstory.risk_control.seller_application_audit`. ONLY for dry runs explicitly requested by the user. Default audits MUST persist to BQ.

The report format is specified in `../seller-audit/references/output-format.md` — that document is for reference only. Do NOT use it as a recipe to hand-write the report; always go through the script.

## General Rules

1. **Total followers:** Sum across ALL platforms. Do not evaluate each in isolation.
2. **User-provided data:** Applicant-claimed data (`inventory_count`, `average_price`, etc.) is fetched from BigQuery at verdict time — `render_verdict.py` resolves it from the Applicant Summary YAML keyed off `handoff.seller.palmstreet_userid`. The handoff itself does NOT carry these fields.
3. **Category mismatch:** Compare `handoff.investigation_summary.actual_category` (what was observed) against the applicant's claimed category (refetched from BQ). Use the ACTUAL category's SOP, not the claimed one. Flag the mismatch in `special_notes`.
4. **Collectibles:** NEVER reject outright. Downgrade all would-be REJECTs to REVIEW.
5. **raw_metrics_text sanity check:** Before finalizing tier, spot-check a few `raw_metrics_text` entries against their parsed metric values. If "1.5K" was parsed as 15000, fix it.
6. **No hallucinated numbers.** Every quantitative claim in the report ("Audited N platforms", "M followers", "K items sold", etc.) must trace back to a specific field in the handoff YAML. Do NOT recompute counts from the investigator's prose narrative or `early_exit_reason`. In particular: "Audited N platforms with M active" must use `investigation_summary.total_platforms_checked` and `total_platforms_active` verbatim — nothing else. If those fields contradict the narrative, trust the fields and note the discrepancy in Special Notes.
7. **Null is not zero.** If `total_followers` or `total_items_sold` is `null`, report it as "not observed" or omit the claim — do not render as "0 followers" or "0 sales", which implies a negative signal that wasn't actually measured.
8. **Verdict lives in the Conclusion section, not as a final step.** The report is structured as Conclusion (Final Verdict / Special Notes / Quality Tier / Risk Level — in that numbered order) → Investigation Steps. Do NOT append a `Step N — Verdict: Apply [Category] SOP` row at the end of Investigation Steps — that pattern is deprecated. `render_verdict.py` produces this layout automatically.

## Decision Shortcuts

For common patterns that speed up verdict, read:
> `../seller-audit/references/shortcuts.md`
