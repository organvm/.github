"""Completion events publish hints only, with no ambient authority or retries."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hint_producer", ROOT / "scripts/dependency-completion-hint.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class HintTests(unittest.TestCase):
    def setUp(self):
        self.event = {"action": "completed", "repository": {"id": module.REPOSITORY_ID,
            "full_name": module.REPOSITORY, "default_branch": "main"}, "workflow_run": {
            "id": 123, "run_attempt": 2, "head_sha": "a"*40, "event": "pull_request",
            "status": "completed", "conclusion": "success", "head_repository": {"id": module.REPOSITORY_ID},
            "path": module.WORKFLOW_PATH, "head_commit": {"message": "untrusted material must be dropped"}}}
        self.hint = {"repository_id": module.REPOSITORY_ID, "run_id": 123, "run_attempt": 2, "head_sha": "a"*40}

    def test_event_reduces_to_exact_hint(self):
        self.assertEqual(module.completion_hint(self.event), self.hint)
        self.event["workflow_run"]["path"] += "@refs/heads/main"
        self.assertEqual(module.completion_hint(self.event), self.hint)

    def test_wrong_scope_and_malformed_runs_hold(self):
        for field, value in [("id", True), ("run_attempt", 0), ("run_attempt", 2**53),
                             ("head_sha", "invalid"), ("event", "push"), ("conclusion", "failure"),
                             ("head_repository", {"id": 1}), ("path", "attacker.yml")]:
            event = copy.deepcopy(self.event); event["workflow_run"][field] = value
            with self.subTest(field=field), self.assertRaises(module.Hold):
                module.completion_hint(event)
        for event in [None, [], {"repository": None}, {**self.event, "action": "requested"}]:
            with self.assertRaises(module.Hold): module.completion_hint(event)

    def test_missing_dedicated_credential_has_no_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.json"; path.write_text(json.dumps(self.event))
            with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_run", "GH_TOKEN": "fixture-ambient",
                                         "LIMEN_CONDUCT_URL": "https://keeper.example.invalid"}, clear=True), \
                 patch("sys.argv", ["producer", "--event", str(path), "--publish"]), \
                 patch.object(module.subprocess, "run") as run, patch("sys.stdout", new_callable=io.StringIO) as out:
                self.assertEqual(module.main(), 77)
                run.assert_not_called()
                self.assertEqual(json.loads(out.getvalue())["reason"], "PUBLISH_UNCONFIGURED")

    def test_parent_timeout_never_retries_or_places_credential_in_argv(self):
        with patch.object(module.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture", 20)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                module.publish(self.hint, "https://keeper.example.invalid", "fixture-observer")
            self.assertEqual(run.call_count, 1)
            args, kwargs = run.call_args
            self.assertNotIn("fixture-observer", str(args))
            self.assertEqual(kwargs["env"], {})
            self.assertEqual(kwargs["timeout"], 20)
            self.assertEqual(json.loads(kwargs["input"])["hint"], self.hint)

    def exchange(self, receipt=None, endpoint="https://keeper.example.invalid"):
        if receipt is None:
            receipt = {**self.hint, "key": f"{module.REPOSITORY_ID}:123:2", "automatic_acceptance": False, "duplicate": False}
        raw = receipt if isinstance(receipt, bytes) else json.dumps(receipt).encode()
        class Response:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit):
                self_limit.append(limit)
                return raw
        self_limit = []
        with patch.object(module.urllib.request, "build_opener") as build:
            build.return_value.open.return_value = Response()
            result = module.exchange({"endpoint": endpoint, "credential": "fixture-observer", "hint": self.hint})
            self.assertEqual(build.call_args.args[0].proxies, {})
            self.assertIsInstance(build.call_args.args[1], module.NoRedirect)
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, endpoint + "/api/conduct/dependencies/completions")
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(json.loads(request.data), self.hint)
            self.assertEqual(self_limit, [module.RESPONSE_LIMIT+1])
            return result

    def test_readback_preserves_exact_identity_without_acceptance(self):
        result = self.exchange()
        self.assertEqual(result["status"], "RECORDED")
        self.assertFalse(result["automatic_acceptance"])
        self.assertEqual(result["hint"], self.hint)

    def test_mismatched_malformed_and_oversized_readback_hold(self):
        receipt = {**self.hint, "key": f"{module.REPOSITORY_ID}:123:2", "automatic_acceptance": False, "duplicate": False}
        for change in [{"head_sha": "b"*40}, {"run_attempt": True}, {"automatic_acceptance": True}, {"duplicate": "false"}]:
            with self.assertRaises(module.Hold): self.exchange({**receipt, **change})
        for raw in [b'[]', b'{"duplicate":false,"duplicate":true}', b'x'*(module.RESPONSE_LIMIT+1)]:
            with self.assertRaises(ValueError): self.exchange(raw)

    def test_endpoint_and_redirect_refusal(self):
        for endpoint in ["http://keeper.example.invalid", "https://user:secret@example.invalid", "https://keeper.example.invalid?query=1"]:
            with self.assertRaises(module.Hold): self.exchange(endpoint=endpoint)
        self.assertIsNone(module.NoRedirect().redirect_request(None, None, 302, None, None, "https://elsewhere.invalid"))

    def test_event_size_and_duplicate_keys_hold_without_publishing(self):
        for data in [b'x'*(module.EVENT_LIMIT+1), b'{"action":"completed","action":"requested"}']:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "event.json"; path.write_bytes(data)
                with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_run"}, clear=True), \
                     patch("sys.argv", ["producer", "--event", str(path)]), patch("sys.stdout", new_callable=io.StringIO):
                    self.assertEqual(module.main(), 77)

    def test_real_cli_emits_hint_and_isolated_publish_failure_is_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.json"
            path.write_text(json.dumps(self.event))
            command = [module.sys.executable, "-I", str(ROOT / "scripts/dependency-completion-hint.py"), "--event", str(path)]
            environment = {"GITHUB_EVENT_NAME": "workflow_run"}
            result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=25)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["hint"], self.hint)
            environment.update(LIMEN_CONDUCT_URL="https://127.0.0.1:9")
            environment[module.TOKEN_ENV] = "fixture-observer-only"
            refused = subprocess.run(command + ["--publish"], env=environment, capture_output=True, text=True, timeout=25)
            self.assertEqual(refused.returncode, 77)
            self.assertEqual(json.loads(refused.stdout)["status"], "HOLD")
            self.assertNotIn("fixture-observer-only", refused.stdout + refused.stderr)

    def test_template_is_outside_active_workflows_and_has_minimal_authority(self):
        import yaml
        path = ROOT / "docs/deployment/dependency-completion.yml"
        template = yaml.safe_load(path.read_text())
        self.assertEqual(template["permissions"], {"contents": "read"})
        triggers = template.get("on", template.get(True))
        self.assertEqual(triggers, {"workflow_run": {"workflows": ["CI Minimal"], "types": ["completed"]}})
        self.assertFalse((ROOT / ".github/workflows/dependency-completion.yml").exists())
        job = template["jobs"]["observe"]
        self.assertIn("DEPENDENCY_COMPLETION_ENABLED", job["if"])
        self.assertEqual(job["steps"][0]["with"]["ref"], "${{ github.sha }}")
        self.assertFalse(job["steps"][0]["with"]["persist-credentials"])
        self.assertNotIn("GH_TOKEN", job["steps"][1]["env"])


if __name__ == "__main__": unittest.main()
