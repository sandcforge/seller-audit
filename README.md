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
- BigQuery service account keys

## Required Secrets

The BigQuery scripts expect a service account key at these paths:

- `skills/seller-audit/assets/bq-reader-key.json`
- `skills/seller-extract/assets/bq-reader-key.json`

These files are intentionally ignored by git. Distribute them through your normal secret-sharing process, not through the repository.

## Python Setup

This project uses `uv` with a committed lockfile.

### First-time setup

```bash
UV_CACHE_DIR=.uv-cache uv sync
```

This creates a local `.venv` from `pyproject.toml` and `uv.lock`.

### Run scripts

Examples:

```bash
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-extract/scripts/bq_query_seller.py --email "seller@example.com"
UV_CACHE_DIR=.uv-cache .venv/bin/python skills/seller-extract/scripts/bq_query_latest.py 10 outputs/latest-scan
```

## Git Hygiene

Before pushing or sharing:

1. Make sure no service account keys are staged.
2. Keep generated audit outputs inside `outputs/`.
3. Commit the workflow code, references, and lockfile.

## Bootstrap Script

If you want a one-command setup, use:

```bash
./scripts/setup_env.sh
```
