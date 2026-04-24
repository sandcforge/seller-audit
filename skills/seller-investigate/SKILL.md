---
name: seller-investigate
description: "Investigate a seller's online footprint by visiting their URLs in Chrome and extracting structured data. This is the Scraper Agent component of the PalmStreet seller audit pipeline. It visits seller-provided URLs, follows secondary links, and runs Google Search fallback when needed. Outputs structured YAML per handoff-schema.md. Does NOT issue verdicts — that is seller-verdict's job. Typically invoked by the seller-audit orchestrator."
---

# Seller Investigation (Scraper Agent)

Investigate a seller's online presence and produce structured YAML data for the Verdict Agent.

## Role Boundaries

- **DO:** Visit URLs in Chrome, extract metrics, follow bio links, run Google Search fallback, detect risks
- **DO NOT:** Read SOP Part B (verdict rules), issue APPROVE/REJECT/REVIEW decisions, read output-format.md

## Inputs

You receive an Applicant Summary (from seller-extract) containing the seller's identity, URLs, category, and business claims.

## Scripts (run before Chrome visits)

### 1. URL Normalization
Before visiting any URL, run:
```bash
echo '["url1", "url2", ...]' | python skills/seller-investigate/scripts/normalize_urls.py
```
This applies all platform-specific rules (invite→user, short link flagging, junk detection, tracking param removal). Only visit URLs where `is_junk` is false. URLs with `needs_chrome_redirect: true` must be visited in Chrome for resolution.

### 2. URL Integrity Verification
After normalization, verify each URL hasn't been mutated:
```bash
python skills/seller-investigate/scripts/verify_url_integrity.py --original "raw_hubspot_url" --visited "normalized_url"
```
If `match: false`, trust the original and re-normalize.

### 3. Identity Scoring (for Google Search results only)
When attributing a Google Search result to the applicant:
```bash
echo '{"applicant": {...}, "found_profile": {...}}' | python skills/seller-investigate/scripts/identity_score.py
```
Only attribute profiles with `match_level: "strong"` (score ≥ 4).

## Investigation Flow

Read the full ReAct loop specification:
> `../seller-audit/references/loop-react.md`

Summary of the loop:
1. **Initialize** action queue (P1: visit provided URLs → P2: follow secondary links → P3: Google Search fallback → P4: WebSearch corroboration)
2. **ACT:** Pick highest-priority incomplete action, visit in Chrome, extract per-page data
3. **REASON:** After each action, evaluate if evidence is sufficient (STRONG_APPROVE, STRONG_REJECT, NEED_REVIEW)
4. **Gate:** Cannot exit before all provided URLs are visited (P1 complete)
5. **Max 5 iterations**

## Loading Platform Scraping Guides

When visiting a platform page, read the corresponding guide for field extraction locations:
- Instagram → `../seller-audit/references/scrape-instagram.md`
- Whatnot → `../seller-audit/references/scrape-whatnot.md`
- Facebook → `../seller-audit/references/scrape-facebook.md`
- TikTok → `../seller-audit/references/scrape-tiktok.md`
- Etsy → `../seller-audit/references/scrape-etsy.md`
- Poshmark → `../seller-audit/references/scrape-poshmark.md`
- eBay → `../seller-audit/references/scrape-ebay.md`
- Mercari → `../seller-audit/references/scrape-mercari.md`
- CollX → `../seller-audit/references/scrape-collx.md`

## Loading Category SOP (Part A Only)

Based on the seller's category, read Part A (Investigation Data Points) of the relevant SOP — this tells you what to focus on during extraction:
- Plants / Flowers / Gardening → `../seller-audit/references/sop-plants.md` Part A
- Jewelry / Coins / Crystals → `../seller-audit/references/sop-shiny.md` Part A
- Beauty / Makeup / Skincare → `../seller-audit/references/sop-beauty.md` Part A
- Collectibles / Trading Cards → `../seller-audit/references/sop-collectibles.md` Part A
- All other → `../seller-audit/references/sop-general.md` Part A

**Do NOT read Part B** (verdict rules) — that is for seller-verdict only.

## Cross-Cutting Protocols

All four protocols live in a single reference — load the section that applies:
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
> `../seller-audit/references/handoff-schema.md`

Every field must be present. Use `null` for unknown values, `[]` for empty arrays. Metrics must be integers/floats (convert "1.5K" → 1500). Include `raw_metrics_text` for each platform as a sanity-check anchor. Set `audit_timestamp` to current UTC time and `sop_applied` to the SOP file used.

## Visual Forensics

When screenshots show product/content images, assess:
- Visual consistency (same backgrounds, lighting, style?)
- Possession evidence (hands holding items, packaging videos?)
- Image authenticity (professional vs amateur? Stock photos? Watermarks?)
- Origin signals (Chinese text, grey shipping bags, Chinese power outlets?)
