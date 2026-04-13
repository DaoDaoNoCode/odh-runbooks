from __future__ import annotations
import asyncio
from enum import Enum
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .schema import Runbook, Step, Confidence, OnFail, IfAlreadyTrue
from .cluster import ClusterClient
from .checks import CheckRunner
from .actions import ActionRunner
from .resolver import DependencyResolver

console = Console()

# Read-only action types — safe to execute in QA mode
_READONLY_ACTIONS = {"query", "none"}


class RunMode(str, Enum):
    IMPLEMENT = "implement"   # full execution (default)
    PLAN      = "plan"        # preview what would happen, no execution
    QA        = "qa"          # read-only checks only, report state


class StepResult:
    def __init__(self, status: str, message: str = "", output=None):
        self.status = status   # success | skipped | stopped | would_create | would_change
        self.message = message
        self.output = output

    @classmethod
    def success(cls, output=None): return cls("success", output=output)

    @classmethod
    def skipped(cls, reason=""): return cls("skipped", reason)

    @classmethod
    def stopped(cls, reason): return cls("stopped", reason)

    @classmethod
    def would_create(cls, msg=""): return cls("would_create", msg)

    @classmethod
    def would_change(cls, msg=""): return cls("would_change", msg)

    @property
    def should_stop(self): return self.status == "stopped"


