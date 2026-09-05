#!/usr/bin/env python3
"""Deliver one already-reviewed Florabase feature without bypassing GitHub protections."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any


REPOSITORY = "alessandrorossato/florabase"
REQUIRED_CHECKS = ("quality", "integration", "build")
BRANCH_PATTERN = re.compile(r"^(feat|fix|docs|ci)/[a-z0-9][a-z0-9._-]*$")
DEFAULT_PR_HEAD_POLL_SECONDS = 2
DEFAULT_PR_HEAD_TIMEOUT_SECONDS = 60


class DeliveryError(Exception):
    pass


@dataclass(frozen=True)
class PullRequest:
    number: int
    node_id: str
    state: str
    head_sha: str
    merge_sha: str | None
    html_url: str
    head_ref: str = ""
    base_ref: str = ""


class Commands:
    def run(self, *command: str, capture: bool = False) -> str:
        try:
            result = subprocess.run(
                command,
                check=True,
                text=True,
                stdout=subprocess.PIPE if capture else None,
                stderr=None,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            rendered = " ".join(command)
            raise DeliveryError(f"command failed: {rendered}") from error
        return result.stdout.strip() if capture else ""


def fail(message: str, *, blocked: bool = False) -> None:
    print(f"feature-deliver: {message}", file=sys.stderr)
    if blocked:
        print("DELIVERY_BLOCKED", file=sys.stderr)
    raise DeliveryError(message)


class Delivery:
    def __init__(self, commands: Commands, sleep: Any = time.sleep, monotonic: Any = time.monotonic) -> None:
        self.commands = commands
        self.sleep = sleep
        self.monotonic = monotonic
        self.poll_seconds = int(os.environ.get("FEATURE_DELIVER_POLL_SECONDS", "10"))
        self.timeout_seconds = int(os.environ.get("FEATURE_DELIVER_TIMEOUT_SECONDS", "1800"))
        self.startup_timeout_seconds = int(
            os.environ.get("FEATURE_DELIVER_STARTUP_TIMEOUT_SECONDS", "300")
        )
        self.delete_timeout_seconds = int(
            os.environ.get("FEATURE_DELIVER_DELETE_TIMEOUT_SECONDS", "120")
        )
        self.pr_head_poll_seconds = int(
            os.environ.get("FEATURE_DELIVER_PR_HEAD_POLL_SECONDS", str(DEFAULT_PR_HEAD_POLL_SECONDS))
        )
        self.pr_head_timeout_seconds = int(
            os.environ.get("FEATURE_DELIVER_PR_HEAD_TIMEOUT_SECONDS", str(DEFAULT_PR_HEAD_TIMEOUT_SECONDS))
        )

    def git(self, *args: str, capture: bool = False) -> str:
        return self.commands.run("git", *args, capture=capture)

    def gh(self, *args: str, capture: bool = False) -> str:
        return self.commands.run("gh", *args, capture=capture)

    def api(self, endpoint: str, *, method: str = "GET", fields: dict[str, str] | None = None) -> Any:
        command = ["api"]
        if method != "GET":
            command.extend(["-X", method])
        command.append(endpoint)
        for name, value in (fields or {}).items():
            command.extend(["-f", f"{name}={value}"])
        raw = self.gh(*command, capture=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            fail(f"GitHub API returned invalid JSON for {endpoint}: {error}", blocked=True)

    @staticmethod
    def normalize_origin(url: str) -> str:
        value = url.strip()
        value = re.sub(r"^git@github\.com:", "https://github.com/", value)
        value = re.sub(r"^ssh://git@github\.com/", "https://github.com/", value)
        return value.removesuffix("/").removesuffix(".git")

    @staticmethod
    def pr_from(value: dict[str, Any]) -> PullRequest:
        head = value.get("head") or {}
        base = value.get("base") or {}
        return PullRequest(
            number=int(value["number"]),
            node_id=str(value["node_id"]),
            state=str(value["state"]).strip().upper(),
            head_sha=str(head.get("sha", "")),
            merge_sha=value.get("merge_commit_sha"),
            html_url=str(value.get("html_url", "")),
            head_ref=str(head.get("ref", "")),
            base_ref=str(base.get("ref", "")),
        )

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            fail(message)

    def preflight(self) -> tuple[str, str, str]:
        self.commands.run("git", "--version")
        self.commands.run("gh", "--version")
        branch = self.git("branch", "--show-current", capture=True)
        self.require(bool(branch), "detached HEAD is not supported")
        self.require(branch != "main", "run this command from a feature branch, not main")
        self.require(bool(BRANCH_PATTERN.fullmatch(branch)), "branch must use feat/, fix/, docs/, or ci/")
        self.require(not self.git("status", "--porcelain", capture=True), "working tree is not clean")
        self.git("rev-parse", "--verify", "HEAD^{commit}")
        origin = self.git("remote", "get-url", "origin", capture=True)
        self.require(
            self.normalize_origin(origin) == f"https://github.com/{REPOSITORY}",
            "origin is not the expected Florabase GitHub repository",
        )
        self.gh("auth", "status")
        self.git("fetch", "origin", "main")
        self.git("show-ref", "--verify", "--quiet", "refs/remotes/origin/main")
        self.git("merge-base", "--is-ancestor", "origin/main", "HEAD")
        base = self.git("merge-base", "origin/main", "HEAD", capture=True)
        self.commands.run("python3", "./scripts/feature-tree-fingerprint.py", "verify", "--branch", branch, "--base", base)
        self.api(f"repos/{REPOSITORY}")

        remote_ref = f"refs/heads/{branch}"
        remote_sha = self.git("ls-remote", "--heads", "origin", remote_ref, capture=True)
        if remote_sha:
            remote_oid = remote_sha.split()[0]
            self.git("fetch", "origin", f"{remote_ref}:refs/remotes/origin/{branch}")
            self.git("merge-base", "--is-ancestor", remote_oid, "HEAD")
        return branch, base, self.git("rev-parse", "HEAD", capture=True)

    def migration_detected(self, base: str, delivery_sha: str) -> bool:
        changed = self.git(
            "diff", "--name-only", f"{base}...{delivery_sha}", "--", "backend/alembic/versions", capture=True
        )
        return any(line.endswith(".py") for line in changed.splitlines())

    def push(self, branch: str, delivery_sha: str) -> None:
        current = self.git("rev-parse", "HEAD", capture=True)
        self.require(current == delivery_sha, "HEAD changed before push; rerun feature-deliver")
        self.git("push", "--set-upstream", "origin", branch)

    def title_and_body(self, branch: str, delivery_sha: str, migration: bool) -> tuple[str, str]:
        subject = self.git("log", "-1", "--format=%s", delivery_sha, capture=True)
        feature = branch.rsplit("/", 1)[-1].upper()
        title = f"{feature}: {subject}" if re.fullmatch(r"[A-Z]+-\d+", feature) else subject
        body = "\n".join(
            [
                f"Branch: `{branch}`",
                f"Feature SHA: `{delivery_sha}`",
                "Local canonical verification completed before this reviewed commit.",
                f"Migration detected: {'yes' if migration else 'no'}.",
            ]
        )
        return title, body

    def validate_open_pr_target(self, pr: PullRequest, branch: str) -> None:
        if pr.state != "OPEN":
            fail(f"pull request #{pr.number} is not open", blocked=True)
        if pr.head_ref != branch or pr.base_ref != "main":
            fail(f"pull request #{pr.number} does not match {branch} into main", blocked=True)

    def is_prior_head(self, head_sha: str, delivery_sha: str) -> bool:
        try:
            self.git("merge-base", "--is-ancestor", head_sha, delivery_sha)
        except DeliveryError:
            return False
        return True

    def wait_for_pr_head(self, pr: PullRequest, branch: str, delivery_sha: str) -> PullRequest:
        self.validate_open_pr_target(pr, branch)
        if pr.head_sha == delivery_sha:
            return pr
        if not self.is_prior_head(pr.head_sha, delivery_sha):
            fail(
                f"pull request #{pr.number} points to unexpected SHA {pr.head_sha}, not delivery SHA {delivery_sha}",
                blocked=True,
            )
        print(f"feature-deliver: waiting for PR #{pr.number} head to update to {delivery_sha}")
        started = self.monotonic()
        while True:
            if self.monotonic() - started >= self.pr_head_timeout_seconds:
                fail(
                    f"timed out waiting for pull request #{pr.number} head to update to delivery SHA {delivery_sha}",
                    blocked=True,
                )
            self.sleep(self.pr_head_poll_seconds)
            current = self.current_pr(pr.number)
            self.validate_open_pr_target(current, branch)
            if current.head_sha == delivery_sha:
                return current
            if not self.is_prior_head(current.head_sha, delivery_sha):
                fail(
                    f"pull request #{pr.number} points to unexpected SHA {current.head_sha}, not delivery SHA {delivery_sha}",
                    blocked=True,
                )

    def find_or_create_pr(self, branch: str, delivery_sha: str, migration: bool) -> PullRequest:
        pulls = self.api(
            f"repos/{REPOSITORY}/pulls?state=open&head=alessandrorossato:{branch}&base=main"
        )
        if not isinstance(pulls, list):
            fail("GitHub returned an invalid pull-request list", blocked=True)
        matching = [
            self.pr_from(value)
            for value in pulls
            if isinstance(value, dict)
            and str(value.get("state", "")).strip().upper() == "OPEN"
            and str((value.get("head") or {}).get("ref", "")) == branch
            and str((value.get("base") or {}).get("ref", "")) == "main"
        ]
        if len(matching) > 1:
            fail(f"multiple open pull requests exist for {branch}", blocked=True)
        if matching:
            pr = matching[0]
            self.validate_open_pr_target(pr, branch)
            return pr
        title, body = self.title_and_body(branch, delivery_sha, migration)
        created = self.api(
            f"repos/{REPOSITORY}/pulls",
            method="POST",
            fields={"title": title, "head": branch, "base": "main", "body": body},
        )
        if not isinstance(created, dict):
            fail("GitHub returned an invalid created pull request", blocked=True)
        pr = self.pr_from(created)
        self.validate_open_pr_target(pr, branch)
        return pr

    def enable_auto_merge(self, pr: PullRequest, delivery_sha: str) -> None:
        mutation = (
            "mutation($id:ID!,$head:GitObjectID!){enablePullRequestAutoMerge(input:"
            "{pullRequestId:$id,mergeMethod:SQUASH,expectedHeadOid:$head})"
            "{pullRequest{number}}}"
        )
        self.gh(
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"id={pr.node_id}",
            "-f",
            f"head={delivery_sha}",
        )

    def current_pr(self, number: int) -> PullRequest:
        value = self.api(f"repos/{REPOSITORY}/pulls/{number}")
        if not isinstance(value, dict):
            fail("GitHub returned an invalid pull request", blocked=True)
        return self.pr_from(value)

    def check_runs(self, delivery_sha: str) -> dict[str, dict[str, Any]]:
        value = self.api(f"repos/{REPOSITORY}/commits/{delivery_sha}/check-runs?per_page=100")
        runs = value.get("check_runs") if isinstance(value, dict) else None
        if not isinstance(runs, list):
            fail("GitHub returned invalid check-run data", blocked=True)
        return {str(run.get("name")): run for run in runs if isinstance(run, dict)}

    def wait_for_checks(self, pr: PullRequest, delivery_sha: str) -> None:
        started = self.monotonic()
        while True:
            current = self.current_pr(pr.number)
            if current.state == "MERGED":
                return
            if current.state != "OPEN":
                fail(f"pull request #{pr.number} is unexpectedly {current.state.lower()}", blocked=True)
            if current.head_sha != delivery_sha:
                fail(f"pull request #{pr.number} no longer points at delivery SHA {delivery_sha}", blocked=True)
            checks = self.check_runs(delivery_sha)
            missing = [name for name in REQUIRED_CHECKS if name not in checks]
            elapsed = self.monotonic() - started
            if missing:
                if elapsed >= self.startup_timeout_seconds:
                    fail(f"Actions did not register current-SHA checks: {', '.join(missing)}", blocked=True)
                self.sleep(self.poll_seconds)
                continue
            running = [name for name in REQUIRED_CHECKS if checks[name].get("status") != "completed"]
            if running:
                if elapsed >= self.timeout_seconds:
                    fail(f"timed out waiting for current-SHA checks: {', '.join(running)}", blocked=True)
                self.sleep(self.poll_seconds)
                continue
            failures = [
                (name, checks[name])
                for name in REQUIRED_CHECKS
                if checks[name].get("conclusion") != "success"
            ]
            if failures:
                details = ", ".join(
                    f"{name} ({run.get('conclusion')}; {run.get('details_url', 'no URL')})"
                    for name, run in failures
                )
                fail(
                    f"current-SHA checks failed for PR #{pr.number}, SHA {delivery_sha}: {details}. "
                    f"Inspect with: gh run list --commit {delivery_sha}",
                    blocked=True,
                )
            return

    def wait_for_merge(self, pr: PullRequest, delivery_sha: str) -> PullRequest:
        started = self.monotonic()
        while True:
            current = self.current_pr(pr.number)
            if current.state == "MERGED":
                if not current.merge_sha:
                    fail(f"merged pull request #{pr.number} has no merge SHA", blocked=True)
                return current
            if current.state != "OPEN" or current.head_sha != delivery_sha:
                fail(f"pull request #{pr.number} cannot be auto-merged safely", blocked=True)
            if self.monotonic() - started >= self.timeout_seconds:
                fail(f"timed out waiting for squash auto-merge of PR #{pr.number}", blocked=True)
            self.sleep(self.poll_seconds)

    def confirm_deleted_branch(self, branch: str) -> None:
        started = self.monotonic()
        remote_ref = f"refs/heads/{branch}"
        while self.git("ls-remote", "--heads", "origin", remote_ref, capture=True):
            if self.monotonic() - started >= self.delete_timeout_seconds:
                fail(f"remote feature branch {branch} was not deleted after merge", blocked=True)
            self.sleep(self.poll_seconds)

    def execute(self) -> None:
        branch, base, delivery_sha = self.preflight()
        migration = self.migration_detected(base, delivery_sha)
        self.push(branch, delivery_sha)
        pr = self.find_or_create_pr(branch, delivery_sha, migration)
        pr = self.wait_for_pr_head(pr, branch, delivery_sha)
        self.enable_auto_merge(pr, delivery_sha)
        self.wait_for_checks(pr, delivery_sha)
        merged = self.wait_for_merge(pr, delivery_sha)
        self.git("fetch", "origin", "main")
        self.git("merge-base", "--is-ancestor", str(merged.merge_sha), "origin/main")
        self.confirm_deleted_branch(branch)
        print("DELIVERY_COMPLETE")
        print(f"PR: #{pr.number}")
        print(f"Feature SHA: {delivery_sha}")
        print(f"Main SHA: {merged.merge_sha}")
        for name in REQUIRED_CHECKS:
            print(f"{name}: passed")
        print(f"Migration: {'yes' if migration else 'no'}")
        if migration:
            print("Database migration detected.")
            print("After make feature-finish, run: make dev-upgrade")


def main() -> None:
    try:
        Delivery(Commands()).execute()
    except DeliveryError:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
