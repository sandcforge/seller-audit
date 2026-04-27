# eBay Store Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `../../seller-audit/references/schema-investigation.md`.

> **URL format rules** (short links, `/str/` vs `/usr/` vs `/itm/`, etc.) → see `url-normalization.md` eBay section.

## Redirect Handling

After URL normalization routes you to an eBay page, check what page type you landed on:
- `/str/{storename}` → Store page, proceed with store scraping below
- `/usr/{username}` → User profile page, proceed with profile scraping below
- `/itm/{id}` → Single listing, extract seller name from "Seller information" sidebar, then visit their store

### Store Page (`/str/`) vs User Profile (`/usr/`)
- `/str/` is the storefront view — shows store branding, categories, all listings
- `/usr/` is the seller profile view — shows feedback score, member since, recent feedback
- Both are valid; extract what's available from whichever page you land on
- If you have `/usr/`, you can construct `/str/` by visiting `ebay.com/str/{username}` (often same as username but not always)

### Single Item Page (`/itm/`)
If the URL is a single item listing:
1. Look for "Seller information" in the right sidebar
2. Extract the seller's username
3. Construct and visit `ebay.com/usr/{username}` or `ebay.com/str/{username}`

## Page Structure

### Store Page Header (`/str/`)
`get_page_text` often fails on eBay (returns minimal content or error). **Use screenshot** as primary extraction method.

The store header shows (left to right):
```
[Store Logo]  {Store Name}
              {feedback_pct}% positive feedback  |  {items_sold} items sold  |  {followers} followers
              [Share] [Contact] [Save Seller]
```

Below header:
```
[Categories]  [Shop]  [Sale]  [About]  [Feedback]    Search all {active_listings} items
```

### User Profile Page (`/usr/`)
The profile page shows:
```
{username}
Member since: {date}
{feedback_score} Feedback score
{feedback_pct}% Positive feedback
[Items for sale]  [Feedback ratings]
```

## Fields to Extract

| Field | Location (Store `/str/`) | Location (Profile `/usr/`) |
|-------|--------------------------|---------------------------|
| store_name / username | Header, large text | Header, large text |
| feedback_pct | Below store name | Below member since |
| feedback_score | Not always shown | Below member since |
| items_sold | After feedback % | Not always shown |
| followers | After items sold | Not always shown |
| active_listings | Search bar placeholder | "Items for sale" link |
| member_since | About tab | Below username |
| location | About tab | May not be shown |

## Extraction Method Priority
1. **Screenshot** (primary) — header metrics are visible in the top area
2. **get_page_text** (fallback) — often returns only product listings, not header
3. **JavaScript** (last resort) — extract from DOM if screenshot unclear

## 404 / Store Not Found Detection
- Page shows "This seller's shop isn't available right now" or "Oops" error
- Redirects to eBay search results instead of store page
- URL remains but page shows "Looking for {storename}? We couldn't find that store"
- Short link (`ebay.us/m/`) shows "Sorry, this link is no longer valid"

## eBay-Specific Metrics Notes
- **Positive feedback %** — Key trust signal. Below 95% = risk flag.
- **Items sold** — Lifetime total, not current month
- **Followers** — eBay followers are less meaningful than other platforms (low numbers are normal)
- **Active listings** — Current inventory size, found in search bar text
- **Feedback score** — Total number of feedback received (unique users), shown on `/usr/` pages

## About Tab (Store pages only)
Click "About" tab for additional info:
- Store description
- Location (city, state)
- Member since date
- Seller policies

## Feedback Tab
Click "Feedback" tab for:
- Recent review text
- Rating breakdown (positive/neutral/negative counts by period)
- Buyer comments

## Output Format
```yaml
platform: ebay
url: https://www.ebay.com/str/{storename}
redirected_from: https://ebay.us/m/{code}  # if applicable
url_type: store | profile | item_redirect
status: active | 404
store_name: string
username: string  # may differ from store_name
feedback_pct: number (0-100)
feedback_score: integer or null
items_sold: integer or null
followers: integer or null
active_listings: integer or null
location: string or null
member_since: string or null
categories_observed: [strings from product listings]
```
