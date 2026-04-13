#!/usr/bin/env python3
"""
ODH Runbook MCP Server

Connects the runbook executor to Claude Desktop (or any MCP client).
Claude can execute runbooks, check cluster state, and answer ODH questions
using natural language — no need to remember CLI commands.

Setup:
  pip install -e ".[mcp]"
  # Then add to Claude Desktop config (see README.md)

Credential modes:
  1. kubeconfig (default): reads ~/.kube/config (works after `oc login`)
  2. Explicit token: set OC_SERVER + OC_TOKEN env vars
  3. Service account: set OC_SA_TOKEN env var (long-lived, non-expiring)
"""
import asyncio
import io
import os
import sys
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP, Context
from rich.console import Console

# Add project to path
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from runner.cluster import ClusterClient
from runner.executor import RunbookExecutor, RunMode
from runner.schema import Runbook
from runner.resolver import DEPENDENCY_REGISTRY
from runner.dependency_map import DEPENDENCY_CHAINS

import yaml

RUNBOOKS_DIR = PROJECT_DIR / "runbooks"

# ── Server setup ──────────────────────────────────────────────────────────────

mcp = FastMCP(
    "ODH Runbooks",
    instructions="""
    You are an ODH/RHOAI platform assistant with access to a runbook executor.
    You can set up ODH components, check cluster state, and explain how things work.

    Key capabilities:
    - list_runbooks: see all available runbooks
    - check_cluster: diagnose what's installed, what's missing
    - check_dependencies: preview what a runbook will auto-provision
    - run_runbook: execute a runbook (plan, qa, or implement mode)
    - ask_odh: answer ODH architecture/config questions

    Always ask the user for confirmation before running in 'implement' mode
    when it will make significant changes (enabling components, deploying models).
    For read-only checks (qa mode) or plan previews, proceed without asking.

    When a user says something like:
    - "set up EvalHub" → use run_runbook with evalhub/create-evaluation-run
    - "check if pipelines work" → use run_runbook with qa mode
    - "what's installed?" → use check_cluster
    - "what will happen if I run X?" → use check_dependencies, then run_runbook in plan mode
    """,
)


# ── Helper: capture Rich output as string ─────────────────────────────────────

def _capture_run(coro) -> str:
    """Run an async coroutine and capture Rich console output as a string."""
    buf = io.StringIO()
    cap = Console(file=buf, width=100)

    # Monkey-patch the module-level console temporarily
    import runner.executor as exec_mod
    import runner.resolver as res_mod
    orig_exec = exec_mod.console
    orig_res = res_mod.console
    exec_mod.console = cap
    res_mod.console = cap

    try:
        asyncio.run(coro)
    except Exception as e:
        cap.print(f"[red]Error: {e}[/red]")
    finally:
        exec_mod.console = orig_exec
        res_mod.console = orig_res

    return buf.getvalue()


def _load_runbook(name: str) -> tuple[Runbook, Path]:
    path = RUNBOOKS_DIR / f"{name}.yaml"
    if not path.exists():
        matches = list(RUNBOOKS_DIR.rglob(f"*{name.split('/')[-1]}*.yaml"))
        if not matches:
            raise ValueError(f"Runbook '{name}' not found. Use list_runbooks() to see available runbooks.")
        path = matches[0]
    return Runbook.model_validate(yaml.safe_load(path.read_text())), path


def _make_cluster() -> ClusterClient:
    """Create a cluster client using the best available credentials."""
    return ClusterClient()


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool
def list_runbooks(component: str = "") -> str:
    """
    List all available ODH runbooks, optionally filtered by component.

    Args:
        component: Filter by component name (e.g. 'evalhub', 'pipelines', 'model-serving').
                   Leave empty to list all runbooks.

    Returns formatted list of runbooks with confidence levels.
    """
    lines = ["# Available ODH Runbooks\n"]
    components = {}

    for yaml_file in sorted(RUNBOOKS_DIR.rglob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text())
            comp = yaml_file.parent.name
            if component and component not in comp:
                continue
            if comp not in components:
                components[comp] = []
            components[comp].append({
                "path": str(yaml_file.relative_to(RUNBOOKS_DIR)).replace(".yaml", ""),
                "name": data.get("name", ""),
                "confidence": data.get("confidence_overall", "?"),
                "desc": data.get("description", "").strip()[:80].split("\n")[0],
                "tested": data.get("rhoai_version_tested") or "not tested",
            })
        except Exception:
            pass

    for comp, runbooks in sorted(components.items()):
        lines.append(f"\n## {comp.upper()}")
        for r in runbooks:
            conf_icon = {"verified": "✓", "doc-derived": "◉", "inferred": "△", "uncertain": "?"}.get(r["confidence"], "?")
            lines.append(f"  {conf_icon} `{r['path']}`")
            lines.append(f"     {r['desc']}")

    lines.append("\n\n**Confidence levels:** ✓ verified  ◉ doc-derived  △ inferred  ? uncertain")
    lines.append("\nUse `check_dependencies(name)` to see what a runbook will auto-provision.")
    return "\n".join(lines)


