"""LangChain tool wrapper. Requires the extra: pip install "datumline-agent-guard[langchain]"."""
import json
from typing import Any, Dict, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .core import verify, verify_file


class AgentGuardInput(BaseModel):
    manifest: Optional[Dict[str, Any]] = Field(
        default=None,
        description='Manifest object: {"job": ..., "claimed_status": "COMPLETED", "artifacts": [...]}. '
        'Artifact types: file (path, min_bytes, must_contain, sha256), json (path, required_keys), url (url, status, must_contain).',
    )
    manifest_path: Optional[str] = Field(default=None, description="Path to a manifest JSON file, used if manifest is not given.")


class AgentGuardTool(BaseTool):
    """Check a completion claim against the artifacts it names.

    Returns the receipt as JSON. verdict is VERIFIED, FAILED, FALSE_DONE
    (claimed done but an artifact is missing) or UNVERIFIABLE (nothing asserted).
    """

    name: str = "agent_guard_verify"
    description: str = (
        "Verify that a task claimed as done actually produced its artifacts (files, JSON files, URLs). "
        "Returns a JSON receipt whose verdict is VERIFIED, FAILED, FALSE_DONE or UNVERIFIABLE. "
        "Treat anything other than VERIFIED as not done."
    )
    args_schema: Type[BaseModel] = AgentGuardInput

    def _run(self, manifest: Optional[Dict[str, Any]] = None, manifest_path: Optional[str] = None, **kwargs: Any) -> str:
        if manifest is None and manifest_path:
            receipt = verify_file(manifest_path)
        else:
            receipt = verify(manifest or {})
        return json.dumps(receipt)
