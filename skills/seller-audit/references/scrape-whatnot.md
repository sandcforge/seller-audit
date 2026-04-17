# Whatnot Profile Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `handoff-schema.md`.

## URL Patterns
- Profile: `https://www.whatnot.com/user/{username}`
- Short link: `https://www.whatnot.com/s/XXXXX` (auto-redirects to profile)
- Invite link: `https://www.whatnot.com/invite/{username}` (NOT a profile — normalize to `/user/{username}`)

## Profile Page — Overview

### Page Text Pattern
The `get_page_text` output follows this structure:
```
{username}{Display Name} MessageFollow{rating} ({review_count} Reviews)•{avg_ship} Avg Ship•{sold_count} Sold{following_count} Following•{followers_count} Followers{bio_text}
```

### Fields to Extract

| Field | Location | Example |
|-------|----------|---------|
| username | First text element | `intheboxcollectibles` |
| display_name | After username | `In The Box Collectibles` |
| rating | Before "(X Reviews)" | `5.0` |
| review_count | Inside parentheses | `267` |
| avg_ship_days | Before "Avg Ship" | `1d` |
| items_sold | Before "Sold" | `1.2K` → parse as 1200 |
| followers | Before "Followers" | `1.8K` → parse as 1800 |
| following | Before "Following" | `1.7K` → parse as 1700 |
| bio | After followers line | Free text, may contain external URLs |
| external_links | Inside bio | Website URLs, IG handles, Discord links |

### Number Parsing
- `1.2K` = 1,200
- `10.5K` = 10,500
- Plain numbers = as-is

### 404 Detection
- Page shows "This page doesn't exist" or blank content = seller not on Whatnot
- Short link 404 does NOT mean seller has no Whatnot → try `whatnot.com/user/{username}`

---

## Tab-by-Tab Extraction (MANDATORY)

After extracting the profile overview, you MUST visit all 4 tabs. The tabs appear below the bio as: **Shop | Shows | Reviews | Clips**. Click each tab and extract data.

### Tab 1: Shop

Navigate to `whatnot.com/user/{username}/shop` or click the "Shop" tab.

**What to look for:**
- **Products (N)** — the count in the heading. Extract the number.
- Product thumbnails — take a screenshot if products exist. Note whether products match the claimed category.
- "Nothing for sale here" — means 0 products listed.

**Key fields:**
| Field | Location | Example |
|-------|----------|---------|
| product_count | "Products (N)" heading | `25` or `0` |
| products_visible | Whether actual product cards are shown | `true` / `false` |
| category_match | Do listed products match claimed category? | `true` / `false` / `N/A (no products)` |

**Red flag:** If product_count is 0 but the seller claims a large inventory in HubSpot, note the discrepancy.

### Tab 2: Shows

Navigate to `whatnot.com/user/{username}/shows` or click the "Shows" tab.

**What to look for:**
- Upcoming shows — scheduled livestreams with date/time and title
- Past shows — historical livestreams (may not always be visible)
- "There's nothing here at the moment! There's no shows scheduled" — means no upcoming shows.

**Key fields:**
| Field | Location | Example |
|-------|----------|---------|
| upcoming_shows | Count of scheduled shows | `3` or `0` |
| show_titles | Titles of upcoming shows | `["Pokemon TCG Breaks", "ETB Opening Night"]` |
| is_active_streamer | Has upcoming or recent shows | `true` / `false` |

**Significance:** Upcoming shows indicate the seller is actively preparing to sell via livestream. This is a strong positive signal even if historical sales are low.

### Tab 3: Reviews

Navigate to `whatnot.com/user/{username}/reviews` or click the "Reviews" tab.

**What to look for:**
- Star rating aggregate (if shown at top)
- Individual review entries — buyer name, rating, date, comment text
- "This seller doesn't have any reviews yet!" — means 0 reviews.

**Key fields:**
| Field | Location | Example |
|-------|----------|---------|
| review_count | Count shown or counted | `267` or `0` |
| avg_rating | Aggregate star rating | `5.0` |
| recent_reviews | Sample of most recent reviews | `[{buyer, rating, date, text}]` |
| negative_reviews | Any reviews below 4 stars | `[]` or details |

**Red flag:** Low ratings (<4.5), complaints about fake/counterfeit items, shipping issues, or no-shows.

### Tab 4: Clips (CRITICAL — requires spot-check)

Navigate to `whatnot.com/user/{username}/clips` or click the "Clips" tab.

