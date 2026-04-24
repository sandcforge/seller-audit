# Scraper → Verdict Handoff Schema

The Scraper Agent MUST output this exact YAML structure for each seller. The Verdict Agent consumes this structure directly — no free-form text, no partial data.

## Schema

```yaml
seller:
  name: string                    # Full name from HubSpot
  company: string or null         # Company name if different
  hubspot_id: string              # ContactId (for URL construction)
  email: string
  phone: string or null
  phone_area_code_location: string or null

category:
  claimed: string                 # From HubSpot Typeform/Aloy Category
  actual: string                  # Observed from storefront content, or same as claimed
  mismatch: boolean               # true if claimed ≠ actual

business_claims:                  # From HubSpot application (may be empty)
  inventory_count: integer or null
  average_price: float or null
  shipping_volume: string or null

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

investigation_summary:
  total_platforms_checked: integer    # Count of platforms ACTUALLY VISITED (any status: active/404/login_blocked/private). Does NOT include negative websearch results where no profile was found. Must equal len(platforms[]).
  total_platforms_active: integer     # Count of platforms[] entries with status == "active"
  total_followers: integer or null    # Sum across ALL active platforms. Null if every active platform has metrics.followers == null. A single non-null value is summed with 0 for nulls; but if ALL are null, emit null (not 0) — "0 followers" is a negative signal and must not be synthesized from missing data.
  total_items_sold: integer or null   # Same null-propagation rule as total_followers.
  highest_rating: float or null
  risk_flags: [string]            # Aggregated risk signals across all platforms
  china_connection_signals: [string]  # From China Connection Protocol, or empty
  phone_cluster_note: string or null  # If phone number matches another seller in batch
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
5. **`categories_observed` must reflect ACTUAL content**, not the seller's claimed category. This is what Verdict Agent uses to detect mismatches.
6. **`risk_flags` is the critical field** for Verdict Agent. Be explicit: "chinese_text_in_listing_photos", "fake_reviews_suspected", "all_stock_photos" — not just "HIGH RISK".
7. **`total_followers` in investigation_summary** = sum across all active platforms. Verdict Agent uses this for tier classification, not individual platform counts. **Null-propagation:** if EVERY active platform has `metrics.followers == null`, emit `null` here — do NOT emit `0`. "0 followers" is a real negative signal and must never be synthesized from missing data. Same rule applies to `total_items_sold`.
7a. **`total_platforms_checked`** counts platforms that were actually visited (entries in `platforms[]`), regardless of status. Websearch queries that returned zero results and produced no `platforms[]` entry do NOT count. If you searched Instagram/TikTok/Etsy and found nothing, that's 0 additional checks, not 3 — reflect that in the investigation narrative, not in this number.
8. **`raw_metrics_text`** must contain the original text string from which metrics were parsed. This lets the Verdict Agent sanity-check parsed numbers (e.g., verify "1.5K" was correctly converted to 1500, not 15000).
9. **`sop_applied`** must name the SOP file actually used. If a category mismatch caused an SOP switch, this reflects the switched-to SOP.
10. **`audit_timestamp`** must be set to the current UTC time when the investigation completes.

## Example (abbreviated)

```yaml
seller:
  name: Frankie Clemente
  company: Frankie's Fossils
  hubspot_id: "123456789"
  email: frankie@example.com
  phone: "(555) 123-4567"
  phone_area_code_location: "Los Angeles, CA"

category:
  claimed: Collectibles
  actual: Collectibles
  mismatch: false

business_claims:
  inventory_count: 200
  average_price: 35.00
  shipping_volume: null

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
  risk_flags: []
  china_connection_signals: []
  phone_cluster_note: null
  investigation_iterations: 2
  early_exit_reason: "STRONG_APPROVE: active Whatnot store with 1523 followers, 1247 sales, 5.0 rating + Instagram cross-reference with 3200 followers"
  sop_applied: "sop-collectibles"
  audit_timestamp: "2026-04-14T10:30:00Z"
```
