# Mercari Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `../../seller-audit/references/schema-investigation.md`.

> **URL format rules** (profile URLs, short links, single items, etc.) → see `url-normalization.md` Mercari section.

## Page Structure

### Profile Page
`get_page_text` works on Mercari. The profile page shows:

```
[Profile Photo]
{display_name}
{rating} ({review_count} ratings)

{items_listed} Listings | {followers} Followers | {following} Following

[About / Bio section]
[Verified badges]
```

### Seller Ratings
Mercari uses a 5-star system:
- Shown as overall average + total review count
- Individual reviews show star rating + text + date
- Rating breakdown by star level may be shown

### Listings Grid
Below profile header:
- Grid of active listings with photo, title, price
- Filter by category/status
- "Sold" items may also be visible

## Fields to Extract

| Field | Location | Notes |
|-------|----------|-------|
| display_name | Header | Seller's display name |
| user_id | URL | Numeric ID from `/u/{id}` |
| rating | Header | Average stars out of 5.0 |
| review_count | Header | Total number of ratings |
| items_listed | Stats or listings grid | Active listings count |
| items_sold | Profile or reviews | Inferred from review count or "sold" items |
| followers | Stats row | |
| following | Stats row | |
| about | Bio section | Seller's description |
| verified | Badge | "ID Verified" or "Email Verified" |
| location | Profile or listings | May be shown on listings |
| categories_observed | Listed items | What products are being sold |
| price_range | Listed items | Min/max prices seen |
| member_since | Profile | Account creation date |

## Extraction Method Priority
1. **get_page_text** (primary) — works well on Mercari
2. **Screenshot** (secondary) — for visual verification of listing content
3. **JavaScript** (rarely needed)

## 404 / Not Found Detection
- "This member's page is not available"
- "User not found"
- Redirect to Mercari homepage
- Empty page with no profile data

## Mercari-Specific Notes
- **ID Verified badge** = seller has verified their identity (moderate trust signal)
- **Quick Shipper badge** = ships within 1-2 days consistently
- **Rating system** — Below 4.0 stars is a red flag on Mercari; most active sellers have 4.5+
- **Items sold** — Mercari doesn't always show total sold count directly; review count is a proxy
- **Price comparison:** Mercari tends toward lower price points than eBay/Etsy. Very low prices ($1-5) on branded items = possible counterfeit flag
- **Inactive profiles:** If profile exists but has 0 listings and no recent activity, seller may have abandoned the platform

## Output Format
```yaml
platform: mercari
url: https://www.mercari.com/u/{id}
redirected_from: https://merc.li/{code}  # if applicable
status: active | 404 | inactive
display_name: string
user_id: string
rating: float or null  # out of 5.0
review_count: integer or null
items_listed: integer or null
items_sold: integer or null  # inferred from reviews if not shown
followers: integer or null
following: integer or null
about: string or null
verified: boolean
badges: [id_verified, quick_shipper, etc.]
location: string or null
member_since: string or null
categories_observed: [strings]
price_range: string or null
```
