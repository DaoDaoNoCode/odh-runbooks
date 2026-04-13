## What does this PR do?

<!-- Briefly describe the change -->

## Type of change

- [ ] New runbook
- [ ] Fix existing runbook (wrong CRD, label, annotation, field name, etc.)
- [ ] Add/update `source_repos` (adding authoritative GitHub repos to a runbook)
- [ ] Confidence promotion (`inferred` → `doc-derived` → `verified`)
- [ ] Tool improvement (agentic executor, wizard, CLI, MCP server, etc.)

## Runbook(s) affected

<!-- List the runbook paths, e.g. evalhub/create-evaluation-run -->

## What source did you check?

<!-- Which GitHub repo or doc confirmed the correct approach?
     e.g. "Checked odh-dashboard source: frontend/src/pages/modelServing/..."
     e.g. "Checked kserve CRD spec: v1beta1 InferenceService, field .spec.predictor.model.runtime"
     This is how runbooks move from inferred → doc-derived -->

## Tested on

- RHOAI/ODH version:
- Cluster type (ROSA, OCP, CRC, etc.):
- Test command: `odh run ... -p ...` or `odh wizard ...`

## Dashboard verification

- [ ] Resources appear and render correctly in the ODH dashboard
- [ ] Not applicable (tool-only change or step doesn't create dashboard-visible resources)

## Confidence level

- [ ] Updated `confidence_overall` or per-step `confidence` (and why)
- [ ] Added `rhoai_version_tested: "2.x"`
- [ ] Added or updated `source_repos` field
