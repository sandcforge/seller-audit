---
name: seller-audit
description: "End-to-end PalmStreet seller audit: extract applicant data from HubSpot, investigate their online footprint, and issue a final verdict. Use this skill whenever you need to audit, review, verify, or investigate a seller for PalmStreet. Triggers on: seller audit, review this seller, check this applicant, verify seller, investigate seller, seller due diligence, HubSpot seller review, audit this contact. Also trigger when the user provides a HubSpot contact URL or seller name and wants an assessment. This skill orchestrates three component skills (seller-extract, seller-investigate, seller-verdict) to produce a final APPROVE/REJECT/REVIEW decision."
---

# PalmStreet Seller Audit — Orchestrator

This skill coordinates the end-to-end seller audit pipeline. It dispatches work to three component skills and assembles the final result.

## Prerequisite: Activate the sandbox first

Before running any script in this skill (extract, BQ queries, etc.), source the sandbox so `python`, `gcloud`, ADC, and project env vars are in place. This is idempotent — safe to run at the start of every session.

```bash
cd <repo-root> && source ./activate.sh
```

`source` only affects the shell that runs it, so each `Bash` tool call needs to either re-source it or chain the work onto the same command with `&&`. After activation, scripts run with no extra flags (e.g. `python skills/seller-audit/scripts/bq_latest_applications.py --limit 1`). See the project `CLAUDE.md` for details on how `activate.sh` recovers from stale venvs across session resets.

## Pipeline Overview

```
1. EXTRACT  →  2. INVESTIGATE  →  3. VERDICT
(HubSpot data)   (Chrome visits)    (SOP + report)
```

Each stage is a separate skill with isolated context:

| Stage | Skill | Role | Key Output |
|-------|-------|------|------------|
| Extract | `seller-extract` | Pull applicant data from HubSpot (BQ or UI) | Applicant Summary |
| Investigate | `seller-investigate` | Visit URLs in Chrome, extract structured data | Handoff YAML |
| Verdict | `seller-verdict` | Apply SOP rules, generate report | Markdown audit report |

## Single Seller Audit

### Step 1: Extract

Invoke seller-extract (or run inline if simple):
```bash
python skills/seller-audit/scripts/bq_query_seller.py --query "<email>"
```
Read the output JSON and produce the Applicant Summary. For full field mapping, see `references/extract-hubspot.md`.

### Step 2: Investigate

Spawn a subagent with seller-investigate:
```
Task(subagent_type="general-purpose", prompt="""
Read skills/seller-investigate/SKILL.md and follow its instructions.

Applicant Summary:
[paste applicant summary here]

Output: structured YAML per ../seller-audit/references/handoff-schema.md
""")
```

**Prompt discipline:** Do NOT add tool-usage instructions, fallback permissions, or workarounds to this prompt. `seller-investigate` owns its own tool discipline (including the mandatory Chrome rule). Language like "if Chrome is unavailable, use web_fetch as fallback" makes subagents skip Chrome by default and produces invalid audits. If the subagent reports a tool problem, verify it yourself before accepting — do not pre-authorize fallbacks.

The subagent will:
- Normalize and verify URLs (via scripts)
- Visit all provided URLs in Chrome
- Follow secondary links and run Google Search fallback if needed
- Output structured handoff YAML

### Step 3: Verdict

Spawn a subagent with seller-verdict:
```
Task(subagent_type="general-purpose", prompt="""
Read skills/seller-verdict/SKILL.md and follow its instructions.

Handoff YAML:
[paste handoff YAML here]

Output: Markdown audit report per ../seller-audit/references/output-format.md
""")
```

The subagent will classify tier/risk, look up the decision matrix, and render the final report.

### Step 4: Deliver

Save the Markdown report to `outputs/audit_{seller_name}.md` and present it to the user.

## Batch Audit (5+ Sellers)

### Step 1: Batch Extract

```bash
python skills/seller-audit/scripts/bq_query_seller.py --query "<name or email>" --limit 10
```

Then audit the returned VIds one by one with `--vid`.

### Step 2: Pre-Screen

Before launching investigations, check for cross-seller patterns:
- **Phone clustering:** Nearly identical phone numbers (differing by 1–4 digits, same area code) suggest household connections. Flag for identity verification.
- **Email domain clustering:** Multiple applicants from same non-public domain.
- **Duplicate usernames:** Same PalmStreet username across records.

### Step 3: Parallel Investigation

Launch one seller-investigate subagent per seller:
```
For each seller in manifest:
    Task(subagent_type="general-purpose", prompt="""
    Read skills/seller-investigate/SKILL.md...
    Applicant Summary: [seller data]
    Output: handoff YAML
    """)
```

Collect all handoff YAMLs when subagents complete.

### Step 4: Batch Verdicts

Apply seller-verdict to each handoff YAML. This can be done in parallel or sequentially.

### Step 5: Compile

Produce individual Markdown reports (one per seller). Do NOT produce executive summary tables or batch statistics — only individual seller sections following the template in `references/output-format.md`.

## Reference Files Index

All shared reference files live in `references/` within this skill. Component skills reference them via `../seller-audit/references/`.

### Core
- `extract-hubspot.md` — Field mapping and extraction methods
- `handoff-schema.md` — Scraper→Verdict data contract
- `output-format.md` — Final report template and structural constraints
- `loop-react.md` — Adaptive investigation loop (ReAct pattern)
- `url-normalization.md` — Platform-specific URL cleanup rules
- `shortcuts.md` — Decision shortcuts from 20+ real audits

### Category SOPs (Part A = investigation, Part B = verdict)
- `sop-plants.md` — Plants / Flowers / Gardening
- `sop-shiny.md` — Jewelry / Coins / Crystals
- `sop-beauty.md` — Beauty / Makeup / Skincare
- `sop-collectibles.md` — Collectibles / Trading Cards (NEVER reject)
- `sop-general.md` — All other categories

### Platform Scraping Guides
- `scrape-instagram.md` (35%) · `scrape-whatnot.md` (23%) · `scrape-facebook.md` (20%)
- `scrape-tiktok.md` (5%) · `scrape-etsy.md` (4.5%) · `scrape-poshmark.md` (4%)
- `scrape-ebay.md` (3%) · `scrape-mercari.md` (1.6%) · `scrape-collx.md` (<1%)

### Cross-Cutting Protocols
- `edge-cases.md` — single reference containing all four protocols:
  - `#china-connection` — China Connection risk signals
  - `#category-mismatch` — Category mismatch handling
  - `#name-ambiguity` — Name disambiguation (Gold/Silver/Bronze)
  - `#tool-failure-recovery` — Recovery from 404s, login walls, tool errors
