"""Authenticated run metadata must precede any completion-based review routing."""
import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("completion", Path(__file__).resolve().parents[1] / "scripts/dependabot-admission.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HEAD = "a" * 40
BASE = "b" * 40
REPO = "organvm/.github"
RID = 1154799938
MESSAGE = "Bump action\n\n---\nupdated-dependencies:\n- dependency-name: actions/checkout\n  update-type: version-update:semver-patch\n...\n"

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.pr = {"number": 1, "state": "open", "draft": False, "commits": 1,
                   "user": {"login": "dependabot[bot]"}, "changed_files": 1,
                   "head": {"sha": HEAD, "ref": "dependabot/github_actions/actions/checkout-7.1.1", "repo": {"id": RID}},
                   "base": {"sha": BASE, "ref": "main", "repo": {"id": RID, "full_name": REPO}}}
        self.run = {"id": 5, "run_attempt": 1, "run_number": 10, "head_sha": HEAD,
                    "repository": {"id": RID}, "head_repository": {"id": RID},
                    "event": "pull_request", "path": ".github/workflows/ci-minimal.yml",
                    "status": "completed", "conclusion": "success",
                    "pull_requests": [{"number": 1, "head": {"sha": HEAD}, "base": {"sha": BASE}}]}
        self.commits = [{"sha": HEAD, "author": {"login": "dependabot[bot]", "type": "Bot"},
                         "commit": {"verification": {"verified": True}, "message": MESSAGE}}]

    def read(self, path):
        self.calls.append(path)
        if path == f"repos/{REPO}/actions/runs/5": return copy.deepcopy(self.run)
        if path == f"repos/{REPO}/pulls/1": return copy.deepcopy(self.pr)
        if "/commits?" in path: return copy.deepcopy(self.commits)
        if path == f"repos/{REPO}": return {"id": RID, "default_branch": "main"}
        if path.endswith("/protection"):
            return {"required_status_checks": {"strict": True, "checks": [{"context": "validate", "app_id": 9}]}}
        if path == "apps/github-actions": return {"id": 9}
        if "/files?" in path: return [{"filename": ".github/workflows/ci.yml", "status": "modified"}]
        if "/runs?" in path: return {"total_count": 1, "workflow_runs": [copy.deepcopy(self.run)]}
        if "/attempts/1/jobs?" in path:
            return {"total_count": 1, "jobs": [{"name": "validate", "run_id": 5, "head_sha": HEAD,
                "status": "completed", "conclusion": "success", "steps": [
                    {"name": "Verify shared automation", "status": "completed", "conclusion": "success"}]}]}
        raise AssertionError(path)

    def assess(self):
        return module.assess_completed_run(self.read, REPO, 5, 1, HEAD)

    def test_bound_verified_completion_routes_only_to_review(self):
        result = self.assess()
        self.assertEqual(result["status"], "REVIEW_READY")
        self.assertFalse(result["automatic_acceptance"])
        self.assertEqual(result["run_attempt"], 1)
        self.assertEqual(len(self.calls), 12)

    def test_unverified_or_human_commit_cannot_supply_metadata(self):
        for field, value in (("author", {"login": "someone", "type": "User"}),
                             ("commit", {"verification": {"verified": False}, "message": MESSAGE})):
            original = copy.deepcopy(self.commits[0])
            self.commits[0][field] = value
            self.assertEqual(self.assess()["reason"], "METADATA_COMMIT_UNVERIFIED")
            self.commits[0] = original

    def test_unknown_major_ambiguous_and_alias_metadata_hold(self):
        for message in [MESSAGE.replace("semver-patch", "semver-major"),
                        MESSAGE.replace("updated-dependencies:", "updated-dependencies: []\nupdated-dependencies:"),
                        MESSAGE.replace("- dependency-name:", "- &alias dependency-name:"),
                        "no signed metadata"]:
            self.commits[0]["commit"]["message"] = message
            self.assertEqual(self.assess()["status"], "HOLD")

    def test_truncated_commit_list_and_head_mismatch_hold(self):
        self.pr["commits"] = 2
        self.assertEqual(self.assess()["reason"], "METADATA_COMMITS_INCOMPLETE")
        self.pr["commits"] = 1
        self.commits[0]["sha"] = "c" * 40
        self.assertEqual(self.assess()["reason"], "METADATA_COMMITS_INCOMPLETE")

    def test_later_verified_major_commit_cannot_hide_behind_first_patch(self):
        first = copy.deepcopy(self.commits[0]); first["sha"] = "b" * 40
        self.commits[0]["commit"]["message"] = MESSAGE.replace("semver-patch", "semver-major")
        self.commits.insert(0, first); self.pr["commits"] = 2
        self.assertEqual(self.assess()["reason"], "REPOSITORY_SPECIFIC_VALIDATION_REQUIRED")

    def test_wrong_attempt_repository_or_refusal_never_reaches_metadata(self):
        for field, value in (("run_attempt", 2), ("repository", {"id": 99}), ("conclusion", "failure")):
            old = copy.deepcopy(self.run); self.run[field] = value
            self.calls.clear()
            self.assertEqual(self.assess()["reason"], "COMPLETION_SOURCE_MISMATCH")
            self.assertEqual(len(self.calls), 1)
            self.run = old

    def test_newer_assessed_run_cannot_accept_an_old_completion(self):
        with patch.object(module, "assess", return_value={"status": "ELIGIBLE", "run_id": 6, "run_attempt": 1}):
            self.assertEqual(self.assess()["reason"], "COMPLETION_SUPERSEDED")

    def test_denied_read_redacts_diagnostics(self):
        def denied(path): raise OSError("private provider diagnostic")
        result = module.assess_completed_run(denied, REPO, 5, 1, HEAD)
        self.assertEqual(result["reason"], "COMPLETION_UNMEASURED")
        self.assertNotIn("private", str(result))
