import json
import os
import tempfile
import unittest

try:
    import langchain_core  # noqa: F401
except ImportError:  # the extra is optional; core tests must pass without it
    langchain_core = None


@unittest.skipIf(langchain_core is None, "langchain extra not installed")
class AgentGuardToolTests(unittest.TestCase):
    def setUp(self):
        from datumline_agent_guard.langchain_tool import AgentGuardTool
        self.tool = AgentGuardTool()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **kwargs):
        return json.loads(self.tool.invoke(kwargs))

    def test_true_claim_is_verified(self):
        out = os.path.join(self.tmp.name, "report.md")
        with open(out, "w") as f:
            f.write("## Findings\n")
        r = self._run(manifest={"claimed_status": "COMPLETED", "artifacts": [{"type": "file", "path": out}]})
        self.assertEqual(r["verdict"], "VERIFIED")

    def test_missing_file_with_completed_is_false_done(self):
        m = {"claimed_status": "COMPLETED",
             "artifacts": [{"type": "file", "path": os.path.join(self.tmp.name, "nope.md")}]}
        self.assertEqual(self._run(manifest=m)["verdict"], "FALSE_DONE")

    def test_manifest_path(self):
        p = os.path.join(self.tmp.name, "m.json")
        with open(p, "w") as f:
            json.dump({"claimed_status": "DONE", "artifacts": []}, f)
        self.assertEqual(self._run(manifest_path=p)["verdict"], "UNVERIFIABLE")

    def test_no_input_is_unverifiable_not_an_error(self):
        self.assertEqual(self._run()["verdict"], "UNVERIFIABLE")

    def test_output_never_advertises(self):
        out = self.tool.invoke({"manifest": {"claimed_status": "DONE", "artifacts": []}})
        self.assertNotIn("gumroad", out.lower())
        self.assertNotIn("http", out.lower())


try:
    from langchain_tests.unit_tests import ToolsUnitTests
except ImportError:
    ToolsUnitTests = None

if ToolsUnitTests is not None:
    from datumline_agent_guard.langchain_tool import AgentGuardTool

    class TestAgentGuardToolStandard(ToolsUnitTests):
        """LangChain's own standard test suite for tools."""

        @property
        def tool_constructor(self):
            return AgentGuardTool

        @property
        def tool_constructor_params(self):
            return {}

        @property
        def tool_invoke_params_example(self):
            return {"manifest": {"claimed_status": "DONE", "artifacts": []}}
