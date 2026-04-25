# Adaptive Investigation Loop (ReAct Pattern)

**When to read:** During the investigation phase (Section 2.5). This guide explains how to use the Reason → Act loop to make dynamic decisions about what to investigate next, rather than following a fixed linear sequence.

---

## 2.5 Adaptive Investigation Loop (ReAct Pattern)

Instead of following a fixed linear sequence, the investigation uses a **Reason → Act** loop that can exit early when evidence is sufficient, or dig deeper when it's not. Maximum **5 iterations**.

### 2.5.1 Initialization

Before entering the loop, prepare:

```
action_queue:                   # Ordered by priority (highest first)
  1. visit_provided_urls        # MANDATORY — must complete before any early exit
  2. follow_secondary_links     # Links found in bios / about pages / linktrees
  3. google_search_fallback     # Google Search in Chrome to expand platform coverage

evidence:
  platforms_visited: []         # Platform result entries (per Section 2.5.5)
  total_followers: 0
  total_items_sold: 0
  risk_flags: []
  secondary_links_found: []     # Links discovered in bios, pending visit
  provided_urls_done: false     # Flips to true when all provided URLs are visited
  all_provided_urls_invalid: false  # Flips to true when every provided URL is 404/dead/empty

iteration: 0
max_iterations: 5
```

**Platform coverage target:** P1 + P2 + P3 together should yield roughly **3–5 platforms** worth of evidence. This is a target, not a quota — see Section 2.5.3 Priority 3 for how to handle the case where P1+P2 only produce 1–2 platforms.

### 2.5.2 REASON Phase — Evaluate Evidence After Each Action

After each action, assess whether evidence is sufficient to proceed to verdict:

**STRONG_APPROVE — high confidence, can exit early:**
- Found ≥1 active storefront with category match AND sales/review history
- Cross-platform consistency (same brand/username on 2+ platforms)
- Total followers ≥ category SOP Tier B threshold

**STRONG_REJECT — high confidence, can exit early:**
- ALL provided URLs are 404/dead/empty AND Google Search fallback (Priority 3) also found zero relevant results
- Zero footprint: 0 followers, 0 sales, 0 reviews across all visited pages and search results

**NEED_REVIEW — partial signal, flag for human:**
- Category mismatch confirmed but needs human judgment
- Name Ambiguity Protocol triggered Bronze Match

**Decision logic:**
```
IF provided_urls_done == false:
    → CONTINUE (cannot exit before visiting all provided URLs)

IF confidence == STRONG_APPROVE or STRONG_REJECT:
    → EXIT loop, proceed to verdict (Section 3)

IF confidence == NEED_REVIEW and no remaining high-value actions:
    → EXIT loop, verdict will be REVIEW

IF iteration >= max_iterations:
    → EXIT loop, proceed to verdict with current evidence
    → If evidence is still ambiguous, verdict defaults to REVIEW

OTHERWISE:
    → CONTINUE to ACT phase
```

### 2.5.3 ACT Phase — Select Next Best Action

Pick the highest-priority incomplete action from the queue:

**Priority 1: Visit Provided URLs** (MANDATORY — at least one full pass required)

Visit every normalized URL from the application using Claude in Chrome. For each URL:

1. Take a screenshot and extract page text
2. Determine page type: Storefront / Social Media / Linktree / Personal Website / 404
3. Check if it's a BUSINESS account or PERSONAL account
4. Extract metrics: followers, sales, reviews, product count, location
5. Note any external links found (Bio, About section, Linktree links) → add to `secondary_links_found`
6. Assess if content matches the claimed business category
7. Load the corresponding `references/scrape-*.md` for structured data extraction

For social media profiles, evaluate:
- Is the content about selling plants/jewelry/beauty/etc., or is it a personal life account?
- Are there product photos with prices, or just personal photos?
- Is there a "shop" link, "DM to order", or business-related bio?

After visiting all provided URLs, set `provided_urls_done = true`.

**Priority 2: Follow Secondary Links**

Visit links discovered in bios, about sections, and linktrees during Priority 1. These are high-confidence connections (e.g., Linktree → Etsy, Instagram bio → Shopify). Only follow links that appear to be storefronts or business pages.

**Priority 3: Google Search in Chrome (platform coverage expansion)**

> **When to run:** Use P3 whenever P1 + P2 haven't yet produced enough platforms to reach the 3–5 target — even if P1 produced live pages. P3 is a regular tool for expanding platform coverage, not a last-resort fallback. Skip P3 only when P1 + P2 have already delivered 3+ platforms with coherent signal.

Use **Google Search in Chrome** (navigate to `google.com` and search) to discover additional platforms the seller operates on. Do NOT construct platform URLs directly — let Google find them.

**Search queries to run (in order, stop when you find relevant results):**
1. `"{PalmStreet Username}" {Category}` (e.g., `"KaosCollection" fashion`)
2. `"{First Last}" {Category} seller` (e.g., `"Kaci Stein" fashion seller`)
3. `"{Email}"` (e.g., `"kaci.stein12@gmail.com"`) — only if queries 1–2 yield nothing

