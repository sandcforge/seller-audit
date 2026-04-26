---
name: seller-audit
description: "End-to-end PalmStreet seller audit for a SINGLE seller, given a PalmStreet uid (`palmstreet_userid`): extract applicant data from HubSpot, investigate their online footprint, and issue a final verdict. Use this skill whenever you need to audit, review, verify, or investigate ONE seller for PalmStreet. Triggers on: seller audit, review this seller, check this applicant, verify seller, investigate seller, seller due diligence, HubSpot seller review, audit this contact. Input is always a PalmStreet uid — if the user provides anything else (email, name, contact link, HubSpot VId), resolve it first via the standalone `scripts/bq_seller.py --query <term>` lookup tool documented in CLAUDE.md, THEN invoke this skill with the resulting uid. This skill orchestrates three component skills (seller-extract, seller-investigate, seller-verdict) to produce a final APPROVE/REJECT/REVIEW decision. Scope is one seller per invocation — for multiple sellers, invoke this skill once per seller."
---

# PalmStreet Seller Audit — Single-Seller Orchestrator

This skill coordinates the end-to-end audit pipeline for **one seller per invocation**, starting from a known `palmstreet_userid`. It dispatches work to three component skills and assembles the final result. Multi-seller workflows are out of scope — invoke this skill once per seller.

**Input contract:** the skill expects a PalmStreet uid. If the user gave anything else (email, name, contact link, HubSpot VId), the caller is responsible for resolving it first — see `scripts/bq_seller.py --query <term>` (project-root standalone tool, NOT a skill component) and the wiring note in CLAUDE.md.

## Prerequisite: Activate the sandbox first

Before running any script in this skill (extract, BQ queries, etc.), source the sandbox so `python`, `gcloud`, ADC, and project env vars are in place. This is idempotent — safe to run at the start of every session.

```bash
cd <repo-root> && source ./activate.sh
```

`source` only affects the shell that runs it, so each `Bash` tool call needs to either re-source it or chain the work onto the same command with `&&`. After activation, scripts run with no extra flags (e.g. `python skills/seller-audit/scripts/bq_query_seller.py --uid <uid>`). See the project `CLAUDE.md` for details on how `activate.sh` recovers from stale venvs across session resets.

## Pipeline Overview

```
1. EXTRACT  →  2. INVESTIGATE  →  3. VERDICT
(HubSpot data)   (Chrome visits)    (SOP + report)
```

Each stage is a separate skill with isolated context:

| Stage | Skill | Role | Key Output |
|-------|-------|------|------------|
| Extract | `seller-extract` | Pull applicant data from HubSpot (BQ or UI) | Applicant Summary YAML |
| Investigate | `seller-investigate` | Visit URLs in Chrome, extract structured data | Handoff YAML |
| Verdict | `seller-verdict` | Apply SOP rules, generate report | Markdown audit report |

## Pipeline Steps

### Step 1: Extract

Invoke seller-extract (or run inline if simple). With the uid already in hand:
```bash
python skills/seller-audit/scripts/bq_query_seller.py --uid "<palmstreet_userid>"
```
The script emits the Applicant Summary YAML on stdout (no file written). Capture it and paste straight into Step 2's prompt without rewriting. For the schema and rules behind the YAML see `references/extract-hubspot.md`.

If you don't have a uid (user gave email/name/contact link only), STOP — that resolution belongs upstream of this skill. Run `python scripts/bq_seller.py --query "<term>"` from the project root, take the uid from column 1 of stdout, and re-enter this skill. Do NOT try to make the audit work without a uid; `render_verdict.py` hard-errors at the end of the pipeline if `palmstreet_userid` is missing.

### Step 2: Investigate

Spawn a subagent with seller-investigate:
```
Task(subagent_type="general-purpose", prompt="""
Read skills/seller-investigate/SKILL.md and follow its instructions.

Applicant Summary YAML:
[paste applicant summary YAML here — schema in ../seller-audit/references/extract-hubspot.md]

Output: structured handoff YAML per ../seller-audit/references/handoff-schema.md
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

Handoff YAML (slim — observed data only, applicant data is refetched from BQ
by the script using handoff.seller.palmstreet_userid):
[paste handoff YAML here]

YOU decide the verdict. The script no longer applies any decision matrix.
Walk SOP Part B yourself and put one of APPROVE / REJECT / REVIEW into
`assessment.verdict`. Routing tags (ESCALATE_TO_MADDY, FLAG_TO_JAMES,
ESCALATE_TO_ME_S_TIER, "Forward to Kay", etc.) are NOT verdicts — write them
into `assessment.special_notes`.

MANDATORY: write the input JSON to `outputs/verdict_input_<palmstreet_userid>.json`
(use the Write tool — do NOT pipe via `echo | stdin`, quoting will fail), then:
  python skills/seller-verdict/scripts/render_verdict.py --input outputs/verdict_input_<uid>.json

Do NOT hand-write the Markdown. The script produces TWO required deliverables in one call:
  1. outputs/audit_<palmstreet_userid>.md
  2. an INSERT into plantstory.risk_control.seller_application_audit
Both are required. Skipping the script silently drops the BQ row.

Confirm both stderr lines appear before reporting success:
  ✓ wrote .../outputs/audit_<uid>.md
  ✓ inserted row into plantstory.risk_control.seller_application_audit (vid=<vid>)

Each `investigation_steps[]` entry must have `heading`, `url` (or "" if none), `status`,
`findings` (1–3 sentences of what was observed), and `signals` (bullet list of what each
finding tells us). Sparse entries (heading-only) render as "Status: unknown" placeholders
and waste the report's strongest narrative section — the human reviewer reads this to
audit your reasoning.
""")
```

The subagent will classify tier/risk, pick the tri-state verdict, build the assessment JSON (with `verdict` + optional `special_notes`), run `render_verdict.py`, and confirm both the markdown write and the BQ insert succeeded.

**Prompt discipline:**
- Do NOT tell the subagent to "save the report to outputs/" as the deliverable — that phrasing has produced subagents that hand-write the .md and skip the script (and therefore skip the BQ insert). Always frame the deliverable as "run render_verdict.py and verify both side effects."
- Do NOT mention `action_items` — that field is gone. Anything an onboarding team would have read from "Action Items" now lives in `special_notes`.

### Step 4: Deliver

The script has already written `outputs/audit_{palmstreet_userid}.md` and inserted the BQ row. Verify the file exists, then present it to the user. If either side effect is missing per the subagent's report, re-run Step 3 — do not paper over a failed BQ insert by treating the local markdown as the final deliverable.

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
