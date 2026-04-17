# Verdict Output Format

**When to read:** When writing the final verdict report (Section 3.3). This guide specifies the exact template and structural constraints for seller verdict reports.

---

## 3.3 Verdict Output Format

Produce a Markdown report for each seller individually (case by case). Do NOT produce executive summary tables or batch statistics — only individual seller sections.

**⚠️ STRICT TEMPLATE — follow this EXACTLY. Do not add, rename, or reorder sections.**

The report has exactly **3 blocks**: Header Table → Summary → Investigation Steps (verdict is the final step).

```
## Seller #N: [Full Name] ([Company Name if different])

**HubSpot:** https://app.hubspot.com/contacts/45316392/record/0-1/{contactId}

| Verdict | Tier | Risk | Category | Action |
|---------|------|------|----------|--------|
| **[APPROVE / REJECT / REVIEW]** | [S / A / B / F] | [LOW / MEDIUM / HIGH] | [Actual category] | [Concise action: what the onboarding team should do next] |

> [2–3 sentence summary. Sentence 1: key evidence (what was found). Sentence 2: main risk or strength. Sentence 3 (if needed): notable context like prior HubSpot status conflict or category mismatch.]

---

### Investigation Steps

[Narrate the audit chronologically — one step per action taken. Each step has a bold heading, what happened, and bullet-pointed signals/findings.]

**Step 1 — [Action description] (provided URL / Google Search / etc.)**
[What URL was visited, what happened (loaded / redirected / 404 / login wall)]

- **[Sub-area]:** [Finding]
- **Signal:** [What this tells us about the seller]

[If URL was dead, mark with ❌ DEAD in the heading]

**Step 2 — [Next action]**
[Continue chronologically...]

[...repeat for each action taken...]

**Step N — Verdict: Apply [Category] SOP**
[This is ALWAYS the final step. Show the verdict derivation:]
- Category: Applied as [X] → actual [Y]. [Mismatch or no mismatch.]
- Tier: [Key metrics] → **Tier [S/A/B/F]**.
- Risk: **[LOW/MEDIUM/HIGH]** — [Primary reason].
- Verdict matrix: Tier [X] + [risk] = **[VERDICT]**. [Any SOP override, e.g., Collectibles downgrade.]
- [If HubSpot status conflicts: Cross-check note.]
- [If APPROVE: "Standard onboarding, no special handling." or special handling from SOP.]
- [If REJECT: Brief rejection reason + any future reconsideration note.]
- [If REVIEW — include a checklist:]
  - **Review checklist:**
    - [ ] [Specific item for human reviewer]
    - [ ] [Another item]
  - Special Handling: [From SOP, or "None"]
```

**Format rules (MUST follow):**
- HubSpot contact link is REQUIRED for every seller
- Every platform URL must be full `https://` clickable format
- If a short link redirected, show: "Provided `[short URL]` → resolved to `[final URL]`"
- Dead URLs: include with ❌ DEAD marker in step heading

**Structural constraint:** The report MUST contain exactly 3 blocks in this order:
1. Header Table (seller name, HubSpot link, verdict/tier/risk/category/action table, summary quote)
2. Investigation Steps (chronological narrative, one bold heading per action)
3. Final Step — Verdict derivation (always the last step)

Any content that does not fit within these 3 blocks must be omitted. Do not add supplementary sections, appendices, metadata footers, confidence scores, or summary tables.

**Length guidance:**
- Clear APPROVE (strong seller): 30–50 lines
- Clear REJECT (dead links / disqualifier): 25–40 lines
- REVIEW (complex, multi-step investigation): 50–80 lines
- If your report exceeds 90 lines, you are being too verbose — cut redundancy
