"""
Agentic runbook executor — Claude has full judgment over execution.

The runbook YAML is a REFERENCE: goal, steps, known bad patterns, source repos.
Claude reads it, checks actual cluster state, consults source repos, and executes
with judgment. Uses the Anthropic SDK directly (no extra dependencies required).

Design principles:
1. The runbook is a GUIDE, not a rigid script — Claude adapts to real cluster state
2. Claude ALWAYS checks source_repos before applying any non-obvious fix
3. No workarounds — if the standard approach doesn't exist yet, add the prerequisite correctly
4. Claude skips steps already done, handles partial state gracefully
5. If no standard fix can be found: stop, explain clearly, tell the user what to do manually
"""
from __future__ import annotations
import asyncio
import subprocess
import os
import yaml
from pathlib import Path
from typing import Optional

import anthropic
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .schema import Runbook

console = Console()

# ─── Tools available to Claude ────────────────────────────────────────────────

TOOLS = [
    {
        "name": "Bash",
        "description": (
            "Execute a bash command on the local machine (which has oc/kubectl configured "
            "to talk to the OpenShift cluster). Use for: oc get, oc apply, oc patch, "
            "oc logs, oc describe, oc process, oc delete, etc. "
            "Always check cluster state before creating/modifying resources."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash/oc command to run"
                },
                "description": {
                    "type": "string",
                    "description": "One-line description of what this command does"
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "WebFetch",
        "description": (
            "Fetch content from a URL. Use for: reading GitHub source code to verify "
            "the correct approach for a fix, checking CRD specs, reading official docs. "
            "For GitHub repos, prefer raw content URLs: "
            "https://raw.githubusercontent.com/<org>/<repo>/main/<path>. "
            "For GitHub file browsing use the API: "
            "https://api.github.com/repos/<org>/<repo>/contents/<path>"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch"
                },
            },
            "required": ["url"],
        },
    },
]

# ─── System prompt ─────────────────────────────────────────────────────────────

AGENTIC_SYSTEM_PROMPT = """You are an expert OpenShift / RHOAI platform engineer executing a runbook on a live cluster.

You have been given:
1. The full runbook YAML — goal, steps (as reference), known bad patterns, and source repos
2. All parameters filled in by the user
3. Direct cluster access via Bash (oc, kubectl commands)
4. Web access to check authoritative source repos (WebFetch)

═══ CORE PRINCIPLES (non-negotiable) ════════════════════════════════════════════

1. CHECK STATE FIRST — Always run `oc get` before creating/patching anything.
   Never assume something doesn't exist. Skip steps that are already done.

2. SOURCE CODE IS THE TRUTH — Before applying any non-obvious configuration, fetch
   the relevant GitHub repo from source_repos to verify the correct approach.
   If a field name, annotation, resource structure, or API is unclear — read the source.
   For GitHub repos, fetch raw content: https://raw.githubusercontent.com/<org>/<repo>/main/<path>

3. NO WORKAROUNDS — Every fix must match what the component's official source code says.
   If the standard approach requires a prerequisite (e.g. an operator, a template, a CRD),
   set up the prerequisite the standard way. Never patch around it.

4. FOLLOW THE OPENDATAHUB PATTERNS — Check https://github.com/opendatahub-io/odh-dashboard
   source when you need to understand how the UI creates resources (correct field names,
   labels, annotations, connection types). The dashboard is the reference implementation
   for what the correct resource structure looks like.

5. ADAPT TO ACTUAL STATE — The runbook steps are a guide. If the cluster is in a
   different state than expected (resource exists but misconfigured, older operator version,
   etc.), use judgment to handle it correctly per the source code.

6. RENDER TEMPLATES — All {{ variable_name }} Jinja2 placeholders in the runbook YAML
   must be substituted with the actual parameter values before use.

7. WHEN STUCK — If after checking source repos you still cannot find a standard fix:
   - Explain exactly what the error is
   - What you checked (which repos, which files)
   - Why no standard fix was found
   - What the user must do manually
   Then output "CANNOT_FIX: <reason>" on its own line and stop.

═══ EXECUTION WORKFLOW ══════════════════════════════════════════════════════════

For each runbook step:
1. Read what the step is trying to accomplish (description)
2. Pre-check: run oc get / oc describe to see current state
3. If already done → skip, move to next step
4. If uncertain about correct approach → fetch source repo first
5. Execute the step (oc apply, oc patch, oc create, etc.)
6. Post-verify: confirm the resource reached desired state
7. Narrate what happened concisely

═══ OUTPUT FORMAT ═══════════════════════════════════════════════════════════════

- Keep narration brief: "Checking if X exists... found / not found"
- Show oc command output when it informs a decision
- Mark problems clearly and explain what you're doing to fix them
- At the end, print the runbook's return_value (formatted) if all succeeded
"""

