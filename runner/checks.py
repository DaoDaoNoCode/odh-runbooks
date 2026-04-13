from __future__ import annotations
import asyncio
import re
from typing import Callable, Optional
from .schema import Check, OnFail
from .cluster import ClusterClient


class CheckResult:
    def __init__(self, passed: bool, actual: str = "", error: str = ""):
        self.passed = passed
        self.actual = actual
        self.error = error


class CheckRunner:
    def __init__(self, cluster: ClusterClient, context: dict, params: dict):
        self.cluster = cluster
        self.context = context
        self.params = params

    async def run(self, check: Check, render: Callable[[str], str]) -> CheckResult:
        """Run a single check. Returns CheckResult."""
        if not check.command:
            return CheckResult(passed=True)

        cmd = render(check.command)
        result = await self.cluster.run(cmd)
        actual = result.stdout.strip()

        if check.expected is not None:
            passed = actual == render(check.expected)
        elif check.expected_min is not None:
            try:
                passed = int(actual) >= check.expected_min
            except ValueError:
                passed = False
        elif check.assert_expr:
            # Simple assert: evaluate expression against context + params
            passed = self._eval_assert(render(check.assert_expr), actual)
        else:
            passed = result.ok

        return CheckResult(passed=passed, actual=actual, error=result.stderr)

    async def poll_until(self, check: Check, render: Callable[[str], str]) -> CheckResult:
        """Poll a check until it passes or times out."""
        timeout_secs = self._parse_duration(check.timeout)
        interval_secs = self._parse_duration(check.poll_interval)
        elapsed = 0.0

        while elapsed < timeout_secs:
            result = await self.run(check, render)
            if result.passed:
                return result
            await asyncio.sleep(interval_secs)
            elapsed += interval_secs

        # Final attempt
        result = await self.run(check, render)
        if not result.passed:
            result.error = f"Timed out after {check.timeout}. Last value: {result.actual}"
        return result

    def _eval_assert(self, expr: str, actual: str) -> bool:
        """Evaluate simple assert expressions like 'value is not empty'."""
        expr = expr.strip()
        if "is not empty" in expr:
            var_name = expr.split("is not empty")[0].strip()
            value = self.context.get(var_name, self.params.get(var_name, actual))
            return bool(value and str(value).strip())
        if "==" in expr:
            parts = expr.split("==")
            left = self.context.get(parts[0].strip(), parts[0].strip())
            right = parts[1].strip().strip("'\"")
            return str(left) == right
        if "in [" in expr:
            match = re.match(r"(.+?)\s+in\s+\[(.+)\]", expr)
            if match:
                var = self.context.get(match.group(1).strip(), match.group(1).strip())
                values = [v.strip().strip("'\"") for v in match.group(2).split(",")]
                return str(var) in values
        return bool(actual)

    def _parse_duration(self, duration: str) -> float:
        """Parse '300s', '5m', '1h' to seconds."""
        duration = duration.strip()
        if duration.endswith("s"):
            return float(duration[:-1])
        if duration.endswith("m"):
            return float(duration[:-1]) * 60
        if duration.endswith("h"):
            return float(duration[:-1]) * 3600
        return float(duration)
