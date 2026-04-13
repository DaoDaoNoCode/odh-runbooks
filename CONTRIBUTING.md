# Contributing to ODH Runbooks

The most valuable contributions are **testing runbooks on a real cluster** and **fixing what's wrong**.
An `inferred` runbook promoted to `verified` by someone who actually ran it is worth more than ten new drafts.

---

## Philosophy: runbooks as Claude's reference guide

Runbooks in this repo are no longer rigid step-by-step scripts. They are **reference guides** that
Claude reads to understand the goal, the correct resource structure, and the known pitfalls.

Claude executes with judgment:
- Checks cluster state before acting (skips steps that are already done)
- Fetches `source_repos` when unsure about the correct approach
- Adapts to the actual state rather than blindly following steps
- Never applies workarounds — stops and explains if no standard fix exists

**This changes how you write runbooks.** The goal is to encode knowledge, not procedures.

---

## Understanding the opendatahub-operator (read this first)

The opendatahub-operator manages ALL ODH/RHOAI components via the `DataScienceCluster` (DSC) CRD.
Understanding it prevents creating resources that conflict with or duplicate operator behavior.

### The `opendatahub.io/managed` annotation

| Annotation | Effect |
|---|---|
| absent (default) | Operator creates once, does NOT continuously reconcile — your changes persist |
| `"false"` | Same as absent — operator created it, you can modify freely |
| `"true"` | Operator reconciles continuously — any manual change is overwritten |

**When you enable a component** (e.g. `kserve.managementState: Managed`), the operator creates
ALL child resources automatically: Deployments, Services, ConfigMaps, CRDs, RBAC, Routes.
**Never create these manually** — the operator owns them.

**The correct pattern for enabling components:**
```yaml
# CORRECT: patch the DSC — operator handles everything else
- id: enable-kserve
  action:
    type: patch
    target: "$(oc get dsc -o name | head -1)"
    patch: '{"spec":{"components":{"kserve":{"managementState":"Managed"}}}}'

# WRONG: creating what the operator would create
- id: create-kserve-deployment   # ← never do this
```

---

## The `source_repos` field (required for all runbooks)

Every runbook must list the authoritative GitHub repos Claude should check when something
is unclear or failing. This is how Claude finds standard fixes instead of improvising.

```yaml
source_repos:
  - "https://github.com/kserve/kserve"
  - "https://github.com/opendatahub-io/odh-model-controller"
  - "https://github.com/opendatahub-io/opendatahub-operator"
  - "https://github.com/opendatahub-io/odh-dashboard"
```

**Rules for `source_repos`:**
- Always include `opendatahub-operator` for anything touching the DSC
- Include `odh-dashboard` for anything involving resource labels/annotations/connection types
  (the dashboard is the reference implementation for what resources should look like)
- Include the upstream component repo (kserve, mlflow, codeflare, etc.)
- 2–5 repos is the right range; more is fine, fewer than 2 is a red flag

---

## Fixing an existing runbook (most valuable contribution)

1. Run the runbook on a real cluster: `odh wizard <component>/<name>`
2. Note what failed and why (wrong field name, missing annotation, wrong runtime name, etc.)
3. Fix the YAML — see the schema below
4. Update the `confidence_overall` field:
   - `inferred` → `doc-derived` (confirmed from source code or official docs)
   - `doc-derived` → `verified` (tested successfully on a real cluster)
5. Add `rhoai_version_tested: "2.x"` if you verified it
6. Open a PR with: what broke, what you checked, what you changed

---

## Adding a new runbook

### 1. Draft it

Use the generator for a starting point:

```bash
odh generate <component> "<task description>"
# e.g.: odh generate feature-store "create a feature view and materialize"
```

All generated steps start as `inferred` — review and fix before committing.

### 2. Runbook schema

