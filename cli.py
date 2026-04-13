#!/usr/bin/env python3
"""
ODH Runbook CLI

Usage:
  odh run evalhub/create-evaluation-run --param project_namespace=my-project --param model_uri=s3://...
  odh ask "how do I enable EvalHub in the dashboard?"
  odh generate genai "enable chat playground"
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
from runner.executor import RunbookExecutor, RunMode
from runner.cluster import ClusterClient
from generator.generator import RunbookGenerator
import anthropic

RUNBOOKS_DIR = Path(__file__).parent / "runbooks"
console = Console()


def load_runbook(name: str) -> tuple[Runbook, Path]:
    """Load a runbook by name (e.g. 'evalhub/create-evaluation-run')."""
    path = RUNBOOKS_DIR / f"{name}.yaml"
    if not path.exists():
        # Try fuzzy match
        matches = list(RUNBOOKS_DIR.rglob(f"*{name.split('/')[-1]}*.yaml"))
        if not matches:
            raise click.ClickException(f"Runbook not found: {name}\nRun 'odh list' to see available runbooks.")
        path = matches[0]
        console.print(f"[dim]Found: {path.relative_to(RUNBOOKS_DIR)}[/dim]")

    data = yaml.safe_load(path.read_text())
    return Runbook.model_validate(data), path


@click.group()
def cli():
    """ODH Runbook Executor — reliable, verified automation for ODH/RHOAI components."""
    pass


@cli.command()
def start():
    """New here? Start with this. Guides you through setup based on your goal.

    \b
    No ODH knowledge required. Just answer 2-3 questions.
    Inspired by 'fly launch' — one command that figures out what you need.

    \b
    Examples:
      odh start            # guided onboarding for any goal
    """
    from runner.start import run_start
    asyncio.run(run_start())


@cli.command()
@click.argument("runbook_name")
@click.option("--param", "-p", multiple=True, help="Parameter as key=value (repeatable)")
@click.option("--mode", "-m", default="implement",
              type=click.Choice(["implement", "plan", "qa"]),
              help="implement=execute, plan=preview, qa=read-only check")
@click.option("--dry-run-only", is_flag=True, help="Alias for --mode plan")
def run(runbook_name: str, param: tuple[str, ...], mode: str, dry_run_only: bool):
    """Execute a runbook by name.

    \b
    Examples:
      odh run evalhub/create-evaluation-run -p project_namespace=my-project -p model_uri=s3://bucket/model
      odh run workbenches/create-workbench -p project_namespace=my-project -p workbench_name=my-nb
      odh run gpu/install-gpu-operator
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
        if parameter.name not in params:
            if parameter.default is not None:
                params[parameter.name] = parameter.default
            elif parameter.required:
                value = click.prompt(f"  {parameter.description} ({parameter.name})")
                params[parameter.name] = value

    if dry_run_only:
        mode = "plan"

    from runner.executor import RunMode
    run_mode = {"plan": RunMode.PLAN, "qa": RunMode.QA, "implement": RunMode.IMPLEMENT}[mode]

    # Check for missing required params — offer wizard if any are missing
    missing_required = [
        p for p in runbook.parameters
        if p.required and p.name not in params
    ]
    if missing_required:
        console.print(f"\n[yellow]Missing {len(missing_required)} required parameter(s):[/yellow]")
        for p in missing_required:
            hint = f" — {p.hint}" if p.hint else ""
            example = f" (e.g. {p.example})" if p.example else ""
            console.print(f"  [red]✗[/red] {p.name}: {p.description}{example}{hint}")
        console.print()
        use_wizard = click.confirm("Run wizard to fill them in interactively?", default=True)
        if use_wizard:
            from runner.wizard import run_wizard
            params = asyncio.run(run_wizard(runbook, ClusterClient(), params)) or {}
            if not params:
                sys.exit(1)
        else:
            console.print("[dim]Tip: use 'odh wizard <runbook>' for interactive param collection[/dim]")
            sys.exit(1)

    cluster = ClusterClient()
    executor = RunbookExecutor(runbook, params, cluster, mode=run_mode, runbook_path=runbook_name)
    success = asyncio.run(executor.run())
    sys.exit(0 if success else 1)


