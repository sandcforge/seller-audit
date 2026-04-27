# Investigation YAML Schema (Scraper → Verdict)

The Scraper Agent MUST output this exact YAML structure for each seller, written to `<work_dir>/investigation.yaml`. The Verdict Agent consumes this structure directly — no free-form text, no partial data.

## Schema

The investigation carries ONLY what the investigator observed. Applicant identity,
HubSpot-side metadata, and form claims (`name`, `email`, `phone`, `online_assets`,
`business_claims`, etc.) are NOT in the investigation — `generate_report.py` re-fetches
those from BigQuery via `bq_query_seller.py --uid <uid>` at verdict time, using
the `seller.palmstreet_userid` join key below.

```yaml
seller:
  palmstreet_userid: string       # REQUIRED — the only seller field on the investigation.
                                  # Acts as the join key: generate_report.py uses it to
                                  # call bq_query_seller.py and re-fetch the applicant
                                  # data (name / email / phone / online_assets /
                                  # business_claims) from BigQuery. Pull from
                                  # HubSpot's `palmstreet_userid` column. generate_report.py
                                  # hard-errors if this is missing — there is no fallback.

platforms:                        # Array of platform investigation results
  - platform: string              # instagram | whatnot | facebook | ebay | etsy | poshmark | tiktok | mercari | website | other
    url: string                   # Final resolved URL (full https://)
    redirected_from: string or null  # Original URL if different (short link, etc.)
    attribution: string           # "provided_by_seller" | "constructed_from_username" | "found_in_bio" | "found_via_websearch"
    status: string                # "active" | "404" | "login_blocked" | "private"
    account_type: string or null  # "business" | "personal" | "marketplace" | null
    metrics:
      followers: integer or null
      following: integer or null
      items_sold: integer or null
      items_listed: integer or null
      reviews_count: integer or null
      rating: float or null       # Out of 5.0
      feedback_pct: float or null # Out of 100 (eBay-specific)
      likes: integer or null      # TikTok total likes, Facebook page likes
    bio: string or null           # Bio/about text (truncated to 200 chars)
    bio_links: [string]           # External links found in bio/about
    categories_observed: [string] # What products/content types were seen
    badges: [string]              # Platform-specific badges (posh_ambassador, star_seller, verified, etc.)
    location: string or null
    member_since: string or null
    risks: [string]               # Specific risk signals found on this platform, or empty
    raw_metrics_text: string or null  # Original text from page extraction (e.g., "1.5K Followers · 1.2K Sold") — sanity check anchor for Verdict Agent

investigation_summary:                # Investigate WRITES this block — cross-platform
                                      # aggregates, the actual-category finding, and process metadata.
  total_platforms_checked: integer    # Count of platforms ACTUALLY VISITED (any status: active/404/login_blocked/private). Does NOT include negative websearch results where no profile was found. Must equal len(platforms[]).
  total_platforms_active: integer     # Count of platforms[] entries with status == "active"
  total_followers: integer or null    # Sum across ALL active platforms. Null if every active platform has metrics.followers == null. A single non-null value is summed with 0 for nulls; but if ALL are null, emit null (not 0) — "0 followers" is a negative signal and must not be synthesized from missing data.
  total_items_sold: integer or null   # Same null-propagation rule as total_followers.
  highest_rating: float or null
  actual_category: string or null     # What the seller is ACTUALLY selling, observed across storefronts.
                                      # Aggregated from `platforms[].categories_observed[]`. Single string;
                                      # if the storefront sells multiple things, join with " / ".
                                      # Verdict compares this against the applicant's claimed category
                                      # (re-fetched from BQ at verdict time) using the protocol in
                                      # edge-cases.md#category-mismatch. If the investigation is
                                      # indeterminate (no active platforms / login-walled / inconclusive
                                      # after a full ReAct loop), emit null and document the reason in
                                      # `early_exit_reason` so verdict knows the actual is not observed.
  risk_flags: [string]            # Aggregated risk signals across all platforms
  china_connection_signals: [string]  # From China Connection Protocol, or empty
  investigation_iterations: integer   # How many ReAct loop iterations were executed (1–5)
  early_exit_reason: string or null   # Why the loop exited early (e.g., "STRONG_APPROVE: active Whatnot store with 1.5K followers + Instagram cross-reference"), or null if max iterations reached
  sop_applied: string                 # Which SOP was used for evaluation (e.g., "sop-plants", "sop-shiny"). If category mismatch, this reflects the ACTUAL category's SOP, not the claimed one.
  audit_timestamp: string             # ISO 8601 timestamp when this investigation was completed (e.g., "2026-04-14T15:30:00Z")
```

## Rules

