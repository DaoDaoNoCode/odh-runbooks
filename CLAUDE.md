# ODH Runbooks — Claude Code Context

This repo contains 66 verified runbooks for making ODH/RHOAI dashboard pages work correctly.
**The goal of every runbook is a direct link to the specific dashboard page at the end.**

You are Claude Code running inside this repo. When a user asks to set up, deploy, or configure
anything RHOAI/ODH-related — read the relevant runbook YAML, check the cluster, execute, and
return a working dashboard URL.

---

## How to execute a runbook

You do NOT need the `odh` CLI. Read the runbook YAML directly and execute using Bash + WebFetch.

```
1. Read runbooks/<component>/<name>.yaml
2. Check cluster state with oc commands (skip steps already done)
3. For anything unclear: fetch the source_repos listed in the runbook from GitHub
4. Execute each step in order using Bash
5. Return the dashboard URL at the end
```

**Rules:**
- Check `source_repos` before applying any non-obvious configuration — never guess
- Skip steps where `pre_check` shows the resource already exists
- If a step fails and no standard fix exists in the source repos: stop and explain what to do manually
- Never create workarounds — only standard approaches from the official source code

---

## Request → runbook → dashboard URL

| User asks for | Read this runbook | Dashboard URL at the end |
|---|---|---|
| EvalHub / evaluation run | `evalhub/create-evaluation-run` | `.../evaluation/{ns}` |
| Deploy vLLM model | `model-serving/deploy-vllm-model` | `.../ai-hub/deployments/{ns}` |
| Deploy any model | `model-serving/deploy-kserve-model` | `.../ai-hub/deployments/{ns}` |
| Pipeline server / Pipelines tab | `pipelines/create-pipeline-server` | `.../develop-train/pipelines/definitions/{ns}` |
| Run a pipeline | `pipelines/compile-and-submit-pipeline` | `.../develop-train/pipelines/runs/{ns}/runs/{runId}` |
| Schedule a recurring pipeline | `pipelines/create-recurring-run` | `.../develop-train/pipelines/runs/{ns}/schedules` |
| Workbench / notebook | `workbenches/create-workbench` | `.../projects/{ns}` → Workbenches tab + direct notebook URL |
| Model Registry UI | `model-registry/enable-registry` | `.../ai-hub/models/registry/{name}` |
| Register a model | `model-registry/register-model` | `.../ai-hub/models/registry/{name}/registered-models` |
| Deploy from model registry | `model-registry/deploy-from-registry` | `.../ai-hub/deployments/{ns}` |
| MLflow experiment tracking | `mlflow/enable-mlflow` | `.../develop-train/mlflow/experiments?workspace={ns}` |
| Ray / distributed workloads | `distributed-workloads/submit-ray-job` | `.../observe-monitor/workload-metrics/workload-status/{ns}` |
| Chat playground | `genai/enable-chat-playground` | `.../playground/{ns}` |
| TrustyAI / bias monitoring | `trustyai/enable-trustyai-service` | `.../ai-hub/deployments/{ns}/metrics/{model}/configure` |
| Enable KServe | `cluster/enable-kserve` | (cluster-level, unblocks model serving) |
| Enable pipelines operator | `cluster/enable-pipelines` | (cluster-level, unblocks pipelines) |
| Enable model registry operator | `cluster/enable-model-registry` | (cluster-level, unblocks registry) |
| Install RHOAI on ROSA | `rosa/install-rhoai-stable` or `rosa/install-rhoai-prerelease` | (cluster-level) |
| Set up everything | `cluster/full-stack-setup` | (enables all components) |
| Create a project | `projects/create-project` | `.../projects/{ns}` |
| Add GPU node | `rosa/setup-gpu-machinepool` | (cluster-level) |
| Observability dashboard | `observability/enable-perses-dashboard` | (cluster-level) |

---

## How runbook YAML is structured

```yaml
name: ...
description: >        # What this does + critical caveats
  ...
source_repos:         # GitHub repos to check BEFORE applying non-obvious configs
  - "https://github.com/kserve/kserve"
  - "https://github.com/opendatahub-io/odh-dashboard"   # reference for labels/annotations
parameters:           # Variables used in {{ }} Jinja2 templates throughout the file
  - name: project_namespace
    discover_cmd: "oc get namespace -l opendatahub.io/dashboard=true ..."
steps:
  - id: step-name
    requires:         # Dependencies — auto-resolve these if missing (run the resolver runbook)
      - type: kserve-enabled
    pre_check:        # Run this first — if it passes, skip the step (idempotency)
      command: "oc get ... | wc -l"
      expected: "1"
      if_already_true: skip
    action:           # What to do
      type: apply
      manifest: |    # Render {{ variables }} before applying
        apiVersion: ...
    post_check:       # Verify it worked
      command: "oc get ... -o jsonpath=..."
      expected: "Ready"
    on_fail_hint: >   # What to check if this step fails
      ...
known_bad_patterns:   # What NEVER to do — reference before any action
  - "never create X manually — the operator auto-creates it"
```

