#!/usr/bin/env python3
"""git-branch-cleanup-lite: find and remove already-merged local Git branches.

This is the FREE Lite edition of the Git Branch Cleanup Tool.

Lite limitations:
  * local branches only (no remote deletion)
  * at most 5 branches are processed per run
  * no age filter, no keep patterns, no JSON output

Get the full version (age filter, --keep patterns, remote deletion,
JSON output, unlimited branches): https://skeilster.gumroad.com/l/uvpwln

Only the local ``git`` binary is used. Deletions always use
``git branch -d`` (never ``-D``), so unmerged work is never lost.
The default is a dry run; nothing is deleted without ``--delete``.

Exit codes:
    0  success (including "nothing to do")
    1  not a Git repository, git missing, detached HEAD, or other fatal error
    2  base branch does not exist (also used by argparse for usage errors)
    4  run completed, but at least one deletion failed
"""
import argparse
import subprocess
import sys

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BAD_BASE = 2
EXIT_PARTIAL = 4

HEADS_PREFIX = "refs/heads/"
MAX_BRANCHES = 5
FULL_VERSION_URL = "https://skeilster.gumroad.com/l/uvpwln"


class GitNotFound(Exception):
    """Raised when the git executable cannot be started."""


def run_git(repo, args):
    """Run git in *repo* and return the CompletedProcess (never raises on rc != 0)."""
    try:
        return subprocess.run(
            ["git", "-C", repo] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise GitNotFound("git executable not found")


def is_git_repo(repo):
    return run_git(repo, ["rev-parse", "--git-dir"]).returncode == 0


def current_branch(repo):
    """Return the checked-out branch name, or None if HEAD is detached."""
    res = run_git(repo, ["symbolic-ref", "-q", "--short", "HEAD"])
    if res.returncode != 0:
        return None
    return res.stdout.strip() or None


def list_branches(repo):
    """Return a list of dicts with keys: name, iso (last commit date)."""
    fmt = "%(refname)%09%(committerdate:iso-strict)"
    res = run_git(repo, ["for-each-ref", "--format=" + fmt, "refs/heads"])
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "git for-each-ref failed")
    branches = []
    for line in res.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2 or not parts[0].startswith(HEADS_PREFIX):
            continue
        branches.append({"name": parts[0][len(HEADS_PREFIX):], "iso": parts[1]})
    return branches


def branch_exists(repo, name):
    res = run_git(
        repo, ["rev-parse", "--verify", "--quiet", HEADS_PREFIX + name + "^{commit}"]
    )
    return res.returncode == 0


def is_merged(repo, name, base):
    res = run_git(
        repo,
        ["merge-base", "--is-ancestor", HEADS_PREFIX + name, HEADS_PREFIX + base],
    )
    return res.returncode == 0


def find_candidates(repo, branches, base, current):
    """Select merged, non-protected branches. Sorted by name."""
    candidates = []
    for b in branches:
        name = b["name"]
        if name == base or name == current:
            continue
        if not is_merged(repo, name, base):
            continue
        candidates.append({"name": name, "last_commit_iso": b["iso"], "action": ""})
    candidates.sort(key=lambda c: c["name"])
    return candidates


def _msg(res):
    return (res.stderr.strip() or res.stdout.strip() or "unknown error").replace("\n", " ")


def process_candidate(repo, cand, delete):
    """Fill in cand['action'] (and cand['error'] on failure). Returns True on success."""
    if not delete:
        cand["action"] = "would-delete"
        return True
    res = run_git(repo, ["branch", "-d", "--", cand["name"]])
    if res.returncode != 0:
        cand["action"] = "failed"
        cand["error"] = _msg(res)
        return False
    cand["action"] = "deleted"
    return True


def format_table(rows):
    headers = ["BRANCH", "LAST COMMIT", "ACTION"]
    data = [[r["name"], r["last_commit_iso"], r["action"]] for r in rows]
    widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()]
    for row in data:
        lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(row)).rstrip())
    return "\n".join(lines)


def build_parser():
    p = argparse.ArgumentParser(
        prog="git-branch-cleanup-lite",
        description="FREE Lite edition: find and remove already-merged local Git "
        "branches (max %d per run). Dry run by default." % MAX_BRANCHES,
        epilog="Lite limits: local branches only, max %d branches per run, no age "
        "filter, no --keep patterns, no JSON output. "
        "Full version: %s" % (MAX_BRANCHES, FULL_VERSION_URL),
    )
    p.add_argument("--repo", default=".", help="path to the repository (default: .)")
    p.add_argument("--base", default="main", help="base branch (default: main)")
    p.add_argument(
        "--delete",
        action="store_true",
        help="actually delete branches with 'git branch -d' (default: dry run)",
    )
    return p


def _run(args):
    repo = args.repo

    if not is_git_repo(repo):
        print("error: not a Git repository: %s" % repo, file=sys.stderr)
        return EXIT_ERROR

    current = current_branch(repo)
    if current is None:
        print(
            "error: HEAD is detached; check out a branch before running cleanup.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    branches = list_branches(repo)
    if not branches:
        print("Repository has no branches; nothing to do.")
        return EXIT_OK

    if not branch_exists(repo, args.base):
        print("error: base branch '%s' does not exist." % args.base, file=sys.stderr)
        return EXIT_BAD_BASE

    all_candidates = find_candidates(repo, branches, args.base, current)
    if not all_candidates:
        print("No merged branches found; nothing to do.")
        return EXIT_OK

    candidates = all_candidates[:MAX_BRANCHES]
    skipped = len(all_candidates) - len(candidates)

    failures = 0
    for cand in candidates:
        if not process_candidate(repo, cand, args.delete):
            failures += 1

    print(format_table(candidates))
    if not args.delete:
        print("\nDry run: no changes made. Use --delete to remove these branches.")
    if skipped:
        print(
            "\nLite limit: %d more merged branch(es) not processed (max %d per run). "
            "Full version: %s" % (skipped, MAX_BRANCHES, FULL_VERSION_URL)
        )

    for cand in candidates:
        if "error" in cand:
            print("error: %s: %s" % (cand["name"], cand["error"]), file=sys.stderr)

    return EXIT_PARTIAL if failures else EXIT_OK


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except GitNotFound as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    except RuntimeError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
