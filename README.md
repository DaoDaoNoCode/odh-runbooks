# ODH Runbooks

> One command to make an ODH dashboard page work correctly — and get a direct link to it when it's done.

**The problem:** RHOAI has 20+ components. To make something show up in the dashboard (an eval run, a deployed model, a workbench, a pipeline), you need the right labels, annotations, CRD versions, operator settings, and resource structure — exactly how the dashboard expects them. Getting any of it wrong means the page doesn't render, the resource doesn't appear, or things break silently. Figuring out the correct sequence means searching through multiple repos and ADRs.

**What this does:** Encodes the correct setup for each ODH dashboard feature as a runbook. You describe what you want. Claude reads the runbook, sets everything up the standard way (no workarounds), and gives you the direct dashboard link when it's done.

```
"create a EvalRun in a-test-project"

  Checking if TrustyAI is enabled...
  → Enabling TrustyAI (DSC patch, standard approach)
  Checking if EvalHub CR exists in a-test-project...
  → Creating EvalHub CR
  Deploying granite-3.3-2b-instruct from OCI catalog (no S3 needed)...
  Creating evaluation job...

✓ EvalHub evaluation run complete.

  https://rhods-dashboard.apps.my-cluster.com/projects/a-test-project/evalHub
```

That link opens the eval run details page in your ODH dashboard. That's the whole point.

---

## Getting started

**You have Claude Code** — that's all you need.

```bash
git clone https://github.com/DaoDaoNoCode/odh-runbooks
cd odh-runbooks
claude
```

`CLAUDE.md` loads automatically. Tell Claude what you want:

```
"create a EvalRun in a-test-project"
"deploy a vLLM model in my namespace"
"show me what's installed on my cluster"
"create a workbench in my-project"
"set up the pipeline server in my-project"
```

Claude reads the relevant runbook, runs the `oc` commands directly using its Bash tool, and gives you the dashboard link at the end. **No API key required** — Claude Code is already Claude.

---

## What each runbook gives you at the end

Every runbook's final output is a link to the specific dashboard page it created or enabled:

| What you want to see in the dashboard | Runbook | Output |
|---|---|---|
| Eval run details page | `evalhub/create-evaluation-run` | `https://.../projects/{ns}/evalHub` |
| Model serving endpoint, ready to query | `model-serving/deploy-vllm-model` | `https://.../projects/{ns}/models` + curl test |
| Model serving (any format) | `model-serving/deploy-kserve-model` | `https://.../projects/{ns}/models/{name}` |
| Workbench, ready to open | `workbenches/create-workbench` | direct notebook URL |
| Pipeline server + Pipelines tab | `pipelines/create-pipeline-server` | `https://.../projects/{ns}/pipelines` |
| Model Registry UI | `model-registry/enable-registry` | `https://.../modelRegistry` |
| MLflow experiment tracking | `mlflow/enable-mlflow` | tracking URI + dashboard link |
| TrustyAI fairness monitoring | `trustyai/enable-trustyai-service` | service URL + bias metrics endpoint |
| Chat playground (GenAI) | `genai/enable-chat-playground` | `https://.../projects/{ns}/chatPlayground` |

Cluster-level setup (no dashboard page, but unblocks everything else):

| What you need enabled | Runbook |
|---|---|
| KServe (required for model serving) | `cluster/enable-kserve` |
| Data Science Pipelines operator | `cluster/enable-pipelines` |
| TrustyAI + EvalHub operator | `cluster/enable-trustyai` |
| Model Registry operator | `cluster/enable-model-registry` |
| Distributed workloads (Ray, Kueue) | `cluster/enable-codeflare` |
| Everything at once | `cluster/full-stack-setup` |
| RHOAI on ROSA (stable) | `rosa/install-rhoai-stable` |
| RHOAI on ROSA (pre-release) | `rosa/install-rhoai-prerelease` |

---

## How it works

**You don't need to know the prerequisites.** If EvalHub needs TrustyAI and TrustyAI isn't enabled, Claude enables it first. If the pipeline server needs S3 and there's no S3, Claude deploys MinIO. Dependencies are resolved automatically.

**Resources are created the way the dashboard expects.** Every runbook encodes the exact labels, annotations, CRD fields, and resource structure that the ODH dashboard uses to render things correctly. It's derived from the dashboard source code and operator docs — not guesswork.

**Claude checks the source repos before acting.** Every runbook lists the authoritative GitHub repos for its component. Before applying any non-obvious configuration, Claude fetches the source to confirm the correct approach. This prevents workarounds — if something requires a prerequisite, Claude adds it the standard way.

**If Claude can't find a standard fix, it stops and tells you** — what it tried, what it checked, and what you need to do manually. No silent workarounds.

---

## Using the `odh` CLI directly

The `odh` CLI runs Claude as an agentic executor — it needs `ANTHROPIC_API_KEY`:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # required for odh CLI
pip install -e .

odh wizard evalhub/create-evaluation-run   # interactive: discovers params from cluster
odh run evalhub/create-evaluation-run -p project_namespace=my-project   # direct
odh run evalhub/create-evaluation-run --dry-run -p project_namespace=my-project  # preview only
odh doctor                                 # what's installed on my cluster?
odh list                                   # all 66 runbooks
```

If you're using Claude Code, you don't need this — Claude Code does everything directly.

---

## All commands

| Command | What it does |
|---|---|
| `odh wizard <runbook>` | Discovers params from your cluster, then executes |
| `odh run <runbook> -p key=val` | Execute with explicit params |
| `odh run <runbook> --dry-run` | Claude checks state, reports what it would do — no changes |
| `odh doctor` | Show which ODH components are installed/missing |
| `odh list` | All 66 runbooks |
| `odh list --workflow` | Runbooks grouped by goal |
| `odh show <runbook>` | Show steps and source repos without running |
| `odh start` | Guided onboarding — Claude asks what you want to set up |

---

## MCP server (Cursor / Claude Desktop)

```json
// ~/.cursor/mcp.json
{
  "mcpServers": {
    "odh-runbooks": {
      "command": "python",
      "args": ["/path/to/odh-runbooks/mcp_server.py"],
      "env": { "KUBECONFIG": "/Users/you/.kube/config" }
    }
  }
}
```

Install: `pip install ".[mcp]"`. Then ask Claude in Cursor: *"set up EvalHub for my-project"*.

---

## Contributing

The most valuable contribution: run a runbook on a real cluster, fix what's wrong, open a PR.
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache License 2.0