AGENTIC_EXECUTION_PROMPT = """\
You are executing the following runbook. Read it carefully — the steps are a reference guide, \
not a rigid script. Adapt to the actual cluster state.

══════════════════════════════════════════════════════════════════
RUNBOOK: {runbook_path}
══════════════════════════════════════════════════════════════════

{runbook_yaml}

══════════════════════════════════════════════════════════════════
PARAMETERS (already collected — substitute all {{ variable }} placeholders with these)
══════════════════════════════════════════════════════════════════

{params_block}

══════════════════════════════════════════════════════════════════
YOUR TASK
══════════════════════════════════════════════════════════════════

Goal: {goal}

Execute this runbook's goal on the live cluster:
• Check current cluster state before each step
• Consult source_repos when the correct approach is unclear
• Never apply a configuration without verifying it matches the official source code
• Substitute all Jinja2 template variables using the parameters above
• When complete, print the return_value from the last step

Begin execution now.
"""

AGENTIC_DRYRUN_PROMPT = """\
You are reviewing the following runbook WITHOUT making any changes.

══════════════════════════════════════════════════════════════════
RUNBOOK: {runbook_path}
══════════════════════════════════════════════════════════════════

{runbook_yaml}

══════════════════════════════════════════════════════════════════
PARAMETERS
══════════════════════════════════════════════════════════════════

{params_block}

══════════════════════════════════════════════════════════════════
YOUR TASK — READ-ONLY REVIEW (no changes to cluster)
══════════════════════════════════════════════════════════════════

1. Check current cluster state with oc get / oc describe
2. For each runbook step, report: already done ✓ / would run → / missing prerequisite ✗
3. Identify any potential problems or missing dependencies
4. Show a clear summary

At the end, show the exact `odh run` command to execute for real.
"""


# ─── Tool execution ────────────────────────────────────────────────────────────

async def _run_bash(command: str, description: str = "") -> str:
    """Execute a bash command and return combined stdout+stderr."""
    label = description or command[:60]
    console.print(f"  [dim]$ {command[:120]}[/dim]")
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        except asyncio.TimeoutError:
            proc.kill()
            return "ERROR: Command timed out after 120 seconds"

        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        combined = (out + err).strip()

        # Show truncated output
        if combined:
            display = combined[:800] + (" [...]" if len(combined) > 800 else "")
            console.print(f"  [dim]{display}[/dim]")
        return combined or "(no output)"

    except Exception as e:
        return f"ERROR: {e}"


async def _fetch_url(url: str) -> str:
    """Fetch a URL and return its content (truncated to 8 KB)."""
    console.print(f"  [dim]GET {url[:100]}[/dim]")
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "odh-runbooks/1.0"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.text
            if len(text) > 8000:
                text = text[:8000] + "\n\n[... truncated — fetch a more specific path ...]"
            return text
    except Exception as e:
        return f"ERROR fetching {url}: {e}"


async def _execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "Bash":
        return await _run_bash(tool_input["command"], tool_input.get("description", ""))
    elif tool_name == "WebFetch":
        return await _fetch_url(tool_input["url"])
    else:
        return f"Unknown tool: {tool_name}"


# ─── Main agentic runner ────────────────────────────────────────────────────────

