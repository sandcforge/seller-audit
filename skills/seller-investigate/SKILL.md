---
name: seller-investigate
description: "Investigate a seller's online footprint by visiting their URLs in Chrome and extracting structured data. This is the Scraper Agent component of the PalmStreet seller audit pipeline. It visits seller-provided URLs, follows secondary links, and runs Google Search fallback when needed. Outputs structured YAML per schema-investigation.md (written to investigation.yaml) and self-validates against that schema before returning. Does NOT issue verdicts — that is seller-verdict's job. Typically invoked by the seller-audit orchestrator."
---

# Seller Investigation (Scraper Agent)

Investigate a seller's online presence and produce structured YAML data for the Verdict Agent.

## Non-Negotiable: Chrome Only

All URL visits MUST go through `mcp__Claude_in_Chrome__*` tools. No exceptions.

- Do NOT use curl, WebFetch, Googlebot user-agent, or any non-Chrome fetch method. OG metadata alone (title, description, coarse like-count) is insufficient evidence — it misses posts, post cadence, product photos, real follower counts, engagement, and live-selling activity. An audit built on OG metadata is not a valid audit.
- If Chrome tool schemas aren't loaded in your environment, use ToolSearch (e.g. `select:mcp__Claude_in_Chrome__navigate,mcp__Claude_in_Chrome__get_page_text,mcp__Claude_in_Chrome__tabs_create_mcp`) to load them before concluding Chrome is unavailable.
- If Chrome is genuinely unavailable (user disabled it, tools missing from the deferred list even after ToolSearch), STOP and report back to the caller. Do not complete the investigation with fallbacks.
- Login walls are NOT a reason to abandon Chrome. Follow the login-wall protocol in `references/scrape-{platform}.md` (typically: `get_page_text` → screenshot → try marketplace/profile URL variant). Stay in Chrome.

## Role Boundaries

- **DO:** Visit URLs in Chrome, extract metrics, follow bio links, run Google Search fallback, detect risks
- **DO NOT:** Read seller-verdict's references (sop-*.md verdict rules, output-format.md, shortcuts.md), issue APPROVE/REJECT/REVIEW decisions, hand-write any markdown report

## Inputs (read by file path — not pasted into the prompt)

The orchestrator passes you a **work directory path** (e.g. `outputs/<uid>/<NN>/`). Read your input from disk:

- **`<work_dir>/applicant.yaml`** — Applicant Summary YAML produced by Step 1 of the orchestrator (`bq_query_seller.py --uid` redirected to disk). Top-level keys: `seller`, `online_assets`, `business_claims`. Schema in `../seller-audit/references/extract-hubspot.md` (section: "Output: Applicant Summary YAML"). Use the `Read` tool to load it.

