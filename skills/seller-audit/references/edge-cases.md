# Cross-Cutting Edge-Case Protocols

**When to read:** During the investigation phase, load the relevant section as specific signals appear (China patterns, category mismatch, ambiguous name match, or tool failure).

---

## China Connection

**Trigger:** Signals that the seller may be operating from or routing inventory through China.

- Pinyin name/email + generic products = HIGH RISK
- Check for: Chinese text, grey/black poly mailers, Yanwen/SF Express labels, "Ships from China", Shenzhen/Guangdong addresses, +86 phone numbers, "Returns to China warehouse"

---

## Category Mismatch

**Trigger:** The seller's actual storefront content does not match their declared category (e.g., claimed "Plants" but sells Art, claimed "Fashion" but sells Jewelry).

1. Record the mismatch: claimed category vs. actual category observed in Chrome
2. **Switch to the actual category's SOP** for tier/verdict evaluation — do NOT use the claimed category's SOP
3. Re-read the correct SOP for the current sub-skill: `skills/seller-investigate/references/sop-{actual}.md` if you're still investigating, `skills/seller-verdict/references/sop-{actual}.md` if you're issuing the verdict. Each sub-skill owns its own scoped SOP — they share filenames but not content.
4. In the final verdict, explicitly flag the mismatch with: "⚠️ CATEGORY MISMATCH: Seller applied as [{claimed}] but actual content is [{actual}]. Evaluated using [{actual}] SOP."
5. If the mismatch is severe (completely unrelated categories), add this to Risk Flags and consider recommending REVIEW so a human can confirm the reassignment

---

## Name Ambiguity

**Trigger:** Online search uncovers records matching the applicant's name but you're unsure whether they refer to the same person.

- **Gold Match** (Name + Age + Location + Email) → flag immediately
- **Silver Match** (Name + Location + Middle name) → flag immediately
- **Bronze Match** (Name + Location only, common name) → search for tie-breaker before flagging. If no tie-breaker, verdict must be REVIEW, not REJECT.

### Attribution Discipline for P3 Platforms (search / username-guess)

For platforms found via P3 (Google Search, username guessing, etc. — i.e. NOT provided by the seller and NOT followed from a verified bio link), use `identity_score.py` and apply this rule:

| `match_level` (score) | Verdict computation | Action / Report treatment |
|---|---|---|
| `strong` (≥ 4) | Include the platform in `platforms[]` and use it in tier/risk math. | Normal. |
| `weak` (2–3), **does NOT swing the verdict** | Compute the verdict WITHOUT this platform. | Report it under a "Weak-identity matches (not attributed)" note in the audit. Do not let it move tier/risk numbers. |
| `weak` (2–3), **DOES swing the verdict** (including/excluding it produces different APPROVE/REJECT/REVIEW outcomes) | Compute the verdict WITHOUT this platform — i.e. the more conservative path. | Add an explicit Action item: **"Human reviewer must verify whether [URL] belongs to this applicant; the audit outcome is sensitive to this attribution."** This applies whether the swing would have raised or lowered the tier. |
| `none` (≤ 1) | Discard. | Not mentioned in the report. |

**Swing test procedure** when you have a weak match:
1. Compute the verdict with the weak-match platform included.
2. Compute the verdict with the weak-match platform excluded.
3. If the two verdicts differ on APPROVE/REJECT/REVIEW (or differ on tier in a way that meaningfully changes follow-up), the swing test FAILS — emit the conservative (excluded) verdict and add the human-review action.
4. If they agree, the weak match is informational only.

**Rationale:** Verdicts must not be driven by signals we can't confirm. But hiding a swing-relevant weak match deprives the human reviewer of the chance to confirm it — so we surface it as an explicit action, not by silently shifting the verdict.

---

## Tool Failure Recovery

**Trigger:** Broken links, inaccessible platforms, or tools that fail during investigation.

- **404 / Dead links** → first, verify URL integrity: go back to the original HubSpot raw URL and compare character-by-character with the URL you visited. If the URL was mutated (common with long concatenated store names), fix it and retry. If the URL matches exactly, apply URL normalization rules (e.g., Whatnot `/invite/` → `/user/`). If the normalized URL also fails, mark as dead and continue to next provided URL.
- **Whatnot short link** → visit in Chrome (it auto-redirects); do NOT try to WebSearch the short URL
- **Whatnot invite link** → replace `/invite/` with `/user/` in the URL
- **Login wall** → follow the login-wall protocol in the platform scrape guide (typically `get_page_text` → screenshot → try marketplace/profile URL variant). Stay in Chrome. Do NOT pivot to curl, WebFetch, or Googlebot-UA fetches — OG metadata is not sufficient evidence.
- **All provided URLs dead** → trigger Google Search fallback (Priority 3) in Chrome before concluding zero footprint
- **WebSearch returns nothing** → this does NOT mean seller has no presence; visit provided URLs in Chrome first
- **Tool errors in Chrome** → retry with screenshot-based extraction or an alternate URL variant. Still in Chrome.
- **Chrome itself unavailable** → stop and report back to the caller; do not complete the audit with non-Chrome fallbacks.
