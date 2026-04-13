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

### Layer 4 — Module federation (EvalHub and other packages)

EvalHub (and MLflow, GenAI, Model Registry, AutoML, etc.) use **webpack module federation**
— their UIs run as **sidecar containers inside the same dashboard pod**, proxied via `/_mf/{name}`.

**Architecture** (from `manifests/modular-architecture/`):
- `federation-config` ConfigMap in the ODH namespace — contains JSON array of all module configs
- Dashboard reads it as `MODULE_FEDERATION_CONFIG` env var
- Each module is a sidecar container (e.g., `eval-hub-ui` on port 8543) in the dashboard pod
- The `odh-dashboard` Service exposes port 8543 as `eval-hub-ui`
- Dashboard backend proxies `/_mf/evalHub/*` → the sidecar on port 8543

**Who creates these?** The `modular-architecture` kustomize overlay applied at **dashboard install time**.
NOT created by the TrustyAI operator or any component operator — it's part of the dashboard deployment.

**4a — `federation-config` ConfigMap** (dashboard install artefact)

```bash
ODH_NS=redhat-ods-applications  # or opendatahub

# Check it exists and has evalHub
oc get configmap federation-config -n $ODH_NS 2>/dev/null && echo "exists" || echo "MISSING"

# Check evalHub is in the config
oc get configmap federation-config -n $ODH_NS \
  -o jsonpath='{.data.module-federation-config\.json}' \
  | python3 -m json.tool | grep -A5 '"evalHub"'
```

If missing: the `modular-architecture` overlay was not applied at install. Dashboard installation issue, not TrustyAI.

**4b — `eval-hub-ui` sidecar container in the dashboard pod**

```bash
# Check the sidecar is in the deployment spec
oc get deployment -n $ODH_NS -l app=rhods-dashboard \
  -o jsonpath='{.items[0].spec.template.spec.containers[*].name}' | tr ' ' '\n' | grep eval

# Check the running pod has the container
oc get pod -n $ODH_NS -l app=rhods-dashboard \
  -o jsonpath='{.items[0].status.containerStatuses[*].name}' | tr ' ' '\n' | grep eval

# End-to-end: does /_mf/evalHub respond?
DASH_POD=$(oc get pod -n $ODH_NS -l app=rhods-dashboard -o name | head -1)
oc exec $DASH_POD -n $ODH_NS -c rhods-dashboard -- \
  curl -sk -o /dev/null -w "%{http_code}" https://localhost:8543/healthcheck
# 200 = sidecar running, connection refused = sidecar not started
```

**Symptom map:**
- `/evaluation` returns **404** → `federation-config` missing evalHub or `eval-hub-ui` sidecar not running
- `/evaluation` shows **blank page** → sidecar running but EvalHub backend (from CR) not ready
- `/evaluation` shows **content** but no runs → everything working, just no eval job submitted yet

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
