# Contributing to ODH Runbooks

Thank you for contributing! The most valuable contributions are **new runbooks** and **fixes to existing ones** based on real cluster testing.

---

## The fastest contribution: fix a runbook

If you run a runbook and something doesn't work — wrong CRD version, missing annotation, wrong field name — please fix it and open a PR. These fixes are the most valuable thing you can contribute because they represent real cluster knowledge.

1. Edit the YAML in `runbooks/`
2. Update the `confidence_overall` field:
   - `inferred` → `doc-derived` (if you confirmed from source code/docs)
   - `doc-derived` → `verified` (if you tested on a real cluster)
3. Add `rhoai_version_tested: "2.x"` if you verified it
4. Open a PR with what you changed and why

---

## Adding a new runbook

### 1. Draft it

Either write it manually or use the generator:

```bash
odh generate <component> "<task description>"
# e.g.: odh generate feature-store "create a feature view and materialize"
```

The generator produces a draft with all steps marked `inferred`. You'll review and correct it.

### 2. Use the correct runbook schema

Every runbook needs:

```yaml
name: component-task-name
description: >
  What this does and why.
  Include: what it creates, any important caveats.
rhoai_version_tested: null   # fill in after testing
confidence_overall: inferred  # start here

parameters:
  - name: param_name
    description: What this parameter is
    required: true
    example: "concrete-example-value"    # add this
    hint: "where to find it / format"   # add this
    discover_cmd: "oc get ... "          # if discoverable from cluster

steps:
  - id: descriptive-step-name
    confidence: inferred
    description: What this step does
    requires:
      - type: namespace           # declare dependencies
        name: "{{ project_namespace }}"
    pre_check:                    # idempotency check
      command: "oc get ... | wc -l"
      expected: "1"
      if_already_true: skip
      on_fail: STOP
    action:
      type: apply
      dry_run: true               # ALWAYS dry_run: true for k8s mutations
      manifest: |
        apiVersion: ...
    post_check:                   # verify before proceeding
      command: "oc get ... -o jsonpath=..."
      expected: "Ready"
      timeout: "300s"
      on_fail: STOP               # ALWAYS STOP, never improvise
    on_fail_hint: "Check: oc describe ... Common cause: ..."
    rollback: "oc delete ..."

known_bad_patterns:
  - "never do X because Y"

rollback_order:
  - "oc delete resource ..."

tags: ["component", "setup"]
estimated_minutes: 10
next_steps:
  - "What to do after: odh wizard ..."
```

### 3. Critical rules for runbook quality

**Every step must:**
- Have a `pre_check` that checks if the resource already exists (idempotency)
- Have `dry_run: true` for any `apply`/`create` action
- Have a `post_check` that verifies the step succeeded
- Use `on_fail: STOP` — never `RETRY` or skip verification

**Dashboard compatibility:**
The resources you create must match exactly what the ODH dashboard creates. Check the dashboard source code or use `odh run X --mode qa` after running to verify the dashboard renders the resource correctly.

Key things the dashboard checks:
- `opendatahub.io/dashboard: "true"` label (required for most resources)
- `openshift.io/display-name` annotation (required for InferenceService, Notebook)
- `notebooks.opendatahub.io/inject-auth: "true"` (NOT inject-oauth — correct key is inject-auth)
- `opendatahub.io/managed: "true"` AND `opendatahub.io/dashboard: "true"` for S3 connections (both required)

### 4. Test it

```bash
# Validate structure
odh show <component>/<runbook-name>

# Preview what it would do
odh run <component>/<runbook-name> --mode plan -p ...

# Check cluster state before/after
odh run <component>/<runbook-name> --mode qa -p ...

# Execute on a real cluster
odh run <component>/<runbook-name> -p ...
```

After a successful run on a real cluster:
- Promote `confidence: inferred` → `confidence: doc-derived` for steps you confirmed
- Set `rhoai_version_tested: "2.X"` on the runbook
- Verify the resource appears correctly in the ODH dashboard

### 5. Open a PR

Include:
- What the runbook does
- Which RHOAI/ODH version you tested on
- Screenshots or output showing it worked in the dashboard (optional but appreciated)

---

## Adding wizard metadata to parameters

When adding parameters, include guidance fields so the wizard can help users:

```yaml
parameters:
  - name: model_uri
    description: Path within the S3 bucket to model artifacts
    required: true
    example: "models/llama3-8b"
    hint: "PATH within bucket only — not the full s3:// URL"
    
  - name: benchmark_provider
    enum: ["lm-evaluation-harness", "garak"]
    hint: "lm-evaluation-harness=accuracy benchmarks, garak=safety/red-teaming"
    
  - name: project_namespace
    discover_cmd: "oc get namespace -l opendatahub.io/dashboard=true -o jsonpath='{.items[*].metadata.name}'"
```

---

## Dependency types

When your runbook needs something to exist first, declare it with `requires:`. The executor will auto-provision it.

Available types:

| Type | What it ensures | How it's resolved |
|---|---|---|
| `namespace` | Project namespace exists | runs `projects/create-project` |
| `s3-connection` | S3 secret exists in namespace | runs `dependencies/provision-s3-connection` |
| `dsp-enabled` | DSP component enabled in DSC | runs `cluster/enable-pipelines` |
| `kserve-enabled` | KServe CRD installed | runs `cluster/enable-kserve` |
| `trustyai-enabled` | TrustyAI component enabled | runs `cluster/enable-trustyai` |
| `model-registry-enabled` | Model Registry operator installed | runs `cluster/enable-model-registry` |
| `training-operator-enabled` | Training Operator CRD installed | runs `cluster/enable-training-operator` |
| `codeflare-enabled` | CodeFlare/Ray/Kueue enabled | runs `cluster/enable-codeflare` |
| `pipeline-server` | DSPA running in namespace | runs `dependencies/provision-pipeline-server` |
| `model-registry-instance` | ModelRegistry CR exists | runs `model-registry/enable-registry` |
| `storage-class` | K8s StorageClass available | **BLOCKER** — cannot auto-provision |
| `gpu-available` | GPU nodes in cluster | **BLOCKER** — cannot auto-provision |
| `dsc-exists` | DataScienceCluster installed | **BLOCKER** — cannot auto-provision |
| `openshift-cluster` | oc login is valid | **BLOCKER** — cannot auto-provision |

To add a new dependency type, add it to `runner/resolver.py`.

---

## Confidence levels

| Level | Meaning | When to use |
|---|---|---|
| `verified` | Tested end-to-end on a real cluster | After two successful runs with no issues |
| `doc-derived` | Confirmed from source code or official docs | After checking the dashboard source, CRD spec, or ADR |
| `inferred` | Best guess from architecture docs/research | Default for new runbooks |
| `uncertain` | Known to be fragile or poorly documented | For steps with external dependencies (OCM, etc.) |

Only humans can promote to `verified` — the generator always outputs `inferred`.

---

## Running tests

```bash
# Validate all runbook YAML files
python -c "
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
    print(f'All runbooks valid.')
"

# Check all dependency types are registered
python -c "
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
if unregistered:
    print(f'UNREGISTERED TYPES: {unregistered}')
else:
    print('All dependency types registered.')
"
```

---

## Questions?

Open an issue or reach out in the ODH Slack workspace.
