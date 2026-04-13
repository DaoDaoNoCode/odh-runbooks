# Security

## Reporting a security issue

Please do not open a public GitHub issue for security vulnerabilities. Report them via:
- GitHub's [private vulnerability reporting](../../security/advisories/new) (preferred)
- Email to the maintainer listed in the repository

## Credential handling

This tool works with your existing cluster credentials — it does **not** store, log, or transmit credentials anywhere.

**How credentials flow:**
- Cluster access: read from your local kubeconfig (`~/.kube/config`) or explicit `OC_TOKEN` env var
- S3 credentials: passed as parameters, stored in Kubernetes Secrets on your cluster (never in files or logs)
- Registry credentials: read from `~/.docker/config.json` (for ROSA pre-release setup only)

**What gets created on your cluster:**
- Kubernetes Secrets for S3 connections — managed by the ODH dashboard, same as creating them through the UI
- Pull secrets for pre-release registries — only when running `rosa/install-rhoai-prerelease`

## The MinIO dev deployment

The `dependencies/provision-minio.yaml` runbook deploys MinIO on-cluster when no external S3 is available. This is **development only**:

- It deploys with a default password — **change it before using in any shared environment**
- It has no TLS, no backup, no HA
- The runbook prints a prominent warning about this

Do not use this MinIO deployment in production or with real data.

## Pre-release registry access

The `rosa/install-rhoai-prerelease.yaml` runbook uses `quay.io/rhoai` and optionally `brew.registry.redhat.io`:

- **quay.io/rhoai**: Requires org-level access — ask your team admin
- **brew.registry.redhat.io**: Requires internal Red Hat registry access — for Red Hat engineers only

These registries are used for pre-release testing only. Stable RHOAI installations (`rosa/install-rhoai-stable.yaml`) use publicly accessible `registry.redhat.io`.

## Known limitations

- The pull secret workaround for ROSA (Kyverno-based) copies credentials to all namespaces by design — this is documented behavior for the ROSA pre-release setup. Do not use on production clusters.
- Service account tokens created for long-lived MCP server access should be scoped appropriately and rotated periodically.