@mcp.tool
def check_cluster() -> str:
    """
    Diagnose the current cluster: check what ODH components are installed,
    what's missing, and what can be auto-provisioned vs. requires manual action.

    No changes are made — read-only.
    Returns a status table.
    """
    CHECKS = [
        ("openshift-cluster",       "OpenShift cluster accessible"),
        ("dsc-exists",              "DataScienceCluster installed"),
        ("storage-class",           "Storage class available"),
        ("dsp-enabled",             "Data Science Pipelines"),
        ("kserve-enabled",          "KServe (model serving)"),
        ("model-registry-enabled",  "Model Registry operator"),
        ("training-operator-enabled","Training Operator (PyTorchJob etc)"),
        ("feast-enabled",           "Feature Store (Feast)"),
        ("codeflare-enabled",       "Distributed Workloads (Ray/Kueue)"),
        ("trustyai-enabled",        "TrustyAI (fairness + EvalHub)"),
        ("gpu-available",           "GPU nodes"),
        ("gpu-operator-installed",  "NVIDIA GPU Operator"),
    ]

    async def _run():
        cluster = _make_cluster()
        from runner.schema import Requirement
        from runner.resolver import DependencyResolver
        resolver = DependencyResolver(cluster, {}, {})
        lines = ["# ODH Cluster Health Report\n"]
        lines.append(f"{'Component':<35} {'Status':<20} {'Action'}")
        lines.append("-" * 80)

        for dep_type, label in CHECKS:
            dep = DEPENDENCY_REGISTRY.get(dep_type, {})
            if not dep:
                continue
            req = Requirement(type=dep_type)
            try:
                ok = await resolver._check(dep, req)
            except Exception:
                ok = False

            if ok:
                status = "✓ installed"
                action = ""
            elif dep.get("blocker"):
                status = "✗ MISSING (blocker)"
                action = "manual fix required"
            else:
                resolver_path = dep.get("resolver", "?")
                status = "✗ missing"
                action = f"auto: {resolver_path}"

            lines.append(f"{label:<35} {status:<20} {action}")

        lines.append("\n\n**Blockers** require manual action before runbooks can proceed.")
        lines.append("**Missing** items are auto-provisioned when you run a runbook that needs them.")
        lines.append("\nRun `run_runbook('cluster/full-stack-setup', ...)` to set up everything.")
        return "\n".join(lines)

    return asyncio.run(_run())


