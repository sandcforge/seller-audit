# Verdict Output Format

**When to read:** When writing the final verdict report (Section 3.3). This guide specifies the exact template and structural constraints for seller verdict reports.

---

## 3.3 Verdict Output Format

Produce one Markdown report per audit invocation (one seller). The report is the individual seller section described below — there is no wrapping summary, table-of-sellers, or executive overview.

**⚠️ STRICT TEMPLATE — follow this EXACTLY. Do not add, rename, or reorder sections.**

The report has exactly **2 blocks**: Conclusion → Investigation Steps. The verdict derivation lives inside the Conclusion section — it is no longer the final investigation step. The previous header (seller name + HubSpot link), the summary table (Verdict / Tier / Risk / Category / Action), and the 2–3 sentence blockquote have all been removed: identifying info is already on the HubSpot Contact record and in the BQ row's `vid` / `user_id` / `full_data` columns, and Conclusion supersedes the table + blockquote.

```
## Conclusion

1. **Final Verdict: [APPROVE / REJECT / REVIEW]** _(Category: [Actual category])_
   - [Bullet 1 — what the audit found at the highest level / what drove the call.]
   - [Bullet 2 — optional supporting point.]
   - [Bullet 3 — optional supporting point.]

2. **Special Notes:**
   - [Anything onboarding / human reviewers need to know that isn't already in tier / risk justifications. Use this for: action items ("Notify GTM Valentin", "Verify Whatnot identity"), REVIEW checklists, escalation routes ("Escalate to Maddy for VIP onboarding — Tier S Plants seller"), or context that explains a signal ("Inventory mismatch is consistent with livestream-only Whatnot model"). Omit / render as `_None_` when there's nothing to add.]

3. **Quality Tier: [S / A / B / F]**
   - [Bullet 1 — the metric or threshold that placed the seller in this tier.]
   - [Bullet 2 — optional supporting evidence (consistency across platforms, presentation quality, etc.).]
   - [Bullet 3 — optional.]

4. **Risk Level: [LOW / MEDIUM / HIGH]**
   - [Bullet 1 — the dominant signal (dead links, inconsistent claims, AI imagery, China-connection, or "no fraud signals detected").]
   - [Bullet 2 — optional secondary signal.]
   - [Bullet 3 — optional.]

---

## Investigation Steps

[Narrate the audit chronologically — one step per action taken. Each step has a bold heading, what happened, and bullet-pointed signals/findings.]

**Step 1 — [Action description] (provided URL / Google Search / etc.)**
[What URL was visited, what happened (loaded / redirected / 404 / login wall)]

- **[Sub-area]:** [Finding]
- **Signal:** [What this tells us about the seller]

[If URL was dead, mark with ❌ DEAD in the heading]

**Step 2 — [Next action]**
[Continue chronologically...]

[...repeat for each action taken — the verdict derivation does NOT appear here.]
```

**Format rules (MUST follow):**
- Do NOT include a seller-name header or HubSpot link inside the report — that info lives on the HubSpot Contact record and in the BQ row's `vid` / `user_id` / `full_data` columns.
- Every platform URL must be full `https://` clickable format
- If a short link redirected, show: "Provided `[short URL]` → resolved to `[final URL]`"
- Dead URLs: include with ❌ DEAD marker in step heading
- The verdict derivation lives in the Conclusion section, NOT as a final investigation step. Do not add a `Step N — Verdict: Apply [Category] SOP` row at the end of Investigation Steps.
- **Conclusion bullets are 1–3 each.** Final Verdict, Quality Tier, and Risk Level each get between 1 and 3 short bullets — no more. If you need more space to explain something, push it into Special Notes or Investigation Steps. Each bullet should stand alone (one fact / one signal / one threshold).

**Structural constraint:** The report MUST contain exactly 2 blocks in this order:
1. Conclusion (Final Verdict, Special Notes, Quality Tier, Risk Level — in that numbered order)
2. Investigation Steps (chronological narrative, one bold heading per action; the verdict is NOT a step here)

Any content that does not fit within these 3 blocks must be omitted. Do not add supplementary sections, appendices, metadata footers, confidence scores, or summary tables.

**Length guidance:**
- Clear APPROVE (strong seller): 30–50 lines
- Clear REJECT (dead links / disqualifier): 25–40 lines
- REVIEW (complex, multi-step investigation): 50–80 lines
- If your report exceeds 90 lines, you are being too verbose — cut redundancy
