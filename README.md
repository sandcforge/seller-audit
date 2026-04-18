# Seller Audit Team

This repository contains the PalmStreet seller audit workflow, including:

- seller data extraction from HubSpot / BigQuery
- seller investigation skills and scraping helpers
- seller verdict rendering
- shared prompts, references, and assets

## Repository Layout

- `skills/`: audit skills, scripts, and references
- `assets/`: shared static resources
- `outputs/`: generated local outputs only

## What Is Safe To Share

This repository is intended to be shareable across computers, but **not every local file should be committed**.

Ignored by default:

- `.venv/`
- `.uv-cache/`
- `outputs/`
- macOS metadata such as `.DS_Store`

## Fresh Machine Setup

Use this section when setting up a brand-new machine for the first time.

### 1. Install required tools

Make sure these tools are available before continuing:

- `git`
- `python3`
- [`uv`](https://docs.astral.sh/uv/)
- `gcloud` (Google Cloud SDK)

Quick checks:

```bash
git --version
python3 --version
uv --version
gcloud --version
```

If `gcloud` is missing, install Google Cloud SDK first. If `uv` is missing, the bootstrap script can install a project-local copy automatically.

### 2. Create the local Python environment

This project uses `uv` with a committed lockfile.

```bash
UV_CACHE_DIR=.uv-cache uv sync
```

This creates a local `.venv` from `pyproject.toml` and `uv.lock`.

### 3. Authenticate BigQuery access

This repository uses sandbox `gcloud` Application Default Credentials (ADC) only.

1. Log into Google Cloud in the browser:

```bash
gcloud auth application-default login
```

2. In the browser, choose the Google account that has access to the BigQuery data.

3. After authorization completes, verify ADC works:

```bash
gcloud auth application-default print-access-token
```

4. Set the default GCP project if needed:

```bash
gcloud config set project plantstory
```

Notes:

- `gcloud auth login` is optional for this repo. The important command for the Python BigQuery client is `gcloud auth application-default login`.
- Successful ADC login usually writes credentials to `~/.config/gcloud/application_default_credentials.json`.
- `./setup.sh` checks `gcloud`, validates ADC, and starts the ADC login flow automatically if credentials are missing.

### 4. Verify the repo can query seller data

Run a known lookup:

```bash
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-audit/scripts/bq_query_seller.py --query "seller@example.com"
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-audit/scripts/bq_query_seller.py --vid 205494706259
```

If successful, the script will:

- print `Found N record(s).` or similar output
- write a JSON file into `outputs/`

## Run Scripts

Examples:

```bash
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-audit/scripts/bq_query_seller.py --query "seller@example.com"
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-audit/scripts/bq_query_seller.py --query "succulent" --limit 10
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-audit/scripts/bq_query_seller.py --vid 205494706259
```

Common checks:

```bash
gcloud auth application-default print-access-token
UV_CACHE_DIR=.uv-cache .venv/bin/python -c "from google.cloud import bigquery; print(bigquery.Client().project)"
```

Common failure cases:

- `Default credentials not found`
  Run `gcloud auth application-default login`.
- `403 Access Denied`
  Your Google account is authenticated but does not have permission to query the dataset.
- `Project was not passed and could not be determined`
  Run `gcloud config set project plantstory` or set the correct project explicitly.

## Git Hygiene

Before pushing or sharing:

1. Make sure no service account keys are staged.
2. Keep generated audit outputs inside `outputs/`.
3. Commit the workflow code, references, and lockfile.

## Bootstrap Script

If you want a one-command setup, use:

```bash
./setup.sh
```
