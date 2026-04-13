from __future__ import annotations
import asyncio
import json
from typing import Callable, Any
import httpx
from .schema import Action
from .cluster import ClusterClient


class ActionResult:
    def __init__(self, success: bool, output: Any = None, error: str = ""):
        self.success = success
        self.output = output
        self.error = error


class ActionRunner:
    def __init__(self, cluster: ClusterClient, context: dict, params: dict):
        self.cluster = cluster
        self.context = context
        self.params = params

    async def run(self, action: Action, render: Callable[[str], str]) -> ActionResult:
        handler = {
            "none":     self._none,
            "query":    self._query,
            "create":   self._apply,
            "apply":    self._apply,
            "patch":    self._patch,
            "delete":   self._delete,
            "wait":     self._wait,
            "api_call": self._api_call,
            "poll":     self._poll,
        }.get(action.type)

        if not handler:
            return ActionResult(False, error=f"Unknown action type: {action.type}")

        try:
            return await handler(action, render)
        except Exception as e:
            return ActionResult(False, error=str(e))

    async def _none(self, action: Action, render: Callable) -> ActionResult:
        return ActionResult(True)

    async def _query(self, action: Action, render: Callable) -> ActionResult:
        cmd = render(action.command)
        result = await self.cluster.run(cmd)
        if not result.ok:
            return ActionResult(False, error=result.stderr)
        return ActionResult(True, output=result.stdout)

    async def _apply(self, action: Action, render: Callable) -> ActionResult:
        if action.manifest:
            manifest = render(action.manifest)
            result = await self.cluster.apply_manifest(manifest, dry_run=False)
        elif action.command:
            result = await self.cluster.run(render(action.command))
        else:
            return ActionResult(False, error="apply action needs manifest or command")

        if not result.ok:
            return ActionResult(False, error=result.stderr)
        return ActionResult(True, output=result.stdout)

    async def _patch(self, action: Action, render: Callable) -> ActionResult:
        target = render(action.target or "")
        patch = render(action.patch or "{}")
        result = await self.cluster.patch(target, patch, action.patch_type)
        if not result.ok:
            return ActionResult(False, error=result.stderr)
        return ActionResult(True, output=result.stdout)

    async def _delete(self, action: Action, render: Callable) -> ActionResult:
        cmd = render(action.command)
        result = await self.cluster.run(cmd)
        if not result.ok:
            return ActionResult(False, error=result.stderr)
        return ActionResult(True)

    async def _wait(self, action: Action, render: Callable) -> ActionResult:
        cmd = render(action.command)
        result = await self.cluster.run(cmd)
        if not result.ok:
            return ActionResult(False, error=result.stderr)
        return ActionResult(True)

    async def _api_call(self, action: Action, render: Callable) -> ActionResult:
        url = render(action.url or "")
        method = (action.method or "GET").upper()
        headers = {k: render(v) for k, v in (action.headers or {}).items()}
        body = render(action.body or "") if action.body else None

        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.request(
                method, url,
                headers=headers,
                content=body.encode() if body else None,
                timeout=30.0
            )
            if resp.status_code >= 400:
                return ActionResult(
                    False,
                    error=f"HTTP {resp.status_code}: {resp.text[:500]}"
                )
            try:
                output = resp.json()
            except Exception:
                output = resp.text
            return ActionResult(True, output=output)

    async def _poll(self, action: Action, render: Callable) -> ActionResult:
        """Poll an API endpoint until a condition is met."""
        url = render(action.url or "")
        headers = {k: render(v) for k, v in (action.headers or {}).items()}
        until_expr = action.until or ""
        timeout_secs = self._parse_duration(action.timeout or "1800s")
        interval_secs = self._parse_duration(action.poll_interval or "30s")
        elapsed = 0.0

        async with httpx.AsyncClient(verify=False) as client:
            while elapsed < timeout_secs:
                resp = await client.get(url, headers=headers, timeout=30.0)
                if resp.status_code < 400:
                    data = resp.json()
                    if self._eval_until(until_expr, data):
                        return ActionResult(True, output=data)
                await asyncio.sleep(interval_secs)
                elapsed += interval_secs

        return ActionResult(False, error=f"Polling timed out after {action.timeout}")

    def _eval_until(self, expr: str, data: dict) -> bool:
        """Evaluate a 'until' condition against response data."""
        # e.g. "response.status.state in ['completed', 'failed', 'cancelled']"
        expr = expr.replace("response.", "")
        try:
            # Navigate nested keys: status.state → data["status"]["state"]
            import re
            match = re.match(r"(.+?)\s+in\s+\[(.+)\]", expr)
            if match:
                key_path = match.group(1).strip()
                values = [v.strip().strip("'\"") for v in match.group(2).split(",")]
                value = data
                for k in key_path.split("."):
                    value = value.get(k, {})
                return str(value) in values
        except Exception:
            pass
        return False

    def _parse_duration(self, duration: str) -> float:
        duration = duration.strip()
        if duration.endswith("s"):
            return float(duration[:-1])
        if duration.endswith("m"):
            return float(duration[:-1]) * 60
        if duration.endswith("h"):
            return float(duration[:-1]) * 3600
        return float(duration)