**For each search:**
1. Navigate to `https://www.google.com` in Chrome
2. Type the search query and submit
3. Take a screenshot of the results page
4. Evaluate the top results for relevance — look for storefronts, social profiles, or business pages that match the seller's identity
5. If a promising result is found, click through and visit it in Chrome to extract data (follow standard per-page data capture in Section 2.5.5)

**⚠️ CRITICAL: Identity Verification for Google Search Results**

Google Search results are NOT guaranteed to belong to the applicant. Common names, shared usernames, and brand-name collisions mean many results will be for a DIFFERENT person or entity. Before attributing any search result to the seller, you MUST verify identity by cross-checking multiple signals:

- **Strong match (can attribute):** ≥2 of the following align with HubSpot data: same full name + same location/state, same email visible on profile, same username across provided URL and found profile, same phone number, same company name + same category
- **Weak match (cannot attribute, note as unconfirmed):** Only 1 signal matches (e.g., same first name but different state, same username but different category). Mark as "Unconfirmed — may not be the same person" in the report.
- **No match (discard):** Zero signals match. Do not include in the report.

When in doubt, do NOT assume a Google result belongs to the seller. It is better to report "Google Search found no confirmed matches" than to incorrectly attribute someone else's profile to the applicant.

**Rules:**
- Maximum 3 Google Search queries total
- If a result page looks relevant (matching name/username + category), visit it in Chrome and extract data
- If 3 searches yield no relevant results, STOP — this confirms zero footprint
- Do NOT construct platform URLs (e.g., do not manually build `instagram.com/{username}` or `poshmark.com/closet/{username}`) — only follow links that Google returns
- ALL pages discovered via Google Search MUST be tagged with `Attribution: "Found via Google Search"` in the report (Section 2.5.5 and Section 3.3 Part 2), and include an identity match assessment (Strong / Weak / No match)

**After completing P3**, if all provided P1 URLs were invalid and P3 also found nothing, set `all_provided_urls_invalid = true`. Return to REASON phase.

**Coverage expectation across P1 + P2 + P3:**

Aim for **3–5 platforms** total. But this is a target, not a quota:
- If P1 + P2 already yield 3+ platforms with coherent signal, skip P3 — you're done.
- Otherwise run P3 to try to reach 3–5 platforms, regardless of whether P1 URLs were live or dead.
- **Do not force coverage.** If P3 finds no results that meet the strong-identity-match bar (see identity verification above), stop at whatever P1 + P2 produced — even if that's only 1–2 platforms. Better to hand off a smaller honest dataset than to pad with weak/unconfirmed matches.

**After acting → return to REASON phase.**

### 2.5.4 Early Exit Rules

1. **Priority 1 is a gate** — The loop MUST NOT exit before all provided URLs have been visited, even if early signals look strong.
2. **Dead Short Links — try URL normalization first** — When a provided short link 404s, apply URL normalization rules (e.g., Whatnot `/invite/` → `/user/`, expand eBay short links by visiting in Chrome). This is part of Priority 1 URL processing, NOT a separate platform construction step.
3. **All provided URLs dead → must run Google Search** — The loop MUST NOT exit with a REJECT verdict before completing Priority 3 (Google Search in Chrome). Only after Google Search also yields nothing can you conclude zero footprint.
4. **Max 5 iterations is a hard cap** — At iteration 5, exit with whatever evidence is available. If ambiguous, default verdict to REVIEW.
5. **Record the exit** — When exiting the loop, record `investigation_iterations` (how many iterations ran) and `early_exit_reason` (why the loop ended, or `null` if max iterations reached).

### 2.5.4b UNABLE_TO_AUDIT Exit

When the investigation cannot proceed due to systemic failures (not just dead URLs), exit with an UNABLE_TO_AUDIT status:

**Trigger conditions (ANY):**
- BigQuery script fails AND HubSpot UI is inaccessible (no seller data at all)
- Chrome browser is unavailable AND all provided URLs require Chrome visits
- HubSpot record contains zero URLs, zero social media, and zero identifying information beyond name/email

**Output:** Produce a truncated report using the standard template (Section 3.3 format in output-format.md) with:
- Verdict: **REVIEW**
- Tier: **N/A**
- Risk: **N/A**
- Action: "Audit incomplete — [specific reason]. Manual follow-up required."
- Summary: Explain what was attempted and why the audit could not be completed
- Investigation Steps: Document each attempted action and its failure reason

Do NOT default to REJECT when the issue is data availability rather than seller quality.

### 2.5.5 Per-Page Data Capture

For each page visited (regardless of which action triggered it), capture:

```
**[Platform] — [full https:// URL]**
- Attribution: [How found: "Provided by seller" / "Found via Google Search" / "Found in Instagram bio"]
- Identity Match: [ONLY for Google Search results — "Strong match (name + location)" / "Weak match (username only)" / "Unconfirmed". Omit this line for seller-provided URLs.]
- Key Metrics: [Followers, Sales, Reviews, etc.]
- Summary: [What was found]
- Risks Identified: [Specific risks or "None"]
```
