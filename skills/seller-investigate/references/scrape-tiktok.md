# TikTok Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `../../seller-audit/references/schema-investigation.md`.

> **URL format rules** (short links, missing `@`, tracking params, etc.) → see `url-normalization.md` TikTok section.

### Login Wall Handling
TikTok frequently shows login popups. Strategies:
1. **Screenshot first** — profile header is usually visible behind the popup
2. **get_page_text** — often returns profile stats even with login wall
3. **Close popup** if possible — look for X button or click outside modal
4. **If fully blocked:** Extract what's visible from screenshot and note "TikTok login wall limited extraction"

## Page Structure

### Profile Header
```
[@username]
[Profile Photo]
{following} Following  |  {followers} Followers  |  {likes} Likes
[Bio text]
[Link in bio if present]
```

### Profile Tabs
- **Videos** — Grid of posted videos (default tab)
- **Reposts** — Content reposted from others
- **Liked** — Usually hidden/private
- **LIVE** — If seller does live selling

## Fields to Extract

| Field | Location | Notes |
|-------|----------|-------|
| username | Header, starts with @ | e.g., `@plantmama2024` |
| display_name | Above username | May differ from username |
| followers | Stats row | Can use K/M notation: 1.2K = 1200, 1.5M = 1500000 |
| following | Stats row | |
| likes | Stats row | Total likes received on all videos |
| bio | Below stats | May contain shop links, business info |
| bio_link | Below bio | External link if present (e.g., Linktree, shop URL) |
| is_business | Badge/label | "Business account" or shop badge indicates TikTok Shop |
| is_verified | Checkmark | Blue checkmark next to name |
| video_count | Videos tab | Number visible or stated |
| categories_observed | Video content | What topics/products are posted about |

### Number Parsing (K/M notation)
TikTok uses abbreviated numbers:
- `1.2K` = 1,200
- `15.6K` = 15,600
- `1.5M` = 1,500,000
- `230` = 230 (no suffix = literal)

## Extraction Method Priority
1. **Screenshot** (primary) — header stats visible even with login wall
2. **get_page_text** (secondary) — often works, returns structured stats
3. **WebSearch** (fallback) — `site:tiktok.com "@username"` may find cached profile

## 404 / Not Found Detection
- "Couldn't find this account"
- "This account doesn't exist"
- Page redirects to TikTok homepage
- "Video is unavailable" (for short links to deleted videos)

## TikTok-Specific Notes
- **TikTok Shop badge** — If present, seller has an active TikTok Shop (strong signal for live selling capability)
- **Low follower counts are normal** for niche sellers — TikTok algorithm is content-based, not follower-based
- **Bio links** are very valuable — often link to Linktree, Whatnot, or other selling platforms
- **Live selling** — Check if seller has "LIVE" content or mentions going live in bio
- **Tracking params** (`?_t=`, `?is_from_webapp=`, `?refer=`) are very common — always strip

## Output Format
```yaml
platform: tiktok
url: https://www.tiktok.com/@{username}
redirected_from: https://vm.tiktok.com/{code}  # if applicable
status: active | 404 | login_blocked
username: string
display_name: string
followers: integer
following: integer
likes: integer
bio: string or null
bio_link: string or null
is_business: boolean
is_verified: boolean
video_count: integer or null
categories_observed: [strings]
login_wall_limited: boolean  # true if extraction was limited
```