@mcp.tool
def check_dependencies(runbook_name: str, params: dict = {}) -> str:
    """
    Preview what a runbook will auto-provision and what might block it.
    No changes are made — read-only planning.

    Args:
        runbook_name: e.g. 'evalhub/create-evaluation-run', 'pipelines/create-pipeline-server'
        params: Parameters the runbook needs (e.g. {'project_namespace': 'my-project'})

    Returns a dependency analysis showing what exists, what will be auto-created,
    and any blockers that need manual fixing first.
    """
    try:
        runbook, _ = _load_runbook(runbook_name)
    except ValueError as e:
        return str(e)

    async def _run():
        cluster = _make_cluster()
        from runner.schema import Requirement
        from runner.resolver import DependencyResolver
        resolver = DependencyResolver(cluster, {}, params)
        lines = [f"# Dependency Analysis: {runbook_name}\n"]

        all_reqs: list[tuple[str, Requirement]] = []
        for step in runbook.steps:
            for req in step.requires:
                all_reqs.append((step.id, req))

        if not all_reqs:
            lines.append("No explicit dependencies declared in this runbook.")
            lines.append("\nParameters required:")
            for p in runbook.parameters:
                req_flag = "(required)" if p.required else f"(default: {p.default})"
                lines.append(f"  - {p.name}: {p.description} {req_flag}")
            return "\n".join(lines)

        seen = set()
        blockers = []
        auto_provisions = []
        satisfied = []

        for step_id, req in all_reqs:
            if req.type in seen:
                continue
            seen.add(req.type)

            dep = DEPENDENCY_REGISTRY.get(req.type, {})
            if not dep:
                continue

            try:
                ok = await resolver._check(dep, req)
            except Exception:
                ok = False

            if ok:
                satisfied.append(req.type)
            elif dep.get("blocker") or not req.can_auto_resolve:
                blockers.append((req.type, dep.get("blocker_message", req.blocker_message or "")))
            else:
                resolver_path = dep.get("resolver", "?")
                auto_provisions.append((req.type, resolver_path))

        if satisfied:
            lines.append("## ✓ Already present")
            for t in satisfied:
                lines.append(f"  - {t}")

        if auto_provisions:
            lines.append("\n## ◉ Will auto-provision (no action needed from you)")
            for t, resolver_path in auto_provisions:
                lines.append(f"  - {t} → runs `{resolver_path}`")

        if blockers:
            lines.append("\n## ✗ BLOCKERS (require manual action first)")
            for t, msg in blockers:
                lines.append(f"\n### {t}")
                if msg:
                    for line in msg.strip().split("\n"):
                        lines.append(f"  {line}")

        lines.append("\n## Parameters needed")
        for p in runbook.parameters:
            val = params.get(p.name)
            if val:
                lines.append(f"  ✓ {p.name} = {val}")
            elif p.required:
                lines.append(f"  ✗ {p.name} (REQUIRED): {p.description}")
            else:
                lines.append(f"  - {p.name} (optional, default: {p.default}): {p.description}")

        if not blockers:
            lines.append(f"\n✓ **No blockers.** Ready to run.")
            lines.append(f"\nNext: `run_runbook('{runbook_name}', params, mode='plan')` to preview,")
            lines.append(f"  or: `run_runbook('{runbook_name}', params, mode='implement')` to execute.")
        else:
            lines.append(f"\n✗ **Fix {len(blockers)} blocker(s) before running.**")

        return "\n".join(lines)

    return asyncio.run(_run())


@mcp.tool
def run_runbook(
    runbook_name: str,
    params: dict = {},
    mode: str = "implement",
) -> str:
    """
    Execute an ODH runbook.

    Args:
        runbook_name: Runbook path e.g. 'evalhub/create-evaluation-run',
                      'pipelines/create-pipeline-server', 'cluster/full-stack-setup'
        params: Dictionary of parameters the runbook needs.
                Example: {'project_namespace': 'my-project', 'model_uri': 's3://...'}
        mode: Execution mode:
              - 'plan'      → Preview what would happen (no changes, safe)
              - 'qa'        → Read-only state check (is everything in place?)
              - 'implement' → Execute for real (makes changes to cluster)

    Returns the execution output including any errors and the final result.

    IMPORTANT: Always run 'plan' mode first for new runbooks, then 'implement'.
    """
    try:
        runbook, _ = _load_runbook(runbook_name)
    except ValueError as e:
        return str(e)

    # Fill defaults
    full_params = {}
    for p in runbook.parameters:
        if p.name in params:
            full_params[p.name] = params[p.name]
        elif p.default is not None:
            full_params[p.name] = p.default

    # Check required params
    missing = [p.name for p in runbook.parameters if p.required and p.name not in full_params]
    if missing:
        return (
            f"❌ Missing required parameters: {', '.join(missing)}\n\n"
            f"Required for this runbook:\n"
            + "\n".join(f"  - {p.name}: {p.description}" for p in runbook.parameters if p.required)
        )

    run_mode = {"plan": RunMode.PLAN, "qa": RunMode.QA, "implement": RunMode.IMPLEMENT}.get(
        mode.lower(), RunMode.IMPLEMENT
    )

    cluster = _make_cluster()
    executor = RunbookExecutor(runbook, full_params, cluster, mode=run_mode)

    buf = io.StringIO()
    cap = Console(file=buf, width=100, highlight=False)

    import runner.executor as exec_mod
    import runner.resolver as res_mod
    orig_exec = exec_mod.console
    orig_res = res_mod.console
    exec_mod.console = cap
    res_mod.console = cap

    success = False
    try:
        success = asyncio.run(executor.run())
    except Exception as e:
        cap.print(f"[red]Unexpected error: {e}[/red]")
    finally:
        exec_mod.console = orig_exec
        res_mod.console = orig_res

    output = buf.getvalue()

    # Strip ANSI escape codes for cleaner Claude output
    import re
    output = re.sub(r'\x1b\[[0-9;]*[mK]', '', output)

    status = "✓ SUCCESS" if success else "✗ FAILED/STOPPED"
    return f"**Mode: {mode} | Status: {status}**\n\n```\n{output}\n```"


