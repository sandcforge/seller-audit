---
name: seller-audit
description: "End-to-end PalmStreet seller audit for a SINGLE seller, given a PalmStreet uid (`palmstreet_userid`): extract applicant data from HubSpot, investigate their online footprint, and issue a final verdict. Use this skill whenever you need to audit, review, verify, or investigate ONE seller for PalmStreet. Triggers on: seller audit, review this seller, check this applicant, verify seller, investigate seller, seller due diligence, HubSpot seller review, audit this contact. Input is always a PalmStreet uid — if the user provides anything else (email, name, contact link, HubSpot VId), resolve it first via the standalone `scripts/bq_seller.py --query <term>` lookup tool documented in CLAUDE.md, THEN invoke this skill with the resulting uid. This skill runs extraction inline (a deterministic BQ script call) and dispatches investigation and verdict to two subagents (seller-investigate, seller-verdict) to produce a final APPROVE/REJECT/REVIEW decision. Scope is one seller per invocation — for multiple sellers, invoke this skill once per seller."
---

# PalmStreet Seller Audit — Single-Seller Orchestrator

This skill coordinates the end-to-end audit pipeline for **one seller per invocation**, starting from a known `palmstreet_userid`. Extraction runs inline as a BQ script call; investigation and verdict each dispatch to an isolated subagent; the orchestrator then assembles the final result. Multi-seller workflows are out of scope — invoke this skill once per seller.

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

