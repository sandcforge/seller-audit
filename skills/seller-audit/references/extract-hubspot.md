# Extract Seller Data from HubSpot

Two methods — always try **Method 1 (BigQuery script)** first. Fall back to **Method 2 (Chrome on HubSpot UI)** only if the script fails.

---

## Method 1: BigQuery Script (Default)

The script queries `plantstory.hubspot.Contact` in BigQuery via sandbox `gcloud` Application Default Credentials (ADC).

### 1.1 Location

The seller-audit orchestrator runs one script inline (Step 1 of `skills/seller-audit/SKILL.md`):

```
skills/seller-audit/scripts/bq_query_seller.py  # uid → Applicant Summary YAML (stdout only)
```

A separate, **standalone** script lives outside the skills tree:

```
scripts/bq_seller.py                            # free-form search → matching PalmStreet uids
```

`scripts/bq_seller.py` is NOT a component of the seller-audit skill. It's an upstream lookup tool you run when the user gave you anything other than a uid (email, name, contact link, VId). See CLAUDE.md "Seller audits" for the wiring. Both scripts resolve paths relative to their own location, so you can invoke them from any working directory.

### 1.2 Usage

```bash
# From the project root:

# Inside the skill — bq_query_seller.py --uid: PalmStreet uid → Applicant
# Summary YAML (per the schema below) on STDOUT ONLY. No file is written.
# Capture the stdout into the next subagent's prompt; persist with
# `> outputs/applicant_<uid>.yaml` only if you specifically want it on disk.
python skills/seller-audit/scripts/bq_query_seller.py --uid eWqpDoVGnBRKHqx8Mpw86P2q95p2

# Outside the skill (lookup) — bq_seller.py --query: free-form search →
# matching PalmStreet uids on stdout (tab-separated rows; column 1 is the
# uid, suitable for piping /xargs). Raw matched rows are dumped to
# outputs/seller_query_<slug>.json for inspection; the path is logged on stderr.
python scripts/bq_seller.py --query "seller@example.com"
python scripts/bq_seller.py --query "palmstreet_username"
python scripts/bq_seller.py --query "Firstname Lastname"
```

Notes:
- The previous `--vid` (HubSpot VId) entry point was **removed** from `bq_query_seller.py`. To audit a contact when you only have a VId, search by VId in `scripts/bq_seller.py --query` (CAST to STRING is supported), then feed the resulting uid into `--uid`.
- The previous `--query` mode on `bq_query_seller.py` was **moved** to a standalone script (`scripts/bq_seller.py`) that lives outside the skills tree, since lookup is a pre-audit step rather than part of the audit pipeline itself.
- Contacts in HubSpot without a `palmstreet_userid` are surfaced on stderr by `bq_seller.py` (`# no_uid …`) but cannot be reached by `--uid` — they exist in HubSpot but never created a PalmStreet account.
- ~80 PalmStreet uids in BQ map to multiple HubSpot Contact rows (mostly duplicates from re-applications). `--uid` picks the most recent by `app__date DESC, createdate DESC` and warns on stderr (`# WARNING: N HubSpot Contact rows share …`); reviewer can manually inspect the older VIds if needed.

### 1.3 Dependencies

Run the scripts from the project `.venv` after `./setup.sh` completes:

```bash
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-audit/scripts/bq_query_seller.py --uid <uid>
UV_CACHE_DIR=.uv-cache .venv/bin/python scripts/bq_seller.py --query "seller@example.com"
```

### 1.4 Fields in the BigQuery row

Both scripts query a fixed whitelist of audit-relevant columns (`SEARCH_FIELDS` in `scripts/bq_seller.py`, `DETAIL_FIELDS` in `skills/seller-audit/scripts/bq_query_seller.py`). Do NOT change either query to `SELECT *` — the Contact table has 400+ columns and the extra marketing/automation fields bloat the output without helping the audit.

Map BQ column → audit field:

| BQ column | Audit field |
|---|---|
| `VId` | HubSpot contact ID (for the URL) |
| `firstname`, `lastname` | Name |
| `company` | Company |
| `email` | Email |
| `phone` (or `hs_calculated_phone_number`) | Phone |
| `website` | Website URL |
| `social_media` | Social Media |
| `palmstreet_username` | PalmStreet Username |
| `palmstreet_userid` | PalmStreet UserID |
| `categories` | Typeform Category |
| `aloy_category` | Aloy Category |
| `inv__count__new_` | Inventory Count |
| `avg__plant_price` | Average Price (used for all categories, not just plants) |
| `price_range` | Price Range |
| `ppw_shipping_volume` | Shipping Volume |
| `selling_experience` | Selling Experience |
| `referred_by` (primary) / `referring_friend` (fallback) | Referred By — coalesce: prefer `referred_by`; fall back to `referring_friend` only when `referred_by` is null/empty. Both columns hold a free-text PalmStreet handle / friend name. The older `referring_friend` column has more noise (`'n/a'`, `'Nop'`, `'Yes, a friend! '`); newer signups populate `referred_by`. Do NOT mix in `self_reported_lead_source__typeform_` — that's "how did you hear about us" (channel), not who referred you. |
| `app__date`, `createdate` | Plumbing only — used by `bq_query_seller.py` `ORDER BY` to pick the most recent row when a `palmstreet_userid` has duplicates. NOT emitted in the YAML. |

**HubSpot internal-status fields no longer extracted.** Earlier versions of this script also emitted an `internal_status` block (sales_stage, approval_date, rejection_reason, contact_owner, record source, metabase status, aloy activation flag, expo name, last_contacted). Verdict has no consumer for those fields, so they were dropped from `DETAIL_FIELDS`. If you need to inspect them ad hoc, run a custom BigQuery query against `plantstory.hubspot.Contact` directly — `bq_seller.py --query` only returns the search whitelist.