@mcp.tool
def show_runbook(runbook_name: str) -> str:
    """
    Show the steps and details of a runbook without executing it.

    Args:
        runbook_name: e.g. 'evalhub/create-evaluation-run'

    Returns detailed runbook spec including all steps, parameters, and known-bad-patterns.
    """
    try:
        runbook, path = _load_runbook(runbook_name)
    except ValueError as e:
        return str(e)

    lines = [
        f"# {runbook.name}",
        f"\n{runbook.description}",
        f"\n**Confidence:** {runbook.confidence_overall}",
        f"**Tested on:** {runbook.rhoai_version_tested or 'not yet tested on a real cluster'}",
    ]

    if runbook.parameters:
        lines.append("\n## Parameters")
        for p in runbook.parameters:
            req = "(required)" if p.required else f"default: `{p.default}`"
            lines.append(f"- **{p.name}** {req}: {p.description}")

    lines.append(f"\n## Steps ({len(runbook.steps)})")
    for i, step in enumerate(runbook.steps, 1):
        deps = ", ".join(f"`{r.type}`" for r in step.requires) if step.requires else "none"
        lines.append(f"\n### {i}. `{step.id}` [{step.confidence}]")
        lines.append(f"{step.description}")
        if step.requires:
            lines.append(f"  - **requires:** {deps}")
        lines.append(f"  - **action:** {step.action.type}")

    if runbook.known_bad_patterns:
        lines.append("\n## Guardrails (never done automatically)")
        for p in runbook.known_bad_patterns:
            lines.append(f"- {p}")

    return "\n".join(lines)


@mcp.tool
def guide_runbook(runbook_name: str, known_params: dict = {}) -> str:
    """
    Guide me through a runbook's parameters — explain each one and discover valid values
    from the cluster so I know exactly what to provide.

    Use this when the user doesn't know what values to pass to a runbook.
    It explains each parameter, shows its format, example, and discovers real values
    from the cluster where possible.

    Args:
        runbook_name: e.g. 'evalhub/create-evaluation-run', 'rosa/install-rhoai-prerelease'
        known_params: params the user already knows (e.g. {'project_namespace': 'my-project'})

    Returns a detailed guide for each parameter with discovered options from the cluster.
    """
    try:
        runbook, _ = _load_runbook(runbook_name)
    except ValueError as e:
        return str(e)

    async def _run():
        cluster = _make_cluster()
        lines = [
            f"# Parameter Guide: {runbook_name}\n",
            f"{runbook.description}\n",
            f"---\n",
        ]

        for param in runbook.parameters:
            val = known_params.get(param.name)
            status = f"✓ already set: `{val}`" if val else ("⚠ **required**" if param.required else f"optional (default: `{param.default}`)")
            lines.append(f"\n## `{param.name}` — {status}")
            lines.append(f"{param.description}")

            if param.hint:
                lines.append(f"\n**Hint:** {param.hint}")

            if param.example:
                lines.append(f"\n**Example:** `{param.example}`")

            if param.enum:
                lines.append(f"\n**Valid options:**")
                for opt in param.enum:
                    default_marker = " ← default" if opt == param.default else ""
                    lines.append(f"  - `{opt}`{default_marker}")

            if param.discover_cmd and not val:
                cmd = param.discover_cmd
                for k, v in {**known_params}.items():
                    cmd = cmd.replace(f"{{{k}}}", v)
                try:
                    result = await asyncio.wait_for(cluster.run(cmd), timeout=10.0)
                    if result.ok and result.stdout.strip():
                        discovered = result.stdout.strip().split()
                        lines.append(f"\n**Available on your cluster ({len(discovered)}):**")
                        for d in discovered[:15]:
                            lines.append(f"  - `{d}`")
                        if len(discovered) > 15:
                            lines.append(f"  - *(and {len(discovered)-15} more)*")
                    else:
                        lines.append(f"\n*No values discovered — you'll need to provide one manually.*")
                except Exception:
                    lines.append(f"\n*Could not discover values from cluster.*")

        lines.append(f"\n---\n## How to run\n")
        required_params = [p for p in runbook.parameters if p.required and p.name not in known_params]
        if required_params:
            lines.append(f"Still need: {', '.join(f'`{p.name}`' for p in required_params)}\n")

        lines.append("```bash")
        lines.append(f"# Interactive wizard (recommended):")
        lines.append(f"odh wizard {runbook_name}")
        lines.append("")
        lines.append(f"# Or provide params directly:")
        example_params = " ".join(
            f"-p {p.name}={p.example or p.default or '<value>'}"
            for p in runbook.parameters if p.required
        )
        lines.append(f"odh run {runbook_name} {example_params}")
        lines.append("```")

        return "\n".join(lines)

    return asyncio.run(_run())


