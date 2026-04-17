# Seller Audit Test Cases

20 real-world test cases

| # | Seller | Primary URL | Test Scenario | Expected Skill Behavior |
|---|--------|------------|---------------|------------------------|
| 1 | Killa Savong | `whatnot.com/invite/tommysavage` | Whatnot invite→user conversion | URL normalization converts `/invite/` to `/user/tommysavage`, visits in Chrome |
| 2 | Richard Saba | `Rms2.llc @gmail.com` | Email in URL field (junk) | Junk detection skips this, relies entirely on username-constructed URLs |
| 3 | James Doherty | `ebay.com/str/granitestatecoinsandcurrency` | eBay `/str/` store page | eBay scraping guide extracts store metrics via screenshot |
| 4 | Justin | `ebay.us/m/W7NwmY` | eBay short link (58.8% of eBay URLs) | Chrome visits short link, follows redirect, scrapes landing page |
| 5 | Gavin Nabors | `facebook.com/share/1E2e234dQb/` | Facebook share link redirect | Chrome visits share link, follows redirect to profile/page |
| 6 | Suphitsara Jaichum | `vt.tiktok.com/ZS9L6WKuLR8Xu-iuV2D/` | TikTok short link + non-US phone (+66) | TikTok short link redirect + China Connection Protocol trigger |
| 7 | Amy McDermott | `poshmark.com/closet/theatomicapron` | Poshmark closet URL | New Poshmark scraping guide extracts closet metrics |
| 8 | Gabriela Carreon Cruz | `mercari.com/u/shoppe?sv=0` | Mercari profile URL | New Mercari scraping guide + strip `?sv=0` tracking param |
| 9 | Abdul Hamid | `instagram.com/kingdom_bonsai.id?igsh=...` | Instagram tracking params + non-US phone (+62) | Strip `?igsh=` param + China Connection Protocol (Indonesia) |
| 10 | Andrew Stump | `ebay.com/sch/i.html?_ssn=estate.auctions&store_name=illselliforyou&...` | eBay search URL (edge case) | URL normalization should flag as non-standard, attempt to extract store_name and construct `/str/` URL |
| 11 | Nadya Langdon | `whatnot.com/s/VBXLBG5u` | Whatnot short link `whatnot.com/s/` (63% of Whatnot URLs) | Chrome visits short link, follows redirect to `/user/` profile, scrapes Whatnot |
| 12 | Charlene Loy | `posh.mk/IKHYpjg7g2b` | Poshmark short link (NOT in url-normalization.md!) | Chrome visits short link, follows redirect to `/closet/` page |
| 13 | Glenda Stahl | `http://whatnot.com` | Bare platform homepage (junk URL) | Junk detection skips — homepage with no path = no profile |
| 14 | Kesley Hill | `facebook.com/marketplace/profile/1006230049/?ref=permalink&mibextid=6ojiHh` | Facebook marketplace profile URL (19.4% of FB URLs) | Strip tracking params, visit marketplace profile, scrape with Facebook guide |
| 15 | Tara Vanicor | `instagram.com/brian.pearlexotics?igsh=ejknOWJ1MWskOXph&utm_source=qr` | Instagram with MULTIPLE tracking params | Strip both `?igsh=` AND `&utm_source=qr`, visit clean profile |
| 16 | Ryder Whitenack | `youtube.com/@LivelyTerrarrium` | YouTube URL (no scraping guide exists) | Skill must handle non-standard platform gracefully |
| 17 | Keisha Owens | `share.collx.app/VeteransCards79` | CollX share link (unknown platform) | Skill must handle completely unknown platform |
| 18 | James Sacksteder | `earthartexoticplants.com/` | Personal website (non-platform URL) | Visit custom domain in Chrome, extract what's visible |
| 19 | Jasmin Kilgore | `facebook.com/share/g/1EYBr95TBg/?mibextid=wwX1fr` | Facebook GROUP share link (should be junk) | Should detect `/share/g/` as group link and skip (or flag as low-value) |
| 20 | Yansen Setiawan | `instagram.com/bigdvsfish` | Plain Instagram + Indonesian name | Tests whether Indonesian-sounding name triggers location investigation |

## Coverage Matrix

| Category | Cases |
|----------|-------|
| **URL Normalization** | #1, #8, #9, #10, #14, #15 |
| **Short Link Redirect** | #4, #6, #11, #12 |
| **Junk Detection** | #2, #13, #19 |
| **Platform Scraping** | #3, #7, #8, #14 |
| **Unknown/Edge Platform** | #16, #17, #18 |
| **Share/Redirect Links** | #5, #12, #19 |
| **China Connection / Non-US** | #6, #9, #20 |
| **Google Search Fallback** | #2 (only URL is junk, must rely on search) |
