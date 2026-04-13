# ODH Runbooks

> Set up any RHOAI/ODH component correctly with a single command — the way the dashboard expects it.

**The problem:** RHOAI has 20+ components that interact in specific ways. Figuring out the correct setup sequence, the right labels/annotations, and the right CRD versions is hard — especially for components you haven't touched before.

**What this does:** Encodes the correct setup steps for every ODH/RHOAI component as verified runbooks. Run one command, get a properly configured environment that the dashboard renders correctly.

```
$ odh wizard evalhub/create-evaluation-run

project_namespace: my-project  (discovered from cluster: 3 options)
model_uri: models/llama3-8b    (path within your S3 bucket)

→ TrustyAI not enabled — auto-enabling
→ No S3 connection — auto-deploying MinIO
→ KServe not enabled — auto-enabling

Step 1/8: enable-trustyai ✓
Step 2/8: create-evalhub-cr ✓
Step 3/8: deploy-model (~10m) ✓
...

✓ EvalHub running: https://rhods-dashboard.../projects/my-project/evalHub
```

---

## Getting started

**Requirements:** `oc` CLI, access to an OpenShift cluster with ODH/RHOAI installed.

### Option 1 — Pull down the repo, just start prompting (recommended)

```bash
git clone https://github.com/DaoDaoNoCode/odh-runbooks odh-runbooks
cd odh-runbooks
claude   # opens Claude Code — CLAUDE.md loads automatically
```

That's it. Tell Claude what you want to set up. The `CLAUDE.md` in this repo
tells Claude exactly what to do with every ODH/RHOAI request.

If you want to run the `odh` CLI directly:
```bash
# uv — no install, just run (requires uv: brew install uv)
uv run cli.py wizard evalhub/create-evaluation-run

# pipx — installs odh globally
pipx install .
odh wizard evalhub/create-evaluation-run
```

### Option 2 — No pull-down, works anywhere

Add one entry to your global `~/.claude/CLAUDE.md`:

```markdown
## ODH Runbooks
When asked about RHOAI/ODH setup, see: https://github.com/DaoDaoNoCode/odh-runbooks
Read the relevant runbook from runbooks/ and follow the steps using the Bash tool.
Key runbooks: evalhub/create-evaluation-run, model-serving/deploy-vllm-model,
cluster/full-stack-setup, rosa/install-rhoai-prerelease
```

Claude Code reads this globally and can fetch runbooks directly from GitHub.
No clone, no install.

Or install the CLI globally once:
```bash
pipx install git+https://github.com/DaoDaoNoCode/odh-runbooks
```

Then `odh` works in any directory, with any Claude Code session.

---

## Quick start

```bash
# Don't know where to start? Run this:
odh start

# Know what you want? Use the wizard:
odh wizard evalhub/create-evaluation-run
odh wizard model-serving/deploy-vllm-model
odh wizard pipelines/create-pipeline-server

# Check what's installed on your cluster:
odh doctor

# See all available runbooks:
odh list
odh list --workflow    # grouped by goal
```

---

## Using with Claude CLI or Cursor

### Option A: MCP server (Claude calls runbooks directly in conversation)

```bash
claude mcp add odh-runbooks \
  python /path/to/odh-runbooks/mcp_server.py \
  --env KUBECONFIG=/Users/you/.kube/config
```

Requires `pip install fastmcp` or `uv pip install fastmcp`.
Then ask Claude: *"Set up EvalHub for my project"* — it calls the right runbook automatically.

### Option B: Claude Code skills (recommended — zero setup)

Add the skills directory to your Claude Code project. Skills act as slash commands
that tell Claude which `odh` command to run:

```
/odh-evalhub        → guides Claude to run: odh wizard evalhub/create-evaluation-run
/odh-deploy-model   → guides Claude to run: odh wizard model-serving/deploy-vllm-model
/odh-setup          → guides Claude to run: odh start
```

Skills are just markdown files — no Python install required. See `.claude/skills/` in this repo.

---

## Commands

| Command | What it does |
|---|---|
| `odh start` | Guided setup — answers "what do you want to accomplish?" |
| `odh wizard <runbook>` | Interactive wizard for a specific runbook |
| `odh run <runbook> -p key=value` | Execute a runbook with explicit parameters |
| `odh run <runbook> --mode plan` | Preview what would happen (no changes) |
| `odh run <runbook> --mode qa` | Read-only state check — is my env ready? |
| `odh list` | Show all 66 runbooks |
| `odh list --workflow` | Runbooks grouped by goal |
| `odh show <runbook>` | Preview a runbook's steps without running |
| `odh doctor` | Check which ODH components are installed |
| `odh ask [runbook]` | Get help — cluster health or runbook details |

---

## How it works

**Runbooks** are YAML files that encode the exact correct steps — right labels, annotations, CRD versions, and API calls — matching what the ODH dashboard creates and expects to render.

**Dependency resolution** is automatic. If EvalHub needs TrustyAI and it's not enabled, the tool enables it. If your project needs an S3 bucket and none exists, it deploys MinIO. You don't need to know the prerequisites.

**Verification** happens at every step. Each step checks the resource was created correctly before moving to the next one. If something fails, it stops with a clear message — never improvises or creates hacky workarounds.

---

## What's covered (66 runbooks)

| Area | Runbooks |
|---|---|
| Cluster setup | Enable KServe, pipelines, CodeFlare, TrustyAI, model registry, training operator, feature store |
| ROSA | Install RHOAI pre-release (Kyverno workaround), stable install, GPU machinepool, teardown |
| Projects | Create project, add user, create S3 connection |
| Workbenches | Create notebook (standard, GPU, with S3), add BYON image |
| Pipelines | Create pipeline server, compile + submit, schedule recurring runs, write KFP components |
| Model serving | KServe deploy, vLLM deploy, canary deployment, custom ServingRuntime, test endpoint |
| Model registry | Enable, register model, deploy from registry, search |
| EvalHub | Create evaluation run with MLflow |
| MLflow | Enable (operator), log training run, register model from run, promote to production, LLM traces, prompt registry |
| AutoML / AutoRAG | Run pipelines |
| Model training | Submit PyTorchJob |
| Distributed workloads | Submit Ray job |
| TrustyAI | Enable TrustyAI service for fairness monitoring |
| Observability | Create Perses dashboard |
| Dependencies | Auto-provision MinIO, S3 connection, pipeline server, PostgreSQL+pgvector |

---

## Confidence levels

Every runbook step has a confidence level so you know what to trust:

| Level | Meaning |
|---|---|
| `verified` | Tested end-to-end on a real cluster |
| `doc-derived` | Confirmed from ODH source code or official docs |
| `inferred` | Derived from ADRs/architecture docs — correct but not tested |
| `uncertain` | Known to be fragile or environment-dependent |

The executor warns you before running `inferred` steps and always asks before `uncertain` ones.

---

## Contributing

The most valuable contribution is **testing a runbook on a real cluster and fixing what's wrong**. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add or fix runbooks.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
