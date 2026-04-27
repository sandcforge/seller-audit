# Facebook Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `../../seller-audit/references/schema-investigation.md`.

> **URL format rules** (profile vs marketplace vs groups, short links, etc.) → see `url-normalization.md` Facebook section.

### Login Wall Handling
Facebook frequently shows login walls. Strategies:
1. **Try `get_page_text` first** — sometimes returns content even with login wall
2. **Screenshot** — captures visible profile info above the login modal
3. **Marketplace profiles** (`/marketplace/profile/`) are often viewable without login
4. **If fully blocked:** Note "Facebook login wall — unable to verify" and move to other platforms. Do NOT ask user to log in unless all other platforms also fail.

## Page Types

### Personal Profile (`/profile.php?id=` or `/{username}`)
Visible info (may be limited by privacy settings):
- Profile name
- Profile photo
- Cover photo
- Bio / Intro section (location, work, education)
- Public posts (if any)

### Business Page (`/{pagename}`)
More useful for seller audits:
- Page name and category
- Follower/like count
- Business description
- Posts with product photos
- Reviews/recommendations
- Location, hours, contact info

### Marketplace Profile (`/marketplace/profile/{id}`)
Most valuable for seller audits:
- Seller name
- Location (city, state)
- Marketplace ratings (stars out of 5)
- Number of ratings
- Active listings with photos/prices
- "Joined Marketplace" date
- Response time

## Fields to Extract

| Field | Location | Notes |
|-------|----------|-------|
| name | Header | Profile name or page name |
| page_type | Inferred | personal / business_page / marketplace |
| followers | Below name (pages) | "X people follow this" |
| likes | Below name (pages) | "X people like this" |
| marketplace_rating | Marketplace profile | Stars out of 5 |
| marketplace_reviews | Marketplace profile | Number of ratings |
| location | Intro/About section | City, State |
| active_listings | Marketplace profile | Count of visible listings |
| categories_observed | Posts/listings | What products are being sold |
| joined_date | About section or marketplace | When profile/marketplace was created |
| business_category | Page info | e.g., "Shopping & Retail", "Pet Breeder" |

## Extraction Method Priority
1. **Screenshot** (primary) — captures header, follower count, visible content
2. **get_page_text** (secondary) — may work for public pages, often blocked by login wall
3. **WebSearch** (fallback) — `site:facebook.com "{seller name}"` can find public pages

## 404 / Not Found Detection
- "This content isn't available right now"
- "The page you requested was not found"
- "This Page Isn't Available" (deactivated or deleted)
- Redirect to Facebook homepage or login page with no profile content

## Facebook-Specific Notes
- **Privacy settings** heavily limit what's visible. If profile appears empty, it may just be private — do NOT treat this as "no footprint"
- **Marketplace ratings** are strong trust signals — rated sellers with 4.5+ stars are generally legitimate
- **Group links** (6.2% of URLs) do NOT identify a seller. Skip unless no other Facebook presence found, in which case note "only provided group link, not personal/business profile"
- **Multiple profiles:** Some sellers have both a personal profile AND a business page. Check both if found.
- **`?mibextid=` tracking param** appears on ~15% of URLs — always strip it

## Output Format
```yaml
platform: facebook
url: https://www.facebook.com/{path}
url_type: personal_profile | business_page | marketplace_profile | group
status: active | 404 | login_blocked
name: string
page_type: personal | business_page | marketplace
followers: integer or null
likes: integer or null
marketplace_rating: float or null  # out of 5.0
marketplace_reviews: integer or null
location: string or null
active_listings: integer or null
business_category: string or null
joined_date: string or null
categories_observed: [strings]
privacy_limited: boolean  # true if login wall blocked most content
```
