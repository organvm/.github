#!/usr/bin/env python3
"""Reduce a completion event to a bounded hint; optionally publish it once.

Event data never supplies code, endpoint, credentials, authority or merge approval.
The keeper and trusted assessor independently establish all acceptance evidence.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY_ID = 1154799938
REPOSITORY = "organvm/.github"
WORKFLOW_PATH = ".github/workflows/ci-minimal.yml"
EVENT_LIMIT = 1024 * 1024
RESPONSE_LIMIT = 4096
TOKEN_ENV = "LIMEN_DEPENDENCY_COMPLETION_OBSERVER_TOKEN"  # allow-secret: environment reference only


class Hold(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Hold("MALFORMED_EVENT")
        result[key] = value
    return result


def positive(value):
    return type(value) is int and 0 < value < 2**53


def completion_hint(event):
    """Filter scope and copy four fields only; this is not an assessment."""
    try:
        repository, run = event["repository"], event["workflow_run"]
        if (event.get("action") != "completed" or repository.get("id") != REPOSITORY_ID
                or type(repository.get("id")) is not int or repository.get("full_name") != REPOSITORY
                or repository.get("default_branch") != "main"
                or run.get("event") != "pull_request" or run.get("status") != "completed"
                or run.get("conclusion") != "success"
                or run.get("head_repository", {}).get("id") != REPOSITORY_ID
                or type(run.get("head_repository", {}).get("id")) is not int
                or run.get("path", "").split("@", 1)[0] != WORKFLOW_PATH
                or not positive(run.get("id")) or not positive(run.get("run_attempt"))
                or not isinstance(run.get("head_sha"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", run["head_sha"])):
            raise Hold("COMPLETION_SCOPE_UNMEASURED")
        return {"repository_id": REPOSITORY_ID, "run_id": run["id"],
                "run_attempt": run["run_attempt"], "head_sha": run["head_sha"]}
    except (KeyError, TypeError, AttributeError):
        raise Hold("COMPLETION_SCOPE_UNMEASURED") from None


def validate_hint(hint):
    if (not isinstance(hint, dict) or set(hint) != {"repository_id", "run_id", "run_attempt", "head_sha"}
            or type(hint["repository_id"]) is not int or hint["repository_id"] != REPOSITORY_ID
            or not positive(hint["run_id"]) or not positive(hint["run_attempt"])
            or not isinstance(hint["head_sha"], str) or not re.fullmatch(r"[a-f0-9]{40}", hint["head_sha"])):
        raise Hold("COMPLETION_SCOPE_UNMEASURED")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


def exchange(request):
    """Internal isolated child: one POST with bounded readback, no redirects/proxy."""
    validate_hint(request["hint"])
    endpoint = request["endpoint"]
    parsed = urllib.parse.urlsplit(endpoint)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
        raise Hold("PUBLISH_UNMEASURED")
    credential = request["credential"]  # allow-secret: runtime request field
    if not isinstance(credential, str) or not credential.strip() or any(c in credential for c in "\r\n\x00"):
        raise Hold("PUBLISH_UNMEASURED")
    outgoing = urllib.request.Request(endpoint.rstrip("/") + "/api/conduct/dependencies/completions",
        data=json.dumps(request["hint"], separators=(",", ":")).encode(), method="POST",
        headers={"Authorization": "Bearer " + credential, "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": "organvm-completion-observer/1"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(outgoing, timeout=15) as response:
        if response.status not in {200, 201}:
            raise Hold("PUBLISH_UNMEASURED")
        raw = response.read(RESPONSE_LIMIT + 1)
    if len(raw) > RESPONSE_LIMIT:
        raise Hold("PUBLISH_UNMEASURED")
    receipt = json.loads(raw, object_pairs_hook=unique_object)
    hint = request["hint"]
    if (not isinstance(receipt, dict) or receipt.get("automatic_acceptance") is not False
            or any(type(receipt.get(key)) is not type(value) or receipt[key] != value for key, value in hint.items())
            or receipt.get("key") != f"{hint['repository_id']}:{hint['run_id']}:{hint['run_attempt']}"
            or type(receipt.get("duplicate")) is not bool):
        raise Hold("PUBLISH_UNMEASURED")
    return {"status": "RECORDED", "hint": hint, "duplicate": receipt["duplicate"], "automatic_acceptance": False}


def publish(hint, endpoint, credential):
    validate_hint(hint)
    if not endpoint or not credential:
        raise Hold("PUBLISH_UNCONFIGURED")
    result = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--exchange"],
        input=json.dumps({"endpoint": endpoint, "credential": credential, "hint": hint}).encode(),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env={}, timeout=20, check=False)
    if result.returncode != 0 or len(result.stdout) > RESPONSE_LIMIT:
        raise Hold("PUBLISH_UNMEASURED")
    observed = json.loads(result.stdout, object_pairs_hook=unique_object)
    if observed.get("status") != "RECORDED" or observed.get("hint") != hint or observed.get("automatic_acceptance") is not False:
        raise Hold("PUBLISH_UNMEASURED")
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--exchange", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.exchange:
            raw = sys.stdin.buffer.read(EVENT_LIMIT + 1)
            if len(raw) > EVENT_LIMIT:
                raise Hold("PUBLISH_UNMEASURED")
            result = exchange(json.loads(raw, object_pairs_hook=unique_object))
        else:
            if os.environ.get("GITHUB_EVENT_NAME") != "workflow_run" or args.event is None:
                raise Hold("COMPLETION_EVENT_REQUIRED")
            with args.event.open("rb") as handle:
                raw = handle.read(EVENT_LIMIT + 1)
            if len(raw) > EVENT_LIMIT:
                raise Hold("EVENT_SIZE_LIMIT")
            hint = completion_hint(json.loads(raw, object_pairs_hook=unique_object))
            result = publish(hint, os.environ.get("LIMEN_CONDUCT_URL", ""), os.environ.get(TOKEN_ENV, "")) if args.publish else {
                "status": "HINT", "hint": hint, "automatic_acceptance": False}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, subprocess.SubprocessError) as error:
        reason = str(error) if isinstance(error, Hold) and not args.exchange else "COMPLETION_UNMEASURED"
        print(json.dumps({"status": "HOLD", "reason": reason, "automatic_acceptance": False}, sort_keys=True))
        return 77


if __name__ == "__main__":
    raise SystemExit(main())
