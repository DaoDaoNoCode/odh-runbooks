#!/usr/bin/env python3
"""
ODH Runbook CLI — AI-powered, agentic execution.

Claude reads the runbook, checks cluster state, consults source repos,
and executes with judgment. No rigid step-by-step scripting.

Usage:
  odh run evalhub/create-evaluation-run -p project_namespace=my-project
  odh wizard model-serving/deploy-vllm-model
  odh doctor
  odh list
"""
import asyncio
import sys
from pathlib import Path
import click
import yaml
from rich.console import Console
from rich.table import Table

from runner.schema import Runbook
from runner.cluster import ClusterClient

RUNBOOKS_DIR = Path(__file__).parent / "runbooks"
console = Console()


def load_runbook(name: str) -> tuple[Runbook, Path]:
    """Load a runbook by name (e.g. 'evalhub/create-evaluation-run')."""
    path = RUNBOOKS_DIR / f"{name}.yaml"
    if not path.exists():
        matches = list(RUNBOOKS_DIR.rglob(f"*{name.split('/')[-1]}*.yaml"))
        if not matches:
            raise click.ClickException(
                f"Runbook not found: {name}\nRun 'odh list' to see available runbooks."
            )
        path = matches[0]
        console.print(f"[dim]Found: {path.relative_to(RUNBOOKS_DIR)}[/dim]")

    data = yaml.safe_load(path.read_text())
    return Runbook.model_validate(data), path


@click.group()
def cli():
    """ODH Runbook Executor — AI-powered automation for ODH/RHOAI components.

    \b
    Claude reads each runbook as a reference guide, checks your cluster state,
    consults the component's source repos, and executes with full judgment.
    No rigid scripts. No silent workarounds.
    """
    pass


@cli.command()
def start():
    """New here? Guided onboarding — answers 2-3 questions and runs the right runbook.

    \b
    Examples:
      odh start    # interactive: what do you want to do?
    """
    from runner.start import run_start
    asyncio.run(run_start())


@cli.command()
@click.argument("runbook_name")
@click.option("--param", "-p", multiple=True, help="Parameter as key=value (repeatable)")
@click.option("--dry-run", is_flag=True, help="Review cluster state and plan — no changes made")
def run(runbook_name: str, param: tuple[str, ...], dry_run: bool):
    """Execute a runbook using Claude's judgment.

    \b
    Claude reads the runbook, checks your cluster state, fetches source repos
    when needed, and applies only standard, verified fixes.

    \b
    Examples:
      odh run evalhub/create-evaluation-run -p project_namespace=my-project
      odh run model-serving/deploy-vllm-model -p project_namespace=my-ns -p model_name=my-model
      odh run cluster/enable-kserve
      odh run evalhub/create-evaluation-run --dry-run -p project_namespace=my-project
    """
    runbook, path = load_runbook(runbook_name)

    # Parse params
    params = {}
    for p in param:
        if "=" not in p:
            raise click.ClickException(f"Invalid param format: '{p}' — use key=value")
        k, v = p.split("=", 1)
        params[k.strip()] = v.strip()

    # Fill defaults
    for parameter in runbook.parameters:
        if parameter.name not in params and parameter.default is not None:
            params[parameter.name] = parameter.default

    # Check for missing required params — offer wizard
    missing_required = [
        p for p in runbook.parameters
        if p.required and (p.name not in params or not str(params.get(p.name, "")).strip())
    ]
    if missing_required:
        console.print(f"\n[yellow]Missing {len(missing_required)} required parameter(s):[/yellow]")
        for p in missing_required:
            hint = f" — {p.hint}" if p.hint else ""
            example = f" (e.g. {p.example})" if p.example else ""
            console.print(f"  [red]✗[/red] {p.name}: {p.description}{example}{hint}")
        console.print()
        if click.confirm("Run wizard to fill them in interactively?", default=True):
            from runner.wizard import run_wizard
            params = asyncio.run(run_wizard(runbook, ClusterClient(), params)) or {}
            if not params:
                sys.exit(1)
        else:
            console.print("[dim]Tip: use 'odh wizard <runbook>' for guided param collection[/dim]")
            sys.exit(1)

    from runner.agentic import run_agentic
    success = asyncio.run(run_agentic(
        runbook, params, ClusterClient(),
        runbook_path=runbook_name,
        dry_run=dry_run,
    ))
    sys.exit(0 if success else 1)


