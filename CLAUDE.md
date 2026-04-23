# CLAUDE.md

## Sandbox

Before running any script in this repo, source the sandbox:

```bash
source ./activate.sh
```

It's idempotent — run it at the start of every session. It sets up `python`, `gcloud`, ADC, and `GOOGLE_CLOUD_PROJECT=plantstory`.

`source` only affects the current shell, so each `Bash` tool call needs to either re-source it or chain work onto the same command with `&&`.
