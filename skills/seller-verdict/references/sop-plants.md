# Plants Category SOP — Verdict Decision
**TRIGGER:** Apply if Category is Plants, Flowers, or Gardening.

---

## Verdict Decision
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

The `verdict` field is strictly tri-state: **APPROVE / REJECT / REVIEW**. Routing tags
(ESCALATE_TO_MADDY, CONTACT_SELLER, ROOKIE_SELLER, etc.) are NOT verdict values — write
them into `assessment.special_notes` instead.

1. HIGH_RISK + Tier S → `verdict: REVIEW`
2. HIGH_RISK + NOT Tier S → `verdict: REJECT`
3. MISSING_INFO → `verdict: REVIEW` · `special_notes: "Contact seller for valid link"`
4. Tier S (no risks) → `verdict: APPROVE` · `special_notes: "Escalate to Maddy for VIP onboarding (White Glove)"`
5. Tier A → `verdict: APPROVE` · `special_notes: "Tag: CONTACT_SELLER"`
6. Tier B → `verdict: APPROVE` · `special_notes: "Tag: ROOKIE_SELLER"`
7. Tier F (no missing info) → `verdict: REJECT`

### Required Special Notes phrasing (when applicable)
- Tier S → "Escalate to Maddy for VIP onboarding"
- Missing Link → "Request More Info (Link) — Follow up applicant"