@cli.command("list")
@click.option("--workflow", "-w", is_flag=True, help="Group by goal/workflow instead of component")
@click.option("--tag", "-t", default="", help="Filter by tag (e.g. beginner, gpu, setup)")
def list_runbooks(workflow: bool, tag: str):
    """List all available runbooks.

    \b
    Examples:
      odh list                  # all runbooks by component
      odh list --workflow       # grouped by what you're trying to accomplish
      odh list --tag beginner   # only beginner-friendly runbooks
      odh list --tag gpu        # only GPU-related runbooks
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
        console.print("[dim]Run 'odh wizard <runbook-name>' to get guided help with any runbook.[/dim]")
        console.print("[dim]Run 'odh start' to be guided through a complete workflow interactively.[/dim]")
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
    console.print("[dim]Tip: 'odh start' guides you if you don't know where to begin.[/dim]")
    console.print("[dim]Tip: 'odh wizard <name>' walks you through any runbook step by step.[/dim]")
    console.print("[dim]Tip: 'odh list --workflow' shows runbooks grouped by goal.[/dim]")


@cli.command(hidden=True)  # internal tool for developing new runbooks
@click.argument("component")
@click.argument("task")
@click.option("--output", "-o", default=None, help="Save to file (default: print to stdout)")
def generate(component: str, task: str, output: str | None):
    """Draft a new runbook using AI from available docs.

    \b
    Examples:
      odh generate genai "enable chat playground"
      odh generate workbenches "create workbench with GPU"
      odh generate gpu "install GPU operator on OpenShift"

    The generated runbook will have all steps marked 'inferred'.
    Test it on a real cluster and promote confidence levels manually.
    """
    client = anthropic.Anthropic()
    generator = RunbookGenerator(client)

    console.print(f"[cyan]Generating runbook for: {component} / {task}[/cyan]")
    console.print("[dim]Using Claude with adaptive thinking — this may take a moment...[/dim]\n")

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
        console.print(f"[yellow]Review carefully before running — all steps are 'inferred'[/yellow]")
    else:
        console.print(yaml_str)


@cli.command()
@click.argument("runbook_name", required=False)
def ask(runbook_name: str | None):
    """Confused? Get help. Shows what to do next.

    \b
    Without a runbook name: runs 'odh doctor' to show cluster health.
    With a runbook name: shows the runbook steps and what params it needs.

    \b
    Examples:
      odh ask                              # what's installed on my cluster?
      odh ask evalhub/create-evaluation-run  # show me what this runbook does
    """
    if runbook_name:
        # Show the runbook details
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
            console.print(f"[dim]Preview first:[/dim]     odh run {runbook_name} --mode plan -p ...")
        except Exception as e:
            console.print(f"[red]{e}[/red]")
    else:
        # Just run doctor
        from runner.cluster import ClusterClient
        asyncio.run(_run_doctor(ClusterClient()))


@cli.command()
@click.argument("runbook_name")
def show(runbook_name: str):
    """Show the steps of a runbook without executing it."""
    runbook, path = load_runbook(runbook_name)

    console.print(f"\n[bold]{runbook.name}[/bold]")
    console.print(f"[dim]{runbook.description}[/dim]")
    console.print(f"Confidence: {runbook.confidence_overall}")
    if runbook.rhoai_version_tested:
        console.print(f"Tested on: {runbook.rhoai_version_tested}")

    console.print(f"\n[bold]Parameters:[/bold]")
    for p in runbook.parameters:
        req = "[red]*required[/red]" if p.required else f"[dim]default: {p.default}[/dim]"
        console.print(f"  {p.name}: {p.description} {req}")

    console.print(f"\n[bold]Steps ({len(runbook.steps)}):[/bold]")
    for i, step in enumerate(runbook.steps, 1):
        color = {
            "verified": "green",
            "doc-derived": "cyan",
            "inferred": "yellow",
            "uncertain": "red"
        }.get(step.confidence, "white")
        console.print(
            f"  {i:2}. [{color}]{step.confidence:12}[/] {step.id}\n"
            f"       [dim]{step.description}[/dim]"
        )

    if runbook.known_bad_patterns:
        console.print(f"\n[bold]Known bad patterns (never done):[/bold]")
        for p in runbook.known_bad_patterns:
            console.print(f"  [dim red]✗ {p}[/dim red]")


@cli.command()
@click.argument("runbook_name")
@click.option("--param", "-p", multiple=True, help="Pre-fill parameter as key=value")
def wizard(runbook_name: str, param: tuple[str, ...]):
    """Interactively fill in runbook parameters with cluster discovery.

    For each parameter the wizard shows:
    - What the parameter means
    - Format hints and examples
    - Available values discovered live from your cluster
    - Enum options as a numbered list to pick from

    Then runs in plan mode so you can see what will happen before executing.

    \b
    Examples:
      odh wizard evalhub/create-evaluation-run
      odh wizard pipelines/create-pipeline-server
      odh wizard rosa/install-rhoai-prerelease
      odh wizard model-serving/deploy-vllm-model -p project_namespace=my-project
    """
    runbook, path = load_runbook(runbook_name)

    # Parse any pre-filled params
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

    # Fill defaults for any unset optional params
    for p in runbook.parameters:
        if p.name not in params and p.default is not None:
            params[p.name] = p.default

    console.print("\n[bold]Parameters collected:[/bold]")
    for k, v in params.items():
        console.print(f"  {k} = {v}")

    console.print()
    if click.confirm("Preview plan before executing?", default=True):
        from runner.executor import RunMode
        executor = RunbookExecutor(runbook, params, ClusterClient(), mode=RunMode.PLAN, runbook_path=runbook_name)
        success = asyncio.run(executor.run())
        if not success:
            sys.exit(1)
        console.print()

    if click.confirm("Execute now?", default=False):
        from runner.executor import RunMode
        executor = RunbookExecutor(runbook, params, ClusterClient(), mode=RunMode.IMPLEMENT, runbook_path=runbook_name)
        success = asyncio.run(executor.run())
        sys.exit(0 if success else 1)
    else:
        console.print("\n[dim]To run later:[/dim]")
        param_str = " ".join(f"-p {k}={v}" for k, v in params.items())
        console.print(f"  odh run {runbook_name} {param_str}")


@cli.command(hidden=True)
@click.argument("runbook_name")
def deps(runbook_name: str):
    """Show what dependencies will be auto-resolved for a runbook.

    \b
    Examples:
      odh deps pipelines/create-pipeline-server
      odh deps model-serving/deploy-vllm-model
      odh deps evalhub/create-evaluation-run
    """
    from runner.dependency_map import DEPENDENCY_CHAINS
    from runner.resolver import DEPENDENCY_REGISTRY

    chain = DEPENDENCY_CHAINS.get(runbook_name, [])

    console.print(f"\n[bold]Dependency chain for: {runbook_name}[/bold]\n")

    if not chain:
        console.print("[dim]No known dependencies registered for this runbook.[/dim]")
        console.print("[dim]Check runbook YAML for 'requires:' fields.[/dim]")
        return

    table = Table(show_header=True)
    table.add_column("Dependency", style="cyan")
    table.add_column("Auto-resolver")
    table.add_column("Blocker?", style="red")

    for dep_type, resolver in chain:
        dep = DEPENDENCY_REGISTRY.get(dep_type, {})
        is_blocker = dep.get("blocker", False) or "BLOCKER" in resolver
        table.add_row(
            dep_type,
            resolver,
            "[red]YES — manual fix required[/red]" if is_blocker else "[green]No — auto-resolved[/green]"
        )

    console.print(table)
    console.print(
        "\n[dim]Auto-resolved dependencies are handled transparently.\n"
        "Blockers require manual intervention before the runbook can proceed.[/dim]"
    )


@cli.command()
def doctor():
    """Diagnose the current cluster — check what's installed and what's missing.

    \b
    Checks: ODH operator, DataScienceCluster, key components, storage, GPU.
    Prints a table showing what's ready and what needs action.
    """
    import asyncio
    from runner.cluster import ClusterClient
    from runner.resolver import DEPENDENCY_REGISTRY

    cluster = ClusterClient()

    CHECKS = [
        ("openshift-cluster",    "OpenShift cluster accessible"),
        ("dsc-exists",           "DataScienceCluster installed"),
        ("dsp-enabled",          "Data Science Pipelines enabled"),
        ("kserve-enabled",       "KServe model serving enabled"),
        ("model-registry-enabled", "Model Registry operator enabled"),
        ("training-operator-enabled", "Training Operator enabled"),
        ("feast-enabled",        "Feature Store (Feast) enabled"),
        ("codeflare-enabled",    "Distributed Workloads (CodeFlare) enabled"),
        ("trustyai-enabled",     "TrustyAI enabled"),
        ("storage-class",        "Storage class available"),
        ("gpu-available",        "GPU nodes available"),
    ]

    async def _run_doctor(cluster):
        return await run_checks()

    async def run_checks():
        table = Table(title="ODH Cluster Health", show_header=True)
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Action")

        from runner.schema import Requirement
        from runner.resolver import DependencyResolver
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
                table.add_row(label, "[yellow]✗ Missing[/yellow]", f"[dim]Auto-resolved: {resolver_path}[/dim]")

        console.print(table)
        console.print("\n[dim]Run 'odh run cluster/full-stack-setup' to set up everything.[/dim]")

    asyncio.run(run_checks())


if __name__ == "__main__":
    cli()
