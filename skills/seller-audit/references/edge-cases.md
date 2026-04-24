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
3. Re-read the correct `sop-{actual}.md` (Part A for investigation + Part B for verdict)
4. In the final verdict, explicitly flag the mismatch with: "⚠️ CATEGORY MISMATCH: Seller applied as [{claimed}] but actual content is [{actual}]. Evaluated using [{actual}] SOP."
5. If the mismatch is severe (completely unrelated categories), add this to Risk Flags and consider recommending REVIEW so a human can confirm the reassignment

---

## Name Ambiguity

**Trigger:** Online search uncovers records matching the applicant's name but you're unsure whether they refer to the same person.

- **Gold Match** (Name + Age + Location + Email) → flag immediately
- **Silver Match** (Name + Location + Middle name) → flag immediately
- **Bronze Match** (Name + Location only, common name) → search for tie-breaker before flagging. If no tie-breaker, verdict must be REVIEW, not REJECT.

---

## Tool Failure Recovery

**Trigger:** Broken links, inaccessible platforms, or tools that fail during investigation.

- **404 / Dead links** → first, verify URL integrity: go back to the original HubSpot raw URL and compare character-by-character with the URL you visited. If the URL was mutated (common with long concatenated store names), fix it and retry. If the URL matches exactly, apply URL normalization rules (e.g., Whatnot `/invite/` → `/user/`). If the normalized URL also fails, mark as dead and continue to next provided URL.
- **Whatnot short link** → visit in Chrome (it auto-redirects); do NOT try to WebSearch the short URL
- **Whatnot invite link** → replace `/invite/` with `/user/` in the URL
- **Login wall** → do not retry same tool, pivot to Google Search fallback or web search
- **All provided URLs dead** → trigger Google Search fallback (Priority 3) before concluding zero footprint
- **WebSearch returns nothing** → this does NOT mean seller has no presence; visit provided URLs in Chrome first
- **Tool errors** → fallback to web search or screenshot-based extraction
