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

## Runbook discovery — match intent to runbook

When the user asks for something, match their intent against the list below. Look for the goal,
not just the exact words. If you find a match: read that runbook YAML and execute it.
If nothing matches: follow the **No runbook found** protocol at the bottom of this section.

---

### Model evaluation / EvalHub
**Runbook:** `evalhub/create-evaluation-run` → dashboard: `.../evaluation/{ns}`

Matches: "run an eval", "evaluate my model", "create an evaluation run", "set up EvalHub",
"benchmark my LLM", "test model accuracy", "run arc_easy", "lm-evaluation-harness",
"garak safety eval", "red-team my model", "model quality check", "evaluation job",
"evalhub", "trustyai eval", "score my model", "how good is my model"

---

### Deploy a model / model serving
**Runbook:** `model-serving/deploy-vllm-model` (LLMs/generative) or `model-serving/deploy-kserve-model` (any format)
→ dashboard: `.../ai-hub/deployments/{ns}`

Matches: "deploy a model", "serve a model", "host a model", "run inference", "get a model endpoint",
"deploy vLLM", "deploy llama", "deploy granite", "deploy an LLM", "model serving",
"InferenceService", "KServe", "set up model server", "I want to query a model via API",
"OpenAI-compatible endpoint", "model is not showing in dashboard", "deploy from OCI",
"modelcar catalog", "deploy without S3", "vLLM on GPU", "vLLM on CPU",
"set up a serving runtime", "deploy a generative model", "deploy a predictive model",
"sklearn model", "xgboost model", "onnx model", "llama3", "mistral", "qwen"

Use `deploy-vllm-model` for LLMs (vLLM runtime). Use `deploy-kserve-model` for sklearn/xgboost/onnx/other formats.

---

### Deploy a model from model registry
**Runbook:** `model-registry/deploy-from-registry` → dashboard: `.../ai-hub/deployments/{ns}`

Matches: "deploy from registry", "deploy a registered model", "promote model to serving",
"take model from registry and deploy", "model registry → deploy"

---

### Workbenches / notebooks
**Runbook:** `workbenches/create-workbench` (standard), `workbenches/create-workbench-gpu` (GPU),
`workbenches/create-workbench-with-connection` (with S3)
→ dashboard: `.../projects/{ns}` → Workbenches tab + direct notebook URL

Matches: "create a workbench", "open a notebook", "start a JupyterLab", "I need a notebook",
"set up a development environment", "create a Jupyter environment", "I want to write code",
"notebook server", "workbench", "data science notebook", "GPU notebook", "CUDA notebook",
"notebook with S3 access", "notebook with data connection", "codeserver", "VSCode in the browser",
"workbench is not showing", "can't open my notebook", "add a custom notebook image" (→ `workbenches/add-byon-image`)

---

### Data Science Pipelines / Kubeflow Pipelines
**Runbook:** `pipelines/create-pipeline-server` (enable pipelines in a project)
→ dashboard: `.../develop-train/pipelines/definitions/{ns}`

Also: `pipelines/compile-and-submit-pipeline` (run a pipeline), `pipelines/upload-and-run-pipeline`,
`pipelines/create-recurring-run` (schedules), `pipelines/write-kfp-component`

Matches: "set up pipelines", "enable pipelines", "I don't see a Pipelines tab", "create pipeline server",
"DSPA", "Data Science Pipelines", "Kubeflow Pipelines", "KFP", "run a pipeline",
"submit a pipeline", "schedule a pipeline", "recurring run", "pipeline server not working",
"pipeline tab missing", "upload a pipeline YAML", "compile a pipeline", "create a pipeline run",
"automate my ML workflow", "ML pipeline", "pipeline experiment"

---

### MLflow / experiment tracking
**Runbook:** `mlflow/enable-mlflow` (enable), `mlflow/log-training-run`, `mlflow/register-model-from-run`,
`mlflow/promote-model-to-production`, `mlflow/search-and-compare-runs`
→ dashboard: `.../develop-train/mlflow/experiments?workspace={ns}`

Matches: "set up MLflow", "track my experiments", "log training runs", "MLflow tracking server",
"experiment tracking", "I want to compare runs", "log metrics", "log artifacts",
"register a model from MLflow", "MLflow UI", "MLflow is not accessible",
"where do I see my training runs", "compare model versions", "MLflow experiment",
"track my fine-tuning", "track my training job", "mlflow.set_tracking_uri"