async def run_agentic(
    runbook: Runbook,
    params: dict,
    cluster,
    runbook_path: str = "",
    dry_run: bool = False,
) -> bool:
    """
    Execute a runbook agentically — Claude reads the full runbook YAML,
    checks cluster state, consults source repos, and executes with judgment.

    Returns True if goal was achieved, False if unrecoverable failure.
    """
    display_name = runbook_path or runbook.name
    goal = runbook.description.strip().split("\n")[0].strip()

    # Serialize the full runbook as YAML context for Claude
    runbook_dict = runbook.model_dump(by_alias=True, exclude_none=True)
    runbook_yaml = yaml.dump(
        runbook_dict, default_flow_style=False, allow_unicode=True, sort_keys=False
    )

    params_block = "\n".join(
        f"  {k} = {v}"
        for k, v in params.items()
        if v is not None and str(v).strip()
    ) or "  (none — using runbook defaults)"

    # Build prompt
    if dry_run:
        prompt = AGENTIC_DRYRUN_PROMPT.format(
            runbook_path=display_name,
            runbook_yaml=runbook_yaml,
            params_block=params_block,
        )
        mode_label = "[yellow]dry-run[/yellow] — Claude reviews cluster state, no changes"
    else:
        prompt = AGENTIC_EXECUTION_PROMPT.format(
            runbook_path=display_name,
            runbook_yaml=runbook_yaml,
            params_block=params_block,
            goal=goal,
        )
        mode_label = "[magenta]agentic[/magenta] — Claude executes with judgment"

    # Header
    source_count = len(runbook.source_repos)
    console.print(Panel(
        f"[bold]{runbook.name}[/bold]\n\n"
        f"{goal}\n\n"
        f"Mode: {mode_label}\n"
        f"Source repos: {source_count} configured"
        + (" (Claude consults these for correct approach)" if source_count else ""),
        title="[magenta]ODH Agentic Executor[/magenta]",
    ))

    if runbook.source_repos:
        console.print("\n[dim]Source repos:[/dim]")
        for repo in runbook.source_repos:
            console.print(f"  [dim]• {repo}[/dim]")

    if params_block.strip() != "(none — using runbook defaults)":
        console.print("\n[dim]Parameters:[/dim]")
        for k, v in params.items():
            if v is not None and str(v).strip():
                console.print(f"  [dim]{k} = {v}[/dim]")

    console.print(f"\n[magenta]Claude is working...[/magenta]\n")

    # ── Agent loop ─────────────────────────────────────────────────────────────
    client = anthropic.AsyncAnthropic()
    messages: list[dict] = [{"role": "user", "content": prompt}]
    max_turns = 60
    turn = 0
    final_text = ""

    while turn < max_turns:
        turn += 1

        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=8096,
            system=AGENTIC_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect text output and tool calls
        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text" and block.text.strip():
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        # Print any text Claude produced
        if text_parts:
            combined_text = "\n".join(text_parts)
            console.print(combined_text)
            final_text = combined_text

        # Add assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        # Done?
        if response.stop_reason == "end_turn":
            break

        # Execute tools
        if tool_uses:
            tool_results = []
            for tool_block in tool_uses:
                result = await _execute_tool(tool_block.name, tool_block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})
        else:
            # No tools and no end_turn — shouldn't happen, but break to avoid infinite loop
            break

    if turn >= max_turns:
        console.print("\n[yellow]Reached max turns limit — stopping.[/yellow]")

    # ── Check for explicit failure signal ─────────────────────────────────────
    if "CANNOT_FIX:" in final_text:
        reason = final_text.split("CANNOT_FIX:")[1].split("\n")[0].strip()
        console.print(Panel(
            f"[red]Claude could not complete this with a standard fix.[/red]\n\n"
            f"Reason: {reason}\n\n"
            f"[yellow]Manual intervention required.\n"
            f"Check the source_repos above for the correct approach.[/yellow]",
            title="[red]Stopped — No Standard Fix Found[/red]",
            border_style="red",
        ))
        return False

    return True
