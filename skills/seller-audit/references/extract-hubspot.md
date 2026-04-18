# Extract Seller Data from HubSpot

Two methods — always try **Method 1 (BigQuery script)** first. Fall back to **Method 2 (Chrome on HubSpot UI)** only if the script fails.

---

## Method 1: BigQuery Script (Default)

The script queries `plantstory.hubspot.Contact` in BigQuery via sandbox `gcloud` Application Default Credentials (ADC).

### 1.1 Location

The script is bundled inside this skill:

```
skills/seller-audit/scripts/bq_query_seller.py
```

The script resolves these paths relative to its own location, so you can invoke
it from any working directory. Output JSONs are written to the project-level
`outputs/` folder (i.e. `<project_root>/outputs/`).

### 1.2 Usage

```bash
# From the project root:
python skills/seller-audit/scripts/bq_query_seller.py --query "seller@example.com"
python skills/seller-audit/scripts/bq_query_seller.py --query "palmstreet_username"
python skills/seller-audit/scripts/bq_query_seller.py --query "Firstname Lastname"
python skills/seller-audit/scripts/bq_query_seller.py --vid 205494706259
```

`--query` returns a list of matching VIds plus summary fields. `--vid` writes the full whitelisted row to `outputs/seller_{vid}.json` and prints a summary of key fields.

### 1.3 Dependencies

Run the script from the project `.venv` after `./setup.sh` completes:

```bash
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-audit/scripts/bq_query_seller.py --query "seller@example.com"
```

### 1.4 Fields in the BigQuery row

The script queries a fixed whitelist of audit-relevant columns (see `FIELDS` in
`bq_query_seller.py`). Do NOT change the query to `SELECT *` — the Contact
table has 400+ columns and the extra marketing/automation fields bloat the
output JSON without helping the audit.

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
| `sales_stage` | Sales Stage (Prospect/Approved/Rejected) |
| `approval_date` | Approval Date |
| `rejection_reason` | Rejection Reason |
| `metabase_status` | Metabase Status |
| `aloy_activation_pending` | Aloy Activation Pending flag |
| `hubspot_owner_id` | Contact Owner (numeric ID) |
| `hs_object_source_label` / `hs_latest_source` / `self_reported_lead_source__typeform_` | Record Source |
| `recent_expo_name` | Recent Expo Name |
| `notes_last_contacted` | Last Contacted |
| `app__date` | Application submission datetime (UTC DATETIME — convert to `America/Los_Angeles` for "today" queries) |
| `createdate` | Contact creation datetime (UTC DATETIME) |

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

## Output: Structured Applicant Summary

Regardless of method, organize extracted data into this format before proceeding to the investigation:

```
## Applicant Summary
- **Name:** [First Last]
- **Company:** [Company Name]
- **Email:** [email]
- **Phone:** [phone] ([area code location])
- **Category:** [from Typeform/Aloy Category]

## Online Assets (from application)
- **Website URL:** [url or "None"]
- **Social Media:** [url or "None"]
- **PalmStreet Username:** [username]

## Business Claims
- **Inventory Count:** [number]
- **Average Price:** [dollar amount]
- **Shipping Volume:** [value or "N/A"]

## Internal Status
- **Sales Stage:** [Applied/Approved/Rejected]
- **Approval Date:** [date or "N/A"]
- **Contact Owner:** [name or owner ID]
- **Referral:** [name or "None"]
```
