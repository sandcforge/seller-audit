# Shiny Category SOP (Jewelry / Coins / Crystals)

**TRIGGER:** Apply if Category is Jewelry, Coins, or Crystals.

---

## PART A: Investigation Data Points

### 1. Jewelry/Luxury Audit (High Priority)
- **Brand Check:** Sells Luxury Brands? (Chanel, LV, Gucci, Rolex, Dior, Cartier, Armani, etc.)
- **Cultural Sensitivity:** Check for "Native American", "Navajo", "Zuni" keywords
- **Price Check:** Compare Listing Price vs Market Price (e.g. $20 for Chanel = Fake)
- **Upcycled Check:** Keywords "Upcycled", "Repurposed" — transparent about it?

### 2. US Location & Identity Verification
- Shipping: Long times (>10 days)? "Global Warehouse"?
- Carriers: Yanwen, 4PX, UniUni, CNE, China Post?
- Origin: Shenzhen, Guangzhou, Yiwu addresses? +86 phone? WhatsApp only? Pinyin email?
- Language: Broken English? "Factory Direct"?
- Policy: "Returns to China warehouse"?
- Phone/Address: US-based validation

### 3. Link Validation
- Must have valid shop/social link

### 4. Quantitative Metrics
- Inventory matches category
- Sales Count: Thresholds 50 (Credibility) / 5,000 (Valentin)
- Follower Count: Thresholds 5,000 / 20,000
- Reviews: >=10 with 4.5+ rating
- Live Stream Activity: Upcoming (bookmarks), Past (engagement), Frequency

---

## PART B: Verdict Decision

### STEP 1: Tier Classification (ANY signal qualifies)

| Tier | Sales | Followers | Other |
|------|-------|-----------|-------|
| **S (VIP)** | >30,000 | >20,000 (non-Poshmark) OR >100,000 (Poshmark, 3:1 ratio) | Bookmarks >200 |
| **A (High Potential)** | 5,000–29,000 | 10,000–19,999 | Reviews >200 (4.8+) |
| **B (Standard)** | 50–4,999 | 5,000–9,999 | Reviews >=10 (4.5+) |
| **F (Insufficient)** | <50 | <5,000 | Reviews <10 OR Rating <4.5 |

### STEP 2: Risk Assessment

- **HIGH RISK:** Luxury below market value, fraud/fakes, non-US coin seller, digital goods, MLMs, Tier F metrics with valid shop
- **MEDIUM RISK:** Upcycled luxury without authenticity proof, no valid link (Tier F exception), international jewelry/crystal
- **LOW RISK:** US-based, authentic engagement, credible metrics

### STEP 3: Decision Matrix

The `verdict` field is strictly tri-state: **APPROVE / REJECT / REVIEW**. Action tags
("Forward to Kay", "Policy Reminder", etc.) are NOT verdict values — write them into
`assessment.special_notes` instead.

| TIER / RISK | HIGH | MEDIUM | LOW |
|-------------|------|--------|-----|
| **S** | REVIEW | REVIEW | APPROVE |
| **A** | REJECT | REVIEW | APPROVE |
| **B** | REJECT | REVIEW | APPROVE |
| **F** | REJECT | REVIEW | REJECT |

### Required Special Notes phrasing (when applicable)
- Intl Jewelry/Crystal → "Forward to Kay"
- Missing Link → "Request More Info (Link)"
- Upcycled/Repurposed → "Policy Reminder"
