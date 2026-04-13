# ODH Runbook Tool

This repo contains verified runbooks for setting up any ODH/RHOAI component correctly.
When a user asks to set up, deploy, or configure anything RHOAI/ODH-related, use this tool.

## How to help users

### If the `odh` CLI is available (check with `which odh` or `odh --version`)

Use these commands:

```bash
odh start                                    # guided setup — asks what they want to do
odh wizard <runbook-name>                    # interactive wizard for a specific runbook
odh run <runbook-name> --mode plan -p ...    # preview without changes
odh run <runbook-name> -p key=value          # execute
odh doctor                                   # check what's installed on the cluster
odh list --workflow                          # see runbooks grouped by goal
odh show <runbook-name>                      # preview steps
```

Always run `--mode plan` before `implement` for unfamiliar runbooks.
Always run `odh doctor` first if the user isn't sure what's installed.

### If `odh` is NOT installed

Read the runbook YAML directly from this repo (or from GitHub) and execute the steps
yourself using the Bash tool. The YAML files in `runbooks/` contain:
- Exact `oc` commands to run
- Pre-checks (run these first to verify state)
- Post-checks (run these to verify success)
- Rollback commands

Follow the steps in order. Stop if any post-check fails — never improvise.

## Common requests → runbooks

| User says | Runbook to use |
|---|---|
| "set up EvalHub" | `evalhub/create-evaluation-run` |
| "deploy a vLLM model" | `model-serving/deploy-vllm-model` |
| "set up pipelines" | `pipelines/create-pipeline-server` |
| "create a workbench" | `workbenches/create-workbench` |
| "enable MLflow" | `mlflow/enable-mlflow` |
| "install RHOAI pre-release on ROSA" | `rosa/install-rhoai-prerelease` |
| "set up everything from scratch" | `cluster/full-stack-setup` |
| "deploy a model from model registry" | `model-registry/deploy-from-registry` |
| "set up GPU" | `rosa/setup-gpu-machinepool` |
| "register a model" | `model-registry/register-model` |

## Key facts about this tool

**Dependencies are auto-resolved.** If EvalHub needs TrustyAI and it's not enabled,
the tool enables it automatically. If S3 is needed and none exists, it deploys MinIO.
Users don't need to know prerequisites.

**Three execution modes:**
- `plan` — shows what would happen, no changes made
- `qa` — reads cluster state, reports what's ready and what's missing
- `implement` — executes (default)

**Confidence levels on steps:**
- `doc-derived` — confirmed from ODH source code
- `inferred` — derived from architecture docs, probably correct
- `uncertain` — ask user to confirm before running

**Every step has a post-check.** If it fails, the tool stops. It never improvises
or creates workarounds. This is intentional — the whole point is "correct or stopped."

## Parameters the user needs

For most runbooks the key parameters are:
- `project_namespace` — discover with: `oc get namespace -l opendatahub.io/dashboard=true --no-headers -o jsonpath='{.items[*].metadata.name}'`
- `model_uri` — path within S3 bucket (not full s3:// URL)
- `s3_connection_name` — discover with: `oc get secret -n <ns> -l opendatahub.io/connection-type=s3 -o jsonpath='{.items[*].metadata.name}'`

The wizard discovers these automatically. For direct runs, help the user find them.

## Install (if odh CLI is not available)

```bash
# Option A — uv (no install, run directly)
uv run /path/to/odh-runbooks/cli.py wizard evalhub/create-evaluation-run

# Option B — pipx (system-wide)
pipx install /path/to/odh-runbooks
odh wizard evalhub/create-evaluation-run

# Option C — alias
alias odh="python /path/to/odh-runbooks/cli.py"
```

Or install from GitHub:
```bash
pipx install git+https://github.com/DaoDaoNoCode/odh-runbooks
```
