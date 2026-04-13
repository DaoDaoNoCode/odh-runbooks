# ODH Runbook Library

Status of all 66 runbooks in this repo.

## Status legend

| Symbol | Meaning |
|---|---|
| [D] | Draft — exists, not tested on a real cluster |
| [T] | Tested — ran on real cluster, confidence promoted |
| [V] | Verified — tested twice, marked `verified` |

All runbooks have `source_repos` configured so Claude knows which GitHub repos to check when something fails.

Generate new drafts with:
```bash
odh generate <component> "<task>"
```

Then test, fix, and promote confidence: `inferred` → `doc-derived` → `verified`.

---

## Cluster / Operator

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `cluster/full-stack-setup` | opendatahub-operator, kserve, data-science-pipelines-operator, trustyai |
| [D] | `cluster/enable-kserve` | kserve, odh-model-controller, opendatahub-operator |
| [D] | `cluster/enable-pipelines` | data-science-pipelines-operator, data-science-pipelines |
| [D] | `cluster/enable-trustyai` | trustyai-explainability, trustyai-service-operator |
| [D] | `cluster/enable-codeflare` | codeflare-operator, kueue |
| [D] | `cluster/enable-training-operator` | training-operator |
| [D] | `cluster/enable-model-registry` | model-registry-operator, kubeflow/model-registry |
| [D] | `cluster/enable-feature-store` | feast-dev/feast |
| [D] | `cluster/configure-cluster-settings` | opendatahub-operator, odh-dashboard |
| [D] | `cluster/configure-group-settings` | opendatahub-operator, odh-dashboard |
| [D] | `cluster/configure-storage-classes` | opendatahub-operator |
| [D] | `cluster/configure-culler` | notebooks, opendatahub-operator |
| [D] | `cluster/create-hardware-profile` | opendatahub-operator, odh-dashboard |
| [D] | `cluster/create-connection-type` | odh-dashboard |

## GPU

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `gpu/install-gpu-operator` | NVIDIA/gpu-operator |
| [D] | `gpu/add-gpu-node-ocm` | NVIDIA/gpu-operator, openshift/rosa |
| [D] | `gpu/verify-gpu-available` | NVIDIA/gpu-operator |

## ROSA

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `rosa/install-rhoai-stable` | opendatahub-operator, openshift/rosa |
| [D] | `rosa/install-rhoai-prerelease` | opendatahub-operator, openshift/rosa |
| [D] | `rosa/install-odh-specific-version` | opendatahub-operator, openshift/rosa |
| [D] | `rosa/setup-gpu-machinepool` | NVIDIA/gpu-operator, openshift/rosa |
| [D] | `rosa/verify-rhoai-install` | opendatahub-operator, openshift/rosa |
| [D] | `rosa/fix-imagestream-registry` | opendatahub-operator, openshift/rosa |
| [D] | `rosa/prepare-registry-credentials` | opendatahub-operator, openshift/rosa |
| [D] | `rosa/teardown-kyverno` | opendatahub-operator |

## Projects

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `projects/create-project` | odh-dashboard, opendatahub-operator |
| [D] | `projects/add-user-to-project` | odh-dashboard, opendatahub-operator |
| [D] | `projects/create-s3-connection` | odh-dashboard, opendatahub-operator |

## Workbenches

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `workbenches/create-workbench` | notebooks, opendatahub-operator, odh-dashboard |
| [D] | `workbenches/create-workbench-gpu` | notebooks, opendatahub-operator, odh-dashboard |
| [D] | `workbenches/create-workbench-with-connection` | notebooks, opendatahub-operator, odh-dashboard |
| [D] | `workbenches/add-byon-image` | notebooks, odh-dashboard |

