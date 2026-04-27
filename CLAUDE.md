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

**The skill takes a PalmStreet uid (`palmstreet_userid`) as its input.** If the user gave you anything else — email, name, username, phone, HubSpot contact link, HubSpot VId — first run `python scripts/bq_seller.py --query "<term>"` to resolve it. Column 1 of stdout is the uid; pipe that into the seller-audit skill. `bq_seller.py` is a standalone lookup tool, not part of any skill.

**One seller per invocation, sequentially.** For multiple sellers, invoke the skill once per uid and produce one verdict `.md` each — never bundle them into one report, never run them concurrently or via parallel subagents.