@mcp.tool
def search_runbooks(keyword: str) -> str:
    """
    Search for runbooks by keyword. Useful when you know what you want to do
    but don't know the exact runbook name.

    Args:
        keyword: Search term, e.g. "evalhub", "gpu", "mlflow", "pipeline", "model deploy"

    Returns matching runbooks with descriptions.
    """
    keyword_lower = keyword.lower()
    matches = []

    for yaml_file in sorted(RUNBOOKS_DIR.rglob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text())
            name = str(yaml_file.relative_to(RUNBOOKS_DIR)).replace(".yaml", "")
            desc = data.get("description", "").strip()
            tags = data.get("tags", [])

            # Search name, description, and tags
            if (keyword_lower in name.lower() or
                keyword_lower in desc.lower() or
                any(keyword_lower in t for t in tags)):
                confidence = data.get("confidence_overall", "?")
                est = data.get("estimated_minutes")
                time_str = f" (~{est} min)" if est else ""
                matches.append(f"**{name}**{time_str} [{confidence}]\n{desc.split(chr(10))[0][:100]}")
        except Exception:
            pass

    if not matches:
        return (
            f"No runbooks found matching '{keyword}'.\n\n"
            f"Try: list_runbooks() to see all available runbooks.\n"
            f"Or: odh list --workflow to see runbooks grouped by goal."
        )

    return f"Found {len(matches)} runbook(s) matching '{keyword}':\n\n" + "\n\n".join(matches)


@mcp.tool
def get_token_status() -> str:
    """
    Check if the cluster token is valid and show when it expires.
    Helps you know when to re-run `oc login`.

    Returns token validity status and instructions for renewal.
    """
    async def _run():
        cluster = _make_cluster()
        result = await cluster.run("oc whoami 2>&1")
        if result.ok:
            user = result.stdout.strip()
            # Try to get token expiry
            exp_result = await cluster.run(
                "oc get secret -n openshift-authentication -o name 2>/dev/null | head -1"
            )
            return (
                f"✓ Token is valid\n"
                f"Logged in as: {user}\n\n"
                f"Token expiry: OpenShift tokens typically expire in 24 hours.\n"
                f"To renew: `oc login` (or copy login command from OpenShift console → user menu → Copy login command)\n\n"
                f"For non-expiring access, use a service account token:\n"
                f"  oc create sa odh-runbooks -n <namespace>\n"
                f"  oc create token odh-runbooks --duration=87600h  # 10 years\n"
                f"  export OC_TOKEN=<token>  # or set in claude_desktop_config.json env"
            )
        else:
            return (
                f"✗ Not logged in or token expired\n\n"
                f"Error: {result.stderr}\n\n"
                f"To fix:\n"
                f"  oc login https://api.your-cluster.com:6443\n"
                f"  # Or: oc login --token=<token> --server=https://api.your-cluster.com:6443\n\n"
                f"Get your login command from: OpenShift Console → user menu → Copy login command"
            )

    return asyncio.run(_run())


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Handle explicit token via env vars
    oc_server = os.environ.get("OC_SERVER")
    oc_token = os.environ.get("OC_TOKEN") or os.environ.get("OC_SA_TOKEN")

    if oc_server and oc_token:
        # Configure oc to use the explicit token
        import subprocess
        subprocess.run(
            ["oc", "login", f"--server={oc_server}", f"--token={oc_token}", "--insecure-skip-tls-verify=true"],
            capture_output=True
        )

    mcp.run()  # stdio transport — works with Claude Desktop