---

### Model Registry
**Runbook:** `model-registry/enable-registry` (enable), `model-registry/register-model`,
`model-registry/search-and-compare-models`
→ dashboard: `.../ai-hub/models/registry/{name}`

Matches: "enable model registry", "set up model registry", "register a model", "catalog my models",
"model versioning", "model lineage", "promote model to production", "model registry",
"I want to keep track of my models", "model catalog", "model governance",
"where do I store my models", "model metadata", "model versions"

---

### Distributed workloads / Ray
**Runbook:** `distributed-workloads/submit-ray-job`
→ dashboard: `.../observe-monitor/workload-metrics/workload-status/{ns}`

Also enable with: `cluster/enable-codeflare`

Matches: "submit a Ray job", "distributed training", "run a Ray cluster", "scale my training",
"multi-node training", "CodeFlare", "AppWrapper", "Kueue", "RayJob", "RayCluster",
"distributed workloads", "train on multiple GPUs across nodes", "Ray tune",
"I want to run a large training job", "parallel training"

---

### PyTorch training jobs
**Runbook:** `model-training/submit-pytorch-job`

Matches: "PyTorchJob", "submit a training job", "run a PyTorch training job",
"Kubeflow Training Operator", "train a model on the cluster", "TFJob"

---

### AutoML / AutoRAG
**Runbook:** `automl/run-automl-pipeline` or `autorag/run-autorag-pipeline`

Matches: "AutoML", "auto machine learning", "automated model training",
"AutoRAG", "auto RAG", "optimize my RAG pipeline", "RAG evaluation"

---

### Chat playground / GenAI
**Runbook:** `genai/enable-chat-playground`
→ dashboard: `.../playground/{ns}`

Matches: "chat with my model", "chat playground", "LLM playground", "test my model in the UI",
"I want a UI to talk to my model", "GenAI studio", "AI playground",
"chat interface", "I don't see the playground", "enable chat"

---

### TrustyAI / fairness / bias monitoring
**Runbook:** `trustyai/enable-trustyai-service`
→ dashboard: `.../ai-hub/deployments/{ns}/metrics/{model}/configure`

Matches: "enable TrustyAI", "bias detection", "fairness metrics", "model explainability",
"detect bias in my model", "monitor my model for drift", "TrustyAI",
"payload logging", "SHAP explanations", "model fairness", "AI governance",
"responsible AI monitoring"

---

### LLM tracing / prompt tracking
**Runbook:** `mlflow/create-llm-trace`, `mlflow/manage-prompts`
→ dashboard: `.../develop-train/mlflow/experiments?workspace={ns}`

Matches: "trace LLM calls", "log prompts and responses", "LLM observability",
"track my prompt templates", "prompt registry", "prompt versioning",
"OpenAI tracing", "LangChain tracing", "trace my LLM application"

---

### Projects / namespaces
**Runbook:** `projects/create-project`, `projects/add-user-to-project`, `projects/create-s3-connection`
→ dashboard: `.../projects/{ns}`

Matches: "create a data science project", "create a new project", "create a namespace",
"I don't have a project", "add a user to my project", "share my project",
"give someone access", "project permissions", "add an S3 connection",
"create a data connection", "connect to S3", "MinIO connection", "object storage connection"

---

### Cluster setup — enabling components
**Runbook:** `cluster/full-stack-setup` (everything) or individual enables below

Matches for full setup: "set up everything", "fresh cluster setup", "configure ODH from scratch",
"enable all components", "I just installed ODH and need to configure it"

| Component the user mentions | Runbook |
|---|---|
| KServe, model serving not working, InferenceService CRD missing | `cluster/enable-kserve` |
| Pipelines operator, DSP, DSPA not found | `cluster/enable-pipelines` |
| TrustyAI operator not installed | `cluster/enable-trustyai` |
| Model registry operator | `cluster/enable-model-registry` |
| CodeFlare, Ray, Kueue, distributed workloads | `cluster/enable-codeflare` |
| Training operator, PyTorchJob CRD | `cluster/enable-training-operator` |
| Feature store, Feast | `cluster/enable-feature-store` |
| Perses, observability dashboard | `observability/enable-perses-dashboard` |
| Culler, idle notebook timeout | `cluster/configure-culler` |
| Group settings, who can access the dashboard | `cluster/configure-group-settings` |
| Hardware profiles, accelerator profiles | `cluster/create-hardware-profile` |
| Custom connection type | `cluster/create-connection-type` |
| Storage classes | `cluster/configure-storage-classes` |
| Cluster-wide settings | `cluster/configure-cluster-settings` |