class RunbookExecutor:
    def __init__(
        self,
        runbook: Runbook,
        params: dict,
        cluster: ClusterClient,
        mode: RunMode = RunMode.IMPLEMENT,
        runbook_path: str = "",  # e.g. "evalhub/create-evaluation-run" for display
    ):
        self.runbook = runbook
        self.params = params
        self.cluster = cluster
        self.mode = mode
        self.runbook_path = runbook_path  # file path for display (e.g. evalhub/create-evaluation-run)
        self.context: dict = {}
        self.rollback_log: list[dict] = []
        self.plan_log: list[dict] = []          # collected in PLAN mode
        self.qa_report: list[dict] = []         # collected in QA mode
        self.checks = CheckRunner(cluster, self.context, params)
        self.actions = ActionRunner(cluster, self.context, params)
        self.resolver = DependencyResolver(cluster, self.context, params)

    def render(self, text: str) -> str:
        all_vars = {**self.params, **self.context}
        try:
            return Template(text).render(**all_vars)
        except Exception:
            return text

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────────

    async def run(self) -> bool:
        if self.mode == RunMode.PLAN:
            return await self._run_plan()
        elif self.mode == RunMode.QA:
            return await self._run_qa()
        else:
            return await self._run_implement()

    # ──────────────────────────────────────────────────────────────────────────
    # IMPLEMENT mode — full execution
    # ──────────────────────────────────────────────────────────────────────────

    async def _run_implement(self) -> bool:
        console.print(Panel(
            f"[bold]{self.runbook.name}[/bold]\n\n{self.runbook.description}\n\n"
            f"Mode: [green]implement[/green] | "
            f"Confidence: [{self._confidence_color(self.runbook.confidence_overall)}]"
            f"{self.runbook.confidence_overall.value if hasattr(self.runbook.confidence_overall, 'value') else self.runbook.confidence_overall}[/]",
            title="[cyan]ODH Runbook Executor[/cyan]"
        ))

        non_empty = {k: v for k, v in self.params.items() if v is not None and str(v).strip() != ""}
        if non_empty:
            table = Table(show_header=True)
            table.add_column("Parameter")
            table.add_column("Value")
            for k, v in non_empty.items():
                table.add_row(k, str(v))
            console.print(table)

        if self.runbook.known_bad_patterns:
            console.print("\n[dim]Guardrails (never done automatically):[/dim]")
            for p in self.runbook.known_bad_patterns:
                console.print(f"  [dim red]✗ {p}[/dim red]")

        total_steps = len(self.runbook.steps)
        est = f"[dim] ~{self.runbook.estimated_minutes} min[/dim]" if self.runbook.estimated_minutes else ""
        console.print(f"\n[dim]Running {total_steps} steps...{est}[/dim]\n")

        for i, step in enumerate(self.runbook.steps, 1):
            # Build step header with optional time estimate
            time_hint = ""
            if step.estimated_seconds and step.estimated_seconds > 30:
                mins = step.estimated_seconds // 60
                secs = step.estimated_seconds % 60
                time_hint = f" [dim](~{mins}m {secs}s)[/dim]" if mins else f" [dim](~{secs}s)[/dim]"
            console.print(f"[cyan]Step {i}/{total_steps}:[/cyan] [bold]{step.id}[/bold]{time_hint}")
            console.print(f"  [dim]{step.description}[/dim]")

            result = await self._execute_step(step)

            if result.should_stop:
                console.print(f"\n[red bold]✗ STOPPED at step '{step.id}'[/red bold]")

                # Build a helpful, human-readable failure panel
                failure_body = f"[red]{result.message}[/red]\n\n"
                failure_body += "[yellow]Nothing further was executed. Cluster state is consistent.[/yellow]"

                # Step-specific recovery guidance (most helpful for non-experts)
                if step.on_fail_hint:
                    failure_body += f"\n\n[bold]What to try:[/bold]\n{step.on_fail_hint}"

                console.print(Panel(failure_body, title="[red]What went wrong[/red]", border_style="red"))

                if self.rollback_log:
                    console.print("\n[dim]Resources created before failure (safe to keep or delete):[/dim]")
                    for e in self.rollback_log:
                        rendered_rb = self.render(e['rollback'])
                        console.print(f"  [dim]• {rendered_rb}[/dim]")

                console.print("\n[dim]Next steps:[/dim]")
                console.print(f"  [dim]• Check cluster state:  odh doctor[/dim]")
                runbook_id = self.runbook_path or self.runbook.name
                param_str = " ".join(f"-p {k}={v}" for k, v in self.params.items() if v is not None and str(v).strip() != "")
                console.print(f"  [dim]• Re-check what exists: odh run {runbook_id} --dry-run {param_str}[/dim]")
                console.print(f"  [dim]• Ask for help:         odh ask \"why did {step.id} fail?\"[/dim]")
                return False

        # Show success
        last = self.runbook.steps[-1]
        if last.return_value:
            console.print(Panel(
                self.render(last.return_value),
                title="[green bold]✓ Complete[/green bold]",
                border_style="green"
            ))

        # Show structured next steps
        if self.runbook.next_steps:
            console.print("\n[bold]What to do next:[/bold]")
            for ns in self.runbook.next_steps:
                console.print(f"  → {ns}")
        return True

    # ──────────────────────────────────────────────────────────────────────────
    # PLAN mode — preview without executing
    # ──────────────────────────────────────────────────────────────────────────

    async def _run_plan(self) -> bool:
        # Use only the first line of the description to keep the panel compact
        first_line = self.runbook.description.strip().split("\n")[0].strip()
        console.print(Panel(
            f"[bold]{self.runbook.name}[/bold]\n\n{first_line}\n\n"
            f"Mode: [yellow]plan[/yellow] — no changes will be made",
            title="[yellow]ODH Runbook Planner[/yellow]"
        ))

        console.print("\n[bold]Step 1/2: Resolving dependencies...[/bold]")
        dep_summary = []

        # Check all dependencies across all steps without resolving
        for step in self.runbook.steps:
            for req in step.requires:
                from .resolver import DEPENDENCY_REGISTRY
                dep = DEPENDENCY_REGISTRY.get(req.type, {})
                satisfied = await self.resolver._check(dep, req) if dep else True
                dep_summary.append({
                    "type": req.type,
                    "satisfied": satisfied,
                    "blocker": dep.get("blocker", False) or not req.can_auto_resolve,
                    "resolver": dep.get("resolver"),
                })

        # Show dependency status
        dep_table = Table(title="Dependencies", show_header=True)
        dep_table.add_column("Dependency")
        dep_table.add_column("Status")
        dep_table.add_column("Action")

        seen = set()
        blockers = []
        auto_provisions = []

        for d in dep_summary:
            if d["type"] in seen:
                continue
            seen.add(d["type"])

            if d["satisfied"]:
                dep_table.add_row(d["type"], "[green]✓ exists[/green]", "none")
            elif d["blocker"]:
                dep_table.add_row(d["type"], "[red]✗ missing (BLOCKER)[/red]", "manual fix required")
                blockers.append(d["type"])
            else:
                resolver = d.get("resolver") or "unknown"
                dep_table.add_row(d["type"], "[yellow]✗ missing[/yellow]", f"auto → {resolver}")
                auto_provisions.append(d["type"])

        console.print(dep_table)

        if blockers:
            console.print(f"\n[red bold]✗ Cannot proceed — {len(blockers)} blocker(s):[/red bold]")
            for b in blockers:
                from .resolver import DEPENDENCY_REGISTRY
                dep = DEPENDENCY_REGISTRY.get(b, {})
                console.print(Panel(dep.get("blocker_message", f"'{b}' is a blocker"), border_style="red"))
            return False

        # Show step plan
        console.print("\n[bold]Step 2/2: Execution plan[/bold]")
        plan_table = Table(title="Steps", show_header=True)
        plan_table.add_column("#")
        plan_table.add_column("Step")
        plan_table.add_column("Confidence")
        plan_table.add_column("Action type")
        plan_table.add_column("Description")

        auto_steps = []
        for resolver_type in auto_provisions:
            from .resolver import DEPENDENCY_REGISTRY
            dep = DEPENDENCY_REGISTRY.get(resolver_type, {})
            resolver = dep.get("resolver")
            if resolver:
                auto_steps.append(f"[auto] {resolver}")

        for rs in auto_steps:
            plan_table.add_row("*", rs, "[dim]auto[/dim]", "create", "auto-provisioned dependency")

        for i, step in enumerate(self.runbook.steps, 1):
            color = self._confidence_color(step.confidence)
            # Use .value to get "doc-derived" not "Confidence.DOC_DERIVED"
            conf_display = step.confidence.value if hasattr(step.confidence, 'value') else str(step.confidence)
            plan_table.add_row(
                str(i),
                step.id,
                f"[{color}]{conf_display}[/]",
                step.action.type,
                step.description[:60]
            )

        console.print(plan_table)

        if auto_provisions:
            console.print(f"\n[yellow]Will auto-provision: {', '.join(auto_provisions)}[/yellow]")

        console.print(f"\n[bold]To execute:[/bold]")
        # Skip empty-value params (e.g. deployed_model_url=) — cleaner output
        param_str = " ".join(
            f"-p {k}={v}" for k, v in self.params.items()
            if v is not None and str(v).strip() != ""
        )
        display_name = self.runbook_path or self.runbook.name
        console.print(f"  odh run {display_name} {param_str}")

        return True

    # ──────────────────────────────────────────────────────────────────────────
    # QA mode — read-only state check
    # ──────────────────────────────────────────────────────────────────────────

    async def _run_qa(self) -> bool:
        console.print(Panel(
            f"[bold]{self.runbook.name}[/bold]\n\n"
            f"Mode: [blue]QA[/blue] — read-only, no changes",
            title="[blue]ODH Runbook QA Check[/blue]"
        ))

        qa_table = Table(title="State Check", show_header=True)
        qa_table.add_column("Check")
        qa_table.add_column("Status")
        qa_table.add_column("Detail")

        all_pass = True

        for step in self.runbook.steps:
            # Check dependencies (read-only)
            for req in step.requires:
                from .resolver import DEPENDENCY_REGISTRY
                dep = DEPENDENCY_REGISTRY.get(req.type, {})
                if not dep:
                    continue
                satisfied = await self.resolver._check(dep, req)
                if satisfied:
                    qa_table.add_row(f"dep: {req.type}", "[green]✓ present[/green]", "")
                elif dep.get("blocker") or not req.can_auto_resolve:
                    qa_table.add_row(f"dep: {req.type}", "[red]✗ MISSING (blocker)[/red]", dep.get("blocker_message", "")[:60])
                    all_pass = False
                else:
                    resolver = dep.get("resolver", "?")
                    qa_table.add_row(f"dep: {req.type}", "[yellow]✗ missing[/yellow]", f"would auto: {resolver}")

            # Run pre-check only (no action)
            if step.pre_check and step.pre_check.command:
                check = await self.checks.run(step.pre_check, self.render)
                step_label = f"step: {step.id}"
                if check.passed:
                    qa_table.add_row(step_label, "[green]✓ satisfied[/green]", "already in desired state")
                elif step.action.type in _READONLY_ACTIONS:
                    qa_table.add_row(step_label, "[blue]→ would query[/blue]", step.description[:60])
                else:
                    qa_table.add_row(step_label, "[yellow]→ would create/modify[/yellow]", step.description[:60])

        console.print(qa_table)

        if all_pass:
            console.print("\n[green bold]✓ All checks passed. Resource state looks correct.[/green bold]")
        else:
            console.print("\n[yellow]Some items are missing. Run to let Claude provision them.[/yellow]")
            console.print("  odh run ...")

        return all_pass

    # ──────────────────────────────────────────────────────────────────────────
    # Step execution (implement mode only)
    # ──────────────────────────────────────────────────────────────────────────

    async def _execute_step(self, step: Step) -> StepResult:
        # 0. Dependency resolution
        if step.requires:
            dep_result = await self.resolver.resolve_all(step.requires)
            if not dep_result.satisfied:
                return StepResult.stopped(
                    f"Dependency not satisfied for '{step.id}':\n\n{dep_result.message}"
                )

        # 1. Confidence gate
        if step.confidence == Confidence.UNCERTAIN:
            console.print(Panel(
                f"[yellow]UNCERTAIN STEP: {step.id}[/yellow]\n{step.description}\n\n[bold]Proceed? (y/N)[/bold]",
                border_style="yellow"
            ))
            if input("> ").strip().lower() != "y":
                return StepResult.stopped(f"User declined uncertain step '{step.id}'")
        elif step.confidence == Confidence.INFERRED:
            console.print(f"  [yellow]⚠ inferred step[/yellow]")

        # 2. Pre-check (idempotency)
        if step.pre_check and step.pre_check.command:
            check = await self.checks.run(step.pre_check, self.render)
            if check.passed and step.pre_check.if_already_true == IfAlreadyTrue.SKIP:
                console.print(f"  [dim]↩ already in desired state — skipped[/dim]")
                return StepResult.skipped()

        # 3. Dry-run gate
        if step.action.dry_run and step.action.manifest:
            result = await self.cluster.apply_manifest(self.render(step.action.manifest), dry_run=True)
            if not result.ok:
                return StepResult.stopped(f"Dry-run failed: {result.stderr}")

        # 4. Execute
        action_result = await self.actions.run(step.action, self.render)
        if not action_result.success:
            return StepResult.stopped(f"Action failed: {action_result.error}")

        if step.action.store_as and action_result.output is not None:
            self.context[step.action.store_as] = action_result.output
            console.print(f"  [dim]→ {step.action.store_as}: {str(action_result.output)[:80]}[/dim]")

        if step.action.store_response_as and action_result.output is not None:
            self.context[step.action.store_response_as] = action_result.output

        # 5. Post-check
        if step.post_check and step.post_check.command:
            console.print(f"  [dim]→ verifying...[/dim]", end="")
            check = await self.checks.poll_until(step.post_check, self.render)
            if not check.passed:
                return StepResult.stopped(
                    f"Post-check failed for '{step.id}':\n"
                    f"  Expected: {step.post_check.expected}\n"
                    f"  Got:      {check.actual}"
                )
            console.print(f" [green]✓[/green]")

        # 6. Track for rollback
        if step.rollback:
            self.rollback_log.append({"step": step.id, "rollback": step.rollback})

        console.print(f"  [green]✓ done[/green]")
        return StepResult.success(output=action_result.output)

    def _confidence_color(self, confidence) -> str:
        return {"verified": "green", "doc-derived": "cyan", "inferred": "yellow", "uncertain": "red"}.get(str(confidence), "white")
