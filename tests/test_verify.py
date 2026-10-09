import json
import os
import subprocess
import sys
import tempfile
import unittest

from datumline_agent_guard import verify
from datumline_agent_guard.cli import main


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _manifest(self, data):
        path = os.path.join(self.dir, "manifest.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_true_claim_is_verified(self):
        out = os.path.join(self.dir, "report.md")
        with open(out, "w") as f:
            f.write("## Findings\nall good\n")
        m = {"job": "T1", "claimed_status": "COMPLETED",
             "artifacts": [{"type": "file", "path": out, "must_contain": ["## Findings"]}]}
        self.assertEqual(verify(m)["verdict"], "VERIFIED")
        self.assertEqual(main([self._manifest(m)]), 0)

    def test_missing_file_with_completed_is_false_done(self):
        m = {"job": "T2", "claimed_status": "COMPLETED",
             "artifacts": [{"type": "file", "path": os.path.join(self.dir, "nope.md")}]}
        self.assertEqual(verify(m)["verdict"], "FALSE_DONE")
        self.assertEqual(main([self._manifest(m)]), 1)

    def test_missing_file_without_done_claim_is_failed(self):
        m = {"claimed_status": "IN_PROGRESS",
             "artifacts": [{"type": "file", "path": os.path.join(self.dir, "nope.md")}]}
        self.assertEqual(verify(m)["verdict"], "FAILED")

    def test_present_but_failing_check_is_failed(self):
        out = os.path.join(self.dir, "report.md")
        with open(out, "w") as f:
            f.write("x")
        m = {"claimed_status": "COMPLETED",
             "artifacts": [{"type": "file", "path": out, "min_bytes": 100}]}
        self.assertEqual(verify(m)["verdict"], "FAILED")

    def test_empty_manifest_is_unverifiable(self):
        self.assertEqual(verify({})["verdict"], "UNVERIFIABLE")
        self.assertEqual(main([self._manifest({"claimed_status": "COMPLETED", "artifacts": []})]), 1)

    def test_cli_entry_exit_code_and_output(self):
        m = {"job": "T3", "claimed_status": "DONE",
             "artifacts": [{"type": "file", "path": os.path.join(self.dir, "nope.md")}]}
        r = subprocess.run([sys.executable, "-m", "datumline_agent_guard", self._manifest(m)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("verdict FALSE_DONE", r.stdout)
        self.assertNotIn("http", r.stdout.lower())  # program output never advertises


if __name__ == "__main__":
    unittest.main()
