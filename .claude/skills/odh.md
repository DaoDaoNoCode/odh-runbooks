# ODH Runbook Tool

Use this skill when someone wants to set up any ODH/RHOAI component or environment.

## How to use

The `odh` CLI handles all ODH/RHOAI environment setup. Key commands:

```bash
odh start                              # guided setup — asks what you want to accomplish
odh wizard <runbook>                   # interactive wizard for a specific runbook
odh run <runbook> --mode plan -p ...   # preview what would happen
odh run <runbook> -p key=value         # execute
odh doctor                             # check what's installed on the cluster
odh list --workflow                    # see runbooks grouped by goal
odh show <runbook>                     # preview steps without running
```

## Common workflows

**Set up EvalHub with MLflow:**
```bash
odh wizard evalhub/create-evaluation-run
```
Needs: `project_namespace` (oc get namespace -l opendatahub.io/dashboard=true), `model_uri` (path in S3 bucket)

**Deploy a vLLM model:**
```bash
odh wizard model-serving/deploy-vllm-model
```
Needs: `project_namespace`, `model_name`, `model_uri`, GPU nodes required

**Install RHOAI pre-release on ROSA:**
```bash
odh wizard rosa/install-rhoai-prerelease
```
Needs: FBC image digest from team release channel, `quay.io/rhoai` credentials from RHOAI DevOps team

**Full environment setup from scratch:**
```bash
odh start
```
No parameters needed — guides interactively.

**Check cluster health:**
```bash
odh doctor
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

## Troubleshooting

If a step fails, the tool stops with a clear message. To check current state without making changes:
```bash
odh run <runbook> --mode qa -p key=value
```

To see what would happen without executing:
```bash
odh run <runbook> --mode plan -p key=value
```
