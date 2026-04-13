# ODH Runbooks

> One command to set up any RHOAI/ODH component correctly — the way the dashboard expects it.

**The problem:** RHOAI has 20+ components that interact in specific ways. Figuring out the correct setup sequence, right labels/annotations, CRD versions, and what the operator auto-creates vs. what you must do manually — it's all scattered across repos, ADRs, and institutional knowledge.

**What this does:** Encodes that knowledge as 66 verified runbooks. Claude reads the runbook as a reference, checks your actual cluster state, fetches the component's GitHub source code when needed to verify the correct approach, and applies only standard fixes — never workarounds.

```
$ odh wizard evalhub/create-evaluation-run

project_namespace  my-project   (3 options discovered from your cluster)
model_catalog_tag  granite-3.3-2b-instruct  ← default

ODH Agentic Executor
  Mode: agentic — Claude executes with judgment
  Source repos: 4 configured

Claude is working...

  Checking if TrustyAI is enabled... not found
  → Enabling TrustyAI via DSC patch (per opendatahub-operator source)
  Checking if EvalHub CR exists... not found
  → Creating EvalHub CR in my-project...
  Deploying model from modelcar catalog (no S3 needed)...
  ...

✓ EvalHub evaluation run complete.
  Dashboard: https://rhods-dashboard.../projects/my-project/evalHub
```

---

## Getting started

**Requirements:** Python ≥ 3.11, `oc` CLI logged into an OpenShift cluster with ODH/RHOAI installed.

### Install

```bash
# Option A — pipx (recommended, installs odh globally)
pipx install git+https://github.com/DaoDaoNoCode/odh-runbooks

# Option B — uv (no install, just run — requires uv: brew install uv)
git clone https://github.com/DaoDaoNoCode/odh-runbooks && cd odh-runbooks
uv run cli.py wizard evalhub/create-evaluation-run

# Option C — develop locally
git clone https://github.com/DaoDaoNoCode/odh-runbooks && cd odh-runbooks
pip install -e .
odh wizard evalhub/create-evaluation-run
```

### Quick start

```bash
odh start                                      # guided onboarding — what do you want to do?
odh wizard evalhub/create-evaluation-run       # set up EvalHub end-to-end
odh wizard model-serving/deploy-vllm-model     # deploy a vLLM model
odh doctor                                     # what's installed on my cluster?
odh list                                       # all 66 runbooks
odh list --workflow                            # grouped by goal
```

---

## Using with Claude Code (recommended)

This is the primary integration. Claude Code reads `CLAUDE.md` automatically and becomes
a full RHOAI platform assistant that can execute runbooks on your behalf.

### Step 1 — Clone and open

```bash
git clone https://github.com/DaoDaoNoCode/odh-runbooks
cd odh-runbooks
claude   # Claude Code CLI opens; CLAUDE.md loads automatically
```

### Step 2 — Just ask

```
"Set up EvalHub for my-project"
"Deploy a granite model in my namespace"  
"What's installed on my cluster?"
"Enable KServe and set up a vLLM model"
```

Claude Code reads the relevant runbook, collects parameters, checks your cluster, and runs the
right `odh` commands — or executes the steps directly using the Bash tool if `odh` isn't installed.

### Setting up Claude Code CLI (if you don't have it)

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Or via other package managers
brew install claude-code   # macOS (if available)

# Log in
claude login
```

Then from the repo directory:
```bash
claude                          # opens interactive session
claude "set up EvalHub"         # one-shot command
claude --dangerously-skip-permissions "odh wizard evalhub/create-evaluation-run"
```

### Using the /odh skill

The repo includes a Claude Code skill at `.claude/skills/odh.md`. In any Claude Code session
inside this repo, you can use:

```
/odh   # invokes the skill — Claude guides you to the right runbook
```

No additional setup needed — Claude Code loads skills from `.claude/skills/` automatically.

### Global setup (works from any directory)

Add to your `~/.claude/CLAUDE.md`:

```markdown
## ODH Runbooks
When asked about RHOAI/ODH setup, fetch runbooks from:
https://github.com/DaoDaoNoCode/odh-runbooks
Read the relevant runbook YAML and follow the steps using Bash.
Key runbooks: evalhub/create-evaluation-run, model-serving/deploy-vllm-model,
cluster/full-stack-setup, rosa/install-rhoai-prerelease
```

Or install `odh` globally so it's available in any session:
```bash
pipx install git+https://github.com/DaoDaoNoCode/odh-runbooks
```

---

## Using with Cursor

Add the MCP server so Claude can run runbooks directly from Cursor chat.

### Add to Cursor MCP config

In Cursor settings → MCP Servers (or `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "odh-runbooks": {
      "command": "python",
      "args": ["/path/to/odh-runbooks/mcp_server.py"],
      "env": {
        "KUBECONFIG": "/Users/you/.kube/config"
      }
    }
  }
}
```

Requires: `pip install ".[mcp]"` (installs fastmcp).

### Using with Claude Desktop

```bash
claude mcp add odh-runbooks \
  python /path/to/odh-runbooks/mcp_server.py \
  --env KUBECONFIG=/Users/you/.kube/config