**Timezone note:** `app__date` and `createdate` are stored as UTC DATETIME
(no timezone). To filter to today in PT, use
`DATE(DATETIME(TIMESTAMP(app__date), 'America/Los_Angeles')) = CURRENT_DATE('America/Los_Angeles')`.

### 1.5 When Method 1 fails

Switch to Method 2 if any of:
- `No results found` for an email/vid/userid you know exists
- Script auth error that can't be fixed quickly (e.g., ADC missing or expired)
- Data in BQ looks stale (BQ sync runs on a delay — if HubSpot was updated in the last few hours, the UI may be fresher)

---

## Method 2: Chrome on HubSpot UI (Fallback)

Use this when the BigQuery script doesn't return the seller or the data is stale.

### 2.1 Navigate to the Contact Page

Open the HubSpot contact URL in Chrome. Pattern:
```
https://app.hubspot.com/contacts/{portalId}/record/0-1/{contactId}
```

PalmStreet portal ID: `45316392`. Full URL example:
```
https://app.hubspot.com/contacts/45316392/record/0-1/205494706259
```

If the page redirects to a login page, ask the user to log in first, then retry.

### 2.2 Read the Left Sidebar

The left sidebar ("About this contact") contains all applicant fields. Use `read_page` or `get_page_text` to extract directly — HubSpot is standard HTML, no screenshots needed. Fall back to screenshot only if text extraction fails.

Fields to capture (same set as Method 1 1.4):

**Identity:** First Name, Last Name, Company, Email, Phone

**Online Assets:** Website URL, Social Media, PalmStreet Username, PalmStreet UserID

**Business Claims:** Typeform Categories, Aloy Category, Inv. Count (New), Average Price Per Product, PPW Shipping Volume

**Internal Status:** Referral, Contact Owner, Sales Stage, Approval Date, Rejection Reason, Metabase Status, Aloy Activation Status, Record Source, Last Contacted, Recent Expo Name

---

## Output: Applicant Summary YAML

Regardless of method, organize extracted data into the YAML structure below before handing off to seller-investigate. Field names match the downstream `schema-investigation.md` where they overlap, so investigate can copy identity fields through without translation.

### Schema

```yaml
seller:
  name: string                    # "First Last" — combined firstname + lastname
  company: string or null         # Company name if different from personal name
  hubspot_id: string              # VId — used for the HubSpot URL and BQ vid column
  palmstreet_userid: string or null  # palmstreet_userid field. REQUIRED downstream by generate_report.py — flag to user if missing.
  palmstreet_username: string or null  # palmstreet_username field
  email: string
  phone: string or null
  phone_area_code_location: string or null  # Best-effort area-code → city/region lookup

online_assets:                    # URLs the applicant provided. Each is a candidate for seller-investigate to visit.
  website: string or null
  social_media: string or null    # Often the primary IG/TikTok/FB URL

business_claims:
  category: string                # From Typeform `categories` or `aloy_category` (prefer Aloy if both set). What the applicant CLAIMS to sell — may not match what they actually sell. Investigate writes its finding to `business_actual.category` after observing the storefronts.
  inventory_count: integer or null
  average_price: float or null    # USD
  price_range: string or null     # Free-text bucket (e.g. "$10–$50") if present
  shipping_volume: string or null
  selling_experience: string or null
  referred_by: string or null     # COALESCE(referred_by, referring_friend). Free-text PalmStreet handle / friend name. Single normalized field — do not split or duplicate. Null if both BQ columns are empty.
```

### Rules

1. **Every field must be present.** Use `null` for unknown values, `[]` for empty arrays — never omit a field. Same discipline as `schema-investigation.md`.
2. **Numbers are numbers, not strings.** `inventory_count: 200`, not `"200"`. `average_price: 35.00`, not `"$35"`.
3. **URLs are full `https://` form** (no bare domains). If HubSpot stored only `instagram.com/foo`, expand to `https://www.instagram.com/foo`.
4. **`business_claims.category` is a single string.** If HubSpot has multiple Typeform categories, join with `" / "` (e.g. `"Plants / Crystals"`) so investigate's category-mismatch check sees the full claim.
5. **Do not invent fields.** If HubSpot has no `palmstreet_userid`, emit `null` and surface the gap to the orchestrator — generate_report.py will hard-error later, so it's better to stop here.
6. **`business_claims.referred_by` is a COALESCE.** Prefer the BQ `referred_by` column; fall back to `referring_friend` only when `referred_by` is null/empty. Never emit both — downstream consumes a single `referred_by` field. If both are populated and disagree, trust `referred_by` (it's the newer Typeform field; `referring_friend` is the legacy column with more noise like `'n/a'` / `'Yes, a friend! '`).

### Example

```yaml
seller:
  name: Frankie Clemente
  company: Frankie's Fossils
  hubspot_id: "205494706259"
  palmstreet_userid: "aB12cD34eF56gH78iJ90"
  palmstreet_username: "frankiefossils"
  email: frankie@example.com
  phone: "(213) 555-0142"
  phone_area_code_location: "Los Angeles, CA"

online_assets:
  website: null
  social_media: "https://www.instagram.com/frankiefossils"

business_claims:
  category: "Collectibles"
  inventory_count: 200
  average_price: 35.00
  price_range: "$10–$100"
  shipping_volume: null
  selling_experience: "2+ years"
  referred_by: "JumanjiJonPlants"
```
