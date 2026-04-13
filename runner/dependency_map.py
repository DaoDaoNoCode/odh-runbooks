"""
Maps dashboard pages/runbooks to their full dependency chains.
Used by 'odh deps <runbook>' to show what will be auto-resolved.
"""

DEPENDENCY_CHAINS = {
    # ── Cluster setup ──────────────────────────────────────────────────────
    "cluster/full-stack-setup": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
        ("dsc-exists", "BLOCKER — install ODH/RHOAI via OperatorHub first"),
        ("storage-class", "BLOCKER — contact cluster admin"),
    ],

    # ── Projects ───────────────────────────────────────────────────────────
    "projects/create-project": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
    ],
    "projects/create-s3-connection": [
        ("namespace", "projects/create-project"),
    ],
    "projects/add-user-to-project": [
        ("namespace", "projects/create-project"),
    ],

    # ── Workbenches ────────────────────────────────────────────────────────
    "workbenches/create-workbench": [
        ("namespace", "projects/create-project"),
        ("storage-class", "BLOCKER — no storage provisioner"),
    ],
    "workbenches/create-workbench-with-connection": [
        ("namespace", "projects/create-project"),
        ("storage-class", "BLOCKER — no storage provisioner"),
    ],
    "workbenches/create-workbench-gpu": [
        ("namespace", "projects/create-project"),
        ("storage-class", "BLOCKER — no storage provisioner"),
        ("gpu-available", "BLOCKER — add GPU nodes: odh run rosa/setup-gpu-machinepool"),
        ("gpu-operator-installed", "gpu/install-gpu-operator"),
    ],

    # ── Pipelines ──────────────────────────────────────────────────────────
    "pipelines/create-pipeline-server": [
        ("dsc-exists", "BLOCKER — install ODH/RHOAI first"),
        ("dsp-enabled", "cluster/enable-pipelines"),
        ("namespace", "projects/create-project"),
        ("s3-connection", "dependencies/provision-s3-connection → dependencies/provision-minio"),
        ("storage-class", "BLOCKER — no storage provisioner"),
    ],
    "pipelines/compile-and-submit-pipeline": [
        ("dsp-enabled", "cluster/enable-pipelines"),
        ("namespace", "projects/create-project"),
        ("pipeline-server", "dependencies/provision-pipeline-server"),
    ],
    "pipelines/upload-and-run-pipeline": [
        ("dsp-enabled", "cluster/enable-pipelines"),
        ("namespace", "projects/create-project"),
        ("pipeline-server", "dependencies/provision-pipeline-server"),
    ],
    "pipelines/create-recurring-run": [
        ("dsp-enabled", "cluster/enable-pipelines"),
        ("namespace", "projects/create-project"),
        ("pipeline-server", "dependencies/provision-pipeline-server"),
    ],

    # ── Model serving ──────────────────────────────────────────────────────
    "model-serving/deploy-kserve-model": [
        ("kserve-enabled", "cluster/enable-kserve"),
        ("namespace", "projects/create-project"),
        ("s3-connection", "dependencies/provision-s3-connection → dependencies/provision-minio"),
    ],
    "model-serving/deploy-vllm-model": [
        ("kserve-enabled", "cluster/enable-kserve"),
        ("namespace", "projects/create-project"),
        ("gpu-available", "BLOCKER — add GPU nodes: odh run rosa/setup-gpu-machinepool"),
        ("gpu-operator-installed", "gpu/install-gpu-operator"),
        ("s3-connection", "dependencies/provision-s3-connection → dependencies/provision-minio"),
    ],
    "model-serving/canary-deployment": [
        ("kserve-enabled", "cluster/enable-kserve"),
        ("namespace", "projects/create-project"),
        ("s3-connection", "dependencies/provision-s3-connection → dependencies/provision-minio"),
    ],
    "model-serving/create-custom-runtime": [
        ("kserve-enabled", "cluster/enable-kserve"),
        ("namespace", "projects/create-project"),
    ],

    # ── Model registry ─────────────────────────────────────────────────────
    "model-registry/enable-registry": [
        ("model-registry-enabled", "cluster/enable-model-registry"),
    ],
    "model-registry/register-model": [
        ("model-registry-instance", "model-registry/enable-registry"),
    ],
    "model-registry/deploy-from-registry": [
        ("model-registry-instance", "model-registry/enable-registry"),
        ("kserve-enabled", "cluster/enable-kserve"),
        ("namespace", "projects/create-project"),
        ("s3-connection", "dependencies/provision-s3-connection → dependencies/provision-minio"),
    ],
    "model-registry/search-and-compare-models": [
        ("model-registry-instance", "model-registry/enable-registry"),
    ],

    # ── EvalHub ────────────────────────────────────────────────────────────
    "evalhub/create-evaluation-run": [
        ("dsc-exists", "BLOCKER — install ODH/RHOAI first"),
        ("namespace", "projects/create-project"),
        ("trustyai-enabled", "cluster/enable-trustyai"),
        ("kserve-enabled", "cluster/enable-kserve"),
        ("s3-connection", "dependencies/provision-s3-connection → dependencies/provision-minio"),
    ],

    # ── MLflow ─────────────────────────────────────────────────────────────
    "mlflow/enable-mlflow": [
        ("dsc-exists", "BLOCKER — install ODH/RHOAI first"),
        ("namespace", "projects/create-project"),  # workspace namespace
    ],

    # ── AutoML/AutoRAG ─────────────────────────────────────────────────────
    "automl/run-automl-pipeline": [
        ("dsp-enabled", "cluster/enable-pipelines"),
        ("namespace", "projects/create-project"),
        ("pipeline-server", "dependencies/provision-pipeline-server"),
        ("s3-connection", "dependencies/provision-s3-connection → dependencies/provision-minio"),
    ],
    "autorag/run-autorag-pipeline": [
        ("dsp-enabled", "cluster/enable-pipelines"),
        ("namespace", "projects/create-project"),
        ("pipeline-server", "dependencies/provision-pipeline-server"),
    ],

    # ── Model training ─────────────────────────────────────────────────────
    "model-training/submit-pytorch-job": [
        ("training-operator-enabled", "cluster/enable-training-operator"),
        ("namespace", "projects/create-project"),
        ("gpu-available", "BLOCKER — add GPU nodes: odh run rosa/setup-gpu-machinepool"),
    ],

    # ── Distributed workloads ──────────────────────────────────────────────
    "distributed-workloads/submit-ray-job": [
        ("codeflare-enabled", "cluster/enable-codeflare"),  # also enables ray + kueue
        ("namespace", "projects/create-project"),
    ],

    # ── TrustyAI ───────────────────────────────────────────────────────────
    "trustyai/enable-trustyai-service": [
        ("trustyai-enabled", "cluster/enable-trustyai"),
        ("namespace", "projects/create-project"),
    ],

    # ── GenAI ──────────────────────────────────────────────────────────────
    "genai/enable-chat-playground": [
        ("kserve-enabled", "cluster/enable-kserve"),
        ("namespace", "projects/create-project"),
    ],

    # ── Observability ──────────────────────────────────────────────────────
    "observability/enable-perses-dashboard": [
        ("namespace", "projects/create-project"),
    ],

    # ── GPU ────────────────────────────────────────────────────────────────
    "gpu/install-gpu-operator": [
        ("gpu-available", "BLOCKER — add GPU nodes first: odh run rosa/setup-gpu-machinepool or odh run gpu/add-gpu-node-ocm"),
        ("storage-class", "BLOCKER — no storage provisioner"),
    ],
    "rosa/setup-gpu-machinepool": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
    ],

    # ── ROSA ───────────────────────────────────────────────────────────────
    "rosa/install-rhoai-prerelease": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
    ],
    "rosa/install-rhoai-stable": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
    ],
    "rosa/install-odh-specific-version": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
    ],
    "rosa/teardown-kyverno": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
    ],
    "rosa/fix-imagestream-registry": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
    ],

    # ── Dependencies ───────────────────────────────────────────────────────
    "dependencies/provision-minio": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
        ("storage-class", "BLOCKER — no storage provisioner"),
    ],
    "dependencies/provision-s3-connection": [
        ("namespace", "projects/create-project"),
        # if no external S3: provision-minio is also called
    ],
    "dependencies/provision-pipeline-server": [
        ("dsp-enabled", "cluster/enable-pipelines"),
        ("s3-connection", "dependencies/provision-s3-connection → dependencies/provision-minio"),
    ],
    "dependencies/provision-postgresql-pgvector": [
        ("openshift-cluster", "BLOCKER — run: oc login ..."),
    ],
}
