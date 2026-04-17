# CollX Scraping Guide

> **Common extraction flow:** Navigate → detect page type → check for 404/login wall → extract metrics via `get_page_text` or screenshot → record per-page data (see `loop-react.md` Section 2.5.5) → output YAML per `handoff-schema.md`.

> **URL format rules** (share links, profile URLs) → see `url-normalization.md` CollX section.

## Critical: Screenshot Does NOT Work

CollX profile pages render via client-side JavaScript. On desktop browsers, the central content area appears **completely blank** in screenshots. You MUST use `get_page_text` as the primary (and only reliable) extraction method. Do NOT rely on screenshots to determine whether the page has content.

## Critical: Wait for JS Rendering

CollX pages are fully client-side rendered and take significant time to load profile data. After navigating to a CollX URL, you **MUST wait at least 5 seconds** before calling `get_page_text`. Without this wait, `get_page_text` will return only header/footer content with no profile data, which looks identical to a 404 — causing a **false 404 misdiagnosis**.

If the first `get_page_text` call returns no profile data (no Items/Value/Followers stats), **wait another 5 seconds and retry** before concluding the page is a true 404. Only declare 404 after TWO failed attempts with adequate wait time.

## Page Structure

### Profile Page

`get_page_text` returns data in this order:

```
Learn More {display_name}Follow on CollX {items_count}Items${value}Value{followers}Followers{following}Following{bio_text}{card_1}{card_2}...Load more
```

The data is concatenated without clear delimiters. Parse using these anchors:
- Name: first text after "Learn More"
- "Follow on CollX" separates name from stats
- Stats block: `{N}Items${N}Value{N}Followers{N}Following`
- Bio: text between stats block and the first card entry
- Cards: repeating pattern of `{year} {set_name}#{number} {player_name} ${price}{grade}`

### Card Listing Format

Each card in the collection follows this pattern:
```
{year} {set_name} - {variant}#{card_number} {player_name} ${price}{grade}
```

Where `grade` is one of:
- `RAW` — ungraded card
- `PSA {N}` — Professional Sports Authenticator grade (1-10)
- `BGS {N}` — Beckett Grading Services grade
- `SGC {N}` — SGC grade

## Fields to Extract

| Field | Location | Notes |
|-------|----------|-------|
| display_name | After "Learn More" | Seller's display name |
| username | URL path | From `share.collx.app/{username}` |
| items_count | Stats block | Total items in collection |
| collection_value | Stats block | Dollar value of collection (CollX-estimated) |
| followers | Stats block | |
| following | Stats block | |
| bio | Between stats and cards | Seller's self-description |
| categories_observed | Card listings | Sports types: baseball, basketball, football, hockey, etc. |
| price_range | Card listings | Min/max prices from visible cards |
| grading_mix | Card listings | Ratio of RAW vs graded (PSA/BGS/SGC) cards — indicates professionalism |
| notable_cards | Card listings | High-value or notable player cards (useful for inventory quality assessment) |

## Extraction Method Priority

1. **get_page_text** (MANDATORY) — the only reliable method on desktop. Always use this first.
2. **Screenshot** — DO NOT use for data extraction. Screenshots show a blank page. Only useful to confirm the page loaded (header/footer visible).
3. **JavaScript** — fallback if `get_page_text` formatting changes.

## 404 / Not Found Detection

- Page title remains "CollX: Scan sports cards to find out what they're worth" but `get_page_text` returns NO profile data (no Items/Value/Followers stats)
- Redirect to CollX homepage without profile data
- Page shows only header + footer with no content in between (AND `get_page_text` also returns no profile data — distinguish from normal JS rendering delay)

## CollX-Specific Notes

- **Collection Value** is unique to CollX — no other platform shows estimated total collection value. Use this as a supplementary data point for inventory assessment, but note it reflects CollX's price estimates, not actual sale prices.
- **Grading mix** is a professionalism signal: sellers with a high proportion of PSA/BGS graded cards are more likely to be serious collectors/dealers vs casual hobbyists.
- **CollX is Collectibles-only** — specifically sports trading cards. If a seller provides a CollX link, this strongly confirms a Collectibles category. Apply `sop-collectibles.md`.
- **Items count ≠ items for sale.** CollX tracks a user's entire collection, not just items listed for sale. A user with 9,000 items may only be selling a fraction.
- **No reviews/ratings system.** CollX does not have seller reviews or transaction ratings. Use follower count and collection size as proxy signals.
- **"Load more" pagination** — `get_page_text` only returns the initially loaded cards (typically ~30). For a full inventory audit, this sample is sufficient.

## Output Format

```yaml
platform: collx
url: https://share.collx.app/{username}
status: active | 404 | empty
display_name: string
username: string
items_count: integer or null
collection_value: float or null  # dollar amount, CollX-estimated
followers: integer or null
following: integer or null
bio: string or null
categories_observed: [strings]  # e.g., ["baseball cards", "basketball cards"]
price_range: string or null  # e.g., "$0.30-$22.00"
grading_mix: string or null  # e.g., "mostly RAW, some PSA 8-10"
notable_cards: [strings] or null  # e.g., ["Caitlin Clark Prizm", "Kobe Bryant Anthology"]
```