---

### ROSA / OpenShift on AWS
**Runbook:** `rosa/install-rhoai-stable`, `rosa/install-rhoai-prerelease`, `rosa/setup-gpu-machinepool`,
`rosa/verify-rhoai-install`, `rosa/fix-imagestream-registry`, `rosa/prepare-registry-credentials`

Matches: "install RHOAI on ROSA", "set up RHOAI on AWS", "pre-release RHOAI",
"install a specific RHOAI version", "nightly build", "RC install", "FBC image",
"add GPU nodes to ROSA", "GPU machinepool", "imagestream 401 error",
"registry.redhat.io error", "pull secret", "Kyverno workaround",
"verify my RHOAI installation", "is RHOAI installed correctly"

---

### GPU / accelerators
**Runbook:** `gpu/install-gpu-operator`, `gpu/add-gpu-node-ocm`, `gpu/verify-gpu-available`

Matches: "install GPU operator", "NVIDIA GPU operator", "add a GPU node", "GPU not available",
"no GPU nodes", "nvidia.com/gpu not showing", "NFD", "node feature discovery",
"accelerator not working", "GPU time slicing", "verify GPU is visible"

---

### Dependencies (auto-provisioned, users rarely ask directly)
These are run automatically when needed, but users might ask:
- "I need MinIO" / "S3 storage for dev" → `dependencies/provision-minio`
- "create an S3 connection for me" → `dependencies/provision-s3-connection`
- "set up a pipeline server in my project" → `dependencies/provision-pipeline-server`
- "I need PostgreSQL with pgvector" → `dependencies/provision-postgresql-pgvector`

---

### What's NOT covered yet

If the user asks for any of the following, no runbook exists. Use the **No runbook found** protocol below.

- Fine-tuning / LoRA training with dataset preparation
- Model serving with token authentication (basic deploy works, auth config is partial)
- OpenShift GitOps / ArgoCD integration for ODH resources
- Cluster upgrade or ODH operator upgrade
- Multi-cluster / federation setup
- Cost allocation, quota management, resource limits
- Building custom notebook images (BYON adds them, but not build pipelines)
- Batch inference jobs
- NVIDIA NIM serving
- LlamaStack integration
- A/B testing / canary traffic splitting in detail
- Serverless model serving (KNative) — needs Service Mesh + Serverless operators
- Data pipeline ETL (KFP components for data prep)

---

### No runbook found

If the user's request doesn't match anything above, respond with:

---
I don't have a runbook for that yet.

Here's what's available: `odh list` shows all 66 runbooks, or ask me about a specific area.

If you'd like this added:
- **Request it:** https://github.com/DaoDaoNoCode/odh-runbooks/issues/new — describe what you want to set up and what the expected dashboard page/outcome is
- **Contribute it:** Generate a draft with `odh generate <component> "<task>"`, test it on a real cluster, and open a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for the runbook schema.
---

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

## Dashboard visibility — 4 layers to check

When a component is enabled but doesn't show in the dashboard, work through these layers in order.
**The runbooks handle all of these** — but if debugging manually, check each layer:

### Layer 1 — DSC component state
```bash
oc get dsc -o jsonpath='{.items[0].spec.components}' | python3 -m json.tool
# component.managementState must be "Managed" (not "Removed")
```

### Layer 2 — OdhDashboardConfig feature flags (most common cause of "component missing")

The dashboard checks these flags from `OdhDashboardConfig.spec.dashboardConfig`.
Two patterns:
- **`disable*` flags** (default `false`): if explicitly set `true`, the section is hidden
- **Tech preview flags** (default `false`/undefined): must be explicitly `true` to show

```bash
ODH_NS=$(oc get odhdashboardconfig --all-namespaces --no-headers \
  -o jsonpath='{.items[0].metadata.namespace}' 2>/dev/null || echo 'redhat-ods-applications')
oc get odhdashboardconfig -n $ODH_NS -o jsonpath='{.spec.dashboardConfig}' | python3 -m json.tool
```

