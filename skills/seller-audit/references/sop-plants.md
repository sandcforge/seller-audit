# Plants Category SOP (Investigation + Verdict)

**TRIGGER:** Apply if Category is Plants, Flowers, or Gardening.

---

## PART A: Investigation Data Points

Extract the following. Mark **[NOT FOUND]** if unavailable.

### 1. Seller Identity & Referrals
- Primary Platform (Palmstreet, Whatnot, Instagram, Website)
- Username/Handle
- Referral Source (specific person or community mentioned?)
- US-Based: YES / NO / NOT FOUND

### 2. Inventory Quality Audit (Primary Lever)
- Plant Rarity: High-Value Plants (HVP) present? List examples. Mostly common big-box plants?
- Plant Maturity & Condition: Mature or cuttings? Overall health.

### 3. Pricing & Revenue Positioning

**Average Price Per Product (APP):**
- Lowest / Highest / Estimated APP

**APP Classification:**
- Rookie Signal: $0–$5
- Contact Signal: $5–$40
- White Glove Signal: $45+

**Checks:** Consistent $45+ present? Pricing aligns with rarity? Common plants overpriced?

### 4. Inventory Size & Depth

**Size Classification:** Micro (1-25) / Small (26-100) / Medium (101-300) / Large (301-1,000) / Enterprise (1,000+)

**Assessment:** Estimated active units, evidence source, signs of depth (multiple SKUs), replenishment visible, can support 1-2 shows/week?

### 5. Social & Platform Credibility

Metrics: IG Followers, Following, Avg Viewers, Review Score, Review Count, Engagement Quality.

**Follower Signal:** Established 10k+ / Strong 5k-10k / Growing 1k-5k / Minimal <500

---

## PART B: Verdict Decision

### Core Philosophy: INVENTORY SUPREMACY RULE

Inventory is evaluated across 3 dimensions: Quality (HVP), APP (pricing power), Size (scale capacity).

**USER DATA RULE:** If `inventory_size` and `average_product_price` from the application are not empty, prioritize them for Tier classification. State whether you used user-provided data or investigator estimates.

Key principles:
- APP $45+ with strong HVP can elevate tier even if social metrics are weaker
- APP under $5 caps seller at Tier B maximum
- Large cheap inventory does NOT elevate tier
- A single High-Risk finding can override all other metrics

### STEP 1: Risk Assessment

**[MISSING_INFO]:** No valid storefront or social media link found.

**[HIGH_RISK]** if ANY:
- Not US-based
- Fraud indicators in visuals or text
- Only common plants + inflated pricing
- Severe negative reviews (dead plants, no delivery)
- Garage-sale presentation (messy, poor lighting, poor plant health)

### STEP 2: Tier Classification

| Tier | Inventory Quality | APP | Inventory Size | Credibility |
|------|------------------|-----|---------------|-------------|
| **S (White Glove)** | Strong HVP, mature collector | $45+ consistent | Medium+ (100+) | 10k+ OR strong show history |
| **A (Contact)** | Good mix HVP + desirable common | $5–$40 (some $45+) | Small-Medium (26–300) | 5k–10k OR 50+ avg viewers |
| **B (Rookie)** | Mostly common, healthy | $0–$5 | Micro-Small (1–100) | 1k–5k OR 10–30 viewers |
| **F (Reject)** | Only big-box | Under $5 | Micro, no depth | <500, no shows |

### STEP 3: Final Routing

1. HIGH_RISK + Tier S → **REVIEW**
2. HIGH_RISK + NOT Tier S → **REJECT**
3. MISSING_INFO → **REVIEW** (Action: Contact seller for valid link)
4. Tier S (no risks) → **ESCALATE_TO_MADDY** (VIP/White Glove)
5. Tier A → **APPROVE** (Tag: CONTACT_SELLER)
6. Tier B → **APPROVE** (Tag: ROOKIE_SELLER)
7. Tier F (no missing info) → **REJECT**

### Required Action Notes
- Tier S: "Escalate to Maddy for VIP onboarding"
- Missing Link: "Request More Info (Link) — Follow up applicant"
