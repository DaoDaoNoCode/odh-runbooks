"""
Interactive parameter wizard for runbooks.

When you don't know what value to provide, the wizard:
1. Shows description + format hint + example value
2. Runs a cluster discovery command to list valid options (if defined)
3. For enum params, shows a numbered list to pick from
4. Lets you type a custom value or pick from discovered ones
5. Builds the complete params dict and offers to run in plan mode first
"""
from __future__ import annotations
import asyncio
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from .schema import Runbook, Parameter
from .cluster import ClusterClient

console = Console()


class ParameterWizard:
    def __init__(self, runbook: Runbook, cluster: ClusterClient, existing_params: dict = {}):
        self.runbook = runbook
        self.cluster = cluster
        self.params: dict = dict(existing_params)

    async def run(self) -> dict | None:
        """
        Walk through parameters interactively.
        Asks required params first (like fly launch — minimal questions).
        Then asks if user wants to customize optional params.
        Returns completed params dict, or None if user cancels.
        """
        from rich.rule import Rule

        # Count required vs optional
        required = [p for p in self.runbook.parameters
                    if p.required and p.name not in self.params]
        optional = [p for p in self.runbook.parameters
                    if not p.required and p.name not in self.params]

        est = f" (~{self.runbook.estimated_minutes} min)" if self.runbook.estimated_minutes else ""
        console.print(Panel(
            f"[bold]{self.runbook.name}[/bold]{est}\n\n"
            f"{self.runbook.description.strip().split(chr(10))[0]}\n\n"
            f"[dim]Required: {len(required)} question(s)  |  "
            f"Optional with defaults: {len(optional)} parameter(s)[/dim]",
            title="[cyan]Parameter Wizard[/cyan]"
        ))

        # Show already-set params
        if self.params:
            console.print("\n[dim]Already set:[/dim]")
            for k, v in self.params.items():
                console.print(f"  [dim]✓ {k} = {v}[/dim]")

        # ── Phase 1: Required params only (the critical 2-5 questions) ──────
        if required:
            console.print(f"\n[bold]Required ({len(required)} question{'s' if len(required) != 1 else ''}):[/bold]")
            for param in required:
                value = await self._collect_param(param)
                if value is None:
                    console.print("\n[yellow]Wizard cancelled.[/yellow]")
                    return None
                if value:
                    self.params[param.name] = value

        # ── Phase 2: Fill optional params with defaults ───────────────────
        for param in optional:
            if param.default is not None:
                self.params[param.name] = param.default

        # ── Phase 3: Offer to customize optional params ───────────────────
        if optional:
            non_empty = [(p, self.params.get(p.name, p.default)) for p in optional]
            shown = [(p, v) for p, v in non_empty if v is not None and str(v).strip() != ""]
            hidden = [(p, v) for p, v in non_empty if v is None or str(v).strip() == ""]
            console.print(f"\n[dim]{len(optional)} optional parameter(s) set to defaults:[/dim]")
            for p, val in shown:
                console.print(f"  [dim]• {p.name} = {val}[/dim]")
            if hidden:
                # Show empty optional params collapsed — they're available but skipped
                console.print(f"  [dim]• {', '.join(p.name for p, _ in hidden)} = (empty — leave as-is)[/dim]")

            if Confirm.ask("\nCustomize any optional parameters?", default=False):
                console.print("\n[bold]Optional parameters:[/bold]")
                for param in optional:
                    console.print(f"\n  [dim]Current: {param.name} = {self.params.get(param.name, param.default)}[/dim]")
                    change = Confirm.ask(f"  Change {param.name}?", default=False)
                    if change:
                        value = await self._collect_param(param)
                        if value:
                            self.params[param.name] = value

        return self.params

    async def _collect_param(self, param: Parameter) -> str | None:
        """Collect a single parameter value interactively."""
        console.print()

        # Header
        required_tag = "[red](required)[/red]" if param.required else f"[dim](optional, default: {param.default or 'empty'})[/dim]"
        console.print(f"[bold cyan]{param.name}[/bold cyan] {required_tag}")
        console.print(f"  {param.description}")

        # Show hint
        if param.hint:
            console.print(f"  [yellow]ℹ {param.hint}[/yellow]")

        # Show example
        if param.example:
            console.print(f"  [dim]Example: {param.example}[/dim]")

        # Show enum options
        if param.enum:
            return await self._pick_from_enum(param)

        # Discover from cluster
        if param.discover_cmd:
            discovered = await self._discover_values(param)
            if discovered:
                return await self._pick_from_list(param, discovered)

        # Free-form input
        return self._prompt_free(param)

    async def _pick_from_enum(self, param: Parameter) -> str | None:
        """Pick from a fixed list of options."""
        console.print(f"\n  [bold]Options:[/bold]")
        for i, option in enumerate(param.enum, 1):
            marker = "[green]← default[/green]" if option == param.default else ""
            console.print(f"    {i}. {option} {marker}")

        default_display = param.default or ""
        while True:
            raw = Prompt.ask(
                f"  Pick (1-{len(param.enum)}) or type value",
                default=param.default or ""
            )
            if not raw and not param.required:
                return param.default or ""
            if raw.isdigit() and 1 <= int(raw) <= len(param.enum):
                return param.enum[int(raw) - 1]
            if raw in param.enum:
                return raw
            if raw and not param.required:
                return raw  # Allow custom value even for enum params
            if not raw and param.required:
                console.print("  [red]This parameter is required.[/red]")
            else:
                console.print(f"  [yellow]Not in list — accepted as custom value: {raw}[/yellow]")
                return raw

    async def _discover_values(self, param: Parameter) -> list[str]:
        """Run the discover command and return results as a list."""
        # Render any {param} references in the discover_cmd
        cmd = param.discover_cmd
        for name, val in self.params.items():
            cmd = cmd.replace(f"{{{name}}}", val)

        console.print(f"  [dim]→ discovering available values...[/dim]", end="")
        try:
            result = await asyncio.wait_for(self.cluster.run(cmd), timeout=15.0)
            if result.ok and result.stdout.strip():
                values = result.stdout.strip().split()
                console.print(f" [green]found {len(values)}[/green]")
                return values
            else:
                console.print(f" [dim]none found[/dim]")
                return []
        except asyncio.TimeoutError:
            console.print(f" [yellow]timed out[/yellow]")
            return []
        except Exception:
            console.print(f" [dim]skipped[/dim]")
            return []

    async def _pick_from_list(self, param: Parameter, options: list[str]) -> str | None:
        """Pick from a discovered list or type custom value."""
        console.print(f"\n  [bold]Available values:[/bold]")
        for i, opt in enumerate(options[:20], 1):  # cap at 20
            console.print(f"    {i}. {opt}")
        if len(options) > 20:
            console.print(f"    [dim]... and {len(options)-20} more[/dim]")

        if param.example and param.example not in options:
            console.print(f"  [dim]Or type a custom value (e.g. {param.example})[/dim]")

        prompt_text = f"  Pick (1-{min(len(options),20)}) or type custom value"
        if not param.required:
            prompt_text += f" [dim](Enter = {param.default or 'skip'})[/dim]"

        while True:
            raw = Prompt.ask(prompt_text, default=param.default or "")
            if not raw:
                if param.required:
                    console.print("  [red]This parameter is required.[/red]")
                    continue
                return param.default or ""
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < min(len(options), 20):
                    return options[idx]
            return raw  # Accept any custom value

    def _prompt_free(self, param: Parameter) -> str | None:
        """Free-form text input."""
        default = param.default or ""
        prompt_text = f"  Value"
        if not param.required and default:
            prompt_text += f" [dim](Enter = {default})[/dim]"

        while True:
            raw = Prompt.ask(prompt_text, default=default)
            if not raw and param.required:
                console.print("  [red]This parameter is required.[/red]")
                continue
            return raw or default


async def run_wizard(runbook: Runbook, cluster: ClusterClient, existing_params: dict = {}) -> dict | None:
    """Entry point for the wizard. Returns params or None if cancelled."""
    wizard = ParameterWizard(runbook, cluster, existing_params)
    return await wizard.run()
