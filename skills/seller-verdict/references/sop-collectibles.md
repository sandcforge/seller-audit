# Collectibles Category SOP (Cards / Toys / Games / Memorabilia) — Verdict Decision
**TRIGGER:** Apply if Category is Collectibles, Trading Cards, Toys, Action Figures, Video Games, or Memorabilia.

**CRITICAL MANDATE:** NEVER reject outright. All would-be REJECTs MUST be downgraded to REVIEW.

---

## Verdict Decision
### STEP 1: Tier Classification (WhatNot OR Social scale)

| Tier | WhatNot | Social (IG/FB/TT) |
|------|---------|-------------------|
| **S (Superior)** | >10K followers AND >2K sold AND >=4.9 | >20K followers |
| **A (Above Average)** | >5K followers AND >1K sold AND >=4.9 | >5K followers |
| **B (Basic)** | >1K followers AND >200 sold AND >=4.8 | >500 followers |
| **F (Fail)** | <1K followers OR <200 sold OR <4.8 | No presence OR <500 |

### STEP 2: Risk Assessment

- **HIGH:** No WhatNot sales/review history, evidence of fraud/fakes
- **MEDIUM:** WhatNot rating <4.8, non-US seller
- **LOW:** Limited presence (likely rookie)

### STEP 3: Routing (NEVER use REJECT)

The `verdict` field is strictly tri-state: **APPROVE / REJECT / REVIEW**. Routing tags
(ESCALATE_TO_ME_S_TIER, ESCALATE_TO_ME_A_TIER, etc.) are NOT verdict values — write them
into `assessment.special_notes` instead. For Collectibles, REJECT is never used —
downgrade to REVIEW.

1. HIGH/MEDIUM RISK or Tier F → `verdict: REVIEW` · `special_notes` cites the specific risk; if non-US add "Forward to Kay"
2. Tier S → `verdict: APPROVE` · `special_notes: "Escalate to User (S Tier)"`
3. Tier A → `verdict: APPROVE` · `special_notes: "Escalate to User (A Tier)"`
4. Tier B (no risk) → `verdict: APPROVE`

**Notes:** Tier S/A must state "Escalate to User" in `special_notes`. Non-US always → REVIEW with "Forward to Kay" in `special_notes`.
