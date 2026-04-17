# Tool Failure Recovery

**When to read:** During the investigation phase (Section 2.5) when you encounter broken links, inaccessible platforms, or tools that fail. This protocol specifies the recovery sequence and when to move to the next action.

---

## 2.7.4 Tool Failure Recovery

- 404/Dead links → **first, verify URL integrity** (Section 2.3.1): go back to the original HubSpot raw URL and compare character-by-character with the URL you visited. If the URL was mutated (common with long concatenated store names), fix it and retry. If the URL matches exactly, apply URL normalization rules (e.g., Whatnot `/invite/` → `/user/`). If the normalized URL also fails, mark as dead and continue to next provided URL.
- Whatnot short link → visit in Chrome (it auto-redirects); do NOT try to WebSearch the short URL
- Whatnot invite link → replace `/invite/` with `/user/` in the URL
- Login wall → do not retry same tool, pivot to Google Search fallback or web search
- All provided URLs dead → trigger Google Search fallback (Priority 3) before concluding zero footprint
- WebSearch returns nothing → this does NOT mean seller has no presence; visit provided URLs in Chrome first
- Tool errors → fallback to web search or screenshot-based extraction