Extract runs inline in the orchestrator (it's a deterministic BQ script call — no reasoning, no Chrome, no context blow-up to justify a subagent). Investigate and Verdict run as isolated subagents:

| Stage | Mode | Role | Key Output |
|-------|------|------|------------|
| Extract | Inline (orchestrator) | Run `bq_query_seller.py --uid` and capture stdout | Applicant Summary YAML |
| Investigate | Subagent (`seller-investigate`) | Visit URLs in Chrome via ReAct loop, extract structured data | Handoff YAML |
| Verdict | Subagent (`seller-verdict`) | Apply SOP rules, run render script, produce report + BQ row | Markdown audit report |

**Why these isolation choices:** Extract is pure IO — inlining it saves a subagent roundtrip with zero context cost. Investigate must be isolated because the ReAct loop fills context with Chrome screenshots and page text; only the slim investigation YAML should reach the orchestrator. Verdict must be isolated for capability scoping (no Chrome, no scrape guides, no investigation SOP, no ReAct loop spec) — the physical absence of those references and tools is a stronger guarantee than prompt discipline.

## Per-audit work directory

Every audit runs in its own work directory under `outputs/<uid>/<NN>/`, where `NN` is a zero-padded attempt number (00, 01, ...). All artifacts (applicant YAML, investigation YAML, verdict YAML, audit Markdown) live here. Re-audits of the same uid get a fresh `NN` — old attempts are preserved for debug. The `outputs/<uid>/latest` symlink is refreshed by `generate_report.py` only on a successful BQ insert, so it always points at the most recent *completed* audit (not failed attempts).

Files inside the work directory:

```
outputs/<uid>/<NN>/
├── _meta.json          — created by allocate_attempt.py; updated by generate_report.py on success
├── applicant.yaml      — Step 1 output (BQ → Applicant Summary YAML)
├── investigation.yaml  — Step 2 output (investigate subagent; self-validated against schema before write)
├── verdict.yaml        — Step 3 input  (verdict subagent composes the assessment; top-level fields ARE the assessment)
└── audit.md            — Step 3 output (generate_report.py)
```

Subagents read inputs from this directory by path (using the `Read` tool) and write outputs by path (using the `Write` tool). **No YAML or large JSON is pasted into prompts** — only the work directory path is passed. This keeps the orchestrator's context lean across multi-audit sessions and gives every audit a clean, complete artifact trail.

## Pipeline Steps

### Step 0: Allocate the work directory

Before anything else, allocate this audit's `outputs/<uid>/<NN>/` directory:

```bash
WORK_DIR=$(python skills/seller-audit/scripts/allocate_attempt.py --uid "<palmstreet_userid>")
echo "$WORK_DIR"   # e.g. /repo/outputs/JccozeKEm4PjM4RRLwTIBVVkYJd2/00
```

The script atomically claims the next free `NN` (concurrency-safe via `mkdir`), creates the directory, and seeds `_meta.json` with the start timestamp. **Capture `$WORK_DIR` and pass it to every subsequent step** — it is the single source of truth for where this audit's artifacts live.

### Step 1: Extract (inline — DO NOT spawn a subagent)

Redirect `bq_query_seller.py`'s stdout into the work directory's `applicant.yaml`:

```bash
python skills/seller-audit/scripts/bq_query_seller.py --uid "<palmstreet_userid>" \
    > "$WORK_DIR/applicant.yaml"
```

The script's stdout is the Applicant Summary YAML — by writing it to disk, Step 2's subagent can read it via the `Read` tool without the orchestrator pasting 80 lines of YAML into the prompt. For the schema and rules behind the YAML, see `references/extract-hubspot.md`.

**Do not spawn a subagent for this step.** Extract is a deterministic script call with no model reasoning — wrapping it in a Task adds a roundtrip and saves no context.

**Fallback to HubSpot UI:** If the BQ script fails (no results for a known uid, ADC auth error you can't fix quickly, or BQ data looks stale), fall back to extracting from the HubSpot contact page in Chrome. The mapping rules and YAML schema are in `references/extract-hubspot.md`. Assemble the YAML by hand following that schema and write it to `$WORK_DIR/applicant.yaml`, then proceed to Step 2.

**No uid? STOP.** If the user gave email/name/contact link only, uid resolution belongs upstream of this skill — run `python scripts/bq_seller.py --query "<term>"` from the project root, take the uid from column 1 of stdout, and re-enter this skill. Do NOT try to make the audit work without a uid; `generate_report.py` hard-errors at the end of the pipeline if `palmstreet_userid` is missing.

### Step 2: Investigate

Spawn a subagent with seller-investigate. **Pass the work directory path — do NOT paste the applicant YAML into the prompt.** The subagent reads `applicant.yaml` from the work directory and writes `investigation.yaml` to the same directory.

```
Task(subagent_type="general-purpose", prompt=f"""
Read skills/seller-investigate/SKILL.md and follow its instructions.

Work directory: {WORK_DIR}
  - INPUT  (read with Read tool): {WORK_DIR}/applicant.yaml
    Schema: ../seller-audit/references/extract-hubspot.md
  - OUTPUT (write with Write tool): {WORK_DIR}/investigation.yaml
    Schema: ../seller-audit/references/schema-investigation.md

Before returning, run the schema self-validation step described in your SKILL
("Self-Validation"). Do NOT echo the YAML in your reply — return only a one-line
confirmation ("investigation.yaml written" or "investigation.yaml written with
schema_validation_failed_after_2_retries") plus any process notes the orchestrator
should see.
""")
```

**Prompt discipline:** Do NOT add tool-usage instructions, fallback permissions, or workarounds to this prompt. `seller-investigate` owns its own tool discipline (including the mandatory Chrome rule) AND its own schema self-validation. Language like "if Chrome is unavailable, use web_fetch as fallback" makes subagents skip Chrome by default and produces invalid audits. If the subagent reports a tool problem, verify it yourself before accepting — do not pre-authorize fallbacks. The orchestrator does NOT re-validate `investigation.yaml` against the schema; that is the investigator's responsibility before it returns.

The subagent will:
- Read `applicant.yaml` for identity, URLs, business claims
- Normalize and verify URLs (via scripts)
- Visit all provided URLs in Chrome
- Follow secondary links and run Google Search fallback if needed
- Write structured investigation YAML to `investigation.yaml`
- Self-validate the YAML against `schema-investigation.md` before returning

### Step 3: Verdict

Spawn a subagent with seller-verdict. **Again pass the work directory path** — applicant + investigation are already on disk, the subagent reads them by path.

```
Task(subagent_type="general-purpose", prompt=f"""
Read skills/seller-verdict/SKILL.md and follow its instructions.

Work directory: {WORK_DIR}
  - INPUTS  (read with Read tool):
      {WORK_DIR}/applicant.yaml       (applicant data — used for category mismatch check)
      {WORK_DIR}/investigation.yaml   (observed data; schema in
                                       ../seller-audit/references/schema-investigation.md)
  - COMPOSE (write with Write tool): {WORK_DIR}/verdict.yaml
      Top-level fields ARE the assessment itself: verdict, tier, risk,
      category_used, *_justification, investigation_steps, special_notes.
      Do NOT wrap them in an outer `assessment:` key — the script rejects
      the wrapped shape with a clear error.
      The script reads applicant.yaml and investigation.yaml from the same
      directory automatically — do NOT re-embed them in verdict.yaml.
  - OUTPUTS (produced by generate_report.py):
      {WORK_DIR}/audit.md
      INSERT into plantstory.risk_control.seller_application_audit
      outputs/<uid>/latest symlink refreshed to point at this attempt
      _meta.json updated with completed_at, last_completed_step, verdict

YOU decide the verdict. The script no longer applies any decision matrix.
Walk your category SOP yourself (the verdict-side `references/sop-{{category}}.md`
in your skill) and put one of APPROVE / REJECT / REVIEW into `verdict.yaml`'s
`verdict:` field. Routing tags (ESCALATE_TO_MADDY, FLAG_TO_JAMES,
ESCALATE_TO_ME_S_TIER, "Forward to Kay", etc.) are NOT verdicts — write them
into `special_notes`.

Run:
  python skills/seller-verdict/scripts/generate_report.py --work-dir {WORK_DIR}

Do NOT hand-write the Markdown. The script produces THREE required deliverables in one call:
  1. {WORK_DIR}/audit.md
  2. an INSERT into plantstory.risk_control.seller_application_audit
  3. outputs/<uid>/latest symlink + _meta.json updates
All are required. Skipping the script silently drops the BQ row.

Confirm all three stderr lines appear before reporting success:
  ✓ wrote .../audit.md
  ✓ inserted row into plantstory.risk_control.seller_application_audit (vid=<vid>)
  ✓ refreshed .../latest → <NN>

Each `investigation_steps[]` entry must have `heading`, `url` (or "" if none), `status`,
`findings` (1–3 sentences of what was observed), and `signals` (bullet list of what each
finding tells us). Sparse entries (heading-only) render as "Status: unknown" placeholders
and waste the report's strongest narrative section — the human reviewer reads this to
audit your reasoning.
""")
```

The subagent will classify tier/risk, pick the tri-state verdict, write its assessment to `verdict.yaml`, run `generate_report.py --work-dir`, and confirm all three side effects succeeded.

**Prompt discipline:**
- Do NOT tell the subagent to "save the report somewhere" as the deliverable — that phrasing has produced subagents that hand-write the .md and skip the script (and therefore skip the BQ insert). Always frame the deliverable as "run generate_report.py and verify the side effects."
- Do NOT mention `action_items` — that field is gone. Anything an onboarding team would have read from "Action Items" now lives in `special_notes`.

### Step 4: Deliver

The script has already written `$WORK_DIR/audit.md`, inserted the BQ row, refreshed the `latest` symlink, and updated `_meta.json`. Verify the file exists at the path the subagent reported, then present it to the user. If any of the three side effects is missing per the subagent's report, re-run Step 3 — do not paper over a failed BQ insert by treating the local markdown as the final deliverable.

For convenience, the user-facing path is `outputs/<uid>/latest/audit.md` (symlink) — they can always read the latest successful audit at that stable location, regardless of attempt number.

## Reference Files Index

References are partitioned by consumer. Each sub-skill owns the files it actually reads; only the truly cross-cutting docs (data contracts, edge-case protocols) live in this orchestrator's `references/`. Sub-skills cross-reference the shared docs via `../seller-audit/references/...`.

### Shared (orchestrator + both sub-skills) — `skills/seller-audit/references/`
- `extract-hubspot.md` — BQ field mapping, fallback decision, Applicant Summary YAML schema. Read by orchestrator (Step 1) and seller-investigate (consumer of the YAML).
- `schema-investigation.md` — Scraper→Verdict data contract for `investigation.yaml`. Read by both seller-investigate (producer + self-validator) and seller-verdict (consumer).
- `edge-cases.md` — Cross-cutting protocols (China connection, category mismatch, name ambiguity, tool failure recovery). Read by both sub-skills.

### Investigation-only — `skills/seller-investigate/references/`
- `loop-react.md` — Adaptive ReAct investigation loop spec.
- `url-normalization.md` — Platform-specific URL cleanup rules (consumed by `normalize_urls.py` and the Chrome visit logic).
- `scrape-{platform}.md` × 9 — Per-platform field extraction guides. Frequency in production: instagram 35%, whatnot 23%, facebook 20%, tiktok 5%, etsy 4.5%, poshmark 4%, ebay 3%, mercari 1.6%, collx <1%.
- `sop-{category}.md` × 5 — Investigation data points for each category SOP (plants, shiny, beauty, collectibles, general). The matching verdict-decision rules live in seller-verdict's references — same filename, scoped content.

### Verdict-only — `skills/seller-verdict/references/`
- `output-format.md` — Final report template and structural constraints.
- `shortcuts.md` — Decision shortcuts from 20+ real audits.
- `sop-{category}.md` × 5 — Verdict decision rules for each category. Counterpart to the investigation-side SOPs of the same name.

**Why split SOPs by file rather than by section within one file?** The previous Part A / Part B layout in a single file forced every reader to know "which half to read and which to skip" — a discipline rule that drifted in subagent prompts. Physical separation makes the boundary structural: each sub-skill simply reads the SOP file in its own `references/` directory; it cannot accidentally consume the other sub-skill's rules.
