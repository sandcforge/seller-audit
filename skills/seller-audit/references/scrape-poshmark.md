# Poshmark Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `handoff-schema.md`.

> **URL format rules** (closet URLs, single listings, tracking params, etc.) → see `url-normalization.md` Poshmark section.

## Page Structure

### Closet Page Header
Poshmark closet pages are well-structured. `get_page_text` works reliably on Poshmark.

```
[@username]
[Profile Photo]
{display_name}
@{username}
{location}

{listings_count} Listings | {followers} Followers | {following} Following

[About section - may contain business description]

[Share] [Follow]
```

### Closet Content
Below the header:
- Grid of listed items with photos, titles, prices
- "My Posh Picks" section (if any)
- Category filters

### Love Notes Tab
"Love Notes" = reviews from buyers. This is a key trust signal:
- Star ratings (1-5)
- Review text
- Buyer username
- Date

## Fields to Extract

| Field | Location | Notes |
|-------|----------|-------|
| username | Header | Starts with @ |
| display_name | Header | May differ from username |
| location | Below name | City, State format |
| listings_count | Stats row | Active listings in closet |
| followers | Stats row | |
| following | Stats row | |
| love_notes_count | Love Notes tab | Total reviews received |
| love_notes_avg | Love Notes tab | Average star rating |
| about | About section | Seller's self-description |
| posh_ambassador | Badge | "Posh Ambassador" badge = trusted seller |
| suggested_user | Badge | "Suggested User" = Poshmark-endorsed |
| top_seller | Badge | Indicates high volume/quality |
| categories_observed | Listed items | What products dominate the closet |
| price_range | Listed items | Min/max prices seen |

## Extraction Method Priority
1. **get_page_text** (primary) — works very well on Poshmark, returns structured data
2. **Screenshot** (secondary) — for visual verification of closet content
3. **JavaScript** (rarely needed)

## 404 / Not Found Detection
- "Closet not found"
- Page shows empty state: "This Posher hasn't listed anything yet"
- Redirect to Poshmark homepage
- "Oops! Something went wrong" error page

## Poshmark-Specific Notes
- **Posh Ambassador** status = high trust signal (requires 5,000+ community shares, high ratings)
- **Suggested User** = curated by Poshmark staff
- **Love Notes** are the primary review system — high count + high rating = strong seller
- **Empty closet** ≠ inactive seller — some sellers clear between seasons/collections
- **Price ranges** vary by category — $5-15 items typical for fast fashion, $50+ for luxury/designer
- **Listings vs sold:** "Listings" count only shows active items. To see sold volume, check if "Love Notes" indicates total transactions.

## Output Format
```yaml
platform: poshmark
url: https://poshmark.com/closet/{username}
status: active | 404 | empty_closet
username: string
display_name: string
location: string or null
listings_count: integer
followers: integer
following: integer
love_notes_count: integer or null
love_notes_avg: float or null  # out of 5.0
about: string or null
badges: [posh_ambassador, suggested_user, top_seller]  # list of badges found
categories_observed: [strings]
price_range: string or null  # e.g., "$5-$120"
```
