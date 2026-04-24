# Seller Audit Team

PalmStreet seller audit workflow: extract seller data from HubSpot / BigQuery, investigate their online footprint, and render a verdict. Everything runs inside a self-contained sandbox under `./sandbox/` — no global Python or gcloud install required.

## Repository Layout

- `activate.sh` — one-command sandbox setup + activation. Source this at the start of every session.
- `skills/` — skill definitions, scripts, and references
  - `skills/seller-audit/scripts/` — BigQuery helpers (`bq_query_seller.py`, `bq_latest_applications.py`)
  - `skills/seller-audit/references/` — SOPs, URL normalization rules, platform scrape guides
- `sandbox/` — gcloud SDK, venv, and ADC credentials (auto-created by `activate.sh`; gitignored)
- `outputs/` — generated audit outputs (gitignored)

Gitignored: `sandbox/`, `.venv/`, `.uv-cache/`, `outputs/`, `.DS_Store`.

## First-time setup

You need `bash`, `curl`, and [`uv`](https://docs.astral.sh/uv/) on the host, plus a plantstory-BQ-capable Google account. `activate.sh` installs the gcloud SDK and Python venv into `./sandbox/`.

1. Source the script. On first run it prints an OAuth URL and returns:

```bash
source ./activate.sh
```

2. Open the URL in a browser, sign in with your plantstory Google account, and copy the verification code Google shows on the success page.

3. Re-source with the code:

```bash
AUTH_CODE='4/0...' source ./activate.sh
```

ADC is now written to `sandbox/.config/gcloud/application_default_credentials.json` and persists across sessions.

## Every subsequent session

```bash
source ./activate.sh
```

Idempotent. Activates the sandbox by setting `PATH`, `VIRTUAL_ENV`, `GOOGLE_APPLICATION_CREDENTIALS`, and `GOOGLE_CLOUD_PROJECT=plantstory`. Because `source` only affects the current shell, each fresh shell (including every new `Bash` tool invocation) needs to either re-source the script or chain onto it: `source ./activate.sh && python …`.

On your local machine the venv persists at `sandbox/.venv-audit`. In the Cowork sandbox it's session-local (`/sessions/<id>/.venv-audit`) and rebuilt each session — fast because wheels come from the persistent `.uv-cache`. The first source of each Cowork session prints `[2/3] Creating venv at …` — that's expected, not an error.

## Run scripts

After sourcing:

```bash
# Look up a specific seller
python skills/seller-audit/scripts/bq_query_seller.py --query "seller@example.com"
python skills/seller-audit/scripts/bq_query_seller.py --vid 217268720946

# Latest applications (default limit 3)
python skills/seller-audit/scripts/bq_latest_applications.py --limit 20
```

Results land in `outputs/seller_<vid>.json` or `outputs/latest_applications_<n>.json`.

Sanity checks:

```bash
gcloud auth application-default print-access-token
python -c "from google.cloud import bigquery; print(bigquery.Client().project)"
```

## Troubleshooting

- **`Default credentials not found`** — delete `sandbox/.config/gcloud/application_default_credentials.json` and re-run the first-time OAuth setup.
- **`403 Access Denied`** — your Google account is authenticated but lacks BigQuery access to the plantstory dataset. Ask an admin.
