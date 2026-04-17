# URL Normalization & Validation Reference

## General Cleanup (apply to ALL URLs first)

1. **Trim whitespace** and remove surrounding quotes
2. **Fix broken protocols:** `http//` → `https://`, `htp://` → `https://`, add `https://` if missing
3. **Extract URLs from free text:** Some sellers paste sentences like "my store is whatnot.com/user/abc" — extract the URL portion
4. **Multiple URLs in one field:** Split on spaces/commas, process each separately
5. **Deduplicate:** Website URL and Social Media fields are often identical — only visit once
6. **Strip common tracking params** from all URLs: `?utm_source=`, `?utm_medium=`, `?utm_campaign=`, `?ref=`, `?fbclid=`, `?gclid=`

## Platform-Specific Normalization

Rules by platform, ordered by URL volume (highest first). Based on real data from 27,650 HubSpot contacts.

**Instagram** (most common, ~35% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `instagram.com/{username}` | ✅ Valid profile | Standard format (55.7%) |
| `instagram.com/{username}?igsh=...` | Strip `?igsh=` param | Tracking param, 10.8% of URLs |
| `instagram.com/{username}?utm_...` | Strip `?utm_` params | Marketing tracking |
| `instagram.com/reel/{id}` | ⚠️ Extract username from page | Single reel, not a profile (3.1%) |
| `instagram.com/p/{id}` | ⚠️ Extract username from page | Single post, not a profile |
| `instagram.com` (no username) | ❌ Skip | Homepage only (1.2%) |
| Free text with no URL | ❌ Skip | Just a username string — construct `instagram.com/{text}` if it looks like a username |

**Whatnot** (~23% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `whatnot.com/s/{code}` | Visit in Chrome | Short link (63%), auto-redirects to profile |
| `whatnot.com/user/{username}` | ✅ Valid profile | Correct profile URL (7%) |
| `whatnot.com/invite/{username}` | Convert to `/user/{username}` | Referral page, NOT profile (13.8%) |
| `whatnot.com/live/{id}` | ⚠️ Visit, extract seller username | Live stream link (2.5%) |
| `whatnot.com` (no path) | ❌ Skip | Homepage only |
| Strip `?referral_source=` | Always | Tracking param |

**Facebook** (~20% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `facebook.com/{username}` | ✅ Valid profile/page | Standard format (33.3%) |
| `facebook.com/marketplace/profile/{id}` | ✅ Visit | Marketplace seller profile (19.4%) |
| `facebook.com/profile.php?id={id}` | ✅ Visit | Numeric profile (11.3%) |
| `fb.me/{code}` | Visit in Chrome | Short link, auto-redirects |
| `facebook.com/groups/{id}` | ❌ Skip | Group link, not seller profile (6.2%) |
| `facebook.com/share/...` | ⚠️ Visit in Chrome | Share link, may redirect to profile |
| `facebook.com` (no path) | ❌ Skip | Homepage only |
| Strip `?mibextid=` | Always | Tracking param |

**TikTok** (~5% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `tiktok.com/@{username}` | ✅ Valid profile | Standard format (72.5%) |
| `tiktok.com/@{username}?_t=...` | Strip `?_t=` and `?is_from_webapp=` | Tracking params |
| `vm.tiktok.com/{code}` | Visit in Chrome | Short link (7.4%), auto-redirects |
| `tiktok.com/{username}` (no @) | Add `@` prefix | Missing @ (3.4%) |
| `tiktok.com` (no username) | ❌ Skip | Homepage only |

**Etsy** (~4.5% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `etsy.com/shop/{Name}` | ✅ Valid shop | Standard format (62.8%) |
| `{Name}.etsy.com` | ✅ Valid shop | Subdomain format, equivalent |
| `etsy.me/{code}` | Visit in Chrome | Short link, auto-redirects |
| `etsy.com/listing/{id}` | ⚠️ Extract shop name from page | Single listing, not shop (8.4%) |
| `etsy.com/shop/{Name}?ref=...` | Strip `?ref=` | Tracking param |
| `etsy.com/people/{username}` | ⚠️ Buyer profile | NOT a shop — may indicate no active shop |
| `etsy.com` (no path) | ❌ Skip | Homepage only |

**Poshmark** (~4% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `poshmark.com/closet/{username}` | ✅ Valid closet | Standard format (75.8%) |
| `poshmark.com/closet/{username}?utm_...` | Strip `?utm_` params | Tracking |
| `poshmark.com/listing/{id}` | ⚠️ Extract seller from page | Single listing (5.6%) |
| `poshmark.com` (no path) | ❌ Skip | Homepage only |

**eBay** (~3% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `ebay.us/m/{code}` | Visit in Chrome | Short link (58.8%!), auto-redirects to store/profile |
| `ebay.com/usr/{username}` | ✅ Valid profile | User profile (8.3%) |
| `ebay.com/str/{storename}` | ✅ Valid store | Store page (6.3%) |
| `ebay.com/itm/{id}` | ⚠️ Extract seller from page | Single listing (3.9%), not a store |
| `ebay.com` (no path) | ❌ Skip | Homepage only |

**Mercari** (~1.6% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `mercari.com/u/{id}` | ✅ Valid profile | Standard format (majority) |
| `merc.li/{code}` | Visit in Chrome | Short link, auto-redirects |
| `mercari.com/item/{id}` | ⚠️ Extract seller from page | Single listing |
| `mercari.com` (no path) | ❌ Skip | Homepage only |

**CollX** (<1% of all URLs):
| URL Pattern | Action | Notes |
|---|---|---|
| `share.collx.app/{username}` | ✅ Valid profile | Standard share link. **MUST use `get_page_text`** — screenshots show blank page |
| `collx.app/{username}` | ✅ Valid profile | Alternative format |
| `share.collx.app` (no path) | ❌ Skip | Homepage only |

## Junk Detection (skip without Chrome visit)

Skip these entirely — they provide no investigative value:

- **Email addresses** in URL fields (e.g., `Rms2.llc@gmail.com`)
- **Platform homepages** with no username/path (e.g., bare `instagram.com`, `tiktok.com`)
- **My-account / login / settings pages** (e.g., `etsy.com/your/account`, `poshmark.com/account/login`)
- **Group links** that don't identify a seller (`facebook.com/groups/...`)
- **Search result URLs** (e.g., `google.com/search?q=...`)
- **Obvious non-URLs** (phone numbers, plain text descriptions, single words)
