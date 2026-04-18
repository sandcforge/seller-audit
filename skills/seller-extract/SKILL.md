---
name: seller-extract
description: "Extract seller applicant data from HubSpot for PalmStreet seller audit. Handles BigQuery script (primary) and Chrome HubSpot UI (fallback) extraction methods. Outputs a structured Applicant Summary. This skill is a component of the seller-audit pipeline — it is typically invoked by the seller-audit orchestrator, not directly by the user."
---

# Seller Data Extraction

Extract applicant data from HubSpot and produce a structured Applicant Summary.

## When to use

This skill is invoked by the seller-audit orchestrator (or manually) when you need to pull seller data from HubSpot. It does NOT investigate the seller's online presence or issue a verdict — those are separate skills.

## Method 1: BigQuery Script (Default)

Run the bundled script to query `plantstory.hubspot.Contact`:

```bash
python skills/seller-audit/scripts/bq_query_seller.py --query "<email/name/phone/username>"
python skills/seller-audit/scripts/bq_query_seller.py --vid <vid>
```

The script uses sandbox `gcloud` Application Default Credentials and writes output to `outputs/`.

### When to fall back

Switch to Method 2 if:
- `No results found` for a known email/vid/userid
- Script auth error (e.g., ADC missing or expired)
- Data looks stale (BQ sync runs on a delay)

## Method 2: Chrome on HubSpot UI (Fallback)

Navigate to the contact page in Chrome:

```
https://app.hubspot.com/contacts/45316392/record/0-1/{contactId}
```

Use `read_page` or `get_page_text` to extract the left sidebar ("About this contact"). Fall back to screenshot only if text extraction fails.

If the page redirects to login, ask the user to log in first.

## Output: Applicant Summary

For the full field mapping (BQ column → audit field) and the structured output template, read:
> `../seller-audit/references/extract-hubspot.md`

Regardless of method, produce this structured summary before returning:

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

## Batch Extraction

For search-style extraction, use query mode to get matching VIds first, then use `--vid` for full details.

## Security Note

Use sandbox `gcloud` ADC for BigQuery access. Do not add ad hoc credential files to the repository.
