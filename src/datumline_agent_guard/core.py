"""
datumline_agent_guard — independent artifact verifier.

Standard library only. Imports NOTHING from the runtime it audits, by design:
the auditor must not share code, process, or state with the thing under audit,
or it cannot contradict it.

Usage:
    agent-guard manifest.json            # prints a receipt, exit 0 on VERIFIED, 1 otherwise
    agent-guard manifest.json --json     # machine-readable receipt

Manifest shape (JSON):
{
  "job": "WO-123",
  "claimed_status": "COMPLETED",          # what the runtime/agent claims
  "artifacts": [
    {"type": "file", "path": "out/report.md", "min_bytes": 200, "must_contain": ["## Findings"]},
    {"type": "json", "path": "out/feed.json", "required_keys": ["last_marked", "entries"]},
    {"type": "url",  "url": "https://example.com/feed.json", "status": 200, "must_contain": ["last_marked"]},
    {"type": "file", "path": "out/data.parquet", "sha256": "<hex>"}
  ]
}

Verdicts:
  VERIFIED    every artifact present and passes every check
  FAILED      an artifact is present but fails a check
  FALSE_DONE  claimed_status is COMPLETED/VERIFIED/DONE and at least one artifact is ABSENT
  UNVERIFIABLE manifest asserts nothing (empty artifact list) — fail-closed, never green
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

DONE_WORDS = {"COMPLETED", "VERIFIED", "DONE", "COMPLETE"}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def check_file(a):
    p = a["path"]
    if not os.path.isfile(p):
        return "ABSENT", f"missing file {p}"
    size = os.path.getsize(p)
    if a.get("min_bytes") and size < a["min_bytes"]:
        return "FAIL", f"{p}: {size} bytes < min {a['min_bytes']}"
    text = None
    if a.get("must_contain") or a.get("min_lines"):
        with open(p, "r", errors="replace") as f:
            text = f.read()
    if a.get("min_lines") and text.count("\n") + 1 < a["min_lines"]:
        return "FAIL", f"{p}: fewer than {a['min_lines']} lines"
    for s in a.get("must_contain", []):
        if s not in text:
            return "FAIL", f"{p}: missing required text {s!r}"
    if a.get("sha256") and _sha256(p) != a["sha256"].lower():
        return "FAIL", f"{p}: sha256 mismatch"
    return "PASS", f"{p}: {size} bytes"


def check_json(a):
    p = a["path"]
    if not os.path.isfile(p):
        return "ABSENT", f"missing file {p}"
    try:
        with open(p) as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        return "FAIL", f"{p}: not valid JSON ({e})"
    for k in a.get("required_keys", []):
        if not (isinstance(data, dict) and k in data):
            return "FAIL", f"{p}: missing key {k!r}"
    return "PASS", f"{p}: valid JSON"


def check_url(a):
    url = a["url"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "datumline-agent-guard/0.1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", errors="replace")
            code = r.getcode()
    except Exception as e:  # noqa: BLE001
        return "ABSENT", f"{url}: unreachable ({e})"
    want = a.get("status", 200)
    if code != want:
        return "FAIL", f"{url}: HTTP {code} != {want}"
    for s in a.get("must_contain", []):
        if s not in body:
            return "FAIL", f"{url}: missing required text {s!r}"
    return "PASS", f"{url}: HTTP {code}"


CHECKS = {"file": check_file, "json": check_json, "url": check_url}


def verify(manifest):
    claimed = str(manifest.get("claimed_status", "")).upper()
    artifacts = manifest.get("artifacts", [])
    results = []
    if not artifacts:
        return {
            "job": manifest.get("job"),
            "claimed_status": claimed,
            "verdict": "UNVERIFIABLE",
            "reason": "manifest asserts no artifacts; refusing to return green on nothing",
            "results": [],
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    absent = failed = 0
    for a in artifacts:
        fn = CHECKS.get(a.get("type"))
        if fn is None:
            state, msg = "FAIL", f"unknown artifact type {a.get('type')!r}"
        else:
            state, msg = fn(a)
        results.append({"artifact": a, "state": state, "detail": msg})
        absent += state == "ABSENT"
        failed += state == "FAIL"
    if absent and claimed in DONE_WORDS:
        verdict = "FALSE_DONE"
    elif absent or failed:
        verdict = "FAILED"
    else:
        verdict = "VERIFIED"
    return {
        "job": manifest.get("job"),
        "claimed_status": claimed,
        "verdict": verdict,
        "absent": absent,
        "failed": failed,
        "checked": len(artifacts),
        "results": results,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def verify_file(path):
    """Load a manifest JSON file and verify it."""
    with open(path) as f:
        return verify(json.load(f))
