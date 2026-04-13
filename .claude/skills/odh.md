# /odh — ODH Runbook Executor

<instructions>
The user wants to set up an ODH/RHOAI component or make a dashboard page work.
Your job: read the right runbook, execute it on the cluster, return a working dashboard link.

## Step 1 — Identify what they want

Map their request to a runbook. Common cases:
- "set up EvalHub / create eval run" → `evalhub/create-evaluation-run`
- "deploy a vLLM model" → `model-serving/deploy-vllm-model`
- "create a workbench / notebook" → `workbenches/create-workbench`
- "set up pipelines" → `pipelines/create-pipeline-server`
- "deploy from model registry" → `model-registry/deploy-from-registry`
- "enable KServe / model serving" → `cluster/enable-kserve`
- "install RHOAI on ROSA" → `rosa/install-rhoai-stable` or `rosa/install-rhoai-prerelease`
- "set up everything" → `cluster/full-stack-setup`

If unclear, run `odh list` or ask one question: "Which namespace do you want this in?"

## Step 2 — Get required parameters

Read `runbooks/<component>/<name>.yaml` and check the `parameters:` section.

For `project_namespace`, discover it:
```bash
oc get namespace -l opendatahub.io/dashboard=true --no-headers -o jsonpath='{.items[*].metadata.name}'
```

If the user provided a namespace, use it. If not, list the options and ask.

Most other parameters have defaults in the runbook — use them unless the user says otherwise.

## Step 3 — Execute the runbook

Read the runbook YAML. For each step:
1. Run the `pre_check` command — if it shows the resource exists, skip the step
2. Check `requires:` — if a dependency is missing, run the resolver runbook first
3. Apply the `action` (apply manifest, run command, etc.) — render `{{ variables }}` first
4. Run the `post_check` to verify it worked

**Before applying any non-obvious configuration:** fetch the relevant repo from `source_repos`
to verify the correct approach. Never guess. Never improvise.

The runbook's `known_bad_patterns` section shows what to NEVER do — check it before acting.

## Step 4 — Return the dashboard link

Every runbook ends with a `return:` value that includes a dashboard URL. Give the user:
- The full clickable URL to the specific dashboard page
- A quick test command if applicable (curl for model endpoints, etc.)

Dashboard URL patterns (your cluster's dashboard host is the prefix):
```bash
# Get the dashboard host:
oc get route rhods-dashboard -n redhat-ods-applications -o jsonpath='{.spec.host}' 2>/dev/null || \
oc get route rhods-dashboard -n opendatahub -o jsonpath='{.spec.host}' 2>/dev/null
```

| Feature | Dashboard path |
|---|---|
| EvalHub runs | `/evaluation/{ns}` |
| Deployed models | `/ai-hub/deployments/{ns}` |
| Pipelines | `/develop-train/pipelines/definitions/{ns}` |
| Pipeline runs | `/develop-train/pipelines/runs/{ns}/runs/{runId}` |
| Schedules | `/develop-train/pipelines/runs/{ns}/schedules` |
| Workbenches | `/projects/{ns}` → Workbenches tab |
| Model Registry | `/ai-hub/models/registry/{registryName}` |
| MLflow experiments | `/develop-train/mlflow/experiments?workspace={ns}` |
| Distributed workloads | `/observe-monitor/workload-metrics/workload-status/{ns}` |
| Chat playground | `/playground/{ns}` |
| Project detail | `/projects/{ns}` |

## If something fails

Check the `on_fail_hint` in the runbook step. Then:
1. Look at `source_repos` — fetch the relevant file to find the correct approach
2. Check `known_bad_patterns` — is this a documented mistake?
3. Run `oc describe` on the failing resource to get the actual error
4. If no standard fix exists: explain what you tried, what you checked, and what the user needs to do manually

Do NOT create workarounds. Only apply fixes that match what the official source code says.
</instructions>
