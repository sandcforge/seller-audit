# CLAUDE.md

## Sandbox

Before running any script in this repo, source the sandbox:

```bash
source ./activate.sh
```

It's idempotent — run it at the start of every session. It sets up `python`, `gcloud`, ADC, and `GOOGLE_CLOUD_PROJECT=plantstory`.

`source` only affects the current shell, so each `Bash` tool call needs to either re-source it or chain work onto the same command with `&&`.

## Seller audits

When the user asks to audit, review, verify, or investigate a seller — or drops a HubSpot contact link / seller name and wants an assessment — invoke the `seller-audit` skill. It orchestrates extraction, investigation, and verdict. Don't try to do the audit steps manually.

Write one verdict `.md` file per seller. For N sellers, produce N separate files — never bundle multiple sellers into one combined report.