1. **Every field must be present.** Use `null` for unknown values, `[]` for empty arrays — never omit a field.
2. **Metrics must be integers/floats, not strings.** Convert "1.2K" → 1200, "15.6K" → 15600 before outputting.
3. **URLs must be full https:// format.** Never use bare domains.
4. **One entry per platform visited.** If a platform returned 404, still include it with `status: "404"` and null metrics.
5. **`categories_observed` (per-platform) and `actual_category` (aggregated) must reflect ACTUAL content** — what you saw on the storefronts. Verdict Agent re-fetches the applicant's claimed category from BigQuery and compares it against `actual_category` using the protocol in edge-cases.md#category-mismatch to decide if a difference is substantive. Never substitute the claim as a shortcut to skip investigation. If the storefront is empty / 404 / login-walled / inconclusive after a full ReAct loop, emit `actual_category: null` and document the reason in `early_exit_reason` so verdict knows the actual is not observed.
6. **`risk_flags` is the critical field** for Verdict Agent. Be explicit: "chinese_text_in_listing_photos", "fake_reviews_suspected", "all_stock_photos" — not just "HIGH RISK".
7. **`total_followers` in investigation_summary** = sum across all active platforms. Verdict Agent uses this for tier classification, not individual platform counts. **Null-propagation:** if EVERY active platform has `metrics.followers == null`, emit `null` here — do NOT emit `0`. "0 followers" is a real negative signal and must never be synthesized from missing data. Same rule applies to `total_items_sold`.
7a. **`total_platforms_checked`** counts platforms that were actually visited (entries in `platforms[]`), regardless of status. Websearch queries that returned zero results and produced no `platforms[]` entry do NOT count. If you searched Instagram/TikTok/Etsy and found nothing, that's 0 additional checks, not 3 — reflect that in the investigation narrative, not in this number.
8. **`raw_metrics_text`** must contain the original text string from which metrics were parsed. This lets the Verdict Agent sanity-check parsed numbers (e.g., verify "1.5K" was correctly converted to 1500, not 15000).
9. **`sop_applied`** must name the SOP file actually used. If a category mismatch caused an SOP switch, this reflects the switched-to SOP.
10. **`audit_timestamp`** must be set to the current UTC time when the investigation completes.
11. **No applicant pass-through.** The investigation carries ONLY observed data. Do NOT include `name`, `email`, `phone`, `online_assets`, or `business_claims` blocks — `generate_report.py` re-fetches those from BigQuery via `bq_query_seller.py --uid <palmstreet_userid>` at verdict time. The investigation's only seller-identity field is `seller.palmstreet_userid` (the join key).

## Example (abbreviated)

```yaml
seller:
  palmstreet_userid: "aB12cD34eF56gH78iJ90"

platforms:
  - platform: whatnot
    url: https://www.whatnot.com/user/frankiefossils
    redirected_from: https://whatnot.com/s/abc123
    attribution: provided_by_seller
    status: active
    account_type: business
    metrics:
      followers: 1523
      following: 89
      items_sold: 1247
      items_listed: null
      reviews_count: 267
      rating: 5.0
      feedback_pct: null
      likes: null
    bio: "Fossil hunter & collector. Weekly live shows!"
    bio_links: ["https://www.instagram.com/frankiefossils"]
    categories_observed: ["fossils", "minerals", "crystals"]
    badges: []
    location: "Los Angeles, CA"
    member_since: null
    risks: []
    raw_metrics_text: "1.5K Followers · 89 Following · 1.2K Sold · 5.0 (267 Reviews)"

  - platform: instagram
    url: https://www.instagram.com/frankiefossils
    redirected_from: null
    attribution: found_in_bio
    status: active
    account_type: business
    metrics:
      followers: 3200
      following: 450
      items_sold: null
      items_listed: null
      reviews_count: null
      rating: null
      feedback_pct: null
      likes: null
    bio: "Fossils & minerals | Whatnot seller | DM for customs"
    bio_links: ["https://whatnot.com/user/frankiefossils"]
    categories_observed: ["fossils", "minerals"]
    badges: []
    location: null
    member_since: null
    risks: []
    raw_metrics_text: "3,200 followers · 450 following"

investigation_summary:
  total_platforms_checked: 5
  total_platforms_active: 2
  total_followers: 4723
  total_items_sold: 1247
  highest_rating: 5.0
  actual_category: "fossils / minerals / crystals"
  risk_flags: []
  china_connection_signals: []
  investigation_iterations: 2
  early_exit_reason: "STRONG_APPROVE: active Whatnot store with 1523 followers, 1247 sales, 5.0 rating + Instagram cross-reference with 3200 followers"
  sop_applied: "sop-collectibles"
  audit_timestamp: "2026-04-14T10:30:00Z"
```