```

Then in Claude Desktop, ask: *"Set up EvalHub for my project"* — Claude calls the right runbook.

### MCP tools available

| Tool | What it does |
|---|---|
| `check_cluster()` | Diagnose what ODH components are installed |
| `list_runbooks()` | Show all 66 runbooks |
| `search_runbooks(keyword)` | Find runbooks by keyword |
| `show_runbook(name)` | Show steps without executing |
| `check_dependencies(name, params)` | Preview what a runbook will auto-provision |
| `guide_runbook(name)` | Walk through parameters with cluster discovery |
| `run_runbook(name, params)` | Execute a runbook agentically |
| `get_token_status()` | Check if your cluster token is valid |

---

## Commands

| Command | What it does |
|---|---|
| `odh run <runbook> -p key=value` | Execute — Claude checks state, fetches source repos, executes |
| `odh run <runbook> --dry-run -p ...` | Review — Claude checks cluster state, no changes made |
| `odh wizard <runbook>` | Collect parameters interactively, then execute |
| `odh start` | Guided onboarding — answers "what do you want to accomplish?" |
| `odh list` | Show all 66 runbooks |
| `odh list --workflow` | Runbooks grouped by goal |
| `odh show <runbook>` | Show a runbook's steps and source repos |
| `odh doctor` | Check which ODH components are installed |
| `odh ask [runbook]` | Get help — cluster health or runbook details |

---

## How it works

**Runbooks** are YAML files that encode the correct steps — right labels, annotations, CRD versions,
and API calls — matching exactly what the ODH dashboard creates and expects to render.

**Claude executes with judgment.** The runbook is a reference guide, not a rigid script.
Claude reads it, checks your actual cluster state with `oc` commands, and adapts to
what's already there — skipping steps that are done, handling partial state gracefully.

**Source repos are the truth.** Every runbook lists the authoritative GitHub repos for
its component. Before applying any non-obvious configuration, Claude fetches the source
code to verify the correct approach. No workarounds — if the standard approach requires a
prerequisite, Claude adds the prerequisite the standard way.

```yaml
# Example: runbooks/evalhub/create-evaluation-run.yaml
source_repos:
  - "https://github.com/eval-hub/eval-hub"
  - "https://github.com/trustyai-explainability/trustyai-service-operator"
  - "https://github.com/kserve/kserve"
  - "https://github.com/opendatahub-io/opendatahub-operator"
```

**Dependency resolution is automatic.** If EvalHub needs TrustyAI and it's not enabled,
Claude enables it. If a project needs an S3 bucket and none exists, Claude deploys MinIO.
You don't need to know the prerequisites.

---

## What's covered (66 runbooks)

| Area | Runbooks |
|---|---|
| Cluster setup | Enable KServe, pipelines, CodeFlare, TrustyAI, model registry, training operator, feature store, full stack |
| ROSA | Install RHOAI stable/pre-release (Kyverno workaround), GPU machinepool, fix imagestream registry |
| Projects | Create project, add user, create S3 connection |
| Workbenches | Create notebook (standard, GPU, with S3), add BYON image |
| Pipelines | Create pipeline server, compile + submit, schedule recurring runs, write KFP components |
| Model serving | KServe deploy, vLLM deploy (GPU + CPU), canary deployment, custom ServingRuntime, test endpoint |
| Model registry | Enable, register model, deploy from registry, search models |
| EvalHub | Create evaluation run with MLflow tracking |
| MLflow | Enable, log training run, register model, promote to production, LLM traces, prompt registry |
| Distributed workloads | Submit Ray job |
| Model training | Submit PyTorchJob |
| TrustyAI | Enable TrustyAI service for fairness monitoring |
| Observability | Enable Perses dashboard |
| GenAI | Enable chat playground |
| Dependencies | Auto-provision MinIO, S3 connection, pipeline server, PostgreSQL+pgvector |

---

## Confidence levels

Every runbook step has a confidence level so you know what to trust:

| Level | Meaning |
|---|---|
| `verified` | Tested end-to-end on a real cluster |
| `doc-derived` | Confirmed from ODH source code or official docs |
| `inferred` | Derived from ADRs/architecture docs — probably correct, not yet cluster-tested |
| `uncertain` | Known to be fragile or environment-dependent |

---

## Contributing

The most valuable contribution is **testing a runbook on a real cluster and fixing what's wrong**.
See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add or improve runbooks.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
