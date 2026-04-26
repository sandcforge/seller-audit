---
name: seller-extract
description: "Extract seller applicant data from HubSpot for PalmStreet seller audit. Handles BigQuery script (primary) and Chrome HubSpot UI (fallback) extraction methods. Outputs a structured Applicant Summary. This skill is a component of the seller-audit pipeline — it is typically invoked by the seller-audit orchestrator, not directly by the user."
---

# Seller Data Extraction

Extract applicant data from HubSpot and produce a structured Applicant Summary.

## When to use

This skill is invoked by the seller-audit orchestrator (or manually) when you need to pull seller data from HubSpot. It does NOT investigate the seller's online presence or issue a verdict — those are separate skills.

## Method 1: BigQuery Script (Default)

This skill enters with a `palmstreet_userid` already in hand (the orchestrator either received it from the user or resolved it via the standalone lookup tool `scripts/bq_seller.py` — see the project `CLAUDE.md`). The extraction step uses one bundled script:

```bash
python skills/seller-audit/scripts/bq_query_seller.py --uid <palmstreet_userid>
```

It queries `plantstory.hubspot.Contact` via sandbox `gcloud` Application Default Credentials and emits a fully-formed Applicant Summary YAML to **stdout only** — no file is written. The YAML is ready to paste straight into the seller-investigate Task prompt.

**Prerequisite:** the shell must have `./activate.sh` sourced first — see the project `CLAUDE.md` for the sandbox activation rule.

**Notes:**
- ~80 uids in BQ correspond to multiple HubSpot Contact rows. The script picks the most recent by `app__date` and warns on stderr (`# WARNING: N HubSpot Contact rows share …`).
- If you need to persist the YAML, redirect: `python … --uid <uid> > outputs/applicant_<uid>.yaml`.
- Don't have a uid? That's outside this skill's job. Run `python scripts/bq_seller.py --query "<term>"` (project-root script, NOT a skill component) to resolve email/name/etc. → uid first.

### Field mapping

For the BQ-column → audit-field mapping and the `FIELDS` whitelist rationale, read:
> `../seller-audit/references/extract-hubspot.md`

### When to fall back

Switch to Method 2 if:
- `No results found` for a known email/vid/userid
- Script auth error (e.g., ADC missing or expired) that can't be fixed quickly
- Data in BQ looks stale (BQ sync runs on a delay — if HubSpot was updated in the last few hours, the UI may be fresher)

## Method 2: Chrome on HubSpot UI (Fallback)

Navigate to the contact page in Chrome:

```
https://app.hubspot.com/contacts/45316392/record/0-1/{contactId}
```

Use `read_page` or `get_page_text` to extract the left sidebar ("About this contact"). Fall back to screenshot only if text extraction fails.

If the page redirects to login, ask the user to log in first.

## Output: Applicant Summary YAML

The hand-off to seller-investigate is a structured YAML document — not Markdown. For the full schema, field-by-field rules, and a worked example, read:
> `../seller-audit/references/extract-hubspot.md` (section: "Output: Applicant Summary YAML")

**Method 1 (--uid) produces this YAML for you.** `bq_query_seller.py --uid <palmstreet_userid>` emits a fully-formed Applicant Summary YAML to **stdout only** (no file is written). Capture the stdout and paste it directly into the next Task prompt; if you need it on disk, redirect to `outputs/applicant_<uid>.yaml`. Field names, types, COALESCE rules, `category` multi-value joining, and field ordering all match `extract-hubspot.md`.

**Method 2 (HubSpot UI) requires you to assemble the YAML by hand** following the schema doc. Top-level keys: `seller`, `online_assets`, `business_claims`. Identity field names (`hubspot_id`, `palmstreet_userid`, `phone_area_code_location`) match `handoff-schema.md` so investigate can copy them through without renaming. Discipline (same as `handoff-schema.md`):
- Every field present — use `null` for unknown, `[]` for empty arrays.
- Numbers as numbers, not strings (`200`, not `"200"`; `35.00`, not `"$35"`).
- URLs in full `https://` form.

In either method, if `palmstreet_userid` ends up `null`, surface the gap to the orchestrator — `render_verdict.py` will hard-error downstream, so stopping here is cheaper than discovering it after a full investigation. (For `--uid` mode this is impossible by construction: the script looks up rows BY uid, so a successful run guarantees the uid is present.)

## Security Note

Use sandbox `gcloud` ADC for BigQuery access. Do not add ad hoc credential files to the repository.
