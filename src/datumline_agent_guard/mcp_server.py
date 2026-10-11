"""
MCP server (stdio) for datumline-agent-guard. Standard library only.

Exposes one tool, ``verify_completion_claim``: give it the manifest an agent
claims to have satisfied (or a path to one) and it returns the independent
receipt: VERIFIED, FAILED, FALSE_DONE or UNVERIFIABLE.

Run:  datumline-agent-guard          (console script; what `uvx datumline-agent-guard` starts)
      python -m datumline_agent_guard.mcp_server

What it touches: it reads the files the manifest names, and fetches the URLs
the manifest names (HTTP GET, 20 s timeout). It sends nothing anywhere else and
writes nothing.
"""
import json
import sys

from . import __version__
from .core import verify, verify_file

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

TOOL = {
    "name": "verify_completion_claim",
    "title": "Verify an agent's completion claim",
    "description": (
        "Check an AI agent's claim that a job is done against the artifacts it says it produced. "
        "Returns a JSON receipt whose 'verdict' is VERIFIED (every artifact present and passing), "
        "FAILED (an artifact fails a check), FALSE_DONE (the job is claimed COMPLETED/DONE but an "
        "artifact is missing) or UNVERIFIABLE (the manifest names no artifacts). Treat anything other "
        "than VERIFIED as not done. Artifact types: file (path, min_bytes, min_lines, must_contain, sha256), "
        "json (path, required_keys), url (url, status, must_contain). Relative paths resolve against the "
        "server's working directory."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "manifest": {
                "type": "object",
                "description": "Manifest: {job, claimed_status, artifacts:[{type, path|url, ...checks}]}",
            },
            "manifest_path": {
                "type": "string",
                "description": "Path to a manifest JSON file, instead of passing 'manifest'.",
            },
        },
    },
    "annotations": {"readOnlyHint": True, "openWorldHint": True},
}


def _result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _call_tool(params):
    if params.get("name") != TOOL["name"]:
        return None
    args = params.get("arguments") or {}
    try:
        if isinstance(args.get("manifest"), dict):
            receipt = verify(args["manifest"])
        elif isinstance(args.get("manifest_path"), str):
            receipt = verify_file(args["manifest_path"])
        else:
            return {
                "content": [{"type": "text", "text": "Provide 'manifest' (object) or 'manifest_path' (string)."}],
                "isError": True,
            }
    except (OSError, ValueError) as e:
        return {"content": [{"type": "text", "text": f"Cannot read manifest: {e}"}], "isError": True}
    return {
        "content": [{"type": "text", "text": json.dumps(receipt, indent=2)}],
        "structuredContent": receipt,
        "isError": False,
    }


def handle(msg):
    """Handle one JSON-RPC message. Returns a response dict, or None for notifications."""
    if not isinstance(msg, dict):
        return _error(None, -32600, "Invalid Request")
    method = msg.get("method")
    req_id = msg.get("id")
    is_notification = "id" not in msg
    params = msg.get("params") or {}

    if method == "initialize":
        asked = params.get("protocolVersion")
        version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return _result(req_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "datumline-agent-guard", "title": "Datumline Agent Guard", "version": __version__},
            "instructions": "Call verify_completion_claim before accepting any agent's 'done'.",
        })
    if is_notification:
        return None
    if method == "ping":
        return _result(req_id, {})
    if method == "tools/list":
        return _result(req_id, {"tools": [TOOL]})
    if method == "tools/call":
        out = _call_tool(params)
        if out is None:
            return _error(req_id, -32602, f"Unknown tool: {params.get('name')!r}")
        return _result(req_id, out)
    return _error(req_id, -32601, f"Method not found: {method!r}")


def serve(stdin=None, stdout=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            resp = _error(None, -32700, "Parse error")
        else:
            resp = handle(msg)
        if resp is not None:
            stdout.write(json.dumps(resp) + "\n")
            stdout.flush()


def main():
    serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