---

## Dependency auto-resolution

When a step has `requires:`, check if the dependency exists. If not, run the resolver runbook first:

| Requirement type | Check | Resolver runbook |
|---|---|---|
| `kserve-enabled` | `oc get crd inferenceservices.serving.kserve.io` | `cluster/enable-kserve` |
| `trustyai-enabled` | `oc get crd trustyaiservices.trustyai.opendatahub.io` | `cluster/enable-trustyai` |
| `dsp-enabled` | `oc get crd datasciencepipelinesapplications.datasciencepipelinesapplications.opendatahub.io` | `cluster/enable-pipelines` |
| `namespace` | `oc get namespace {name}` | `projects/create-project` |
| `pipeline-server` | `oc get dspa -n {ns}` | `dependencies/provision-pipeline-server` |
| `s3-connection` | `oc get secret -n {ns} -l opendatahub.io/connection-type=s3` | `dependencies/provision-s3-connection` |
| `gpu-available` | `oc get nodes -l nvidia.com/gpu.present=true` | **BLOCKER** — tell user to add GPU nodes |
| `dsc-exists` | `oc get dsc` | **BLOCKER** — ODH operator not installed |

---

## Key technical facts

**The dashboard host:**
```bash
oc get route rhods-dashboard -n redhat-ods-applications -o jsonpath='{.spec.host}' 2>/dev/null || \
oc get route rhods-dashboard -n opendatahub -o jsonpath='{.spec.host}' 2>/dev/null
```

**RHOAI operator namespace:** `redhat-ods-applications` (RHOAI) or `opendatahub` (ODH)

**DataScienceCluster patch pattern** (enabling components):
```bash
oc patch $(oc get dsc -o name | head -1) --type merge \
  -p '{"spec":{"components":{"kserve":{"managementState":"Managed"}}}}'
```

**The operator auto-creates** (never create these manually):
- OpenShift Routes for deployed models
- ServiceMonitors and PodMonitors
- ClusterRoleBindings when auth is enabled
- Templates for ServingRuntimes in `redhat-ods-applications`

**ServingRuntime templates** (RHOAI stores these as OpenShift Templates, not ClusterServingRuntimes):
```bash
oc get template -n redhat-ods-applications | grep vllm
oc process -n redhat-ods-applications vllm-cuda-runtime-template | oc apply -n <ns> -f -
```

**Dashboard labels required on resources** (so they appear in the UI):
- `opendatahub.io/dashboard: "true"` — required on most resources
- `openshift.io/display-name: "..."` — required on InferenceService, Notebook, connections
- `opendatahub.io/connection-type: "uri"` — on URI data connections (for OCI/modelcar models)
- `opendatahub.io/connection-type: "s3"` — on S3 data connections

**OCI model catalog** (no S3 needed):
```
oci://quay.io/redhat-ai-services/modelcar-catalog:granite-3.3-2b-instruct  (5 GB)
oci://quay.io/redhat-ai-services/modelcar-catalog:llama-3.2-1b-instruct    (2.5 GB)
oci://quay.io/redhat-ai-services/modelcar-catalog:granite-3.3-8b-instruct  (16 GB)
```

**modelFormat.name is case-sensitive:** must be `vLLM` not `vllm`

---

## Parameters to discover from the cluster

```bash
# ODH Data Science Projects (valid namespaces)
oc get namespace -l opendatahub.io/dashboard=true --no-headers -o jsonpath='{.items[*].metadata.name}'

# Deployed models in a namespace
oc get inferenceservice -n <namespace> --no-headers

# Existing S3 connections
oc get secret -n <namespace> -l opendatahub.io/connection-type=s3 -o jsonpath='{.items[*].metadata.name}'

# ServingRuntime templates (built-in runtimes)
oc get template -n redhat-ods-applications --no-headers -o custom-columns=NAME:.metadata.name | grep -i vllm

# What's enabled in DataScienceCluster
oc get dsc -o jsonpath='{.items[0].spec.components}' | python3 -m json.tool
```

---

## Installing the `odh` CLI (optional — needs ANTHROPIC_API_KEY)

The `odh` CLI is an alternative that calls Claude via API. It's optional — Claude Code already
does everything the `odh` CLI does, without needing a separate API key.

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
odh wizard evalhub/create-evaluation-run
odh doctor
odh list
```
