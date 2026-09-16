"""A passing label or old CI run must never authorize a dependency merge."""
import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("admission", ROOT / "scripts/dependabot-admission.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HEAD = "a" * 40
BASE = "b" * 40


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.pr = {"number": 1, "state": "open", "draft": False,
                   "user": {"login": "dependabot[bot]"}, "changed_files": 1,
                   "head": {"sha": HEAD, "repo": {"id": 7}},
                   "base": {"sha": BASE, "ref": "main", "repo": {"id": 7, "full_name": "owner/repo"}}}
        self.protection = {"required_status_checks": {"strict": True, "checks": [{"context": "validate", "app_id": 9}]}}
        self.files = [{"filename": ".github/workflows/ci.yml", "status": "modified"}]
        self.run = {"id": 5, "run_number": 10, "head_sha": HEAD, "event": "pull_request",
                    "path": ".github/workflows/ci-minimal.yml", "repository": {"id": 7},
                    "head_repository": {"id": 7}, "status": "completed", "conclusion": "success",
                    "pull_requests": [{"number": 1, "head": {"sha": HEAD}, "base": {"sha": BASE}}]}
        self.jobs = [{"name": "validate", "run_id": 5, "head_sha": HEAD,
                      "status": "completed", "conclusion": "success", "steps": [
                          {"name": "Verify shared automation", "status": "completed", "conclusion": "success"}]}]
        self.calls = []
        self.after = None

    def read(self, path):
        self.calls.append(path)
        if path == "repos/owner/repo/pulls/1":
            return copy.deepcopy(self.after if self.after is not None and self.calls.count(path) > 1 else self.pr)
        if path == "repos/owner/repo":
            return {"id": 7, "default_branch": "main"}
        if path.endswith("/protection"):
            return copy.deepcopy(self.protection)
        if path == "apps/github-actions":
            return {"id": 9}
        if "/files?" in path:
            return copy.deepcopy(self.files)
        if "/jobs?" in path:
            return {"total_count": len(self.jobs), "jobs": copy.deepcopy(self.jobs)}
        if "/runs?" in path:
            return {"total_count": 1, "workflow_runs": [copy.deepcopy(self.run)]}
        raise AssertionError(path)

    def assess(self, **kwargs):
        args = {"read": self.read, "repo": "owner/repo", "number": 1, "head": HEAD,
                "ecosystem": "github_actions", "update_type": "version-update:semver-patch"}
        args.update(kwargs)
        return module.assess(**args)

    def test_only_bound_executed_ci_is_eligible(self):
        result = self.assess()
        self.assertEqual(result["status"], "ELIGIBLE")
        self.assertEqual(result["base_sha"], BASE)
        self.assertEqual(len(self.calls), 8)

    def test_majors_and_other_ecosystems_do_not_read_or_launch(self):
        for args in ({"update_type": "version-update:semver-major"}, {"ecosystem": "npm"}):
            with self.subTest(args=args):
                self.assertEqual(self.assess(**args)["status"], "HOLD")
        self.assertFalse(self.calls)

    def test_changed_scope_and_unprotected_sources_hold(self):
        for filename in ("package.json", "scripts/run.py", "../workflow.yml"):
            self.files[0]["filename"] = filename
            self.assertEqual(self.assess()["status"], "HOLD")
        self.files[0]["filename"] = ".github/workflows/ci.yml"
        for required in (None, {"strict": False, "checks": []}, {"strict": True, "checks": [{"context": "validate", "app_id": 99}]}):
            self.protection["required_status_checks"] = required
            self.assertEqual(self.assess()["status"], "HOLD")

    def test_zero_step_and_skipped_predicates_hold(self):
        for steps in ([], [{"name": "Verify shared automation", "status": "completed", "conclusion": "skipped"}]):
            self.jobs[0]["steps"] = steps
            self.assertEqual(self.assess()["reason"], "CI_NO_EXECUTED_PREDICATE")

    def test_wrong_workflow_head_or_repository_cannot_spoof_ci(self):
        original = copy.deepcopy(self.run)
        for key, value in (("head_sha", "c" * 40), ("path", ".github/workflows/spoof.yml"),
                           ("repository", {"id": 8}), ("event", "workflow_dispatch")):
            self.run = {**original, key: value}
            self.assertEqual(self.assess()["status"], "HOLD")

    def test_old_base_and_moving_base_hold(self):
        self.run["pull_requests"][0]["base"]["sha"] = "c" * 40
        self.assertEqual(self.assess()["reason"], "CI_BASE_GENERATION_UNMEASURED")
        self.run["pull_requests"][0]["base"]["sha"] = BASE
        self.calls.clear()
        self.after = copy.deepcopy(self.pr)
        self.after["base"]["sha"] = "c" * 40
        self.assertEqual(self.assess()["reason"], "BASE_MOVED")

    def test_pending_failed_and_denied_ci_never_wait(self):
        for conclusion in (None, "failure", "cancelled"):
            self.run["conclusion"] = conclusion
            self.assertEqual(self.assess()["reason"], "CI_NOT_SUCCESSFUL")
        def denied(path):
            raise OSError("credential diagnostic must not be emitted")
        self.assertEqual(self.assess(read=denied)["reason"], "API_UNMEASURED")

    def test_incomplete_connections_and_file_lists_hold(self):
        self.pr["changed_files"] = 2
        self.assertEqual(self.assess()["status"], "HOLD")
        with self.assertRaises(module.Hold):
            module.connection({"total_count": 2, "jobs": [{}]}, "jobs")

    def test_newer_pending_run_supersedes_old_success(self):
        base_read = self.read
        def read(path):
            if "/runs?" in path:
                newer = {**self.run, "id": 6, "run_number": 11, "status": "in_progress", "conclusion": None}
                return {"total_count": 2, "workflow_runs": [copy.deepcopy(self.run), newer]}
            return base_read(path)
        self.assertEqual(self.assess(read=read)["reason"], "CI_NOT_SUCCESSFUL")

    def test_head_movement_and_fork_source_hold(self):
        self.after = copy.deepcopy(self.pr)
        self.after["head"]["sha"] = "c" * 40
        self.assertEqual(self.assess()["reason"], "PR_IDENTITY_OR_STATE")
        self.after = None
        self.pr["head"]["repo"]["id"] = 8
        self.assertEqual(self.assess()["reason"], "REPOSITORY_OR_BASE")

    def test_read_budget_stops_before_network(self):
        reader = module.Reader()
        reader.remaining = 0
        with patch.object(module.urllib.request, "urlopen", side_effect=AssertionError("no network")):
            with self.assertRaises(module.Hold):
                reader("repos/owner/repo")

    def test_workflow_uses_trusted_base_and_exact_head_submission(self):
        data = yaml.load((ROOT / ".github/workflows/dependabot-auto-merge.yml").read_text(), Loader=yaml.BaseLoader)
        job = data["jobs"]["dependabot"]
        self.assertIn("base.ref == github.event.repository.default_branch", job["if"])
        self.assertIn("head.repo.id == github.event.repository.id", job["if"])
        checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(checkout["with"]["ref"], "${{ github.event.pull_request.base.sha }}")
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        merge = job["steps"][-1]
        self.assertIn("admission.outputs.eligible", merge["if"])
        self.assertIn('--match-head-commit "$PR_HEAD"', merge["run"])
        self.assertNotIn("--admin", merge["run"])


if __name__ == "__main__":
    unittest.main()