```yaml
name: component-task-name           # matches the file path
description: >
  What this does and why.
  Include: what gets created, important caveats, CPU vs GPU paths if applicable.
  What the ODH dashboard auto-creates (do NOT create these manually).
rhoai_version_tested: null           # fill in after testing on a real cluster
confidence_overall: inferred         # start here; promote after testing

parameters:
  - name: project_namespace
    description: OpenShift project namespace
    required: true
    discover_cmd: "oc get namespace -l opendatahub.io/dashboard=true -o jsonpath='{.items[*].metadata.name}'"
    hint: "Must be an ODH Data Science Project"
  
  - name: model_name
    description: Name for the InferenceService (lowercase, hyphens only)
    required: true
    example: "llama-3-2-3b-instruct"
    hint: "Max 63 chars. Lowercase letters, numbers, hyphens."
  
  - name: accelerator
    description: GPU or CPU deployment
    required: false
    default: gpu
    enum: ["gpu", "cpu"]
    hint: "gpu: supported. cpu: experimental, ~3 tokens/s"

steps:
  - id: descriptive-step-name
    confidence: inferred             # start here; promotes after verification
    description: >
      What this step does and WHY. Include:
      - What resource gets created or modified
      - What the operator auto-creates (so Claude knows not to touch it)
      - Any known gotchas for this step
      - GPU vs CPU differences if applicable
    requires:
      - type: kserve-enabled         # auto-resolved dependency
      - type: namespace
        name: "{{ project_namespace }}"
    pre_check:                       # idempotency — skip if already done
      command: "oc get inferenceservice {{ model_name }} -n {{ project_namespace }} --no-headers 2>/dev/null | wc -l | tr -d ' '"
      expected: "1"
      if_already_true: skip
      on_fail: STOP
    action:
      type: apply
      dry_run: true                  # dry_run: true for all k8s mutations
      manifest: |
        apiVersion: serving.kserve.io/v1beta1
        kind: InferenceService
        metadata:
          name: {{ model_name }}
          namespace: {{ project_namespace }}
          labels:
            opendatahub.io/dashboard: "true"    # required for dashboard visibility
          annotations:
            openshift.io/display-name: "{{ model_name }}"   # required for dashboard
    post_check:                      # verify before moving to next step
      command: "oc get inferenceservice {{ model_name }} -n {{ project_namespace }} -o jsonpath='{.status.modelStatus.states.activeModelState}'"
      expected: "Loaded"
      timeout: "900s"
      poll_interval: "30s"
      on_fail: STOP
    on_fail_hint: >
      What to check when this step fails. Specific oc commands to run.
      Common causes and their fixes.
    rollback: "oc delete inferenceservice {{ model_name }} -n {{ project_namespace }} 2>/dev/null || true"

source_repos:
  - "https://github.com/kserve/kserve"
  - "https://github.com/opendatahub-io/odh-model-controller"
  - "https://github.com/opendatahub-io/opendatahub-operator"
  - "https://github.com/opendatahub-io/odh-dashboard"

known_bad_patterns:
  - "never create the Route manually — odh-model-controller auto-creates it"
  - "never use modelFormat.name: vllm (lowercase) — it must be 'vLLM' (case-sensitive)"
  - "never use Serverless mode without Service Mesh and Serverless operators installed"

rollback_order:
  - "oc delete inferenceservice {{ model_name }} -n {{ project_namespace }}"

tags: ["model-serving", "kserve"]
estimated_minutes: 15
next_steps:
  - "Test the endpoint: curl -k {{ model_url }}/v1/models"
```

### 3. Runbook quality checklist

Before submitting, verify:

- [ ] **`source_repos`** — all authoritative repos listed (operator, dashboard, upstream component)
- [ ] **`description`** is informative — explains goal, caveats, what operator auto-creates
- [ ] **`known_bad_patterns`** — at least 2-3 real gotchas documented
- [ ] **`on_fail_hint`** on every step that can fail meaningfully
- [ ] **Parameters** have `example`, `hint`, and `discover_cmd` or `enum` where applicable
- [ ] **Jinja2 templates** use `{{ variable }}` syntax (not `{variable}` Python format strings)
- [ ] **YAML is valid** — run the validation script below

### 4. Dashboard compatibility

Resources must match exactly what the ODH dashboard creates. Check the dashboard source code
(`https://github.com/opendatahub-io/odh-dashboard`) or inspect what the dashboard creates
with `oc get <resource> -o yaml` after creating it through the UI.

Key annotations and labels the dashboard checks:
- `opendatahub.io/dashboard: "true"` — required for most resources to appear in dashboard
- `openshift.io/display-name` — required for InferenceService, Notebook, connections
- `notebooks.opendatahub.io/inject-auth: "true"` — correct key (NOT `inject-oauth`)
- `opendatahub.io/connection-type` — on Secret resources for data connections
- `opendatahub.io/managed: "true"` AND `opendatahub.io/dashboard: "true"` — for S3 connections (both required)

