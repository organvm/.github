#!/usr/bin/env python3
"""Pull the meta-org profile README from the corpus that OWNS its data.

This org profile is a *projection*, not a hand-kept document. The corpus
(organvm-corpvs-testamentvm) renders it from the organs that own the truth —
config (the organ showcase), repo-registry.json (per-organ counts), and
system-metrics.json/system-snapshot.json (live totals) — and commits the result
to .github-template/generated/meta-organvm.profile-README.md.

This script fetches that rendered projection and writes it to profile/README.md.
Pull model: no cross-org token, mirroring how the portfolio fetches the corpus's
system-metrics.json at build time. Nothing here decides framing or pins a number
— every figure is whatever the corpus published.

The one thing we PRESERVE is the <!-- PORTFOLIO-HUB-START -->..<!-- ..-END -->
block: it is injected and owned by a different organ (the portfolio-hub tool),
so we re-attach it rather than clobber it.

Usage:
    python3 scripts/refresh-profile.py            # write profile/README.md if changed
    python3 scripts/refresh-profile.py --check    # exit 1 if it would change (CI drift gate)
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "profile" / "README.md"
SOURCE_URL = (
    "https://raw.githubusercontent.com/organvm/organvm-corpvs-testamentvm/"
    "main/.github-template/generated/meta-organvm.profile-README.md"
)
HUB_START = "<!-- PORTFOLIO-HUB-START -->"
HUB_END = "<!-- PORTFOLIO-HUB-END -->"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "organvm-profile-refresh"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed trusted URL)
        return resp.read().decode("utf-8")


def preserved_hub_block(existing: str) -> str:
    """Return the portfolio-hub block (owned by another organ) to re-attach, or ''."""
    if HUB_START in existing and HUB_END in existing:
        start = existing.index(HUB_START)
        end = existing.index(HUB_END) + len(HUB_END)
        return "\n\n" + existing[start:end].strip() + "\n"
    return ""


def _essay_count(projection: str) -> str | None:
    """The SSOT essay count, read from the projection body (e.g. '65 published essays')."""
    m = re.search(r"(\d[\d,]*)\+?\s+published essays", projection)
    return m.group(1) if m else None


def compose(projection: str, existing: str) -> str:
    body = projection.rstrip("\n")
    hub = preserved_hub_block(existing)
    if hub:
        # The portfolio-hub link label ("[N Essays](...)") carries an essay count
        # drawn from the SAME SSOT as the body. Normalize it to the projected count
        # so the page can never show two different essay numbers — the whole page
        # is one derive-never-pin projection, hub included.
        n = _essay_count(projection)
        if n:
            hub = re.sub(r"\[\d[\d,]*\+?\s+Essays\]", f"[{n} Essays]", hub)
    return body + ("\n" + hub if hub else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Pull the projected meta-org profile from the corpus.")
    ap.add_argument("--check", action="store_true", help="Exit 1 if profile/README.md is out of date")
    ap.add_argument("--source", default=SOURCE_URL, help="Override the projection source URL")
    args = ap.parse_args()

    try:
        projection = fetch(args.source)
    except Exception as exc:  # network/transient — never wedge the beat
        print(f"WARNING: could not fetch projection ({exc}); leaving profile unchanged", file=sys.stderr)
        return 0

    if not projection.strip() or "# meta-" not in projection:
        print("WARNING: projection looks empty/invalid; leaving profile unchanged", file=sys.stderr)
        return 0

    existing = PROFILE_PATH.read_text() if PROFILE_PATH.exists() else ""
    desired = compose(projection, existing)

    if existing == desired:
        print("ok: profile/README.md already matches the corpus projection")
        return 0

    if args.check:
        print("DRIFT: profile/README.md is out of date — run scripts/refresh-profile.py", file=sys.stderr)
        return 1

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(desired)
    print(f"Updated profile/README.md from corpus projection ({len(desired.split())} words)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
