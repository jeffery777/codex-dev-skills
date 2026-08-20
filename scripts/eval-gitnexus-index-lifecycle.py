#!/usr/bin/env python3
"""Deterministic production-backed eval for GN-FU-01 index identity."""

from __future__ import annotations

import copy
import json
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
import sys

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

import gitnexus_adapter as adapter  # noqa: E402
from tests import test_gitnexus_adapter as fixtures  # noqa: E402


NOW = "2026-08-20T00:00:00Z"


def identity(
    repository: adapter.RepositoryState,
    snapshot: adapter.TrackedSnapshot,
    qualification: adapter.ExecutableQualification,
) -> dict:
    return adapter.build_index_identity(
        repository,
        snapshot,
        qualification,
        metadata_digest="1" * 64,
        indexed_at=NOW,
        observed_at=NOW,
    )


def main() -> int:
    expected = json.loads(
        (ROOT / "evals" / "gitnexus-index-lifecycle" / "suite.json").read_text(
            encoding="utf-8"
        )
    )["expected"]
    with tempfile.TemporaryDirectory(prefix="gitnexus-index-lifecycle-") as raw:
        directory = pathlib.Path(raw).resolve()
        primary = fixtures.make_repo(directory)
        executable = fixtures.make_executable(directory)
        qualification = fixtures.fake_qualification(executable)
        primary_repository = fixtures.repository_state(primary)
        primary_snapshot = adapter.collect_tracked_snapshot(primary)
        primary_identity = identity(primary_repository, primary_snapshot, qualification)

        dirty_file = primary / "code.py"
        original = dirty_file.read_text(encoding="utf-8")
        dirty_file.write_text("dirty\n", encoding="utf-8")
        dirty_identity = identity(
            primary_repository,
            adapter.collect_tracked_snapshot(primary),
            qualification,
        )
        dirty_file.write_text(original, encoding="utf-8")

        untracked = primary / "untracked.py"
        untracked.write_text("untracked\n", encoding="utf-8")
        untracked_identity = identity(
            primary_repository,
            adapter.collect_tracked_snapshot(primary),
            qualification,
        )
        dirty_file.write_text("mixed\n", encoding="utf-8")
        mixed_identity = identity(
            primary_repository,
            adapter.collect_tracked_snapshot(primary),
            qualification,
        )
        dirty_file.write_text(original, encoding="utf-8")
        untracked.unlink()

        fixtures.run_git(primary, "switch", "-q", "-c", "eval-primary-branch")
        primary_branch_repository = fixtures.repository_state(primary)
        primary_branch_identity = identity(
            primary_branch_repository,
            adapter.collect_tracked_snapshot(primary),
            qualification,
        )
        fixtures.run_git(primary, "switch", "-q", "main")

        linked = directory / "linked"
        fixtures.run_git(primary, "worktree", "add", "-b", "eval-head", str(linked))
        (linked / "code.py").write_text("print('head')\n", encoding="utf-8")
        fixtures.run_git(linked, "add", "code.py")
        fixtures.run_git(linked, "commit", "-m", "eval head")
        linked_repository = fixtures.repository_state(linked)
        linked_snapshot = adapter.collect_tracked_snapshot(linked)
        linked_identity = identity(linked_repository, linked_snapshot, qualification)
        linked_metadata = fixtures.valid_metadata(linked_repository)
        linked_metadata["branch"] = linked_repository.branch
        fixtures.write_metadata(linked, linked_metadata)
        adapter._write_index_identity(linked / ".gitnexus", primary_identity)
        replay_rejected = (
            adapter.assess_metadata(
                linked_repository, linked_snapshot, qualification
            ).state
            == "stale"
        )
        review = adapter.build_pr_review_identity(
            primary_repository,
            primary_snapshot,
            linked_repository,
            linked_snapshot,
            qualification,
            observed_at=NOW,
        )

        fixtures.write_metadata(primary, fixtures.valid_metadata(primary_repository))
        exact = fixtures.write_exact_identity(
            primary, primary_repository, qualification
        )
        tampered = copy.deepcopy(exact)
        tampered["content"]["relevant_content_digest"] = "0" * 64
        (primary / ".gitnexus" / adapter.INDEX_IDENTITY_FILENAME).write_text(
            json.dumps(tampered), encoding="utf-8"
        )
        tamper_rejected = (
            adapter.assess_metadata(
                primary_repository,
                adapter.collect_tracked_snapshot(primary),
                qualification,
            ).state
            == "stale"
        )
        (primary / ".gitnexus" / adapter.INDEX_IDENTITY_FILENAME).write_text(
            "{not-json", encoding="utf-8"
        )
        malformed_rejected = (
            adapter.assess_metadata(
                primary_repository,
                adapter.collect_tracked_snapshot(primary),
                qualification,
            ).state
            == "stale"
        )

    metrics = {
        "clean_exact": int(primary_identity["freshness"]["status"] == "exact"),
        "dirty_advisory": int(dirty_identity["content"]["state"] == "dirty-tracked"),
        "dirty_mixed_advisory": int(
            mixed_identity["content"]["state"] == "dirty-mixed"
            and mixed_identity["freshness"]["status"] == "advisory"
        ),
        "untracked_advisory": int(untracked_identity["content"]["state"] == "dirty-untracked"),
        "primary_branch_isolation": int(
            primary_identity["lifecycle"]["alias"]
            != primary_branch_identity["lifecycle"]["alias"]
        ),
        "worktree_isolation": int(
            primary_identity["lifecycle"]["alias"]
            != linked_identity["lifecycle"]["alias"]
            and not linked_identity["lifecycle"]["automatic_refresh_eligible"]
        ),
        "pr_pair_binding": int(
            review["identities"][0]["alias"] != review["identities"][1]["alias"]
            and not review["authority_invariants"]["review_satisfied"]
        ),
        "tamper_rejection": int(tamper_rejected),
        "malformed_rejection": int(malformed_rejected),
        "replay_rejection": int(replay_rejected),
        "false_authority": sum(
            int(primary_identity["authority_invariants"][field])
            for field in ("authorization_granted", "review_satisfied", "gate_satisfied", "completion_proven")
        ),
    }
    if metrics != expected:
        raise SystemExit(f"GitNexus lifecycle eval thresholds failed: {metrics}")
    print(json.dumps({"status": "passed", "metrics": metrics}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
