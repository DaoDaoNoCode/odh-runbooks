# ODH Runbook Tool

This repo contains 66 verified runbooks for setting up any ODH/RHOAI component correctly.
When a user asks to set up, deploy, or configure anything RHOAI/ODH-related, use this tool.

## How to help users

### If the `odh` CLI is available (check with `which odh`)

```bash
odh start                                    # guided onboarding — asks what they want to do
odh wizard <runbook-name>                    # interactive wizard — collects params, then executes
odh run <runbook-name> -p key=value          # execute directly with known params
odh run <runbook-name> --dry-run -p ...      # Claude reviews state, no changes
odh doctor                                   # check what's installed on the cluster
odh list --workflow                          # runbooks grouped by goal
odh show <runbook-name>                      # preview steps and source repos
```

Always run with `--dry-run` first for unfamiliar runbooks.
Always run `odh doctor` first if the user isn't sure what's installed.

### If `odh` is NOT installed

Read the runbook YAML directly and execute the steps using the Bash tool.
The YAML files in `runbooks/` contain:
- Exact `oc` commands to run
- Pre-checks (run first to verify state)
- Post-checks (run to verify success)
- `source_repos` (fetch these to verify correct approach before acting)
- Rollback commands

Follow the steps in order. Check `source_repos` before applying any non-obvious configuration.
Stop if any post-check fails — never improvise.

## How Claude executes (agentic mode)

There is only one execution mode — agentic. Claude:
1. Reads the full runbook YAML as a reference guide (not a rigid script)
2. Checks actual cluster state with `oc` commands before each step
3. Skips steps that are already done
4. Fetches `source_repos` (the component's GitHub repos) when unsure about the correct approach
5. Never applies workarounds — only standard fixes found in the source code
6. If no standard fix exists: explains what it checked and what the user must do manually

## Common requests → runbooks

| User says | Runbook to use |
|---|---|
| "set up EvalHub" | `evalhub/create-evaluation-run` |
| "deploy a vLLM model" | `model-serving/deploy-vllm-model` |
| "deploy a model" | `model-serving/deploy-kserve-model` |
| "set up pipelines" | `pipelines/create-pipeline-server` |
| "create a workbench" | `workbenches/create-workbench` |
| "enable MLflow" | `mlflow/enable-mlflow` |
| "install RHOAI pre-release on ROSA" | `rosa/install-rhoai-prerelease` |
| "install RHOAI stable on ROSA" | `rosa/install-rhoai-stable` |
| "set up everything from scratch" | `cluster/full-stack-setup` |
| "deploy a model from model registry" | `model-registry/deploy-from-registry` |
| "register a model" | `model-registry/register-model` |
| "set up GPU" | `rosa/setup-gpu-machinepool` |
| "enable TrustyAI" | `trustyai/enable-trustyai-service` |
| "submit a Ray job" | `distributed-workloads/submit-ray-job` |
| "submit a PyTorch job" | `model-training/submit-pytorch-job` |
| "enable model registry" | `cluster/enable-model-registry` |
| "enable KServe" | `cluster/enable-kserve` |
| "create a project" | `projects/create-project` |
| "add S3 connection" | `projects/create-s3-connection` |
| "enable feature store" | `cluster/enable-feature-store` |
| "enable observability" | `observability/enable-perses-dashboard` |

## Key facts about this tool

**Dependencies are auto-resolved.** If EvalHub needs TrustyAI and it's not enabled,
Claude enables it automatically. If S3 is needed and none exists, Claude deploys MinIO.
Users don't need to know prerequisites.

**Source repos are the truth.** Before applying any non-obvious configuration, Claude
fetches the relevant GitHub repo from `source_repos` to verify the correct approach.
This prevents workarounds and ensures only standard, operator-compatible configurations
are applied.

**Every runbook has `source_repos`.** For model-serving runbooks:
kserve, odh-model-controller, opendatahub-operator, odh-dashboard.
For EvalHub: eval-hub, trustyai-service-operator, kserve, opendatahub-operator.

**Confidence levels on steps:**
- `doc-derived` — confirmed from ODH source code
- `inferred` — derived from architecture docs, probably correct but not cluster-tested
- `uncertain` — ask user to confirm before running

## Parameters the user needs

For most runbooks the key parameters are:
- `project_namespace` — discover with: `oc get namespace -l opendatahub.io/dashboard=true --no-headers -o jsonpath='{.items[*].metadata.name}'`
- `model_name` — chosen by user (lowercase, hyphens, max 63 chars)
- `model_oci_uri` — for vLLM: `oci://quay.io/redhat-ai-services/modelcar-catalog:<tag>`

The wizard discovers these automatically. For direct runs, help the user find them with `odh doctor` and `odh show <runbook>`.

## Install (if odh CLI is not available)

```bash
# Option A — uv (no install, run directly)
uv run /path/to/odh-runbooks/cli.py wizard evalhub/create-evaluation-run

# Option B — pipx (system-wide)
pipx install /path/to/odh-runbooks
odh wizard evalhub/create-evaluation-run

# Option C — pip
pip install -e /path/to/odh-runbooks
odh wizard evalhub/create-evaluation-run

# Option D — from GitHub
pipx install git+https://github.com/DaoDaoNoCode/odh-runbooks
```
