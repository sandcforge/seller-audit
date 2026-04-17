# Instagram Profile Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `handoff-schema.md`.

## URL Patterns
- Profile: `https://www.instagram.com/{username}/`
- Alternative: `https://instagram.com/{username}`

## Page Text Pattern
The `get_page_text` output follows this structure:
```
{username}Options{display_name}{post_count} posts{followers} followers{following} following{account_type}{bio_text} Follow Message
```

## Fields to Extract

| Field | Location | Example |
|-------|----------|---------|
| username | First text element | `big.isopods` |
| display_name | After "Options" | `Big.isopods` |
| post_count | Before "posts" | `24` |
| followers | Before "followers" | `171` |
| following | Before "following" | `81` |
| account_type | After following count | `Pet Breeder`, `Shopping & Retail`, `Artist`, etc. |
| bio | After account type | Free text, may contain business info |
| highlights | Named story highlights | e.g., "New additions", "Photography", "orders" |
| content_types | Grid labels | `Post`, `Reel`, `Clip`, `Carousel` |

## Account Type Indicators
- **Business account:** Shows category label (Pet Breeder, Shopping & Retail, Product/Service, etc.)
- **Personal account:** No category label between following count and bio
- **Creator account:** May show "Creator" or specific creator category

## Key Bio Signals for Seller Audit
- `DM to order` / `pm me` / `DM for pricing` → active seller
- `Shop link in bio` / `linktr.ee` / `linkpop.com` → follow the link (Section 2.5)
- Website URL in bio → visit in Chrome
- `📍 {City, State}` → location info
- Emoji-heavy bio with product descriptions → business account

## Login Wall Detection
- If page shows "Log in to Instagram" or only partial content → Instagram requires login
- Fallback: use `get_page_text` which often works even without login
- If still blocked: note "Instagram login wall" and move on

## Private Account Detection
- Page shows "This account is private" → note as MEDIUM risk flag
- Cannot extract follower content, only follower/following counts

## 404 Detection
- "Sorry, this page isn't available" = account doesn't exist
- Blank/minimal content after username = likely 404 or suspended

## Output Format
```yaml
platform: instagram
url: https://www.instagram.com/{username}/
status: active | private | 404 | login_wall
username: string
display_name: string
posts: integer
followers: integer
following: integer
account_type: string (business category or "personal")
bio: string
external_links: [urls found in bio]
is_business: boolean
location: string or null
content_signals: [list of observed content themes]
```
