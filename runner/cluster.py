from __future__ import annotations
import asyncio
import json
from typing import Optional


class CommandResult:
    def __init__(self, stdout: str, stderr: str, returncode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.ok = returncode == 0

    def __str__(self):
        return self.stdout if self.ok else self.stderr


class ClusterClient:
    async def run(self, command: str, stdin: Optional[str] = None) -> CommandResult:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin else None,
        )
        stdout, stderr = await proc.communicate(input=stdin.encode() if stdin else None)
        return CommandResult(stdout.decode().strip(), stderr.decode().strip(), proc.returncode)

    async def oc(self, *args: str, dry_run: bool = False) -> CommandResult:
        cmd = "oc " + " ".join(args)
        if dry_run:
            cmd += " --dry-run=server"
        return await self.run(cmd)

    async def apply_manifest(self, manifest: str, dry_run: bool = False) -> CommandResult:
        cmd = "oc apply -f -"
        if dry_run:
            cmd += " --dry-run=server"
        return await self.run(cmd, stdin=manifest)

    async def patch(self, resource: str, patch: str, patch_type: str = "merge", dry_run: bool = False) -> CommandResult:
        cmd = f"oc patch {resource} --type={patch_type} -p '{patch}'"
        if dry_run:
            cmd += " --dry-run=server"
        return await self.run(cmd)

    async def get_token(self) -> str:
        result = await self.run("oc whoami -t")
        if not result.ok:
            raise RuntimeError(f"Could not get cluster token: {result.stderr}")
        return result.stdout

    async def get_dsc_name(self) -> str:
        result = await self.run("oc get dsc --no-headers -o name | head -1")
        return result.stdout.replace(
            "datasciencecluster.datasciencecluster.opendatahub.io/", ""
        )

    async def jsonpath(self, resource: str, path: str) -> str:
        result = await self.oc("get", resource, f"-o=jsonpath='{path}'")
        return result.stdout.strip("'")

    async def wait_for(self, resource: str, condition: str, namespace: str, timeout: str = "300s") -> CommandResult:
        return await self.oc(
            "wait", resource,
            f"-n {namespace}",
            f"--for=condition={condition}",
            f"--timeout={timeout}"
        )
