"""
odh start — the magic entry point for newcomers.

Inspired by `fly launch` and `vercel`: one command, no flags needed,
guides you through setup based on what you want to accomplish.

Workflow:
1. Check cluster connection
2. Run odh doctor to show current state
3. Ask "what do you want to do?" (3-5 options)
4. Based on answer, show the required runbook sequence
5. Offer to run the first one in wizard mode
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

RUNBOOKS_DIR = Path(__file__).parent.parent / "runbooks"

# ── Workflows ─────────────────────────────────────────────────────────────────
# Each workflow is a guided sequence for a specific goal.
# Inspired by fly.io's deployment workflows — goal-first, not tool-first.

WORKFLOWS = [
    {
        "id": "dev-setup",
        "title": "Set up a development environment for ODH dashboard work",
        "description": "Install RHOAI pre-release, create a project, workbench, and pipeline server",
        "tags": ["beginner", "setup"],
        "steps": [
            ("rosa/install-rhoai-prerelease",
             "Install RHOAI pre-release on your ROSA cluster",
             "Need the rhoai_image FBC digest from your team's release channel"),
            ("cluster/full-stack-setup",
             "Enable all ODH components + create a dev project",
             "Need S3 credentials (or will auto-deploy MinIO)"),
            ("workbenches/create-workbench",
             "Create a Jupyter workbench for development",
             None),
        ],
        "time_estimate": "20-30 minutes",
        "result": "A fully configured ODH environment ready for dashboard development",
    },
    {
        "id": "evalhub",
        "title": "Set up EvalHub with MLflow and deploy a model for evaluation",
        "description": "Enable TrustyAI, deploy a model, create an EvalHub evaluation run linked to MLflow",
        "tags": ["evalhub", "mlflow", "model"],
        "steps": [
            ("cluster/enable-kserve",
             "Enable KServe model serving (if not already enabled)",
             None),
            ("mlflow/enable-mlflow",
             "Enable MLflow experiment tracking",
             None),
            ("evalhub/create-evaluation-run",
             "Deploy a model and create an EvalHub evaluation run with MLflow",
             "Need a model URI in S3 — or start with a test model"),
        ],
        "time_estimate": "15-25 minutes",
        "result": "EvalHub page in the dashboard with a running evaluation linked to MLflow",
    },
    {
        "id": "llm-deploy",
        "title": "Deploy an LLM and use it in the GenAI chat playground",
        "description": "Deploy a vLLM model, connect it to the GenAI chat interface",
        "tags": ["genai", "llm", "model-serving"],
        "steps": [
            ("cluster/enable-kserve",
             "Enable KServe (if not already enabled)",
             None),
            ("rosa/setup-gpu-machinepool",
             "Add GPU nodes (if your cluster doesn't have them)",
             "Need rosa CLI and cluster name"),
            ("model-serving/deploy-vllm-model",
             "Deploy an LLM using vLLM runtime",
             "Need model weights in S3 or use HuggingFace hub"),
            ("genai/enable-chat-playground",
             "Connect the deployed model to the chat playground",
             None),
        ],
        "time_estimate": "30-60 minutes (GPU node provisioning takes 10-15 min)",
        "result": "A working LLM accessible via the RHOAI GenAI chat playground",
    },
    {
        "id": "pipeline",
        "title": "Create and run a Data Science Pipeline",
        "description": "Set up a pipeline server and run your first KFP pipeline",
        "tags": ["pipelines", "kfp"],
        "steps": [
            ("projects/create-project",
             "Create a Data Science Project (if you don't have one)",
             None),
            ("pipelines/create-pipeline-server",
             "Create a pipeline server in your project",
             "Needs S3 storage (auto-provisions MinIO if not available)"),
            ("pipelines/compile-and-submit-pipeline",
             "Submit your first pipeline run",
             "Need a compiled pipeline.yaml"),
        ],
        "time_estimate": "10-15 minutes",
        "result": "A running pipeline visible in the Pipelines section of your project",
    },
    {
        "id": "model-registry",
        "title": "Register a model and deploy it from the Model Registry",
        "description": "Create a model registry entry and deploy from it to KServe",
        "tags": ["model-registry", "deployment"],
        "steps": [
            ("cluster/enable-model-registry",
             "Enable the Model Registry operator",
             None),
            ("model-registry/enable-registry",
             "Create a model registry instance",
             None),
            ("model-registry/register-model",
             "Register your model in the registry",
             None),
            ("model-registry/deploy-from-registry",
             "Deploy the registered model to KServe",
             None),
        ],
        "time_estimate": "10-15 minutes",
        "result": "A model visible in Model Registry and deployed via KServe",
    },
    {
        "id": "gpu-workbench",
        "title": "Create a GPU-enabled workbench for ML training",
        "description": "Add GPU nodes, install operators, create a GPU notebook",
        "tags": ["gpu", "workbench", "training"],
        "steps": [
            ("rosa/setup-gpu-machinepool",
             "Add GPU nodes and install NFD + NVIDIA GPU Operator",
             "Need rosa CLI, cluster name, and instance type choice"),
            ("workbenches/create-workbench-gpu",
             "Create a CUDA-enabled Jupyter workbench",
             None),
        ],
        "time_estimate": "20-30 minutes",
        "result": "A GPU-enabled workbench with PyTorch/CUDA ready",
    },
]


async def run_start(cluster=None) -> None:
    """Entry point for `odh start`."""
    from .cluster import ClusterClient
    from .resolver import DEPENDENCY_REGISTRY

    if cluster is None:
        cluster = ClusterClient()

    # Welcome
    console.print(Panel(
        "[bold]Welcome to the ODH Runbook Tool[/bold]\n\n"
        "This will guide you through setting up your environment.\n"
        "[dim]No prior ODH knowledge required.[/dim]",
        title="[cyan]odh start[/cyan]",
        border_style="cyan"
    ))

    # Quick cluster check
    console.print("\n[bold]First, checking your cluster connection...[/bold]")
    result = await cluster.run("oc whoami 2>/dev/null")
    if not result.ok:
        console.print(Panel(
            "[red]Not connected to an OpenShift cluster.[/red]\n\n"
            "You need to log in first:\n\n"
            "  [bold]oc login https://api.your-cluster.com:6443[/bold]\n\n"
            "Get the login command from:\n"
            "  OpenShift Console → your username (top right) → Copy login command",
            title="[red]Not connected[/red]",
            border_style="red"
        ))
        return

    username = result.stdout.strip()
    server = await cluster.run("oc whoami --show-server 2>/dev/null")
    console.print(f"  ✓ Connected as [green]{username}[/green] → {server.stdout.strip()}\n")

    # Quick state check
    dsc = await cluster.run("oc get dsc --no-headers 2>/dev/null | wc -l | tr -d ' '")
    has_dsc = int(dsc.stdout.strip() or "0") > 0
    projects = await cluster.run(
        "oc get namespace -l opendatahub.io/dashboard=true --no-headers 2>/dev/null | wc -l | tr -d ' '"
    )
    project_count = int(projects.stdout.strip() or "0")

    if has_dsc:
        console.print(f"  ✓ ODH/RHOAI is installed")
        console.print(f"  ✓ {project_count} Data Science Project(s) found")
    else:
        console.print("  [yellow]⚠ ODH/RHOAI is NOT installed yet[/yellow]")
        console.print("  [dim]→ You'll need to install it first. Choose workflow 1 below.[/dim]")

    # Show workflows
    console.print("\n[bold]What do you want to accomplish?[/bold]\n")
    for i, wf in enumerate(WORKFLOWS, 1):
        console.print(f"  [cyan]{i}.[/cyan] {wf['title']}")
        console.print(f"     [dim]{wf['description']}[/dim]")
        console.print(f"     [dim]Time: {wf['time_estimate']}[/dim]\n")

    console.print(f"  [cyan]{len(WORKFLOWS)+1}.[/cyan] Show me what's installed (health check)")
    console.print(f"  [cyan]{len(WORKFLOWS)+2}.[/cyan] I know what I want — show me all runbooks\n")

    choice_raw = Prompt.ask(
        "Pick a number",
        choices=[str(i) for i in range(1, len(WORKFLOWS) + 3)],
        default="1"
    )
    choice = int(choice_raw)

    if choice == len(WORKFLOWS) + 1:
        # Health check
        console.print("\n[dim]Running odh doctor...[/dim]")
        from .resolver import DEPENDENCY_REGISTRY
        from .schema import Requirement
        from .resolver import DependencyResolver

        checks = [
            ("dsc-exists", "ODH/RHOAI installed"),
            ("dsp-enabled", "Data Science Pipelines"),
            ("kserve-enabled", "KServe model serving"),
            ("model-registry-enabled", "Model Registry"),
            ("trustyai-enabled", "TrustyAI/EvalHub"),
            ("gpu-available", "GPU nodes"),
            ("storage-class", "Storage class"),
        ]
        resolver = DependencyResolver(cluster, {}, {})
        table = Table(show_header=True)
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Fix with")

        for dep_type, label in checks:
            dep = DEPENDENCY_REGISTRY.get(dep_type, {})
            req = Requirement(type=dep_type)
            try:
                ok = await resolver._check(dep, req)
            except Exception:
                ok = False

            if ok:
                table.add_row(label, "[green]✓ ready[/green]", "")
            elif dep.get("blocker"):
                table.add_row(label, "[red]✗ needs setup[/red]", "manual (see docs)")
            else:
                resolver_path = dep.get("resolver", "?")
                table.add_row(label, "[yellow]✗ not enabled[/yellow]", f"odh run {resolver_path}")

        console.print(table)
        console.print("\n[dim]Run 'odh doctor' anytime to check this.[/dim]")
        return

    if choice == len(WORKFLOWS) + 2:
        console.print("\n[dim]Run 'odh list' to see all runbooks, or 'odh wizard <name>' to get guided help.[/dim]")
        return

    # Show selected workflow
    wf = WORKFLOWS[choice - 1]
    console.print(f"\n[bold cyan]Workflow: {wf['title']}[/bold cyan]")
    console.print(f"[dim]Result: {wf['result']}[/dim]")
    console.print(f"[dim]Total time: {wf['time_estimate']}[/dim]\n")

    # Show the steps
    console.print("[bold]Here's what we'll do:[/bold]")
    table = Table(show_header=False, box=None)
    table.add_column("#", style="cyan")
    table.add_column("Runbook")
    table.add_column("What it does")
    table.add_column("Note", style="dim")

    for i, (runbook_path, what, note) in enumerate(wf["steps"], 1):
        table.add_row(str(i), runbook_path, what, note or "")
    console.print(table)

    console.print()
    if not Confirm.ask("Start with step 1 now?", default=True):
        console.print("\n[dim]You can run any step manually:[/dim]")
        for runbook_path, _, _ in wf["steps"]:
            console.print(f"  odh wizard {runbook_path}")
        return

    # Run the first step in wizard mode
    first_runbook = wf["steps"][0][0]
    console.print(f"\n[cyan]Starting wizard for: {first_runbook}[/cyan]")

    import yaml
    from .schema import Runbook
    from .wizard import run_wizard
    from .executor import RunbookExecutor, RunMode

    yaml_path = RUNBOOKS_DIR / f"{first_runbook}.yaml"
    if not yaml_path.exists():
        console.print(f"[red]Runbook not found: {yaml_path}[/red]")
        return

    runbook = Runbook.model_validate(yaml.safe_load(yaml_path.read_text()))
    params = await run_wizard(runbook, cluster)

    if not params:
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # Fill defaults
    for p in runbook.parameters:
        if p.name not in params and p.default is not None:
            params[p.name] = p.default

    if Confirm.ask("\nPreview plan before executing?", default=True):
        executor = RunbookExecutor(runbook, params, cluster, mode=RunMode.PLAN)
        await executor.run()
        console.print()

    if Confirm.ask("Execute now?", default=False):
        executor = RunbookExecutor(runbook, params, cluster, mode=RunMode.IMPLEMENT)
        success = await executor.run()
        if success and len(wf["steps"]) > 1:
            console.print(f"\n[green bold]Step 1 complete![/green bold]")
            console.print(f"\n[bold]Next step:[/bold] {wf['steps'][1][1]}")
            console.print(f"  [cyan]odh wizard {wf['steps'][1][0]}[/cyan]")
    else:
        param_str = " ".join(f"-p {k}={v}" for k, v in params.items())
        console.print(f"\n[dim]To run later:[/dim]")
        console.print(f"  odh run {first_runbook} {param_str}")