| Component | Flag to check | Fix |
|---|---|---|
| Model serving / KServe | `disableModelServing`, `disableKServe` | set to `false` |
| Pipelines | `disablePipelines` | set to `false` |
| TrustyAI bias metrics | `disableTrustyBiasMetrics` | set to `false` |
| EvalHub / LM Eval | `disableLMEval` | set to `false` |
| Model Registry | `disableModelRegistry` | set to `false` |
| Distributed Workloads | `disableDistributedWorkloads` | set to `false` |
| Feature Store | `disableFeatureStore` | set to `false` |
| MLflow (**tech preview**) | `mlflow` | set to `true` |
| Training Jobs (**tech preview**) | `trainingJobs` | set to `true` |

Fix a blocked component:
```bash
CFG=$(oc get odhdashboardconfig -n $ODH_NS -o name | head -1)
# Example: unblock model serving
oc patch $CFG -n $ODH_NS --type merge \
  -p '{"spec":{"dashboardConfig":{"disableModelServing":false,"disableKServe":false}}}'

# Enable MLflow tech preview
oc patch $CFG -n $ODH_NS --type merge \
  -p '{"spec":{"dashboardConfig":{"mlflow":true}}}'
```

### Layer 3 — DSCI capabilities
```bash
oc get dsci -o jsonpath='{.items[0].status.conditions}' | python3 -m json.tool
# All required capabilities must have status: "True"
# This is automatic when DSCI is healthy — rarely needs manual intervention
```

### Layer 4 — Module federation (two different patterns)

The `federation-config` ConfigMap in the ODH namespace is the source of truth for all federated modules.
The dashboard reads it as `MODULE_FEDERATION_CONFIG` env var. But the modules themselves run in two different ways:

**Pattern A — Sidecar in dashboard pod (EvalHub, GenAI, Model Registry, MaaS, AutoML, AutoRAG)**

These run as sidecar containers inside the same dashboard pod, added by the `modular-architecture` kustomize overlay at dashboard install time.

| Module | Sidecar name | Port | federation-config service target |
|---|---|---|---|
| EvalHub | `eval-hub-ui` | 8543 | `odh-dashboard:8543` |
| GenAI | `gen-ai-ui` | 8143 | `odh-dashboard:8143` |
| Model Registry | `model-registry-ui` | 8043 | `odh-dashboard:8043` |
| MLflow (new pkg) | `mlflow-ui` | 8343 | `odh-dashboard:8343` |

Check:
```bash
ODH_NS=redhat-ods-applications  # or opendatahub

# federation-config ConfigMap (must exist — dashboard install artefact)
oc get configmap federation-config -n $ODH_NS -o jsonpath='{.data.module-federation-config\.json}' \
  | python3 -m json.tool | grep '"name"'

# sidecar containers in dashboard pod
oc get deployment -n $ODH_NS -l app=rhods-dashboard \
  -o jsonpath='{.items[0].spec.template.spec.containers[*].name}' | tr ' ' '\n'
```

If `federation-config` or sidecars are missing: the `modular-architecture` overlay was not applied at dashboard install. Dashboard installation issue, not a component operator issue.

**Pattern B — Separate pod from a component operator (MLflow via mlflow-operator)**

MLflow is served from a **separate pod** created by the **mlflow-operator** — not a sidecar.
The federation-config entry `mlflowEmbedded` points directly to this pod's service:

```json
{
  "name": "mlflowEmbedded",
  "remoteEntry": "/mlflow/static-files/federated/remoteEntry.js",
  "service": { "name": "mlflow", "namespace": "opendatahub", "port": 8443 }
}
```

The `mlflow` service is created by the mlflow-operator when the MLflow CR (which MUST be named `mlflow`) reaches Ready. The MLflow server pod serves the federated UI at `/mlflow/static-files/federated/remoteEntry.js` (hardcoded `staticPrefix=/mlflow` in the operator).

Check:
```bash
# Is the mlflow service running?
oc get service mlflow -n $ODH_NS

# Is the pod ready?
oc get pod -l app=mlflow -n $ODH_NS

# Does the federated UI respond?
MLFLOW_POD=$(oc get pod -l app=mlflow -n $ODH_NS -o name | head -1)
oc exec $MLFLOW_POD -n $ODH_NS -- curl -sk -o /dev/null -w "%{http_code}" \
  https://localhost:8443/mlflow/static-files/federated/remoteEntry.js
# 200 = working
```

**Symptom maps:**

