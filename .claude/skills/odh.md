# ODH Runbook Tool

Use this skill when someone wants to set up any ODH/RHOAI component or environment.

## How to use

Claude executes runbooks agentically — reads the runbook as a reference, checks cluster state,
fetches source repos when unsure, and applies only standard fixes. No `--mode` flags needed.

```bash
odh start                              # guided onboarding — asks what you want to accomplish
odh wizard <runbook>                   # interactive wizard — collect params, then execute
odh run <runbook> -p key=value         # execute directly
odh run <runbook> --dry-run -p ...     # Claude reviews state, no changes made
odh doctor                             # check what's installed on the cluster
odh list --workflow                    # see runbooks grouped by goal
odh show <runbook>                     # preview steps and source repos
```

## Common workflows

**Set up EvalHub (zero S3 config needed):**
```bash
odh wizard evalhub/create-evaluation-run
# Only needs: project_namespace
# Claude auto-deploys model from OCI catalog, no S3 or credentials required
```

**Deploy a vLLM model:**
```bash
odh wizard model-serving/deploy-vllm-model
# Needs: project_namespace, model_name
# GPU required; supports built-in NVIDIA GPU runtime or experimental CPU
```

**Install RHOAI pre-release on ROSA:**
```bash
odh wizard rosa/install-rhoai-prerelease
# Needs: FBC image digest from team release channel
# Handles Kyverno pull secret workaround automatically
```

**Full environment setup from scratch:**
```bash
odh start
# No parameters needed — guides interactively through all components
```

**Check cluster health:**
```bash
odh doctor
# Shows what's installed, what's missing, what can be auto-provisioned
```

## When parameters are unknown

Run the wizard — it discovers valid values from the cluster:
```bash
odh wizard <runbook-name>
```

Or show what parameters a runbook needs:
```bash
odh show <runbook-name>
```

Or check what's available:
```bash
# Find available namespaces
oc get namespace -l opendatahub.io/dashboard=true --no-headers -o jsonpath='{.items[*].metadata.name}'

# Find available models in namespace
oc get inferenceservice -n <namespace> --no-headers
```

## Troubleshooting

If Claude cannot complete a step with a standard fix, it will explain:
- What the error is
- Which source repos it checked
- Why no standard fix was found
- What the user must do manually

To review cluster state without making changes:
```bash
odh run <runbook> --dry-run -p project_namespace=<ns>
```

To see what a runbook does before running it:
```bash
odh show <runbook-name>
```