### 5. Test it

```bash
# Validate YAML structure
odh show <component>/<runbook-name>

# Dry-run — Claude reviews cluster state, no changes
odh run <component>/<runbook-name> --dry-run -p project_namespace=my-project

# Execute on a real cluster
odh wizard <component>/<runbook-name>

# Verify the resource appears correctly in the ODH dashboard after running
```

After a successful run:
- Promote `confidence: inferred` → `confidence: doc-derived` for steps confirmed from source code
- Promote `confidence: doc-derived` → `confidence: verified` after two successful cluster runs
- Set `rhoai_version_tested: "2.X"` on the runbook

---

## Dependency types

When your runbook needs something to exist first, declare it with `requires:`.
Claude auto-provisions it by running the resolver runbook.

| Type | What it ensures | How resolved |
|---|---|---|
| `namespace` | ODH Data Science Project namespace exists | `projects/create-project` |
| `s3-connection` | S3 secret exists in namespace | `dependencies/provision-s3-connection` |
| `dsp-enabled` | Data Science Pipelines enabled in DSC | `cluster/enable-pipelines` |
| `kserve-enabled` | KServe CRD installed | `cluster/enable-kserve` |
| `trustyai-enabled` | TrustyAI component enabled | `cluster/enable-trustyai` |
| `model-registry-enabled` | Model Registry operator installed | `cluster/enable-model-registry` |
| `training-operator-enabled` | Training Operator CRD installed | `cluster/enable-training-operator` |
| `codeflare-enabled` | CodeFlare/Ray/Kueue enabled | `cluster/enable-codeflare` |
| `pipeline-server` | DSPA running in namespace | `dependencies/provision-pipeline-server` |
| `model-registry-instance` | ModelRegistry CR exists | `model-registry/enable-registry` |
| `storage-class` | K8s StorageClass available | **BLOCKER** — cannot auto-provision |
| `gpu-available` | GPU nodes available in cluster | **BLOCKER** — cannot auto-provision |
| `dsc-exists` | DataScienceCluster installed | **BLOCKER** — cannot auto-provision |
| `openshift-cluster` | `oc login` is valid | **BLOCKER** — cannot auto-provision |

To add a new dependency type, register it in `runner/resolver.py`.

---

## Confidence levels

| Level | Meaning | When to use |
|---|---|---|
| `verified` | Tested end-to-end on a real cluster | After ≥2 successful runs with no issues |
| `doc-derived` | Confirmed from ODH source code or official docs | After checking dashboard source, CRD spec, or operator code |
| `inferred` | Best guess from architecture docs/research | Default for new runbooks |
| `uncertain` | Fragile or environment-dependent | For steps with external dependencies (OCM, registry credentials) |

Only humans can promote to `verified` — the generator always outputs `inferred`.

---

## Validating your changes

```bash
# Validate all runbook YAML files
python3 -c "
import yaml
from pathlib import Path
from runner.schema import Runbook
errors = []
for f in Path('runbooks').rglob('*.yaml'):
    try:
        Runbook.model_validate(yaml.safe_load(f.read_text()))
    except Exception as e:
        errors.append(f'{f}: {e}')
if errors:
    print('ERRORS:')
    for e in errors: print(e)
else:
    print(f'All {len(list(Path(\"runbooks\").rglob(\"*.yaml\")))} runbooks valid.')
"

# Check all dependency types are registered
python3 -c "
import yaml
from pathlib import Path
from runner.resolver import DEPENDENCY_REGISTRY
used = set()
for f in Path('runbooks').rglob('*.yaml'):
    data = yaml.safe_load(f.read_text())
    for step in data.get('steps', []):
        for req in step.get('requires', []):
            if isinstance(req, dict):
                used.add(req.get('type', ''))
unregistered = used - set(DEPENDENCY_REGISTRY.keys()) - {''}
print('Unregistered types:', unregistered or 'none — all good')
"

# Check all runbooks have source_repos
python3 -c "
import yaml
from pathlib import Path
missing = []
for f in Path('runbooks').rglob('*.yaml'):
    data = yaml.safe_load(f.read_text())
    if not data.get('source_repos'):
        missing.append(str(f.relative_to(Path('runbooks'))))
print('Missing source_repos:', missing or 'none — all good')
"
```

---

## Questions?

Open an issue on GitHub or reach out in the ODH Slack workspace.
