# Shiny Category SOP (Jewelry / Coins / Crystals) — Verdict Decision
**TRIGGER:** Apply if Category is Jewelry, Coins, or Crystals.

---

## Verdict Decision
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
