"""Independent verifier for AI agent completion claims.

    from datumline_agent_guard import verify
    receipt = verify({"claimed_status": "COMPLETED", "artifacts": [...]})
    receipt["verdict"]  # VERIFIED | FAILED | FALSE_DONE | UNVERIFIABLE
"""
from .core import DONE_WORDS, verify, verify_file

__all__ = ["DONE_WORDS", "verify", "verify_file", "VERDICTS", "__version__"]
__version__ = "0.1.0"
VERDICTS = ("VERIFIED", "FAILED", "FALSE_DONE", "UNVERIFIABLE")