EvalHub (`/evaluation`):
- **404** → `federation-config` missing `evalHub` or `eval-hub-ui` sidecar not running (dashboard install)
- **blank page** → sidecar running but EvalHub CR backend not ready yet
- **content, no runs** → everything working, no eval job submitted

MLflow (`/develop-train/mlflow`):
- **404 / blank** → `mlflow` service not running (mlflow-operator hasn't created it yet — check MLflow CR)
- **loads but API fails** → `mlflow: true` flag not set in OdhDashboardConfig

---

## Pod scheduling — fail fast, don't wait 15 minutes

When a model deployment step polls for `activeModelState=Loaded`, **always check pod conditions
after the first 45 seconds**. Two terminal conditions that will NEVER self-resolve:

### Unschedulable — no node has sufficient resources
```bash
# Check for Unschedulable condition
oc get pod -l serving.kserve.io/inferenceservice=<model> -n <ns> \
  -o jsonpath='{.items[0].status.conditions[?(@.reason=="Unschedulable")].message}'

# Check what resources nodes actually have
oc get nodes --no-headers | awk '{print $1, $4, $5}'
oc get nodes -l nvidia.com/gpu.present=true --no-headers || echo "(no GPU nodes)"
```

**If GPU requested but no GPU nodes:** this is the most common case. Standard fix:
1. `oc delete inferenceservice <model> -n <ns>`
2. `oc delete servingruntime vllm-cuda-runtime -n <ns>` (if created)
3. Recreate with CPU runtime: `oc process -n redhat-ods-applications vllm-cpu-runtime-template | oc apply -n <ns> -f -`
4. Use a small model: `qwen2.5-0.5b-instruct` (~1 GB, needs ~6 Gi memory, ~4 CPU)

**If CPU/memory insufficient:** use a smaller model or reduce resource requests.
Check: `oc describe nodes | grep -A 5 "Allocated resources"`

### ImagePullBackOff / ErrImagePull — check WHICH image before deciding

```bash
# Find the failing image
oc describe pod -l serving.kserve.io/inferenceservice=<model> -n <ns> | grep "Failed to pull image"
```

**Two different situations — different responses:**

**1. Subscription-gated image** (`quay.io/rhoai/`, `registry.redhat.io/rh*`):
Not terminal — fixable. These are RHOAI-subscription images. The standard fix is to use
the public CPU runtime image instead: `quay.io/rh-aiservices-bu/vllm-cpu-openai-ubi9:0.3`

```bash
# Delete the runtime that uses the subscription image
oc delete servingruntime <runtime-name> -n <ns>
oc delete inferenceservice <model> -n <ns>
# Recreate ServingRuntime with the public image, then redeploy the InferenceService
```

**2. Public registry image with wrong URI** (`quay.io/rh-aiservices-bu/`, `quay.io/redhat-ai-services/`):
Truly terminal if the URI is wrong — retrying won't help.
Verify the image reference and fix the URI.

### CrashLoopBackOff / OOMKilled — check logs, attempt one standard fix

These conditions mean the container started but is crashing. Unlike Unschedulable/ImagePullBackOff,
these are often fixable. **Pull the logs, read them, apply at most one clear standard fix.**

```bash
# Get logs (try both container names used by KServe)
oc logs -l serving.kserve.io/inferenceservice=<model> -n <ns> --tail=60
oc logs -l serving.kserve.io/inferenceservice=<model> -n <ns> -c kserve-container --tail=60
```

**Common fixable log errors and their standard fixes:**

| Log shows | Root cause | Standard fix |
|---|---|---|
| `max_model_len` exceeds model's max | --max-model-len too high | Reduce to model's actual max (e.g. qwen2.5-0.5b max is 2048) |
| `killed` / `OOMKilled` in events | Not enough memory for the model | Reduce `--max-model-len` further or use a smaller model |
| `RuntimeError: bfloat16 is not supported` | Wrong dtype for GPU type | Change `--dtype=half` → `--dtype=bfloat16`, or remove `--dtype` |
| `no module named vllm` / import error | Wrong container image | Check runtime image — likely wrong ServingRuntime |
| `CUDA out of memory` | GPU VRAM too small | Reduce `--gpu-memory-utilization` to 0.85, or reduce `--max-model-len` |

**When applying a fix to an InferenceService:** re-apply the full manifest (not `oc patch` with index-based args) to avoid fragile index arithmetic. Delete and recreate is cleaner.

**Principle:** one root cause → one standard fix. If the log is unclear → show it and stop.

**Never:** patch around the error with env hacks, skip validation, or modify operator-owned resources.

### Polling — always track the NEWEST pod

When multiple pods exist (during a rolling update after a patch), **always sort by creation time and track the newest one**. Old terminating/crashing pods are irrelevant.

```bash
# WRONG — head -1 may return an old pod from a previous rollout
POD_NAME=$(oc get pods -l serving.kserve.io/inferenceservice=<model> -n <ns> --no-headers | head -1 | awk '{print $1}')

# CORRECT — sort by age, newest last
POD_NAME=$(oc get pods -l serving.kserve.io/inferenceservice=<model> -n <ns> \
  --no-headers --sort-by=.metadata.creationTimestamp 2>/dev/null | tail -1 | awk '{print $1}')

# Skip if the pod is being terminated (old rollout pod)
IS_TERMINATING=$(oc get pod "$POD_NAME" -n <ns> \
  -o jsonpath='{.metadata.deletionTimestamp}' 2>/dev/null)
[ -n "$IS_TERMINATING" ] && continue  # wait for new pod to appear
```

### `1/2 Running` + readiness probe failed — normal during model loading

The most common `1/2 Running` state is **not an error**. It is the expected lifecycle
of any ML serving container: start → load weights into memory → begin serving → ready.

The readiness probe fires against the serving port (e.g. 8080) the whole time.
While weights are loading it gets `connection refused` because the HTTP server
hasn't started yet. This is normal. Once loading completes, the server starts,
the readiness probe passes, and the pod goes to `2/2 Running`.

**The only thing that matters during this wait: is the container still Running?**
```bash
# Generic: check container states (not readiness)
oc get pod <pod> -n <ns> \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}: {.state}{"\n"}{end}'
```

- Container state `running` + readiness failing → **still loading, keep waiting**
- Container state `waiting: CrashLoopBackOff` → crashed, check logs
- Container state `terminated: OOMKilled` → out of memory, reduce resources

**Read events to understand what's happening (generic diagnostic):**
```bash
oc get events -n <ns> \
  --field-selector involvedObject.name=<pod-name> \
  --sort-by='.lastTimestamp' | tail -10
```

Event says `Readiness probe failed: connection refused` → server loading, normal.
Event says `Readiness probe failed: HTTP 500` → server started but erroring, check logs.
Event says `OOMKilled` or `BackOff` → real failure, investigate.

**Container roles in a KServe predictor pod — know which one to check:**

| Container name | Role | Expected logs |
|---|---|---|
| `kserve-container` | The actual model server (vLLM, OVMS, etc.) | Loading progress, errors → **check this for diagnostics** |
| `modelcar` | OCI model file server — serves model files from the image at `/mnt/models` | **Always 0 lines — silent by design, this is normal** |
| `kube-rbac-proxy` / other proxies | Auth/network proxy injected by OpenShift | Minimal logs unless misconfigured |

**Always check `kserve-container` for model loading status:**
```bash
# CORRECT — gets actual model server logs
oc logs <pod> -n <ns> -c kserve-container --tail=60

# WRONG — may return modelcar (0 lines), which tells you nothing
oc logs <pod> -n <ns> --tail=60
```

If `kserve-container` logs show active loading output (weight loading progress, device initialization) → the model is loading, keep waiting.  
If `kserve-container` logs are empty after 5+ minutes → the container may be waiting for model files from `modelcar` or has a silent startup issue. Check: `oc describe pod <pod> -n <ns> | grep -A 5 Events`.

**CPU model load times (rough estimates):** qwen2.5-0.5b ≈ 5-10 min, llama-3.2-1b ≈ 15 min, granite-3.3-2b ≈ 25-30 min. If `kserve-container` shows active output within these windows — it is working normally.

**If `kserve-container` logs show `Application startup complete` but the pod stays `1/2 Running`:**
The server is up but the readiness probe can't reach it — almost always a port mismatch.
```bash
# Check what port vLLM is actually serving on:
oc logs <pod> -n <ns> -c kserve-container | grep "Starting vLLM API server"
# e.g. "on http://0.0.0.0:8000" → vLLM is on 8000, KServe probes 8080 → mismatch

# Fix: ServingRuntime must declare port 8080 AND pass --port=8080 to vLLM
# Also: --model=/mnt/models ensures vLLM reads the modelcar-provided model files,
# not its own default (you may see facebook/opt-125m if this arg is missing)
```

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
