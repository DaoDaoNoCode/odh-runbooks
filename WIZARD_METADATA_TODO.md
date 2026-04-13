# Runbooks still needing wizard metadata (example/hint/discover_cmd/enum)

Priority order for adding metadata:

## High priority (most commonly used, most confusing params)
- projects/create-project — project_name format
- projects/create-s3-connection — s3_endpoint format, aws_access_key_id where to find
- model-serving/deploy-kserve-model — model_format enum, model_uri format
- model-registry/deploy-from-registry — model_version_id where to find
- pipelines/create-pipeline-server — auto-discovery now handles most params
- rosa/setup-gpu-machinepool — instance_type options per GPU tier
- workbenches/create-workbench-gpu — notebook_image CUDA variants
- model-training/submit-pytorch-job — training_image examples

## Add quickly with:
  odh generate <component> "<task>"  # regenerates with AI that knows the schema
