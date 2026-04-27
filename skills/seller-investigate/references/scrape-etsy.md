# Etsy Shop Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `../../seller-audit/references/schema-investigation.md`.

## URL Patterns
- Shop page: `https://www.etsy.com/shop/{ShopName}`
- Buyer profile: `https://www.etsy.com/people/{username}` (NOT a shop — this is a buyer page)

## Page Text Pattern
The `get_page_text` output follows this structure:
```
{ShopName} {Location} Latest activity: {date}
{sales_count} Sales {rating} ({review_count}) {years} years on Etsy
...
About {ShopName}
{description}
Sales {total_sales}
On Etsy since {year}
...
Shop members
{owner_name} Owner
```

## Fields to Extract

| Field | Location | Example |
|-------|----------|---------|
| shop_name | First text element | `GemstoneCircleAU` |
| location | After shop name | `South Australia, Australia` |
| last_activity | After "Latest activity:" | `Feb 14, 2026` |
| sales_count | Before "Sales" | `9.1k` → parse as 9100 |
| rating | Before "(X)" | `4.9` |
| review_count | Inside parentheses | `1.9k` → parse as 1900 |
| years_on_etsy | Before "years on Etsy" | `9` |
| listing_count | "All (N)" in tab area | `173` |
| admirers | In about section | `3343 Admirers` |
| owner_name | Under "Shop members" | `Kate` |
| description | Under "About" heading | Shop description text |
| on_etsy_since | In about section | `2016` |

## Number Parsing
- `9.1k` = 9,100
- `1.9k` = 1,900
- Plain numbers = as-is

## Shop vs Buyer Profile
- **Shop URL** (`/shop/Name`): Shows sales, ratings, listings, about section
- **Buyer URL** (`/people/name`): Shows favorites, wishlists — NOT a seller page
- If `/shop/Name` redirects to `/people/name`, the seller has NO Etsy shop

## 404 Detection
- "Uh oh! Sorry, the page you were looking for was not found" = shop doesn't exist
- Redirect to Etsy homepage or search = shop removed/closed

## Key Signals for Seller Audit
- **"Latest activity" date** — If months ago, shop may be dormant
- **Sales count vs review count** — High sales + low reviews is normal; low sales + 0 reviews = new/inactive
- **"On vacation" banner** — Shop temporarily closed
- **Location** — Non-US location = potential risk flag for some SOPs
- **Admirers count** — Fans who saved the shop (found in about section)

## Etsy Star Seller Badge
Look for "Star Seller" badge near shop name — indicates:
- 95%+ 5-star reviews
- Ships on time
- Responds to messages quickly

## Output Format
```yaml
platform: etsy
url: https://www.etsy.com/shop/{ShopName}
status: active | vacation | 404
shop_name: string
location: string
last_activity: date string
sales: integer
rating: number (0-5)
reviews: integer
years_on_etsy: integer
active_listings: integer
admirers: integer
owner_name: string
is_star_seller: boolean
categories_observed: [strings from listing categories]
```
