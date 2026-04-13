"""
Dependency resolver — checks requirements and auto-provisions missing dependencies.

When a step declares `requires: [{type: s3-connection, namespace: ...}]`, the
resolver:
1. Checks if the dependency already exists (fast path — skip)
2. If missing: looks up the resolver runbook for that dependency type
3. Runs the resolver runbook (which itself uses the full executor with protections)
4. Re-checks — if still missing after resolver ran, that's a blocker → STOP

Blockers (can_auto_resolve: false or resolver: None):
  - gpu-available: cannot create GPU nodes automatically
  - storage-class:  cannot install a storage provisioner automatically
  - dsc-exists:    cannot install ODH operator automatically
  - openshift-cluster: cannot log in automatically

Everything else auto-resolves along the happy path.
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import yaml
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel

from .schema import Requirement, Runbook

if TYPE_CHECKING:
    from .cluster import ClusterClient

console = Console()

RUNBOOKS_DIR = Path(__file__).parent.parent / "runbooks"


def _detect_odh_namespace_cmd() -> str:
    """Shell command that detects whether this is ODH or RHOAI and returns the namespace."""
    return (
        "oc get namespace redhat-ods-applications --no-headers 2>/dev/null | grep -q . "
        "&& echo 'redhat-ods-applications' || echo 'opendatahub'"
    )


# ── Dependency type registry ──────────────────────────────────────────────────
DEPENDENCY_REGISTRY: dict[str, dict] = {

    # ── Cluster access ────────────────────────────────────────────────────────
    "openshift-cluster": {
        "check": "oc whoami 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": None,
        "blocker": True,
        "blocker_message": (
            "Not logged into an OpenShift cluster.\n"
            "Run:  oc login https://api.your-cluster.com:6443\n"
            "      oc login --token=<token> --server=https://api.your-cluster.com:6443"
        ),
    },

    # ── ODH operator ─────────────────────────────────────────────────────────
    "dsc-exists": {
        "check": "oc get dsc --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": None,
        "blocker": True,
        "blocker_message": (
            "No DataScienceCluster found. ODH/RHOAI operator must be installed first.\n\n"
            "Install via OperatorHub:\n"
            "  OpenShift AI (RHOAI): search 'Red Hat OpenShift AI' in OperatorHub\n"
            "  Open Data Hub (ODH):  search 'Open Data Hub' in OperatorHub\n\n"
            "Then create a DataScienceCluster CR to deploy components."
        ),
    },

    # ── Storage ───────────────────────────────────────────────────────────────
    "storage-class": {
        "check": "oc get storageclass --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": None,
        "blocker": True,
        "blocker_message": (
            "No StorageClass found. A storage provisioner is required.\n\n"
            "Common options:\n"
            "  AWS:   EBS CSI driver (built into ROSA/OSD)\n"
            "  GCP:   Persistent Disk CSI driver\n"
            "  Azure: Azure Disk CSI driver\n"
            "  Local: NFS provisioner or local-path-provisioner\n"
            "  Ceph:  Rook-Ceph operator\n\n"
            "Contact your cluster admin."
        ),
    },

    # ── Namespace ─────────────────────────────────────────────────────────────
    "namespace": {
        "check": "oc get namespace {{ name }} --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": "projects/create-project",
        "resolver_params": lambda req, ctx: {
            "project_name": req.name or ctx.get("project_namespace", "odh-dev"),
            "display_name": req.name or ctx.get("project_namespace", "odh-dev"),
        },
        "blocker": False,
    },

    # ── S3 storage ────────────────────────────────────────────────────────────
    "s3-connection": {
        "check": (
            "oc get secret -n {namespace} "
            "-l opendatahub.io/connection-type=s3 "
            "--no-headers 2>/dev/null | wc -l | tr -d ' '"
        ),
        "expected_min": 1,
        "resolver": "dependencies/provision-s3-connection",
        "resolver_params": lambda req, ctx: {
            "project_namespace": req.namespace or ctx.get("project_namespace", ""),
        },
        "blocker": False,
    },

    # ── ODH components ────────────────────────────────────────────────────────
    "dsp-enabled": {
        "check": (
            "oc get dsc -o jsonpath='"
            "{.items[0].spec.components.datasciencepipelines.managementState}'"
            " 2>/dev/null"
        ),
        "expected": "Managed",
        "resolver": "cluster/enable-pipelines",
        "resolver_params": lambda req, ctx: {},
        "blocker": False,
    },
    "kserve-enabled": {
        "check": "oc get crd inferenceservices.serving.kserve.io --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": "cluster/enable-kserve",
        "resolver_params": lambda req, ctx: {},
        "blocker": False,
    },
    "trustyai-enabled": {
        "check": (
            "oc get dsc -o jsonpath="
            "'{.items[0].spec.components.trustyai.managementState}'"
            " 2>/dev/null"
        ),
        "expected": "Managed",
        "resolver": "cluster/enable-trustyai",
        "resolver_params": lambda req, ctx: {},
        "blocker": False,
    },
    "model-registry-enabled": {
        "check": "oc get crd modelregistries.modelregistry.opendatahub.io --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": "cluster/enable-model-registry",
        "resolver_params": lambda req, ctx: {},
        "blocker": False,
    },
    "training-operator-enabled": {
        "check": "oc get crd pytorchjobs.kubeflow.org --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": "cluster/enable-training-operator",
        "resolver_params": lambda req, ctx: {},
        "blocker": False,
    },
    "feast-enabled": {
        "check": "oc get crd featurestores.feast.dev --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": "cluster/enable-feature-store",
        "resolver_params": lambda req, ctx: {
            "project_namespace": req.namespace or ctx.get("project_namespace", ""),
        },
        "blocker": False,
    },
    "codeflare-enabled": {
        "check": "oc get crd rayclusters.ray.io --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": "cluster/enable-codeflare",
        "resolver_params": lambda req, ctx: {},
        "blocker": False,
    },

    # ── Project-level services ─────────────────────────────────────────────────
    "pipeline-server": {
        "check": "oc get dspa -n {{ namespace }} --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": "dependencies/provision-pipeline-server",
        "resolver_params": lambda req, ctx: {
            "project_namespace": req.namespace or ctx.get("project_namespace", ""),
        },
        "blocker": False,
    },
    "model-registry-instance": {
        "check": "oc get modelregistry -n odh-model-registries --no-headers 2>/dev/null | wc -l | tr -d ' '",
        "expected_min": 1,
        "resolver": "model-registry/enable-registry",
        "resolver_params": lambda req, ctx: {},
        "blocker": False,
    },
    "mlflow-server": {
        # MLflow operator deploys the server in the ODH namespace (redhat-ods-applications or opendatahub)
        # NOT in the user project namespace. Check for the MLflow CR and/or pod.
        "check": (
            "oc get mlflow mlflow --no-headers 2>/dev/null | wc -l | tr -d ' '"
        ),
        "expected_min": 1,
        "resolver": "mlflow/enable-mlflow",
        "resolver_params": lambda req, ctx: {
            "project_namespace": req.namespace or ctx.get("project_namespace", ""),
        },
        "blocker": False,
    },

    # ── GPU — blockers (cannot auto-provision hardware) ───────────────────────
    "gpu-available": {
        "check": (
            "oc get nodes "
            "-o jsonpath='{.items[*].status.allocatable.nvidia\\.com/gpu}' "
            "| tr ' ' '\\n' | grep -v '^0$' | grep -v '^$' | wc -l | tr -d ' '"
        ),
        "expected_min": 1,
        "resolver": None,
        "blocker": True,
        "blocker_message": (
            "GPU nodes required but none found.\n\n"
            "Add GPU nodes first:\n"
            "  ROSA/OSD: odh run gpu/add-gpu-node-ocm -p cluster_name=<name>\n"
            "  Self-managed: add GPU machine sets via oc or OpenShift console\n\n"
            "After nodes join, install the GPU Operator:\n"
            "  odh run gpu/install-gpu-operator"
        ),
    },
    "gpu-operator-installed": {
        "check": "oc get clusterpolicy -n nvidia-gpu-operator --no-headers 2>/dev/null | grep -c ready || echo 0",
        "expected_min": 1,
        "resolver": "gpu/install-gpu-operator",
        "resolver_params": lambda req, ctx: {},
        "blocker": False,
    },
}


class DependencyResult:
    def __init__(self, satisfied: bool, message: str = ""):
        self.satisfied = satisfied
        self.message = message


class DependencyResolver:
    def __init__(self, cluster, context: dict, params: dict):
        self.cluster = cluster
        self.context = context
        self.params = params

    def _render(self, text: str, req: Requirement) -> str:
        # req.name and req.namespace may themselves be Jinja2 templates
        # e.g. name: "{{ project_namespace }}" — render them first with params
        base_vars = {**self.params, **self.context}
        try:
            rendered_name = Template(req.name or "").render(**base_vars)
        except Exception:
            rendered_name = req.name or ""
        try:
            rendered_namespace = Template(req.namespace or "").render(**base_vars)
        except Exception:
            rendered_namespace = req.namespace or ""

        all_vars = {
            **base_vars,
            "namespace": rendered_namespace or self.params.get("project_namespace", ""),
            "name": rendered_name,
        }
        try:
            return Template(text).render(**all_vars)
        except Exception:
            return text

    async def _check(self, dep: dict, req: Requirement) -> bool:
        cmd = self._render(dep["check"], req)
        result = await self.cluster.run(cmd)
        actual = result.stdout.strip().strip("'")

        if "expected_min" in dep:
            try:
                return int(actual) >= dep["expected_min"]
            except ValueError:
                return False
        elif "expected" in dep:
            return actual == dep["expected"]
        return result.ok

    async def resolve_all(self, requirements: list[Requirement]) -> DependencyResult:
        for req in requirements:
            result = await self._resolve_one(req)
            if not result.satisfied:
                return result
        return DependencyResult(satisfied=True)

    async def _resolve_one(self, req: Requirement) -> DependencyResult:
        dep = DEPENDENCY_REGISTRY.get(req.type)
        if not dep:
            console.print(f"  [yellow]⚠ Unknown dependency type '{req.type}' — skipping[/yellow]")
            return DependencyResult(satisfied=True)

        # Fast path: already satisfied
        if await self._check(dep, req):
            console.print(f"  [dim]✓ {req.type}: present[/dim]")
            return DependencyResult(satisfied=True)

        # Explicit override on the requirement
        if not req.can_auto_resolve:
            msg = req.blocker_message or f"Required dependency '{req.type}' is missing and marked as non-auto-resolvable."
            return DependencyResult(satisfied=False, message=msg)

        # Registry-level blocker
        if dep.get("blocker"):
            return DependencyResult(
                satisfied=False,
                message=dep.get("blocker_message", f"'{req.type}' is missing and cannot be auto-provisioned.")
            )

        resolver_path = dep.get("resolver")
        if not resolver_path:
            return DependencyResult(
                satisfied=False,
                message=f"'{req.type}' is missing and has no resolver configured."
            )

        console.print(Panel(
            f"[yellow]Missing dependency: [bold]{req.type}[/bold][/yellow]\n\n"
            f"Auto-provisioning via: [cyan]{resolver_path}[/cyan]",
            title="[yellow]→ Auto-resolving[/yellow]",
            border_style="yellow"
        ))

        success = await self._run_resolver(dep, req, resolver_path)
        if not success:
            return DependencyResult(
                satisfied=False,
                message=f"Resolver '{resolver_path}' failed to provision '{req.type}'. See output above."
            )

        # Verify resolver worked
        if not await self._check(dep, req):
            return DependencyResult(
                satisfied=False,
                message=(
                    f"Resolver '{resolver_path}' completed but '{req.type}' is still missing.\n"
                    "Check the resolver output above for details."
                )
            )

        console.print(f"  [green]✓ {req.type}: auto-provisioned[/green]")
        return DependencyResult(satisfied=True)

    async def _run_resolver(self, dep: dict, req: Requirement, resolver_path: str) -> bool:
        from .executor import RunbookExecutor

        yaml_path = RUNBOOKS_DIR / f"{resolver_path}.yaml"
        if not yaml_path.exists():
            console.print(f"  [red]Resolver not found: {yaml_path}[/red]")
            return False

        runbook = Runbook.model_validate(yaml.safe_load(yaml_path.read_text()))

        resolver_params_fn = dep.get("resolver_params")
        extra_params = resolver_params_fn(req, {**self.params, **self.context}) if resolver_params_fn else {}

        resolver_params = {**self.params, **extra_params}
        for param in runbook.parameters:
            if param.name not in resolver_params and param.default is not None:
                resolver_params[param.name] = param.default

        executor = RunbookExecutor(runbook, resolver_params, self.cluster)
        return await executor.run()
