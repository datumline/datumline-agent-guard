# datumline-agent-guard

An independent verifier for AI agent work. An agent says a job is `COMPLETED`; `agent-guard` checks the artifacts it claims to have produced and returns a verdict. A completion claim with a missing artifact is reported as `FALSE_DONE`, not as a pass.

Standard library only, no dependencies. It imports nothing from the runtime it audits, so it can contradict that runtime.

## Install

```bash
pip install datumline-agent-guard
```

## CLI

```bash
agent-guard manifest.json          # human-readable receipt
agent-guard manifest.json --json   # machine-readable receipt
```

Exit code is `0` only on `VERIFIED`; every other verdict exits `1` (bad input exits `2`), so it can gate CI or an agent loop.

## Manifest

```json
{
  "job": "WO-123",
  "claimed_status": "COMPLETED",
  "artifacts": [
    {"type": "file", "path": "out/report.md", "min_bytes": 200, "must_contain": ["## Findings"]},
    {"type": "json", "path": "out/feed.json", "required_keys": ["last_marked", "entries"]},
    {"type": "url",  "url": "https://example.com/feed.json", "status": 200, "must_contain": ["last_marked"]},
    {"type": "file", "path": "out/data.parquet", "sha256": "<hex>"}
  ]
}
```

Relative paths resolve against the current working directory.

## Verdicts

| Verdict | Meaning |
|---|---|
| `VERIFIED` | every artifact is present and passes every check |
| `FAILED` | an artifact is present but fails a check, or is absent without a completion claim |
| `FALSE_DONE` | `claimed_status` is COMPLETED / COMPLETE / DONE / VERIFIED and at least one artifact is absent |
| `UNVERIFIABLE` | the manifest asserts no artifacts; fail-closed, never green |

## Library

```python
from datumline_agent_guard import verify, verify_file

receipt = verify({"claimed_status": "COMPLETED", "artifacts": [{"type": "file", "path": "out/report.md"}]})
if receipt["verdict"] != "VERIFIED":
    raise SystemExit(receipt["verdict"])
```

## GitHub Action

Fail a workflow when an agent's "done" doesn't check out:

```yaml
- uses: datumline/datumline-agent-guard@v0.2.0
  with:
    manifest: agent-output/manifest.json   # what the agent claims it produced
    # fail-on: false-done                  # only fail on FALSE_DONE (default: anything but VERIFIED)
```

The step installs this package from the action's own source (no network fetch), writes the receipt to the job summary, sets the `verdict` and `receipt` outputs, and exits non-zero unless the verdict is `VERIFIED`. It needs `python3` 3.9+ on the runner, which GitHub-hosted runners have.

## MCP server

The same verifier as an MCP tool, `verify_completion_claim`, for Claude, ChatGPT, Copilot, Cursor or any MCP client. Standard library only, stdio transport.

```json
{
  "mcpServers": {
    "agent-guard": { "command": "uvx", "args": ["datumline-agent-guard"] }
  }
}
```

Or `pip install datumline-agent-guard` and run `datumline-agent-guard` (alias `agent-guard-mcp`). The tool takes `manifest` (object) or `manifest_path` (string) and returns the receipt; anything other than `"verdict": "VERIFIED"` means not done. It reads the files and fetches the URLs the manifest names, and sends nothing anywhere else.

<!-- mcp-name: io.github.datumline/agent-guard -->

## LangChain

```bash
pip install "datumline-agent-guard[langchain]"
```

```python
from datumline_agent_guard.langchain_tool import AgentGuardTool

tool = AgentGuardTool()  # name: agent_guard_verify
tool.invoke({"manifest": {"claimed_status": "COMPLETED", "artifacts": [{"type": "file", "path": "out/report.md"}]}})
# -> JSON receipt; anything other than "verdict": "VERIFIED" means not done
```

Give it to an agent as a tool, or call it yourself before accepting the agent's "done". It also takes `manifest_path` instead of `manifest`. It passes LangChain's standard tool tests (`langchain-tests`). Requires Python 3.10+; the core package needs only 3.9 and has no dependencies.

## Related

The same verifier ships inside the free, MIT-licensed [Receipted Operator](https://github.com/datumline/receipted-operator) Claude Code plugin, which adds a receipt ledger, truthful statuses and a hook that refuses unreceipted "done". Datumline also publishes paid method kits at [datumlinehq.gumroad.com](https://datumlinehq.gumroad.com).

## License

MIT