**What to look for:**
- **"Clips by {username} (N)"** — total clip count in the heading.
- Clip thumbnails — take a screenshot of the grid.
- Each clip shows: title, view count, and "Clipped by @{username}".

**Key fields:**
| Field | Location | Example |
|-------|----------|---------|
| clip_count | "Clips by {username} (N)" heading | `21` or `0` |
| clip_titles | Visible clip titles from the grid | `["Bangers", "Zardy boy", "Fire"]` |

#### Clip Spot-Check Protocol (MANDATORY if clip_count > 0)

You MUST click into at least **3 clips** (sample from different positions in the grid — first row and second row) to verify content. For each clip, record:

| Field | Where to Find | Example |
|-------|---------------|---------|
| clip_title | Top of clip page | `"Duckrace got the slabby patty"` |
| clip_views | Next to "Clipped by" | `33` |
| source_seller | "About the Seller" section on the right sidebar | `cardscoinsandcollectables` |
| source_seller_followers | Below seller name | `2.9K` |
| source_seller_rating | Stats box | `4.9` |
| source_seller_items_sold | Stats box | `9,879` |
| content_description | What the video shows (from screenshot) | `Pokemon card opening on stream` |
| is_own_stream | Is the source_seller the same as the applicant? | `true` / `false` |

**How to interpret clip data:**

1. **Clips from OWN stream** (`is_own_stream = true`): Strong positive signal. The applicant is an active seller who livestreams. Note the content type and whether it matches the claimed category.

2. **Clips from OTHER sellers' streams** (`is_own_stream = false`): This means the applicant is a **viewer/moderator** who clips moments from streams they watch. This is NOT selling activity. It proves community involvement but NOT selling capability.
   - Check if ALL clips are from other sellers' streams → the applicant is a buyer/mod, not a seller
   - Check if the content category is consistent with the application (e.g., all Pokemon clips + applied as Trading Cards = category match)

3. **Mixed clips** (some own, some others): Normal pattern for active community sellers.

**Content Consistency Assessment:**

After spot-checking ≥3 clips, issue a consistency verdict:
- **CONSISTENT:** All sampled clips are thematically aligned with the claimed category. Content appears authentic.
- **INCONSISTENT:** Clips show different categories than claimed, or content appears suspicious/unrelated.
- **INCONCLUSIVE:** Not enough information to determine consistency (e.g., clips are too vague).

Record this in the report as:
```
- Clips: {clip_count} clips posted — [all from own streams / all from other sellers' streams / mixed].
  Content: [description of what clips show].
  Spot-check ({N} of {total} sampled):
    - "{title}" ({views} views) — from **{source_seller}** ({source_stats}). [content description].
    - "{title}" ({views} views) — from **{source_seller}** ({source_stats}). [content description].
    - "{title}" ({views} views) — from **{source_seller}** ({source_stats}). [content description].
  Consistency verdict: [CONSISTENT / INCONSISTENT / INCONCLUSIVE]
```

---

## Common Pitfalls
- Bio text runs together with product listings — extract bio BEFORE "Shop" / "Shows" / "Reviews" / "Clips" tabs
- Some sellers have upcoming shows listed — note if active livestreamer
- Rating may not appear if seller has 0 reviews
- Clips are often from OTHER sellers' streams — always check the "About the Seller" sidebar to identify the source
- A seller with high followers but 0 products/0 sold is likely a moderator or buyer, not a seller
- Clip view counts are generally low (10-50) — this is normal, not a red flag

## Output Format
```yaml
platform: whatnot
url: https://www.whatnot.com/user/{username}
status: active | 404
username: string
display_name: string
rating: number (0-5) | null
reviews: integer
avg_ship_days: integer | null
items_sold: integer
followers: integer
following: integer
bio: string
external_links: [urls]
# Shop tab
product_count: integer
products_visible: boolean
category_match: boolean | null
# Shows tab
upcoming_shows: integer
show_titles: [strings]
is_active_streamer: boolean
# Reviews tab
recent_reviews: [{buyer, rating, date, text}]
negative_reviews: [{buyer, rating, date, text}]
# Clips tab
clip_count: integer
clips_from_own_streams: integer
clips_from_other_streams: integer
clip_spot_check:
  - title: string
    views: integer
    source_seller: string
    source_seller_stats: string
    content: string
    is_own_stream: boolean
clip_consistency: CONSISTENT | INCONSISTENT | INCONCLUSIVE
categories_observed: [strings from product listings and clip content]
```