You READ this YAML to drive your investigation — you do NOT copy it into your investigation output. URLs come from `online_assets.website` and `online_assets.social_media`. The claimed category is `business_claims.category` (single string; multi-category claims are joined with `" / "`) — use it to load the right `references/sop-{category}.md` (your investigation SOP — same filename as verdict's, but scoped to data-points) and as the baseline for the category-mismatch check. You may also verify numeric claims like `inventory_count` against what you observe and call out discrepancies in `risk_flags`.

## Output contract (investigation.yaml written to file)

Write your investigation YAML to **`<work_dir>/investigation.yaml`** using the `Write` tool, then run the schema self-validation step (see "Self-Validation" below) before returning. Do NOT echo the YAML in your reply to the orchestrator — return only a one-line confirmation ("investigation.yaml written" or "investigation.yaml written with schema_validation_failed_after_2_retries") plus any process notes.

The investigation YAML is slim — it contains ONLY observed data plus a join key. Do NOT pass through `name`, `email`, `phone`, `online_assets`, or `business_claims` — `generate_report.py` reads those from `<work_dir>/applicant.yaml` directly (the file is on the same disk it has access to). The full schema is in `../seller-audit/references/schema-investigation.md`. Top-level blocks:

- `seller.palmstreet_userid` — the only seller-identity field (join key for the BQ refetch). Copy from input verbatim.
- `platforms[]` — one entry per platform you actually visited, with metrics, bio, risks, etc.
- `investigation_summary` — cross-platform aggregates (`total_followers`, `total_items_sold`, `risk_flags`, ...), the actual-category finding (`actual_category`, aggregated from `platforms[].categories_observed[]`), and process metadata (`investigation_iterations`, `early_exit_reason`, `sop_applied`, `audit_timestamp`).

Your category *finding* lives in `investigation_summary.actual_category`. Verdict re-fetches the claimed category from BigQuery and computes mismatch on the fly. If the storefront is empty / 404 / login-walled / inconclusive, emit `actual_category: null` and document the reason in `early_exit_reason` — do NOT substitute the claimed category as a shortcut.

## Scripts (run around Chrome visits)

### 1. URL Normalization (run ONCE, before any Chrome visit)
```bash
echo '["url1", "url2", ...]' | python skills/seller-investigate/scripts/normalize_urls.py
```
Applies all platform-specific rules (invite→user, short link flagging, junk detection, tracking param removal) and emits one object per URL with: `original`, `normalized`, `platform`, `is_junk`, `junk_reason`, `notes`, `needs_chrome_visit`, and **`expected_identifier`** — the canonical identifier (username / shop name / numeric id) the visited page MUST resolve to.

Only visit URLs where `is_junk` is false. URLs with `needs_chrome_visit: true` must be visited in Chrome for resolution. **Keep the full normalize output in your working state** — you'll feed it back into verify in step 2.

### 2. URL Integrity Verification (run ONCE, after Chrome visits)
After visiting all P1 URLs in Chrome, take the normalize output, attach the URL Chrome actually landed on as a `visited` field, and pipe the array into verify:

```bash
echo '[
  {"original": "...", "expected_identifier": "frankiefossils", "visited": "https://www.whatnot.com/user/frankiefossils", "is_junk": false},
  {"original": "...", "expected_identifier": "granitestatecoinsandcurrency", "visited": "https://granitestatecoinsandcurrency.etsy.com", "is_junk": false}
]' | python skills/seller-investigate/scripts/verify_url_integrity.py
```

The script:
- Skips entries where `is_junk: true` (nothing was visited).
- Uses `expected_identifier` from normalize as the authoritative identifier — no need to re-derive from `original`.
- Returns one result per non-junk entry with `match`, `diff_positions`, `diff_summary`, `recommendation`.

For any result with `match: false` and `recommendation: "trust_original"`, treat the visited page as a different identity (silent character mutation, redirect to a different account, etc.) and either re-visit the normalized URL or flag in `risks`.

### 3. Identity Scoring (for Google Search results only)
When attributing a Google Search result to the applicant:
```bash
echo '{"applicant": {...}, "found_profile": {...}}' | python skills/seller-investigate/scripts/identity_score.py
```
Only attribute profiles with `match_level: "strong"` (score ≥ 4).

## Investigation Flow

Read the full ReAct loop specification:
> `references/loop-react.md`

Summary of the loop:
1. **Initialize** action queue (P1: visit provided URLs → P2: follow secondary links → P3: Google Search in Chrome to expand platform coverage)
2. **ACT:** Pick highest-priority incomplete action, visit in Chrome, extract per-page data
3. **REASON:** After each action, evaluate if evidence is sufficient (STRONG_APPROVE, STRONG_REJECT, NEED_REVIEW)
4. **Gate:** Cannot exit before all provided URLs are visited (P1 complete)
5. **Coverage target:** P1 + P2 + P3 together should yield roughly 3–5 platforms. P3 runs whenever P1+P2 haven't hit the target — it is NOT gated on P1 URLs being dead. If P3 finds no strong-identity matches, stop at whatever P1+P2 produced (even 1–2 platforms) rather than attributing weak matches.
6. **Max 5 iterations**

## Loading Platform Scraping Guides

When visiting a platform page, read ONLY the guide for that platform — do not pre-load all 9. Each guide is in this skill's `references/`:
- Instagram → `references/scrape-instagram.md`
- Whatnot → `references/scrape-whatnot.md`
- Facebook → `references/scrape-facebook.md`
- TikTok → `references/scrape-tiktok.md`
- Etsy → `references/scrape-etsy.md`
- Poshmark → `references/scrape-poshmark.md`
- eBay → `references/scrape-ebay.md`
- Mercari → `references/scrape-mercari.md`
- CollX → `references/scrape-collx.md`

## Loading Category SOP (investigation data points)

Based on the seller's category, read this skill's investigation SOP — it lists the data points to focus on during extraction. Each SOP is scoped to investigation only; the matching verdict rules live in seller-verdict's references and are not your concern.
- Plants / Flowers / Gardening → `references/sop-plants.md`
- Jewelry / Coins / Crystals → `references/sop-shiny.md`
- Beauty / Makeup / Skincare → `references/sop-beauty.md`
- Collectibles / Trading Cards → `references/sop-collectibles.md`
- All other → `references/sop-general.md`

## Cross-Cutting Protocols

All four protocols live in a single reference shared with the orchestrator — load the section that applies:
- China Connection signals → `../seller-audit/references/edge-cases.md#china-connection`
- Category mismatch detected → `../seller-audit/references/edge-cases.md#category-mismatch`
- Name ambiguity in search results → `../seller-audit/references/edge-cases.md#name-ambiguity`
- Tool failures (404, login wall, etc.) → `../seller-audit/references/edge-cases.md#tool-failure-recovery`

## Chrome Tab Management

Each seller investigation uses its own Chrome tab:
1. Call `tabs_context_mcp` (with `createIfEmpty: true`), then `tabs_create_mcp`
2. Use this tab for all visits during this seller's investigation
3. After investigation completes, call `tabs_close_mcp`

## Output Contract

Output YAML following the exact schema in:
> `../seller-audit/references/schema-investigation.md`

Every field must be present. Use `null` for unknown values, `[]` for empty arrays. Metrics must be integers/floats (convert "1.5K" → 1500). Include `raw_metrics_text` for each platform as a sanity-check anchor. Set `audit_timestamp` to current UTC time and `sop_applied` to the SOP file used.

**Narrative must match the YAML.** Anything you describe in your summary/reply must be reflected in the structured fields, and vice versa. Common divergences to avoid:

- Claiming "searched 4 platforms" in prose while `total_platforms_checked` is 2 — `total_platforms_checked` counts entries in `platforms[]` (i.e., platforms actually visited), not platforms you merely ran a websearch for and found nothing. If you want to document negative websearches, put them in the narrative AND keep `total_platforms_checked` honest.
- Summing `null` followers as `0` in `total_followers` — if every active platform has `metrics.followers == null`, emit `null`, not `0`. "0 followers" is a negative signal the Verdict Agent will act on.
- Describing signals in prose that aren't anchored in `platforms[].risks`, `categories_observed`, `badges`, etc. If you saw it, capture it in a field.

Before emitting the YAML, re-read your own summary and confirm every number and claim maps to a field.

## Self-Validation (mandatory before returning)

You own schema correctness for `investigation.yaml`. The orchestrator does NOT re-validate — when you report "investigation.yaml written", the verdict subagent will read it directly. Bad data here goes straight into the audit report.

After writing `<work_dir>/investigation.yaml`, run the validator:

```bash
python skills/seller-audit/scripts/validate_investigation.py \
    --file <work_dir>/investigation.yaml
```

Exit code semantics:
- `0` — valid. Return to the orchestrator with `"investigation.yaml written"`.
- `1` — schema errors. Each error is one line on stderr (path + reason). Read them, fix the YAML, re-run validate. **Retry budget: 2.**
- `2` — script-level error (file missing, YAML parse failure). Fix and retry; this does NOT consume a schema-retry slot.

**If you exhaust the 2-retry budget for schema errors:** do NOT return success silently and do NOT escalate to the orchestrator with prose. Instead, write a *schema-compliant* shell investigation YAML — every required field present, `platforms: []`, all metrics `null` — and set:

```yaml
investigation_summary:
  early_exit_reason: "schema_validation_failed_after_2_retries: <last error message verbatim>"
  actual_category: null
  total_platforms_checked: 0
  total_platforms_active: 0
  ...
```

Then re-run validate one final time to confirm the shell itself passes (it must — the shell's whole purpose is to be schema-compliant). Return `"investigation.yaml written with schema_validation_failed_after_2_retries"` so the orchestrator's logs make the failure visible. The verdict subagent will pick this up via the `early_exit_reason` prefix and emit a REVIEW verdict with N/A tier/risk.

**Why a retry budget at all?** The validator's errors are deterministic and mechanical (missing field, wrong type, count mismatch, bad enum). Two retries is enough to fix them all if you're paying attention; if you can't fix them in two passes, you're in a state where another iteration won't help — bail with the documented signal so a human can look at it.

**Common errors and how to fix them:**

| Error | Fix |
|---|---|
| `metrics.followers: must be int or null, got str ('1.5K')` | Parse "1.5K" → 1500 before writing. Same for any string-shaped metric. |
| `total_platforms_checked: must equal len(platforms[])` | The field counts visited platforms (entries in `platforms[]`), not websearch attempts. Decrement until equal. |
| `total_platforms_active: must equal count of status=="active"` | Recount; only `status: "active"` entries qualify. |
| `platforms[i].url: must start with https://` | Expand bare domains. `instagram.com/foo` → `https://www.instagram.com/foo`. |
| `<field>: missing required field` | Add the field with `null` (scalars) or `[]` (arrays). Never omit. |
| `seller.palmstreet_userid: required non-empty string` | Copy from `applicant.yaml` `seller.palmstreet_userid` verbatim. This is the BQ join key; no fallback. |

## Visual Forensics

When screenshots show product/content images, assess:
- Visual consistency (same backgrounds, lighting, style?)
- Possession evidence (hands holding items, packaging videos?)
- Image authenticity (professional vs amateur? Stock photos? Watermarks?)
- Origin signals (Chinese text, grey shipping bags, Chinese power outlets?)
