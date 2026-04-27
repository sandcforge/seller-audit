#!/usr/bin/env python3
"""Allocate the next attempt directory for an audit.

The seller-audit pipeline writes per-audit artifacts under
``outputs/<uid>/<NN>/``. ``NN`` is a zero-padded 2-digit attempt number
starting at ``00``. Re-audits of the same uid get a fresh ``NN`` so old
attempts (including failed ones) are preserved for debugging.

Usage:
    python skills/seller-audit/scripts/allocate_attempt.py --uid <uid>

Stdout: the absolute path of the newly created attempt directory, e.g.
        ``/repo/outputs/JccozeKEm4PjM4RRLwTIBVVkYJd2/00``
Stderr: ``✓ allocated attempt NN for uid <uid>`` (one line, for human visibility)

Concurrency-safe: ``mkdir`` without ``exist_ok`` is atomic on POSIX, so two
processes racing to allocate ``00/`` for the same uid will produce one winner
and one falls through to ``01/``.

Side effect: writes ``<attempt_dir>/_meta.json`` initialized with the audit's
start timestamp and uid. The verdict step (``generate_report.py``) updates this
file on completion (``completed_at``, ``last_completed_step``, ``verdict``).
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# This script lives at <repo>/skills/seller-audit/scripts/allocate_attempt.py,
# so three parents up is the repo root regardless of the caller's cwd.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Cap the attempt count. 100 is well past any sane re-audit scenario; anything
# higher signals a runaway loop.
MAX_ATTEMPTS = 100


def allocate_attempt(uid: str) -> Path:
    """Atomically claim the next free outputs/<uid>/<NN>/ directory.

    Returns the freshly created Path. Raises RuntimeError if the cap is hit.
    """
    base = REPO_ROOT / "outputs" / uid
    base.mkdir(parents=True, exist_ok=True)
    for n in range(MAX_ATTEMPTS):
        attempt_dir = base / f"{n:02d}"
        try:
            # exist_ok=False (the default) is the atomic claim.
            attempt_dir.mkdir()
            return attempt_dir
        except FileExistsError:
            continue
    raise RuntimeError(
        f"attempt count exhausted (>={MAX_ATTEMPTS}) for uid={uid!r}; "
        f"check outputs/{uid}/ for runaway re-audit loops."
    )


def write_meta(attempt_dir: Path, uid: str) -> None:
    """Initialize _meta.json with the audit's start state.

    Schema (kept stable; generate_report.py updates these fields on completion):
      uid                    str
      attempt                str ("00", "01", ...)
      started_at             ISO 8601 UTC timestamp
      completed_at           null until verdict success
      last_completed_step    null | "extract" | "investigate" | "verdict"
      verdict                null until verdict success | "APPROVE" | "REJECT" | "REVIEW"
    """
    meta = {
        "uid": uid,
        "attempt": attempt_dir.name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "last_completed_step": None,
        "verdict": None,
    }
    (attempt_dir / "_meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Allocate the next outputs/<uid>/<NN>/ work directory "
        "for an audit attempt. Prints the attempt directory's absolute path "
        "to stdout."
    )
    parser.add_argument(
        "--uid",
        required=True,
        help="PalmStreet uid (palmstreet_userid).",
    )
    args = parser.parse_args()

    attempt_dir = allocate_attempt(args.uid)
    write_meta(attempt_dir, args.uid)

    # Stdout: the path (consumable by shell: WORK_DIR=$(allocate_attempt.py ...))
    sys.stdout.write(str(attempt_dir) + "\n")
    # Stderr: human-readable confirmation
    sys.stderr.write(
        f"✓ allocated attempt {attempt_dir.name} for uid {args.uid}\n"
    )


if __name__ == "__main__":
    main()
