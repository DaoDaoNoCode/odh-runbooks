from __future__ import annotations
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Confidence(str, Enum):
    VERIFIED = "verified"       # tested on real cluster — executes automatically
    DOC_DERIVED = "doc-derived" # direct from CRD spec/official docs — dry-run gate
    INFERRED = "inferred"       # derived from ADRs/code — warns before each step
    UNCERTAIN = "uncertain"     # best guess — hard stops and asks user


class OnFail(str, Enum):
    STOP = "STOP"
    RETRY_ONCE = "RETRY_ONCE"
    ASK_USER = "ASK_USER"


class IfAlreadyTrue(str, Enum):
    SKIP = "skip"
    REAPPLY = "re-apply"
    FAIL = "fail"


class Check(BaseModel):
    command: Optional[str] = None
    expected: Optional[str] = None
    expected_min: Optional[int] = None
    assert_expr: Optional[str] = Field(None, alias="assert")
    if_already_true: IfAlreadyTrue = IfAlreadyTrue.SKIP
    timeout: str = "30s"
    poll_interval: str = "5s"
    on_fail: OnFail = OnFail.STOP

    model_config = {"populate_by_name": True}


class Action(BaseModel):
    type: Literal["create", "patch", "apply", "delete", "wait", "query", "api_call", "poll", "none"]
    command: Optional[str] = None
    target: Optional[str] = None
    manifest: Optional[str] = None
    patch: Optional[str] = None
    patch_type: str = "merge"
    dry_run: bool = False
    store_as: Optional[str] = None
    method: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    body: Optional[str] = None
    store_response_as: Optional[str] = None
    until: Optional[str] = None
    timeout: Optional[str] = None
    poll_interval: Optional[str] = None


class Requirement(BaseModel):
    """
    Declares a dependency that must exist before this step runs.
    If missing, the executor looks up a resolver runbook and runs it first.
    """
    type: str                              # e.g. "s3-connection", "namespace", "gpu-available"
    namespace: Optional[str] = None       # scope (templated)
    name: Optional[str] = None            # specific resource name (templated)
    params: Optional[dict] = None         # extra params passed to resolver
    can_auto_resolve: bool = True         # False = blocker, executor stops with clear message
    blocker_message: Optional[str] = None # shown when can_auto_resolve=False


class Step(BaseModel):
    id: str
    confidence: Confidence
    description: str
    requires: list[Requirement] = []      # dependencies checked and auto-resolved
    pre_check: Optional[Check] = None
    action: Action
    post_check: Optional[Check] = None
    rollback: Optional[str] = None
    return_value: Optional[str] = Field(None, alias="return")
    # UX guidance fields
    on_fail_hint: Optional[str] = None   # Human-readable recovery hint shown when this step fails
    estimated_seconds: Optional[int] = None  # Shown as "this may take ~N minutes"

    model_config = {"populate_by_name": True}


class Parameter(BaseModel):
    name: str
    description: str
    required: bool = False
    default: Optional[str] = None
    # Guidance fields — shown in wizard mode
    example: Optional[str] = None        # concrete example value
    hint: Optional[str] = None           # where to find this / format note
    discover_cmd: Optional[str] = None   # oc command to list valid values (may use {param} substitution)
    enum: Optional[list[str]] = None     # valid options if constrained to a list


class Runbook(BaseModel):
    name: str
    description: str
    rhoai_version_tested: Optional[str] = None
    confidence_overall: Confidence
    parameters: list[Parameter] = []
    steps: list[Step] = []
    known_bad_patterns: list[str] = []
    rollback_order: list[str] = []
    # UX guidance fields
    tags: list[str] = []                # e.g. ["setup", "gpu", "beginner"]
    estimated_minutes: Optional[int] = None   # Total time estimate for the whole runbook
    next_steps: list[str] = []          # Suggested runbooks/commands to run after this one
