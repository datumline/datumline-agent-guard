import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

from datumline_agent_guard.mcp_server import handle, serve


def rpc(method, params=None, id_=1):
    m = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        m["params"] = params
    return m


class McpServerTests(unittest.TestCase):
    def test_initialize_and_list(self):
        r = handle(rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}))
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", r["result"]["capabilities"])
        self.assertIsNone(handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        tools = handle(rpc("tools/list", id_=2))["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], ["verify_completion_claim"])

    def test_missing_file_is_false_done(self):
        with tempfile.TemporaryDirectory() as d:
            m = {"job": "M1", "claimed_status": "COMPLETED",
                 "artifacts": [{"type": "file", "path": os.path.join(d, "nope.md")}]}
            r = handle(rpc("tools/call", {"name": "verify_completion_claim", "arguments": {"manifest": m}}))
            self.assertFalse(r["result"]["isError"])
            self.assertEqual(r["result"]["structuredContent"]["verdict"], "FALSE_DONE")
            self.assertEqual(json.loads(r["result"]["content"][0]["text"])["verdict"], "FALSE_DONE")

    def test_present_file_is_verified_via_path(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "r.md")
            with open(out, "w") as f:
                f.write("## Findings\n")
            mp = os.path.join(d, "m.json")
            with open(mp, "w") as f:
                json.dump({"claimed_status": "COMPLETED", "artifacts": [{"type": "file", "path": out}]}, f)
            r = handle(rpc("tools/call", {"name": "verify_completion_claim", "arguments": {"manifest_path": mp}}))
            self.assertEqual(r["result"]["structuredContent"]["verdict"], "VERIFIED")

    def test_bad_calls(self):
        r = handle(rpc("tools/call", {"name": "verify_completion_claim", "arguments": {}}))
        self.assertTrue(r["result"]["isError"])
        self.assertEqual(handle(rpc("tools/call", {"name": "other"}))["error"]["code"], -32602)
        self.assertEqual(handle(rpc("nope"))["error"]["code"], -32601)

    def test_stdio_roundtrip_in_subprocess(self):
        lines = [
            rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            rpc("tools/call", {"name": "verify_completion_claim", "arguments": {"manifest": {
                "claimed_status": "DONE", "artifacts": [{"type": "file", "path": "/definitely/not/here.txt"}]}}}, id_=3),
        ]
        p = subprocess.run([sys.executable, "-m", "datumline_agent_guard.mcp_server"],
                           input="\n".join(json.dumps(x) for x in lines) + "\n",
                           capture_output=True, text=True, timeout=30)
        out = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
        self.assertEqual(len(out), 2)  # notification gets no reply
        self.assertEqual(out[1]["result"]["structuredContent"]["verdict"], "FALSE_DONE")


if __name__ == "__main__":
    unittest.main()