## Pipelines

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `pipelines/create-pipeline-server` | data-science-pipelines-operator, data-science-pipelines, kubeflow/pipelines |
| [D] | `pipelines/upload-and-run-pipeline` | data-science-pipelines, kubeflow/pipelines |
| [D] | `pipelines/compile-and-submit-pipeline` | data-science-pipelines, kubeflow/pipelines |
| [D] | `pipelines/create-recurring-run` | data-science-pipelines, kubeflow/pipelines |
| [D] | `pipelines/write-kfp-component` | data-science-pipelines, kubeflow/pipelines |

## Model Serving

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `model-serving/deploy-vllm-model` | kserve, odh-model-controller, vllm-project/vllm |
| [D] | `model-serving/deploy-kserve-model` | kserve, odh-model-controller |
| [D] | `model-serving/deploy-llmd-model` | kserve, odh-model-controller |
| [D] | `model-serving/canary-deployment` | kserve, odh-model-controller |
| [D] | `model-serving/create-custom-runtime` | kserve, odh-model-controller |
| [D] | `model-serving/test-model-endpoint` | kserve |

## Model Registry

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `model-registry/enable-registry` | model-registry-operator, kubeflow/model-registry |
| [D] | `model-registry/register-model` | model-registry-operator, kubeflow/model-registry |
| [D] | `model-registry/deploy-from-registry` | model-registry-operator, kserve |
| [D] | `model-registry/search-and-compare-models` | model-registry-operator, kubeflow/model-registry |

## EvalHub

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `evalhub/create-evaluation-run` | eval-hub/eval-hub, trustyai-service-operator, kserve |

## MLflow

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `mlflow/enable-mlflow` | mlflow/mlflow, opendatahub-operator |
| [D] | `mlflow/log-training-run` | mlflow/mlflow |
| [D] | `mlflow/create-llm-trace` | mlflow/mlflow |
| [D] | `mlflow/register-model-from-run` | mlflow/mlflow, kubeflow/model-registry |
| [D] | `mlflow/promote-model-to-production` | mlflow/mlflow, kubeflow/model-registry |
| [D] | `mlflow/manage-prompts` | mlflow/mlflow |
| [D] | `mlflow/search-and-compare-runs` | mlflow/mlflow |

## Distributed Workloads

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `distributed-workloads/submit-ray-job` | codeflare-operator, codeflare-sdk, ray-project/ray, kueue |

## Model Training

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `model-training/submit-pytorch-job` | kubeflow/training-operator |

## TrustyAI

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `trustyai/enable-trustyai-service` | trustyai-explainability, trustyai-service-operator |

## Observability

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `observability/enable-perses-dashboard` | perses/perses, perses/perses-operator |

## GenAI

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `genai/enable-chat-playground` | odh-dashboard, kserve |

## AutoML / AutoRAG

| Status | Path | Source repos checked |
|--------|------|---------------------|
| [D] | `automl/run-automl-pipeline` | data-science-pipelines-operator, kubeflow/pipelines |
| [D] | `autorag/run-autorag-pipeline` | kserve, data-science-pipelines-operator |

## Dependencies (auto-provisioned)

These runbooks are called automatically when a dependency is missing — users never call them directly.

| Status | Path | What it provisions |
|--------|------|-------------------|
| [D] | `dependencies/provision-minio` | MinIO S3-compatible storage (dev/test only) |
| [D] | `dependencies/provision-s3-connection` | S3 Secret in a namespace |
| [D] | `dependencies/provision-pipeline-server` | DSPA (pipeline server) in a namespace |
| [D] | `dependencies/provision-postgresql-pgvector` | PostgreSQL with pgvector extension |

---

## Priority: promote these to `verified`

Most-used runbooks that would benefit most from real cluster testing:

1. `evalhub/create-evaluation-run` — core use case for the whole project
2. `model-serving/deploy-vllm-model` — most common model deployment
3. `cluster/enable-kserve` — prerequisite for model serving
4. `cluster/full-stack-setup` — the big one
5. `rosa/install-rhoai-prerelease` — complex multi-step, high value if it works reliably
