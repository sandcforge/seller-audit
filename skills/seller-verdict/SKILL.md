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

Based on the `category.actual` field (not `category.claimed`), read Part B (Verdict Decision) of the relevant SOP:
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
- `business_claims` (user-provided data) — note whether investigation verified these

**Flexible tier adjustment:** When near a threshold boundary, adjust by ONE level based on quality signals. Document justification.

## Step 3: Assess Risk

Apply the SOP's risk assessment rules. Use:
- `investigation_summary.risk_flags` — primary risk input
- `investigation_summary.china_connection_signals`
- `platforms[].risks` — per-platform risk signals
- Category-specific risk criteria from the SOP

## Step 4: Look Up Verdict

Use the render_verdict.py script to apply the decision matrix and generate the report:

```bash
echo '{
  "handoff": <paste handoff YAML as JSON>,
  "assessment": {
    "tier": "<S|A|B|F>",
    "risk": "<HIGH|MEDIUM|LOW>",
    "category_used": "<plants|shiny|beauty|collectibles|general>",
    "tier_justification": "<why this tier>",
    "risk_justification": "<why this risk level>",
    "investigation_steps": [...],
    "special_notes": "<optional>",
    "hubspot_status_conflict": null
  }
}' | python skills/seller-verdict/scripts/render_verdict.py --input -
```

The script:
- Applies the correct category's decision matrix
- Handles special routing (ESCALATE_TO_MADDY, ESCALATE_TO_RAJ, etc.)
- Generates the Markdown report in the correct format
- Auto-generates review checklists for REVIEW verdicts
- Warns if the report exceeds 90 lines

If the script is unavailable, apply the decision matrix manually. The report format is specified in:
> `../seller-audit/references/output-format.md`

## Step 5: Cross-Check with HubSpot Status

If the handoff YAML shows `sales_stage: Approved` or `Rejected` in the seller data, compare your verdict. If they differ, add a note:
- "NOTE: This seller was previously [APPROVED/REJECTED] on [date], but this audit recommends [VERDICT] because [reason]."

## General Rules

1. **Total followers:** Sum across ALL platforms. Do not evaluate each in isolation.
2. **User-provided data:** If `business_claims.inventory_count` and `business_claims.average_price` are non-null, use them — but note whether investigation verified them.
3. **Category mismatch:** Use the ACTUAL category's SOP, not the claimed one. Flag this in the report.
4. **Collectibles:** NEVER reject outright. Downgrade all would-be REJECTs to REVIEW.
5. **raw_metrics_text sanity check:** Before finalizing tier, spot-check a few `raw_metrics_text` entries against their parsed metric values. If "1.5K" was parsed as 15000, fix it.

## Decision Shortcuts

For common patterns that speed up verdict, read:
> `../seller-audit/references/shortcuts.md`