@cli.command("list")
@click.option("--workflow", "-w", is_flag=True, help="Group by goal/workflow instead of component")
@click.option("--tag", "-t", default="", help="Filter by tag (e.g. beginner, gpu, setup)")
def list_runbooks(workflow: bool, tag: str):
    """List all available runbooks.

    \b
    Examples:
      odh list                  # all runbooks by component
      odh list --workflow       # grouped by goal
      odh list --tag gpu        # GPU-related runbooks only
    """
    if workflow:
        from runner.start import WORKFLOWS
        console.print("\n[bold]Runbooks by workflow (goal-first view)[/bold]\n")
        for wf in WORKFLOWS:
            if tag and tag not in wf.get("tags", []):
                continue
            console.print(f"[bold cyan]{wf['title']}[/bold cyan]")
            console.print(f"  [dim]{wf['description']}[/dim]")
            console.print(f"  [dim]Time: {wf['time_estimate']}[/dim]")
            for i, (runbook_path, what, note) in enumerate(wf["steps"], 1):
                note_str = f" [dim]({note})[/dim]" if note else ""
                console.print(f"  {i}. [cyan]{runbook_path}[/cyan] — {what}{note_str}")
            console.print()
        console.print("[dim]Run 'odh wizard <runbook>' for guided help with any runbook.[/dim]")
        console.print("[dim]Run 'odh start' to be guided through a complete workflow.[/dim]")
        return

    table = Table(title="Available Runbooks", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Confidence")
    table.add_column("Time")
    table.add_column("Description")

    for yaml_file in sorted(RUNBOOKS_DIR.rglob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text())
            name = str(yaml_file.relative_to(RUNBOOKS_DIR)).replace(".yaml", "")
            confidence = data.get("confidence_overall", "?")
            desc = data.get("description", "").strip().split("\n")[0][:55]
            tags = data.get("tags", [])
            est = data.get("estimated_minutes")
            time_str = f"~{est}m" if est else ""

            if tag and tag not in tags:
                continue

            color = {"verified": "green", "doc-derived": "cyan",
                     "inferred": "yellow", "uncertain": "red"}.get(confidence, "white")
            table.add_row(name, f"[{color}]{confidence}[/]", time_str, desc)
        except Exception:
            pass

    console.print(table)
    console.print()
    console.print("[dim]'odh start' guides you if you don't know where to begin.[/dim]")
    console.print("[dim]'odh wizard <name>' walks you through any runbook interactively.[/dim]")
    console.print("[dim]'odh list --workflow' shows runbooks grouped by goal.[/dim]")


@cli.command(hidden=True)
@click.argument("component")
@click.argument("task")
@click.option("--output", "-o", default=None, help="Save to file (default: print to stdout)")
def generate(component: str, task: str, output: str | None):
    """Draft a new runbook using AI from available docs.

    \b
    Examples:
      odh generate genai "enable chat playground"
      odh generate workbenches "create workbench with GPU"
    """
    import anthropic
    from generator.generator import RunbookGenerator

    client = anthropic.Anthropic()
    generator = RunbookGenerator(client)

    console.print(f"[cyan]Generating runbook for: {component} / {task}[/cyan]")
    console.print("[dim]Using Claude — this may take a moment...[/dim]\n")

    yaml_str = asyncio.run(generator.generate(component, task))

    valid, msg = generator.validate_yaml(yaml_str)
    if not valid:
        console.print(f"[red]Generated YAML failed validation: {msg}[/red]")
        console.print("[yellow]Raw output saved to generated-runbook.yaml[/yellow]")
        Path("generated-runbook.yaml").write_text(yaml_str)
        return

    if output:
        Path(output).write_text(yaml_str)
        console.print(f"[green]✓ Saved to {output}[/green]")
        console.print("[yellow]Review carefully before running — all steps are 'inferred'[/yellow]")
    else:
        console.print(yaml_str)


@cli.command()
@click.argument("runbook_name", required=False)
def ask(runbook_name: str | None):
    """Get help or show runbook details.

    \b
    Without a runbook name: runs 'odh doctor' to show cluster health.
    With a runbook name: shows steps and what params it needs.

    \b
    Examples:
      odh ask                                # what's installed on my cluster?
      odh ask evalhub/create-evaluation-run  # show me this runbook
    """
    if runbook_name:
        try:
            runbook, _ = load_runbook(runbook_name)
            console.print(f"\n[bold]{runbook.name}[/bold]")
            console.print(f"[dim]{runbook.description.strip().split(chr(10))[0]}[/dim]\n")
            console.print("[bold]Required to run:[/bold]")
            for p in runbook.parameters:
                if p.required:
                    console.print(f"  -p {p.name}=... ({p.description})")
                    if p.example:
                        console.print(f"     [dim]e.g. {p.example}[/dim]")
            console.print(f"\n[dim]Run interactively:[/dim]  odh wizard {runbook_name}")
            console.print(f"[dim]Review first:[/dim]      odh run {runbook_name} --dry-run -p ...")
        except Exception as e:
            console.print(f"[red]{e}[/red]")
    else:
        asyncio.run(_run_doctor(ClusterClient()))


@cli.command()
@click.argument("runbook_name")
def show(runbook_name: str):
    """Show a runbook's steps and parameters without running it."""
    runbook, path = load_runbook(runbook_name)

    console.print(f"\n[bold]{runbook.name}[/bold]")
    console.print(f"[dim]{runbook.description}[/dim]")
    conf = runbook.confidence_overall.value if hasattr(runbook.confidence_overall, 'value') else runbook.confidence_overall
    console.print(f"Confidence: {conf}")
    if runbook.rhoai_version_tested:
        console.print(f"Tested on: {runbook.rhoai_version_tested}")

    console.print(f"\n[bold]Parameters:[/bold]")
    for p in runbook.parameters:
        req = "[red]*required[/red]" if p.required else f"[dim]default: {p.default}[/dim]"
        console.print(f"  {p.name}: {p.description} {req}")

    console.print(f"\n[bold]Steps ({len(runbook.steps)}):[/bold]")
    for i, step in enumerate(runbook.steps, 1):
        color = {"verified": "green", "doc-derived": "cyan",
                 "inferred": "yellow", "uncertain": "red"}.get(
            step.confidence.value if hasattr(step.confidence, 'value') else str(step.confidence), "white"
        )
        console.print(
            f"  {i:2}. [{color}]{step.confidence.value if hasattr(step.confidence, 'value') else step.confidence:12}[/] "
            f"{step.id}\n       [dim]{step.description[:80]}[/dim]"
        )

    if runbook.source_repos:
        console.print(f"\n[bold]Source repos (checked for standard fixes):[/bold]")
        for r in runbook.source_repos:
            console.print(f"  [dim]• {r}[/dim]")

    if runbook.known_bad_patterns:
        console.print(f"\n[bold]Known bad patterns (never done):[/bold]")
        for p in runbook.known_bad_patterns:
            console.print(f"  [dim red]✗ {p}[/dim red]")


@cli.command()
@click.argument("runbook_name")
@click.option("--param", "-p", multiple=True, help="Pre-fill parameter as key=value")
def wizard(runbook_name: str, param: tuple[str, ...]):
    """Interactively collect parameters, then run with Claude's judgment.

    \b
    For each parameter, the wizard shows:
    - What the parameter means + format hints + examples
    - Available values discovered live from your cluster
    - Enum options as a numbered list

    \b
    Examples:
      odh wizard evalhub/create-evaluation-run
      odh wizard model-serving/deploy-vllm-model
      odh wizard model-serving/deploy-vllm-model -p project_namespace=my-project
    """
    runbook, path = load_runbook(runbook_name)

    pre_params = {}
    for p in param:
        if "=" in p:
            k, v = p.split("=", 1)
            pre_params[k.strip()] = v.strip()

    from runner.wizard import run_wizard
    params = asyncio.run(run_wizard(runbook, ClusterClient(), pre_params))
    if not params:
        console.print("[yellow]Cancelled.[/yellow]")
        sys.exit(1)

    # Fill defaults for unset optional params
    for p in runbook.parameters:
        if p.name not in params and p.default is not None:
            params[p.name] = p.default

    console.print("\n[bold]Parameters collected:[/bold]")
    for k, v in params.items():
        if v is not None and str(v).strip() != "":
            console.print(f"  {k} = {v}")

    console.print()
    if click.confirm("Execute now?", default=True):
        from runner.agentic import run_agentic
        success = asyncio.run(run_agentic(
            runbook, params, ClusterClient(),
            runbook_path=runbook_name,
        ))
        sys.exit(0 if success else 1)
    else:
        param_str = " ".join(
            f"-p {k}={v}" for k, v in params.items()
            if v is not None and str(v).strip() != ""
        )
        console.print(f"\n[dim]To run later:[/dim]  odh run {runbook_name} {param_str}")


@cli.command()
def doctor():
    """Diagnose cluster — check what ODH components are installed and what's missing.

    \b
    Checks: ODH operator, DataScienceCluster, key components, storage, GPU.
    """
    from runner.resolver import DEPENDENCY_REGISTRY
    from runner.schema import Requirement
    from runner.resolver import DependencyResolver

    cluster = ClusterClient()

    CHECKS = [
        ("openshift-cluster",         "OpenShift cluster accessible"),
        ("dsc-exists",                "DataScienceCluster installed"),
        ("dsp-enabled",               "Data Science Pipelines enabled"),
        ("kserve-enabled",            "KServe model serving enabled"),
        ("model-registry-enabled",    "Model Registry operator enabled"),
        ("training-operator-enabled", "Training Operator enabled"),
        ("feast-enabled",             "Feature Store (Feast) enabled"),
        ("codeflare-enabled",         "Distributed Workloads (CodeFlare) enabled"),
        ("trustyai-enabled",          "TrustyAI enabled"),
        ("storage-class",             "Storage class available"),
        ("gpu-available",             "GPU nodes available"),
    ]

    async def run_checks():
        table = Table(title="ODH Cluster Health", show_header=True)
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Action")

        resolver = DependencyResolver(cluster, {}, {})

        for dep_type, label in CHECKS:
            dep = DEPENDENCY_REGISTRY.get(dep_type, {})
            if not dep:
                continue
            req = Requirement(type=dep_type)
            ok = await resolver._check(dep, req)

            if ok:
                table.add_row(label, "[green]✓ OK[/green]", "")
            elif dep.get("blocker"):
                table.add_row(label, "[red]✗ Missing[/red]", "[red]Manual action required[/red]")
            else:
                resolver_path = dep.get("resolver", "?")
                table.add_row(label, "[yellow]✗ Missing[/yellow]", f"[dim]odh run {resolver_path}[/dim]")

        console.print(table)
        console.print("\n[dim]Run 'odh run cluster/full-stack-setup' to set up everything.[/dim]")

    asyncio.run(run_checks())


async def _run_doctor(cluster):
    """Shared doctor logic (used by 'odh ask' with no args)."""
    from runner.resolver import DEPENDENCY_REGISTRY
    from runner.schema import Requirement
    from runner.resolver import DependencyResolver

    CHECKS = [
        ("openshift-cluster",         "OpenShift cluster"),
        ("dsc-exists",                "DataScienceCluster"),
        ("kserve-enabled",            "KServe"),
        ("dsp-enabled",               "Pipelines"),
        ("trustyai-enabled",          "TrustyAI"),
        ("model-registry-enabled",    "Model Registry"),
        ("gpu-available",             "GPU nodes"),
    ]

    resolver = DependencyResolver(cluster, {}, {})
    parts = []
    for dep_type, label in CHECKS:
        dep = DEPENDENCY_REGISTRY.get(dep_type, {})
        if not dep:
            continue
        req = Requirement(type=dep_type)
        ok = await resolver._check(dep, req)
        parts.append(f"{'[green]✓[/green]' if ok else '[red]✗[/red]'} {label}")

    console.print("  " + "  ".join(parts))
    console.print("\n[dim]Run 'odh doctor' for a full health check.[/dim]")


if __name__ == "__main__":
    cli()
