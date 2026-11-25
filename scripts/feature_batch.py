#!/usr/bin/env python3
"""Prepare and prove a consolidated Florabase delivery without rewriting source branches."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from feature_worktree import (
    AgentState,
    agent_id,
    owned_resources,
    require_no_pending_handoff,
    require_no_running_mounts,
    require_operator_identity,
    require_writer,
    retire_finished_worktree,
    worktrees,
    write_finished_proof,
)
from workflow_environment import BRANCH_PATTERN, Repository, WorkflowError, run
from workflow_resources import (
    FileLock,
    Owner,
    ResourceError,
    Resources,
    verification_lock,
)

BATCH = re.compile(r"ci/(?:wf-04-)?batch-[a-z0-9][a-z0-9._-]*")
FEATURE = re.compile(r"[A-Z][A-Z0-9-]*-[0-9]+")
OID = re.compile(r"[0-9a-f]{40}")
REPOSITORY = "alessandrorossato/florabase"
CHECKS = {"quality", "integration", "build"}
DIRECTORY = "docs/release/evidence/batches"
PROGRESS = "docs/progress.md"
RECEIPT = "info/florabase-feature-verification.json"
REVIEW = "info/florabase-batch-review.json"


def require(condition: object, message: str) -> None:
    if not condition:
        raise WorkflowError(message)


def oid(value: Any) -> str:
    require(isinstance(value, str) and OID.fullmatch(value), "expected a full Git commit SHA")
    return str(value)


def manifest_path(branch: str) -> str:
    require(BATCH.fullmatch(branch), "expected a batch branch, for example ci/batch-example")
    return f"{DIRECTORY}/{branch.split('/', 1)[1]}.json"


def batch_summary(value: dict[str, Any]) -> str:
    """Return the reviewed one-line batch summary used for the PR title (WF-07)."""
    text = value.get("summary")
    require(
        isinstance(text, str)
        and 10 <= len(text) <= 72
        and text == text.strip()
        and text.isprintable()
        and "`" not in text
        # A commit-like hex run contains a digit; words such as "feedback" stay allowed.
        and not re.search(r"(?<![0-9a-fA-F])(?=[a-fA-F]*[0-9])[0-9a-fA-F]{7,}(?![0-9a-fA-F])", text)
        and not re.match(r"[a-z]+\s*(\([^)]*\))?\s*!?\s*:", text, re.IGNORECASE),
        "batch summary must be one plain line of 10-72 characters without commit IDs or a type prefix",
    )
    return str(text)


def summary_title(value: dict[str, Any]) -> str:
    """Return the validated summarized PR title of a batch plan or manifest (WF-07)."""
    branch = str(value.get("branch"))
    name = branch.removeprefix("ci/").removeprefix("wf-04-").removeprefix("batch-")
    title = f"chore(release): {batch_summary(value)} (batch {name})"
    require(len(title) <= 100, "batch PR title is too long; shorten the summary or split the batch")
    return title


def json_object(raw: str) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON member: {key}")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(value, dict), "expected a JSON object")
    return dict(value)


def read_json(path: Path) -> dict[str, Any]:
    require(not path.is_symlink(), f"refusing linked evidence file: {path}")
    return json_object(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    require(not path.is_symlink() and not path.parent.is_symlink(), f"refusing linked path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as output:
        temporary = Path(output.name)
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def status(path: Path) -> str:
    return run(
        ["git", "--no-optional-locks", "-C", str(path), "status", "--porcelain"], capture=True
    )


def lock_busy(path: Path) -> bool:
    try:
        with path.open("rb") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(lock, fcntl.LOCK_UN)
    except FileNotFoundError:
        return False
    return False


def attached(repo: Repository, branch: str) -> Repository:
    matches = [item for item in worktrees(repo) if item.get("branch") == f"refs/heads/{branch}"]
    require(len(matches) == 1, f"{branch}: exactly one attached source worktree is required")
    item = matches[0]
    path = Path(item["worktree"])
    require(
        "prunable" not in item and "locked" not in item and not path.is_symlink(),
        f"{branch}: source registration is unavailable or locked",
    )
    target = Repository(path)
    require(
        target.source == path and target.common == repo.common and target.source != repo.primary,
        f"{branch}: source worktree or repository identity differs",
    )
    return target


def commits(repo: Repository, base: str, tip: str) -> list[str]:
    return repo.git("rev-list", "--topo-order", "--reverse", f"{base}..{tip}").splitlines()


def sources_from(value: dict[str, Any]) -> list[dict[str, Any]]:
    sources = value.get("sources")
    if not isinstance(sources, list) or not sources:
        raise WorkflowError("batch needs at least one source")
    ids, branches, tips = set(), set(), set()
    for item in sources:
        require(isinstance(item, dict), "invalid source record")
        feature, branch, tip = item.get("id"), item.get("branch"), oid(item.get("tip"))
        require(
            isinstance(feature, str) and FEATURE.fullmatch(feature) and feature != "WF-04",
            "invalid or reserved source feature identifier",
        )
        require(
            isinstance(branch, str)
            and BRANCH_PATTERN.fullmatch(branch)
            and not BATCH.fullmatch(branch),
            f"{feature}: invalid source branch",
        )
        require(
            feature not in ids and branch not in branches and tip not in tips,
            f"{feature}: duplicate source identity",
        )
        ids.add(feature)
        branches.add(branch)
        tips.add(tip)
    return list(sources)


def snapshot(repo: Repository, base: str, item: dict[str, Any]) -> dict[str, Any]:
    branch, tip = item["branch"], oid(item["tip"])
    target = attached(repo, branch)
    writer = require_no_pending_handoff(target)["writer"]
    require(writer, f"{branch}: no source writer claim")
    require(
        target.git("branch", "--show-current") == branch
        and target.git("rev-parse", "HEAD") == tip
        and not status(target.source),
        f"{branch}: source tip or clean worktree changed",
    )
    require(
        not lock_busy(target.metadata / "florabase-verification.lock"),
        f"{branch}: verification is active",
    )
    reviewer, evidence = item.get("reviewer"), item.get("evidence")
    require(
        isinstance(reviewer, str) and reviewer.strip() and reviewer != writer["agent"],
        f"{branch}: independent review of the pinned tip is required",
    )
    if (
        not isinstance(evidence, list)
        or not evidence
        or not all(isinstance(p, str) for p in evidence)
    ):
        raise WorkflowError(f"{branch}: committed evidence references are required")
    for path in evidence:
        require(
            re.fullmatch(r"docs/[\w./-]+\.md", path) and ".." not in Path(path).parts,
            f"{branch}: invalid evidence path",
        )
        require(
            repo.git("cat-file", "-t", f"{tip}:{path}") == "blob",
            f"{branch}: evidence path is missing at the pinned tip",
        )
    source_base = repo.git("merge-base", base, tip)
    require(
        set(evidence).intersection(paths_between(repo, source_base, tip)),
        f"{branch}: evidence references are unchanged from the source base",
    )
    changes = commits(repo, base, tip)
    require(changes, f"{branch}: no commits outside the batch base")
    return {
        "id": item["id"],
        "branch": branch,
        "tip": tip,
        "base": source_base,
        "commits": changes,
        "reviewer": reviewer,
        "evidence": evidence,
        "writer": writer["agent"],
        "claim": writer["claim_id"],
    }


def parents(repo: Repository, sha: str) -> list[str]:
    return repo.git("rev-list", "--parents", "-1", sha).split()[1:]


def tree(repo: Repository, sha: str) -> str:
    return repo.git("rev-parse", f"{sha}^{{tree}}")


def paths_between(repo: Repository, before: str, after: str) -> list[str]:
    return sorted(repo.git("diff", "--name-only", "-z", before, after, "--").split("\0"))[1:]


def progress_bytes(repo: Repository, sha: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo.source), "show", f"{sha}:{PROGRESS}"])


def additive_progress(repo: Repository, previous: str, tip: str) -> bytes:
    common = progress_bytes(repo, repo.git("merge-base", previous, tip))
    ours, theirs = progress_bytes(repo, previous), progress_bytes(repo, tip)
    # Both sides usually insert below the shared "# Engineering progress" heading: set aside the
    # longest line prefix all three versions share, merge the remainders, then restore it.
    lines = [text.splitlines(keepends=True) for text in (common, ours, theirs)]
    shared = 0
    while shared < len(lines[0]) - 1 and all(
        shared < len(side) and side[shared] == lines[0][shared] for side in lines[1:]
    ):
        shared += 1
    header = b"".join(lines[0][:shared])
    size = len(header)
    return header + _additive_progress(common[size:], ours[size:], theirs[size:])


def _additive_progress(common: bytes, ours: bytes, theirs: bytes) -> bytes:
    require(
        bool(common),
        "progress conflict cannot be resolved by retaining both sets of additions",
    )
    if ours.count(common) == 1 and theirs.count(common) == 1:
        prefix, suffix = ours.split(common)
        other_prefix, other_suffix = theirs.split(common)
        return prefix + other_prefix + common + suffix + other_suffix
    # Allow a pure top-of-file prepend from the incoming source when the integration branch
    # already carried a non-conflicting edit deeper in docs/progress.md (for example on main).
    if theirs.endswith(common) and theirs.count(common) == 1:
        other_prefix = theirs[: -len(common)]
        common_lines = common.splitlines(keepends=True)
        anchor = b"".join(common_lines[: min(len(common_lines), 3)])
        if other_prefix and other_prefix.endswith(b"\n") and anchor and ours.count(anchor) == 1:
            idx = ours.index(anchor)
            prefix, ours_body = ours[:idx], ours[idx:]
            if prefix and prefix.endswith(b"\n"):
                return prefix + other_prefix + ours_body
    raise WorkflowError("progress conflict cannot be resolved by retaining both sets of additions")


def merge_result(repo: Repository, previous: str, tip: str) -> tuple[str, list[str]]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo.source),
            "merge-tree",
            "--write-tree",
            "--name-only",
            "--no-messages",
            "-z",
            previous,
            tip,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    lines = result.stdout.strip("\0").split("\0")
    if result.returncode == 0:
        return oid(lines[0]), []
    require(
        result.returncode == 1 and lines[1:] == [PROGRESS],
        f"source {tip} has an unsupported conflict: {', '.join(lines[1:]) or result.stderr.strip()}",
    )
    return oid(lines[0]), [PROGRESS]


def validate_merge(repo: Repository, previous: str, tip: str, merge: str, resolutions: Any) -> None:
    require(parents(repo, merge) == [previous, tip], "source merge has unexpected parents")
    expected, conflicts = merge_result(repo, previous, tip)
    require(resolutions == conflicts, "recorded merge resolutions do not match Git")
    if not conflicts:
        require(
            tree(repo, merge) == expected, "source merge differs from the reproducible merge tree"
        )
        return
    require(
        set(paths_between(repo, expected, merge)) <= {PROGRESS}
        and progress_bytes(repo, merge) == additive_progress(repo, previous, tip),
        "source merge lost changes or differs from the additive progress resolution",
    )


def load_manifest(repo: Repository, branch: str, head: str) -> dict[str, Any]:
    path = manifest_path(branch)
    value = json_object(repo.git("show", f"{oid(head)}:{path}"))
    require(
        type(value.get("version")) is int
        and value["version"] == 1
        and value.get("branch") == branch,
        "unknown batch manifest version or branch",
    )
    if "summary" in value:
        summary_title(value)
    base, bootstrap = oid(value.get("base")), oid(value.get("bootstrap"))
    if "correction" in value:
        correction = value["correction"]
        prior = oid(correction["supersedes"])
        require(
            parents(repo, head) == [prior], "batch correction must directly extend its prior head"
        )
        original = load_manifest(repo, branch, prior)
        require(
            correction.get("provenance_head", prior)
            == original.get("correction", {}).get(
                "provenance_head", original.get("correction", {}).get("supersedes", prior)
            ),
            "batch correction changes the original PR provenance head",
        )
        require(
            {key: field for key, field in value.items() if key != "correction"}
            == {key: field for key, field in original.items() if key != "correction"},
            "batch correction changes the original provenance",
        )
        changed = set(paths_between(repo, prior, head)) - {path}
        require(
            changed
            and changed == set(correction["paths"])
            and all(name.startswith(("scripts/", "docs/")) for name in changed)
            and isinstance(correction.get("reason"), str)
            and correction["reason"].strip(),
            "batch correction must account for each changed workflow or documentation path",
        )
        return value
    bootstrap_commits = commits(repo, base, bootstrap)
    require(
        value.get("bootstrap_commits") == bootstrap_commits, "bootstrap commit inventory differs"
    )
    require(
        repo.git("merge-base", base, bootstrap) == base,
        "bootstrap does not contain the pinned base",
    )
    require(
        all(len(parents(repo, sha)) == 1 for sha in bootstrap_commits), "bootstrap must be linear"
    )
    previous = bootstrap
    for item in sources_from(value):
        tip, merge = oid(item["tip"]), oid(item.get("merge"))
        require(
            item.get("base") == repo.git("merge-base", base, tip)
            and item.get("commits") == commits(repo, base, tip)
            and item["commits"],
            f"{item['id']}: invalid source ancestry or commit inventory",
        )
        validate_merge(repo, previous, tip, merge, item.get("resolutions"))
        previous = merge
    followups = value.get("reconciliation")
    if not isinstance(followups, dict) or not all(
        isinstance(name, str)
        and (
            (name.startswith("docs/") and name.endswith(".md"))
            or (name.startswith("scripts/") and name.endswith(".py"))
        )
        and ".." not in Path(name).parts
        and isinstance(reason, str)
        and reason.strip()
        for name, reason in followups.items()
    ):
        raise WorkflowError("invalid reconciliation record")
    require(
        parents(repo, head) == [previous]
        and set(paths_between(repo, previous, head)) == {path, *followups},
        "final manifest commit includes unexpected edits or omits recorded reconciliation",
    )
    return value


def proposal(repo: Repository, request: dict[str, Any]) -> dict[str, Any]:
    repo.require_origin()
    base, branch = oid(request.get("base")), request.get("branch")
    if not isinstance(branch, str):
        raise WorkflowError("expected a batch branch")
    manifest_path(branch)
    require(
        repo.git("rev-parse", "origin/main") == base,
        "cached origin/main differs from the approved base",
    )
    result = {**request, "version": 1, "sources": [], "blockers": []}
    for item in sources_from(request):
        try:
            result["sources"].append(snapshot(repo, base, item))
        except (WorkflowError, OSError) as error:
            result["blockers"].append({"id": item["id"], "message": str(error)})
    return result


def discover(repo: Repository) -> list[dict[str, Any]]:
    result = []
    for item in worktrees(repo):
        branch = item.get("branch", "").removeprefix("refs/heads/")
        if not BRANCH_PATTERN.fullmatch(branch) or BATCH.fullmatch(branch):
            continue
        entry: dict[str, Any] = {
            "branch": branch,
            "tip": item.get("HEAD"),
            "worktree": item["worktree"],
            "blockers": ["exact-tip independent review must be supplied in a request"],
        }
        try:
            target = attached(repo, branch)
            entry["writer"] = require_no_pending_handoff(target)["writer"]
            if not entry["writer"]:
                entry["blockers"].append("no source writer claim")
            if status(target.source):
                entry["blockers"].append("source worktree is dirty")
            if lock_busy(target.metadata / "florabase-verification.lock"):
                entry["blockers"].append("source verification is active")
        except (WorkflowError, OSError) as error:
            entry["blockers"].append(str(error))
        result.append(entry)
    return sorted(result, key=lambda entry: entry["branch"])


def prepare(repo: Repository, plan: dict[str, Any]) -> None:
    agent_id(required=True)
    require_writer(repo)
    require(AgentState(repo).load()["writer"], "the integration worktree must be claimed")
    require(
        not plan.get("blockers") and plan == proposal(repo, plan),
        "source plan is blocked or changed",
    )
    branch, base = plan["branch"], oid(plan["base"])
    path = manifest_path(branch)
    summary_title(plan)
    summary = batch_summary(plan)
    require(
        repo.git("branch", "--show-current") == branch and not status(repo.source),
        "prepare from the clean claimed batch worktree",
    )
    require(not (repo.source / path).exists(), "a batch manifest already exists")
    bootstrap = repo.git("rev-parse", "HEAD")
    require(
        repo.git("merge-base", base, bootstrap) == base,
        "batch bootstrap is not based on pinned main",
    )
    previous = bootstrap
    prepared = []
    with verification_lock(repo.metadata):
        for item in sources_from(plan):
            tip = oid(item["tip"])
            require(
                repo.git("merge-base", previous, tip) != tip,
                f"{item['id']}: source already contained",
            )
            expected, conflicts = merge_result(repo, previous, tip)
            if conflicts:
                content = additive_progress(repo, previous, tip)
                merge = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo.source),
                        "merge",
                        "--no-ff",
                        "--no-commit",
                        "--no-edit",
                        tip,
                    ],
                    check=False,
                )
                require(
                    merge.returncode == 1
                    and repo.git("diff", "--name-only", "--diff-filter=U") == PROGRESS,
                    "unexpected merge state; inspect the isolated batch worktree",
                )
                (repo.source / PROGRESS).write_bytes(content)
                repo.git("add", "--", PROGRESS)
            else:
                repo.git("merge", "--no-ff", "--no-commit", "--no-edit", tip)
                require(
                    repo.git("write-tree") == expected,
                    "staged merge differs from reproducible tree",
                )
            repo.git("commit", "-m", f"Merge {item['id']} {item['branch']} at {tip}")
            merged = repo.git("rev-parse", "HEAD")
            validate_merge(repo, previous, tip, merged, conflicts)
            prepared.append({**item, "merge": merged, "resolutions": conflicts})
            previous = merged
        require(plan == proposal(repo, plan), "source plan changed during preparation")
        write_json(
            repo.source / path,
            {
                "version": 1,
                "branch": branch,
                "summary": summary,
                "base": base,
                "bootstrap": bootstrap,
                "bootstrap_commits": commits(repo, base, bootstrap),
                "sources": prepared,
                "reconciliation": {},
            },
        )
    print(f"Prepared {branch}; commit {path} with the reviewed reconciliation")


def title_body(value: dict[str, Any], head: str, migration: bool) -> tuple[str, str]:
    bootstrap = value["bootstrap_commits"]
    entries = ([("WF-04", "Workflow bootstrap", bootstrap)] if bootstrap else []) + [
        (item["id"], item["branch"], item["commits"]) for item in sources_from(value)
    ]
    short = [sha[:12] for _, _, shas in entries for sha in shas]
    require(
        len(set(short)) == len(set(sha for _, _, shas in entries for sha in shas)),
        "source commit abbreviations collide",
    )
    # Manifests without a summary predate WF-07; their delivered PR titles must regenerate exactly.
    summary = batch_summary(value) if "summary" in value else None
    if summary is None:
        title = "Batch " + ", ".join(
            f"{feature} {' '.join(sha[:12] for sha in shas)}" for feature, _, shas in entries
        )
        require(
            len(title) <= 256,
            "batch provenance would exceed GitHub's PR title limit; split the batch",
        )
    else:
        title = summary_title(value)
    body = "\n".join(
        ([f"Summary: {summary}", ""] if summary else [])
        + [
            f"Batch head: `{head}`",
            f"Pinned main: `{value['base']}`",
            f"Manifest: `{manifest_path(value['branch'])}`",
            f"Migration detected: {'yes' if migration else 'no'}.",
            "",
        ]
        + [
            f"- {feature} ({branch}): " + ", ".join(f"`{sha}`" for sha in shas)
            for feature, branch, shas in entries
        ]
    )
    return title, body


def strict_protection(rules: Any) -> set[int]:
    require(
        isinstance(rules, list) and all(isinstance(rule, dict) for rule in rules),
        "invalid GitHub main rules response",
    )
    squash, strict = set(), set()
    for rule in rules:
        parameters = rule.get("parameters") or {}
        if rule.get("type") == "pull_request" and "squash" in parameters.get(
            "allowed_merge_methods", []
        ):
            squash.add(rule.get("ruleset_id"))
        if (
            rule.get("type") == "required_status_checks"
            and parameters.get("strict_required_status_checks_policy") is True
            and CHECKS
            <= {
                check["context"]
                for check in parameters["required_status_checks"]
                if check.get("integration_id") == 15368
            }
        ):
            strict.add(rule.get("ruleset_id"))
    require(squash, "main needs a pull-request rule allowing protected squash")
    require(strict, "main needs strict up-to-date GitHub Actions checks")
    ids = squash | strict
    require(
        all(type(identifier) is int and identifier > 0 for identifier in ids),
        "cannot identify the rulesets enforcing main protection",
    )
    return ids


def validate_ruleset(identifier: int, value: Any) -> None:
    require(
        isinstance(value, dict)
        and value.get("id") == identifier
        and value.get("target") == "branch"
        and value.get("enforcement") == "active"
        and value.get("bypass_actors") == [],
        f"ruleset {identifier} is inactive or has unproven bypass restrictions",
    )


def validate_platform_tree(
    repo: Repository, branch: str, base: str, head: str, merged: str
) -> None:
    value = json_object(repo.git("show", f"{head}:{manifest_path(branch)}"))
    require(
        value.get("branch") == branch
        and value.get("base") == base
        and type(value.get("version")) is int
        and value["version"] == 1
        and tree(repo, head) == tree(repo, merged),
        "platform batch merge differs from the pinned base or verified head tree",
    )


def finalized_receipt(repo: Repository, branch: str, head: str, base: str) -> dict[str, Any]:
    require(
        repo.git("rev-parse", "HEAD") == head and not status(repo.source),
        "batch worktree differs from frozen HEAD",
    )
    receipt = read_json(repo.metadata / RECEIPT)
    require(
        receipt.get("version") == 3
        and receipt.get("head") == head
        and receipt.get("verification", {}).get("mode") == "full"
        and receipt.get("stage_evidence") == {"mode": "fresh", "reused": []},
        "batch requires a fresh v3 FULL receipt with no reused stages",
    )
    verified = subprocess.run(
        [
            "python3",
            str(repo.source / "scripts/feature-tree-fingerprint.py"),
            "verify",
            "--branch",
            branch,
            "--base",
            base,
        ],
        cwd=repo.source,
        capture_output=True,
        text=True,
        check=False,
    )
    require(
        verified.returncode == 0, verified.stderr.strip() or "cannot validate exact-tree receipt"
    )
    review = read_json(repo.metadata / REVIEW)
    require(
        review.get("head") == head
        and review.get("tree") == tree(repo, head)
        and review.get("base") == base
        and review.get("result") == "pass"
        and bool(review.get("evidence"))
        and bool(review.get("reviewer"))
        and review["reviewer"] != (AgentState(repo).load()["writer"] or {}).get("agent"),
        "missing independent approval of the exact batch commit",
    )
    require(
        datetime.fromisoformat(receipt["completed_at"])
        >= datetime.fromisoformat(review["recorded_at"]),
        "the fresh gate must follow independent approval",
    )
    return {
        "receipt": receipt,
        "review": review,
        "receipt_sha256": hashlib.sha256((repo.metadata / RECEIPT).read_bytes()).hexdigest(),
    }


def squash_proof(repo: Repository, batch: dict[str, Any], head: str, merge: str) -> None:
    require(
        parents(repo, merge) == [batch["base"]] and tree(repo, merge) == tree(repo, head),
        "squash commit differs from the pinned base or verified integration tree",
    )
    repo.git("merge-base", "--is-ancestor", merge, "origin/main")


def proof_file(repo: Repository, pr: int) -> Path:
    require(type(pr) is int and pr > 0, "a positive batch PR number is required")
    return repo.common / "info" / f"florabase-batch-pr-{pr}.json"


def proof_ref(pr: int) -> str:
    return f"refs/florabase/batches/pr-{pr}"


def record_delivery(
    repo: Repository, pr: int, branch: str, head: str, merge: str, evidence: dict[str, Any]
) -> None:
    require_operator_identity()
    batch = load_manifest(repo, branch, head)
    squash_proof(repo, batch, head, merge)
    path = proof_file(repo, pr)
    pinned = repo.git("for-each-ref", "--format=%(objectname)", proof_ref(pr))
    require(pinned in ("", head), "a different integration head is already archived for this PR")
    if not pinned:
        repo.git("update-ref", proof_ref(pr), head, "0" * 40)
    write_json(
        path, {"version": 1, "pr": pr, "branch": branch, "head": head, "merge": merge, **evidence}
    )


def delivered_batch(repo: Repository, pr: int) -> tuple[dict[str, Any], dict[str, Any]]:
    proof = read_json(proof_file(repo, pr))
    branch, head, merge = proof["branch"], oid(proof["head"]), oid(proof["merge"])
    require(
        proof.get("version") == 1
        and proof.get("pr") == pr
        and repo.git("rev-parse", proof_ref(pr)) == head
        and proof["review"]["head"] == head
        and proof["review"]["result"] == "pass"
        and proof["receipt"]["head"] == head
        and proof["receipt"]["branch"] == branch
        and proof["receipt"]["version"] == 3
        and proof["receipt"]["verification"]["mode"] == "full"
        and proof["receipt"]["stage_evidence"] == {"mode": "fresh", "reused": []},
        "batch delivery evidence is incomplete",
    )
    archived = (json.dumps(proof["receipt"], sort_keys=True) + "\n").encode()
    require(
        hashlib.sha256(archived).hexdigest() == proof["receipt_sha256"],
        "archived batch receipt checksum differs",
    )
    batch = load_manifest(repo, branch, head)
    require(
        proof["receipt"]["base"] == batch["base"] and proof["review"]["tree"] == tree(repo, head),
        "archived batch receipt or review differs from the delivered tree",
    )
    squash_proof(repo, batch, head, merge)
    return batch, proof


def verify_pr(value: dict[str, Any], proof: dict[str, Any]) -> None:
    require(
        value.get("number") == proof["pr"]
        and value.get("merged") is True
        and value.get("state") == "closed"
        and value.get("merge_commit_sha") == proof["merge"]
        and value.get("head", {}).get("ref") == proof["branch"]
        and value.get("head", {}).get("sha") == proof["head"]
        and value.get("head", {}).get("repo", {}).get("full_name") == REPOSITORY
        and value.get("base", {}).get("ref") == "main"
        and value.get("base", {}).get("repo", {}).get("full_name") == REPOSITORY,
        "GitHub PR identity, repository, head or squash commit differs from the delivery proof",
    )


def finish_target(repo: Repository, branch: str, tip: str, proof: dict[str, Any]) -> Repository:
    records = worktrees(repo)
    if any(item.get("branch") == f"refs/heads/{branch}" for item in records):
        return attached(repo, branch)
    matches = []
    for item in records:
        if (
            "detached" not in item
            or item.get("HEAD") != tip
            or "prunable" in item
            or "locked" in item
        ):
            continue
        path = Path(item["worktree"])
        if path.is_symlink() or not path.is_dir():
            continue
        target = Repository(path)
        if target.source != path or target.common != repo.common:
            continue
        try:
            recorded = read_json(target.metadata / "info/florabase-finished.json")
        except FileNotFoundError:
            continue
        if (
            recorded.get("version"),
            recorded.get("batch_pr"),
            recorded.get("branch"),
            recorded.get("sha"),
            recorded.get("merge"),
        ) == (2, proof["pr"], branch, tip, proof["merge"]):
            matches.append(target)
    require(len(matches) == 1, f"{branch}: no attached source or resumable batch finish")
    return matches[0]


def finish_source(repo: Repository, item: dict[str, Any], proof: dict[str, Any]) -> Path:
    require_operator_identity()
    branch, tip = item["branch"], oid(item["tip"])
    source = finish_target(repo, branch, tip, proof)
    state = AgentState(source)
    with FileLock(state.lock, "source writer state"), verification_lock(source.metadata):
        require_no_pending_handoff(source)
        current = source.git("branch", "--show-current")
        ref = f"refs/heads/{branch}"
        local_tip = source.git("for-each-ref", "--format=%(objectname)", ref)
        require(
            current in ("", branch)
            and local_tip in ("", tip)
            and source.git("rev-parse", "HEAD") == tip
            and not status(source.source),
            f"{branch}: source tip or clean worktree changed after the batch",
        )
        quality = Owner.quality(source.source, source.metadata)
        remaining = owned_resources(source)
        require(
            not (set(remaining) - {quality.project}),
            f"{branch}: source still owns Docker resources",
        )
        require_no_running_mounts(source.source)
        if quality.project in remaining:
            Resources(quality).clean()
        require(not owned_resources(source), f"{branch}: source still owns Docker resources")
        write_finished_proof(source, branch, tip, proof["merge"], batch_pr=proof["pr"])
        if current:
            source.git("switch", "--detach", tip)
        if local_tip:
            source.git("update-ref", "-d", ref, tip)
        state.path.unlink(missing_ok=True)
    return source.source


def validate_finished_source(repo: Repository, pr: int, branch: str, tip: str, merge: str) -> None:
    batch, proof = delivered_batch(repo, pr)
    require(
        proof["merge"] == merge
        and any(item["branch"] == branch and item["tip"] == tip for item in sources_from(batch)),
        "source is omitted or differs from the exact verified batch delivery",
    )


def finish(repo: Repository, pr: int, source_branch: str | None) -> int:
    require_operator_identity()
    repo.require_origin()
    require(
        repo.source == repo.primary
        and repo.git("branch", "--show-current") == "main"
        and not status(repo.source),
        "run batch finish from clean primary main",
    )
    repo.git("fetch", "origin", "main")
    batch, proof = delivered_batch(repo, pr)
    verify_pr(
        json_object(run(["gh", "api", f"repos/{REPOSITORY}/pulls/{pr}"], capture=True)), proof
    )
    selected = [item for item in sources_from(batch) if source_branch in (None, item["branch"])]
    require(selected, "requested source is omitted from the verified batch")
    repo.git("merge", "--ff-only", "origin/main")
    keep_worktree = os.environ.get("KEEP_WORKTREE") == "1"
    current_cwd = Path.cwd().resolve()
    failed = False
    for item in selected:
        try:
            source_path = finish_source(repo, item, proof)
        except (WorkflowError, ResourceError, OSError) as error:
            print(f"UNFINISHED {item['branch']}: {error}", file=sys.stderr)
            failed = True
        else:
            if keep_worktree:
                print(
                    f"FINISHED {item['branch']} at {item['tip']}; "
                    f"RETAINED {source_path} (KEEP_WORKTREE=1)"
                )
            elif current_cwd.is_relative_to(source_path.resolve()):
                print(
                    f"FINISHED {item['branch']} at {item['tip']}; "
                    f"RETAINED {source_path} (current working directory)"
                )
            else:
                retired, reason = retire_finished_worktree(repo, source_path)
                if retired:
                    print(f"FINISHED {item['branch']} at {item['tip']}; RETIRED {source_path}")
                else:
                    print(
                        f"FINISHED {item['branch']} at {item['tip']}; "
                        f"RETAINED {source_path} ({reason})"
                    )
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan").add_argument("request", nargs="?", type=Path)
    commands.add_parser("prepare").add_argument("plan", type=Path)
    review = commands.add_parser("review")
    review.add_argument("file", type=Path)
    finish_parser = commands.add_parser("finish")
    finish_parser.add_argument("pr", type=int)
    finish_parser.add_argument("--source")
    args = parser.parse_args()
    try:
        repo = Repository(Path.cwd())
        if args.command == "plan":
            if args.request is None:
                print(json.dumps(discover(repo), indent=2, sort_keys=True))
                return 0
            value = proposal(repo, read_json(args.request))
            print(json.dumps(value, indent=2, sort_keys=True))
            return int(bool(value["blockers"]))
        if args.command == "prepare":
            prepare(repo, read_json(args.plan))
        elif args.command == "review":
            require_writer(repo)
            state = AgentState(repo).load()
            value = read_json(args.file)
            branch = repo.git("branch", "--show-current")
            head = repo.git("rev-parse", "HEAD")
            manifest = load_manifest(repo, branch, head)
            require(
                state["writer"]
                and value.get("reviewer") not in (None, "", state["writer"]["agent"])
                and value.get("result") == "pass"
                and value.get("head") == head
                and value.get("base") == manifest["base"]
                and value.get("tree") == tree(repo, head)
                and value.get("evidence")
                and not status(repo.source),
                "review must independently approve the exact clean batch commit",
            )
            with verification_lock(repo.metadata):
                value["recorded_at"] = datetime.now(UTC).isoformat()
                write_json(repo.metadata / REVIEW, value)
        elif args.command == "finish":
            return finish(repo, args.pr, args.source)
    except (WorkflowError, ResourceError, OSError, KeyError, TypeError, ValueError) as error:
        print(f"feature-batch: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
