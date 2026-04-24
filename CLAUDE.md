# CLAUDE.md

## Sandbox

Before running any script in this repo, source the sandbox:

```bash
source ./activate.sh
```

It's idempotent — run it at the start of every session. It sets up `python`, `gcloud`, ADC, and `GOOGLE_CLOUD_PROJECT=plantstory`.

`source` only affects the current shell, so each `Bash` tool call needs to either re-source it or chain work onto the same command with `&&`.

In Cowork, the venv is intentionally session-local — the first `source ./activate.sh` of each session prints `[2/3] Creating venv at /sessions/<id>/.venv-audit...` and installs packages from the cached wheels. That's expected, not an error.

## Scripts

BigQuery helpers live under `skills/seller-audit/scripts/`, not `assets/`. After sourcing the sandbox, run them directly:

```bash
python skills/seller-audit/scripts/bq_query_seller.py --query "<email/name/phone/username>"
python skills/seller-audit/scripts/bq_query_seller.py --vid <vid>
python skills/seller-audit/scripts/bq_latest_applications.py --limit 20
```

Outputs are written to `outputs/`. The script accepts `--query` and `--vid` (not `--email` or `--userid`).
