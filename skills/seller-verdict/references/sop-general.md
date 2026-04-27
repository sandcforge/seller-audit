# General Category SOP — Verdict Decision
**TRIGGER:** Apply when category does not match Plants, Shiny, Beauty, or Collectibles.

---

## Verdict Decision
### STEP 1: Tier Classification

| Tier | Volume | Presentation | Maturity |
|------|--------|-------------|----------|
| **S (Elite)** | >5,000 sold or Top-Rated | Professional, branded, large-scale | High social following (>10k) with engagement |
| **A (Professional)** | >500 sold | High-quality photography, consistent branding | >1 year established |
| **B (Hobbyist)** | <500 sold | Authentic content | Side hustle, handmade, casual reseller |
| **F (Invalid)** | N/A | Empty shop, abandoned, 404 | Prohibited (Services, Digital, MLMs) |

### STEP 2: Risk Assessment

- **HIGH (REJECT):** Stolen photos, identity theft, dropshipping (Pinyin + stock photos), Western name + Pinyin email, prohibited items
- **MEDIUM (REVIEW):** Private profile, empty shop, name mismatch, long "On Vacation"
- **LOW (PASS):** US location, physical inventory, active shop, discrepancies resolved

### STEP 3: Decision Matrix

The `verdict` field is strictly tri-state: **APPROVE / REJECT / REVIEW**. Any escalation
or routing notes go into `assessment.special_notes`, never into the verdict.

| TIER / RISK | HIGH | MEDIUM | LOW |
|-------------|------|--------|-----|
| **S** | REVIEW | REVIEW | APPROVE |
| **A** | REJECT | REVIEW | APPROVE |
| **B** | REJECT | REVIEW | APPROVE |
| **F** | REJECT | REJECT | REJECT |
