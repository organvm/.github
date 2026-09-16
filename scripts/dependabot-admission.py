#!/usr/bin/env python3
"""One bounded read-only Actions-update admission; never waits or merges."""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
import time

from pathlib import Path
from urllib.parse import quote


class Hold(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Repository moves and redirects require fresh scope verification."""

    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


class Reader:
    def __init__(self):
        self.deadline = time.monotonic() + 90
        self.remaining = 12

    def __call__(self, path):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or self.remaining <= 0:
            raise Hold("READ_BUDGET")
        self.remaining -= 1
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "organvm-dependency-admission",
                   "X-GitHub-Api-Version": "2026-03-10"}
        credential = os.environ.get("GH_TOKEN")
        if credential:
            headers["Authorization"] = "Bearer " + credential
        request = urllib.request.Request("https://api.github.com/" + path, headers=headers)
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=min(15, remaining)) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise Hold("API_RESPONSE_LIMIT")
        return json.loads(raw)


def identity(pr, repo, number, head):
    if (not isinstance(pr, dict) or pr.get("number") != number
            or pr.get("state") != "open" or pr.get("draft") is not False
            or pr.get("user", {}).get("login") != "dependabot[bot]"
            or pr.get("head", {}).get("sha") != head):
        raise Hold("PR_IDENTITY_OR_STATE")
    base, source = pr["base"], pr["head"]
    repository_id = base["repo"]["id"]
    if (type(repository_id) is not int or repository_id <= 0
            or base["repo"]["full_name"].casefold() != repo.casefold()
            or source["repo"]["id"] != repository_id
            or not re.fullmatch(r"[0-9a-f]{40}", base.get("sha", ""))):
        raise Hold("REPOSITORY_OR_BASE")
    return repository_id, base["sha"]


def connection(value, key):
    rows = value.get(key) if isinstance(value, dict) else None
    if (not isinstance(rows, list) or type(value.get("total_count")) is not int
            or value["total_count"] != len(rows)
            or any(not isinstance(row, dict) for row in rows)):
        raise Hold("INCOMPLETE_CONNECTION")
    return rows


def assess(read, repo, number, head, ecosystem, update_type):
    result = {"status": "HOLD", "reason": "UNMEASURED", "head": head}
    try:
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
                or type(number) is not int or number <= 0
                or not re.fullmatch(r"[0-9a-f]{40}", head)):
            raise Hold("INVALID_INPUT")
        if ecosystem not in {"github_actions", "github-actions"}:
            raise Hold("NOT_ACTIONS_ONLY")
        if update_type not in {"version-update:semver-patch", "version-update:semver-minor"}:
            raise Hold("REPOSITORY_SPECIFIC_VALIDATION_REQUIRED")
        prefix = "repos/" + repo
        pr = read(prefix + f"/pulls/{number}")
        generation = identity(pr, repo, number, head)
        repository = read(prefix)
        if (repository.get("id") != generation[0]
                or repository.get("default_branch") != pr["base"].get("ref")):
            raise Hold("NOT_DEFAULT_BASE")
        protection = read(prefix + "/branches/" + quote(pr["base"]["ref"], safe="") + "/protection")
        required = protection.get("required_status_checks")
        app = read("apps/github-actions")
        if (not isinstance(required, dict) or required.get("strict") is not True
                or type(app.get("id")) is not int
                or not isinstance(required.get("checks"), list)
                or not any(isinstance(check, dict) and check.get("context") == "validate"
                           and check.get("app_id") == app["id"] for check in required["checks"])):
            raise Hold("SERVER_REQUIRED_CI_UNMEASURED")
        files = read(prefix + f"/pulls/{number}/files?per_page=100")
        if (not isinstance(files, list) or not files or len(files) >= 100
                or type(pr.get("changed_files")) is not int or len(files) != pr["changed_files"]
                or any(not isinstance(row, dict) or row.get("status") != "modified"
                       or not re.fullmatch(r"\.github/workflows/[^/]+\.ya?ml", row.get("filename", ""))
                       for row in files)):
            raise Hold("CHANGED_SCOPE_UNMEASURED_OR_NON_ACTIONS")
        runs = connection(read(prefix + f"/actions/workflows/ci-minimal.yml/runs?head_sha={head}&event=pull_request&per_page=100"), "workflow_runs")
        if not runs or any(type(run.get("run_number")) is not int for run in runs):
            raise Hold("CI_MISSING")
        run = max(runs, key=lambda row: row["run_number"])
        if (run.get("head_sha") != head or run.get("event") != "pull_request"
                or not isinstance(run.get("path"), str)
                or not re.fullmatch(r"\.github/workflows/ci-minimal\.yml(?:@[^\s]+)?", run["path"])
                or run.get("repository", {}).get("id") != generation[0]
                or run.get("head_repository", {}).get("id") != generation[0]
                or type(run.get("id")) is not int):
            raise Hold("CI_SOURCE_MISMATCH")
        references = run.get("pull_requests")
        if (not isinstance(references, list)
                or not any(isinstance(ref, dict) and ref.get("number") == number
                           and ref.get("head", {}).get("sha") == head
                           and ref.get("base", {}).get("sha") == generation[1] for ref in references)):
            raise Hold("CI_BASE_GENERATION_UNMEASURED")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise Hold("CI_NOT_SUCCESSFUL")
        attempt = run.get("run_attempt")
        if type(attempt) is not int or attempt <= 0:
            raise Hold("CI_ATTEMPT_UNMEASURED")
        jobs = connection(read(prefix + f"/actions/runs/{run['id']}/attempts/{attempt}/jobs?per_page=100"), "jobs")
        if not jobs or any(job.get("head_sha") != head or job.get("run_id") != run["id"]
                           or job.get("status") != "completed" or job.get("conclusion") != "success"
                           for job in jobs):
            raise Hold("CI_JOBS_UNMEASURED")
        validators = [job for job in jobs if job.get("name") == "validate"]
        if len(validators) != 1:
            raise Hold("CI_VALIDATOR_MISSING")
        steps = validators[0].get("steps")
        if (not isinstance(steps, list) or any(not isinstance(step, dict) for step in steps)
                or not any(step.get("name") == "Verify shared automation"
                           and step.get("status") == "completed" and step.get("conclusion") == "success"
                           for step in steps)):
            raise Hold("CI_NO_EXECUTED_PREDICATE")
        current_run = read(prefix + f"/actions/runs/{run['id']}")
        binding = ("id", "run_attempt", "run_number", "head_sha", "event", "path",
                   "repository", "head_repository", "pull_requests", "status", "conclusion")
        if (not isinstance(current_run, dict)
                or type(current_run.get("run_attempt")) is not int
                or any(current_run.get(key) != run.get(key) for key in binding)):
            raise Hold("CI_RUN_CHANGED")
        if identity(read(prefix + f"/pulls/{number}"), repo, number, head) != generation:
            raise Hold("BASE_MOVED")
        result.update(status="ELIGIBLE", reason="EXACT_HEAD_ACTIONS_CI", run_id=run["id"], run_attempt=attempt, base_sha=generation[1])
    except Hold as error:
        result["reason"] = str(error)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        result["reason"] = "API_UNMEASURED"
    return result



def verified_metadata(read, repo, number, head):
    """Derive only signed Dependabot patch/minor metadata; never trust labels.

    Verification contract reviewed against fetch-metadata v3 at
    25dd0e34f4fe68f24cc83900b1fe3fe149efef98. Require the entire bounded
    commit list to be verified bot commits, stronger than first-commit-only.
    """
    pr = read(f"repos/{repo}/pulls/{number}")
    identity(pr, repo, number, head)
    if not pr["head"].get("ref", "").startswith("dependabot/github_actions/"):
        raise Hold("METADATA_ECOSYSTEM_UNMEASURED")
    commits = read(f"repos/{repo}/pulls/{number}/commits?per_page=100")
    if (not isinstance(commits, list) or not 0 < len(commits) < 100
            or type(pr.get("commits")) is not int or len(commits) != pr["commits"]
            or commits[-1].get("sha") != head):
        raise Hold("METADATA_COMMITS_INCOMPLETE")
    for commit in commits:
        if (commit.get("author", {}).get("login") != "dependabot[bot]"
                or commit.get("author", {}).get("type") != "Bot"
                or commit.get("commit", {}).get("verification", {}).get("verified") is not True):
            raise Hold("METADATA_COMMIT_UNVERIFIED")
    types = set()
    for commit in commits:
        types.update(_message_types(commit["commit"].get("message")))
    return "github_actions", ("version-update:semver-minor" if "version-update:semver-minor" in types
                              else "version-update:semver-patch")


def _message_types(message):
    import yaml
    if not isinstance(message, str) or len(message.encode()) > 65536:
        raise Hold("METADATA_MESSAGE_UNMEASURED")
    fragments = re.findall(r"^---\n(.*?)^\.\.\.\n", message, re.MULTILINE | re.DOTALL)
    if len(fragments) != 1:
        raise Hold("METADATA_BLOCK_UNMEASURED")
    # The trusted bot metadata is parsed as data; aliases and duplicate mapping
    # keys cannot make an ambiguous payload appear to be a patch update.
    class MetadataLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
            if any(not isinstance(key, str) for key in keys) or len(keys) != len(set(keys)):
                raise Hold("METADATA_AMBIGUOUS")
            return super().construct_mapping(node, deep=deep)
    if any(isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
           for token in yaml.scan(fragments[0])):
        raise Hold("METADATA_AMBIGUOUS")
    data = yaml.load(fragments[0], Loader=MetadataLoader)
    dependencies = data.get("updated-dependencies") if isinstance(data, dict) else None
    if not isinstance(dependencies, list) or not 0 < len(dependencies) <= 100:
        raise Hold("METADATA_DEPENDENCIES_UNMEASURED")
    types = set()
    for dependency in dependencies:
        if (not isinstance(dependency, dict)
                or not isinstance(dependency.get("dependency-name"), str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+", dependency["dependency-name"])
                or dependency.get("update-type") not in {"version-update:semver-patch", "version-update:semver-minor"}):
            raise Hold("REPOSITORY_SPECIFIC_VALIDATION_REQUIRED")
        types.add(dependency["update-type"])
    return types


def assess_completed_run(read, repo, run_id, expected_attempt, expected_head):
    """Read-only trusted consumer; a completion event is only a bounded hint."""
    result = {"status": "HOLD", "reason": "UNMEASURED", "automatic_acceptance": False}
    try:
        import yaml
    except ImportError:
        return {**result, "reason": "METADATA_PARSER_UNAVAILABLE"}
    try:
        # Explicit shared-template scope, distinct from the relay allowlist.
        if (repo != "organvm/.github" or type(run_id) is not int or run_id <= 0
                or type(expected_attempt) is not int or expected_attempt <= 0
                or not isinstance(expected_head, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_head)):
            raise Hold("COMPLETION_SCOPE_UNCONFIGURED")
        run = read(f"repos/{repo}/actions/runs/{run_id}")
        refs = run.get("pull_requests")
        if (run.get("id") != run_id or run.get("run_attempt") != expected_attempt
                or type(run.get("run_attempt")) is not int
                or run.get("head_sha") != expected_head or run.get("event") != "pull_request"
                or run.get("status") != "completed" or run.get("conclusion") != "success"
                or run.get("repository", {}).get("id") != 1154799938
                or run.get("head_repository", {}).get("id") != 1154799938
                or not isinstance(refs, list) or len(refs) != 1
                or type(refs[0].get("number")) is not int or refs[0]["number"] <= 0
                or refs[0].get("head", {}).get("sha") != expected_head):
            raise Hold("COMPLETION_SOURCE_MISMATCH")
        number = refs[0]["number"]
        ecosystem, update_type = verified_metadata(read, repo, number, expected_head)
        assessed = assess(read, repo, number, expected_head, ecosystem, update_type)
        if assessed["status"] != "ELIGIBLE":
            return {**assessed, "automatic_acceptance": False}
        if assessed.get("run_id") != run_id or assessed.get("run_attempt") != expected_attempt:
            raise Hold("COMPLETION_SUPERSEDED")
        return {**assessed, "status": "REVIEW_READY", "pr": number,
                "repository_id": 1154799938, "automatic_acceptance": False}
    except Hold as error:
        result["reason"] = str(error)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, yaml.YAMLError):
        result["reason"] = "COMPLETION_UNMEASURED"
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--completed-run", type=int)
    parser.add_argument("--expected-attempt", type=int)
    parser.add_argument("--expected-head")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    args = parser.parse_args()
    if args.completed_run is not None:
        result = assess_completed_run(Reader(), args.repo, args.completed_run, args.expected_attempt, args.expected_head)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "REVIEW_READY" else 2
    if args.expected_attempt is not None or args.expected_head is not None:
        parser.error("expected attempt/head require --completed-run")
    try:
        number = int(os.environ.get("PR_NUMBER", "0"))
    except ValueError:
        number = 0
    result = assess(Reader(), os.environ.get("GITHUB_REPOSITORY", ""), number,
                    os.environ.get("PR_HEAD", ""), os.environ.get("DEPENDENCY_ECOSYSTEM", ""),
                    os.environ.get("DEPENDENCY_UPDATE_TYPE", ""))
    print(json.dumps(result, sort_keys=True))
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
            stream.write("eligible=" + str(result["status"] == "ELIGIBLE").lower() + "\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as stream:
            stream.write(f"Dependabot admission: **{result['status']}** — {result['reason']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
