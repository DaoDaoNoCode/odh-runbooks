"""
Runbook Generator — uses Claude + RAG to draft runbooks for any ODH component.

Usage:
    generator = RunbookGenerator(anthropic_client, rag_client)
    yaml_str = await generator.generate("genai", "enable chat playground")
    # Returns YAML runbook draft with all steps marked 'inferred'
    # Human reviews, tests on cluster, promotes confidence levels to 'doc-derived'/'verified'
"""
from __future__ import annotations
import anthropic
import yaml

SYSTEM_PROMPT = """You are an ODH/RHOAI runbook expert. You generate runbooks that drive an executor.

CRITICAL RULES — every single one is non-negotiable:
1. Every step MUST have both pre_check and post_check
2. Every step that creates/modifies a K8s resource MUST have dry_run: true
3. post_check.on_fail is ALWAYS "STOP" — never RETRY, never IMPROVISE
4. Mark confidence as "doc-derived" only when you have the exact CRD spec from docs
5. Mark confidence as "inferred" for anything you reasoned about
6. NEVER use "verified" — only humans can promote to verified after real cluster testing
7. Include known_bad_patterns listing common mistakes for this component
8. The rollback_order lists resources in reverse creation order
9. Use Jinja2 template syntax {{ param_name }} for all variable references
10. pre_check.if_already_true: "skip" for idempotency on every create step

Output ONLY valid YAML matching this schema exactly. No prose, no markdown fences.

Schema:
  name: string
  description: string
  rhoai_version_tested: null
  confidence_overall: inferred
  parameters:
    - name: string
      description: string
      required: bool
      default: string | null
  steps:
    - id: snake_case_string
      confidence: doc-derived | inferred | uncertain
      description: string
      pre_check:
        command: string   # oc/shell command to check current state
        expected: string  # exact expected output
        if_already_true: skip
        timeout: "30s"
        on_fail: STOP
      action:
        type: create | patch | apply | query | wait | api_call | poll | none
        manifest: |   # for create/apply
          yaml here
        dry_run: true   # always true for k8s mutations
        store_as: variable_name   # optional, stores stdout
        # for api_call:
        method: POST
        url: string
        headers: {}
        body: |
          json here
        store_response_as: variable_name
      post_check:
        command: string
        expected: string
        timeout: "300s"
        poll_interval: "10s"
        on_fail: STOP
      rollback: "oc delete ..."
      return: |   # only on the LAST step
        Summary of what was created and URLs
  known_bad_patterns:
    - "never do X because Y"
  rollback_order:
    - "oc delete resource/name -n namespace"
"""


class RunbookGenerator:
    def __init__(self, client: anthropic.Anthropic, rag_client=None):
        self.client = client
        self.rag = rag_client

    async def generate(self, component: str, task: str) -> str:
        """
        Generate a runbook YAML draft for a given component and task.
        All steps will be marked 'inferred' — human must verify before promoting.
        """
        context = ""
        if self.rag:
            docs = await self.rag.search(f"{component} {task} setup configuration")
            crd_specs = await self.rag.search(f"{component} CRD apiVersion kind spec fields")
            rbac = await self.rag.search(f"{component} RBAC service account namespace")
            context = f"\n\nAvailable documentation:\n\n{docs}\n\nCRD Specs:\n{crd_specs}\n\nRBAC:\n{rbac}"

        response = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=8000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Generate a runbook for: {task} ({component})\n"
                    f"{context}\n\n"
                    f"Remember: all steps must be 'inferred' unless you have the exact CRD spec. "
                    f"Never mark anything 'verified'. Include all known_bad_patterns for {component}."
                )
            }]
        )

        return next(b.text for b in response.content if b.type == "text")

    def validate_yaml(self, yaml_str: str) -> tuple[bool, str]:
        """Basic structural validation of a generated runbook."""
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            return False, f"Invalid YAML: {e}"

        required_top = ["name", "description", "steps", "confidence_overall"]
        for field in required_top:
            if field not in data:
                return False, f"Missing required field: {field}"

        for i, step in enumerate(data.get("steps", [])):
            if "id" not in step:
                return False, f"Step {i} missing 'id'"
            if "confidence" not in step:
                return False, f"Step {step.get('id', i)} missing 'confidence'"
            if "action" not in step:
                return False, f"Step {step.get('id', i)} missing 'action'"
            if step.get("confidence") == "verified":
                return False, f"Step {step['id']} marked 'verified' — only humans can do this after real cluster testing"

        return True, "ok"
