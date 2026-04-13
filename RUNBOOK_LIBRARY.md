# ODH Runbook Library

All runbooks below can be generated with:
  odh generate <component> "<task>"

Then reviewed and saved to the appropriate path. After testing on a real cluster,
promote confidence levels from `inferred` → `doc-derived` → `verified`.

## Status legend
- [ ] not yet generated
- [D] draft generated, not tested
- [T] tested on cluster, confidence promoted
- [V] fully verified

---

## Cluster / Operator

| Status | Path | Description |
|--------|------|-------------|
| [D] | cluster/enable-trustyai | Enable TrustyAI in DataScienceCluster |
| [ ] | cluster/enable-kserve | Enable KServe single-model serving |
| [ ] | cluster/enable-modelmesh | Enable ModelMesh multi-model serving |
| [ ] | cluster/enable-pipelines | Enable Data Science Pipelines |
| [ ] | cluster/enable-codeflare | Enable CodeFlare / distributed workloads |
| [ ] | cluster/enable-mlflow | Enable MLflow experiment tracking |
| [ ] | cluster/enable-feature-store | Enable Feast feature store |
| [ ] | cluster/enable-ray | Enable Ray distributed computing |
| [ ] | cluster/configure-culler | Configure notebook auto-stop (culler) |
| [ ] | cluster/configure-model-serving-platform | Set cluster-wide serving platform (KServe vs ModelMesh) |

## GPU

| Status | Path | Description |
|--------|------|-------------|
| [ ] | gpu/add-gpu-node-ocm | Add a GPU node via OpenShift Cluster Manager (OCM) |
| [ ] | gpu/install-gpu-operator | Install NVIDIA GPU Operator on OpenShift |
| [ ] | gpu/verify-gpu-available | Verify GPU is visible and allocatable in the cluster |
| [ ] | gpu/install-amd-gpu-operator | Install AMD ROCm GPU Operator |
| [ ] | gpu/configure-time-slicing | Configure NVIDIA GPU time-slicing for shared access |

## Projects

| Status | Path | Description |
|--------|------|-------------|
| [ ] | projects/create-project | Create a new Data Science Project |
| [ ] | projects/add-user-to-project | Add a user to an existing project |
| [ ] | projects/create-connection | Create an S3/database connection in a project |

## Workbenches

| Status | Path | Description |
|--------|------|-------------|
| [ ] | workbenches/create-workbench | Create a Jupyter workbench in a project |
| [ ] | workbenches/create-workbench-gpu | Create a workbench with GPU resource |
| [ ] | workbenches/stop-workbench | Stop a running workbench |
| [ ] | workbenches/add-byon-image | Add a custom (BYON) notebook image |
| [ ] | workbenches/add-storage-to-workbench | Attach PVC storage to a workbench |

## Pipelines (DSP)

| Status | Path | Description |
|--------|------|-------------|
| [ ] | pipelines/enable-dsp | Enable Data Science Pipelines in a project |
| [ ] | pipelines/create-pipeline-server | Create a DSPA (pipeline server) in a project |
| [ ] | pipelines/upload-and-run-pipeline | Upload a KFP pipeline YAML and create a run |
| [ ] | pipelines/schedule-pipeline | Create a recurring pipeline schedule |
| [ ] | pipelines/run-automl-pipeline | Run the AutoML pipeline on a dataset |
| [ ] | pipelines/run-autorag-pipeline | Run the AutoRAG optimization pipeline |

## Model Serving

| Status | Path | Description |
|--------|------|-------------|
| [ ] | model-serving/deploy-kserve-model | Deploy a model via KServe InferenceService |
| [ ] | model-serving/deploy-modelmesh-model | Deploy a model via ModelMesh |
| [ ] | model-serving/deploy-vllm-model | Deploy an LLM with vLLM serving runtime |
| [ ] | model-serving/create-serving-runtime | Register a custom ServingRuntime |
| [ ] | model-serving/test-model-endpoint | Send a test request to a deployed model |
| [ ] | model-serving/enable-token-auth | Enable token authentication on a model endpoint |

## Model Registry

| Status | Path | Description |
|--------|------|-------------|
| [ ] | model-registry/enable-registry | Create a new Model Registry instance |
| [ ] | model-registry/register-model | Register a model version in the registry |
| [ ] | model-registry/deploy-from-registry | Deploy a registered model to KServe |
| [ ] | model-registry/add-user-to-registry | Grant a user access to a model registry |

## EvalHub

| Status | Path | Description |
|--------|------|-------------|
| [D] | evalhub/create-evaluation-run | Create an evaluation run linked to MLflow |
| [ ] | evalhub/run-safety-evaluation | Run garak safety evaluation on a deployed model |
| [ ] | evalhub/run-benchmark-collection | Run a named benchmark collection (leaderboard-v2) |

## GenAI / Chat Playground

| Status | Path | Description |
|--------|------|-------------|
| [ ] | genai/enable-chat-playground | Enable the GenAI chat playground in the dashboard |
| [ ] | genai/connect-model-to-playground | Connect a deployed model to the chat playground |
| [ ] | genai/configure-llama-stack | Configure Llama Stack for the GenAI plugin |
| [ ] | genai/enable-maas | Enable Model-as-a-Service (MaaS) |

## MLflow

| Status | Path | Description |
|--------|------|-------------|
| [ ] | mlflow/enable-mlflow | Enable MLflow in a project |
| [ ] | mlflow/create-experiment | Create an MLflow experiment |
| [ ] | mlflow/view-experiment-runs | Get experiment run URLs for a project |

## Distributed Workloads

| Status | Path | Description |
|--------|------|-------------|
| [ ] | distributed-workloads/submit-ray-job | Submit a Ray distributed training job |
| [ ] | distributed-workloads/create-ray-cluster | Create a RayCluster for interactive use |
| [ ] | distributed-workloads/configure-kueue-quota | Set up Kueue resource quotas for a team |

## Hardware Profiles

| Status | Path | Description |
|--------|------|-------------|
| [ ] | cluster/create-hardware-profile | Create a hardware profile (CPU/GPU tier) |
| [ ] | cluster/create-toleration-profile | Add node toleration to a hardware profile |

---

## Adding new runbooks

1. Generate a draft:
   ```
   odh generate <component> "<task description>"
   ```

2. Review the YAML, fix anything obviously wrong

3. Test on a throwaway cluster:
   ```
   odh run <component>/<runbook-name> --param ...
   ```

4. For every step that worked correctly, change confidence from `inferred` → `doc-derived`

5. After a second successful run with no manual intervention, update `rhoai_version_tested`
   and change `confidence_overall` to `doc-derived`

6. Commit. Others can now use it reliably.
