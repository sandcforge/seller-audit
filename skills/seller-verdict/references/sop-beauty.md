# Beauty Category SOP (Makeup / Skincare / Fragrance / Hair) — Verdict Decision
**TRIGGER:** Apply if Category is Beauty, Makeup, Skincare, Fragrance, or Hair.

**GOLDEN RULE:** Verify if the applicant fits the "Sephora-level" standard. They must have EITHER excellent inventory (Sephora/Ulta quality) OR strong hosting capabilities.

---

## Verdict Decision
### STEP 1: Tier Classification (highest met, platform-weighted)

| Tier | IG/FB/WN Followers | TikTok Followers | Other Signals |
|------|-------------------|-----------------|---------------|
| **S (VIP)** | >10,000 | >50,000 | VIP Referral, WN Bookmarks >50, Avg Viewers >100, Premier/Ambassador II |
| **A (Ideal)** | 5,000–10,000 | 10,000–50,000 | WN Bookmarks 20-50, Sephora brands, Boutique vibe, Rating >=4.9 |
| **B (Rookie)** | 1,000–5,000 | 5,000–10,000 | WN Bookmarks 10-20, Curated Sephora/Ulta, Live history |
| **F (Reject)** | <1,000 | <5,000 | WN Bookmarks <10, Drugstore only |

### STEP 2: Risk Classification

- **HIGH (Blocker):** Garage Sale vibe, ONLY drugstore brands, ONLY GWP/Testers, banned, fake followers
- **MEDIUM:** Follower:Following ratio <1:1, non-US
- **LOW:** US-based, physical inventory, boutique presentation, Sephora brands

### STEP 3: Routing

The `verdict` field is strictly tri-state: **APPROVE / REJECT / REVIEW**. Routing tags
(ESCALATE_TO_RAJ, FLAG_TO_JAMES, etc.) are NOT verdict values — write them into
`assessment.special_notes` instead.

1. VIP Referral OR Tier S → `verdict: APPROVE` · `special_notes: "Escalate to Raj"`
2. Pure Influencer (high followers, no stock) → `verdict: REVIEW` · `special_notes: "Flag to James — Affiliate candidate"`
3. HIGH RISK or Tier F (no VIP referral) → `verdict: REJECT`
4. (Tier A or B) + LOW RISK → `verdict: APPROVE`
5. Anything else (e.g. MEDIUM risk in A/B) → `verdict: REVIEW`
