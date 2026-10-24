import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest

import git_branch_cleanup_tool_lite as tool

HAVE_GIT = shutil.which("git") is not None


def git(repo, *args):
    cmd = [
        "git", "-C", repo,
        "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "-c", "commit.gpgsign=false",
    ] + list(args)
    subprocess.run(
        cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def make_repo():
    path = tempfile.mkdtemp()
    git(path, "init", "-q")
    git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    git(path, "commit", "-q", "--allow-empty", "-m", "initial")
    return path


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = tool.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def branch_names(repo):
    return sorted(b["name"] for b in tool.list_branches(repo))


class TestPureFunctions(unittest.TestCase):
    def test_format_table(self):
        rows = [{"name": "a", "last_commit_iso": "2024-01-01", "action": "deleted"}]
        text = tool.format_table(rows)
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("BRANCH"))
        self.assertIn("deleted", lines[1])

    def test_help_mentions_full_version(self):
        self.assertIn(tool.FULL_VERSION_URL, tool.build_parser().format_help())
        self.assertIn(tool.FULL_VERSION_URL, tool.__doc__)

    def test_limit_constant(self):
        self.assertEqual(tool.MAX_BRANCHES, 5)


@unittest.skipUnless(HAVE_GIT, "git not available")
class TestWithRepo(unittest.TestCase):
    def setUp(self):
        self.repo = make_repo()
        self.addCleanup(shutil.rmtree, self.repo, True)

    def test_dry_run_does_not_delete(self):
        git(self.repo, "branch", "merged")
        code, out, _ = run_main(["--repo", self.repo])
        self.assertEqual(code, tool.EXIT_OK)
        self.assertIn("would-delete", out)
        self.assertIn("merged", branch_names(self.repo))

    def test_delete_removes_only_merged(self):
        git(self.repo, "branch", "merged")
        git(self.repo, "checkout", "-q", "-b", "unmerged")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "work")
        git(self.repo, "checkout", "-q", "main")
        code, out, _ = run_main(["--repo", self.repo, "--delete"])
        self.assertEqual(code, tool.EXIT_OK)
        self.assertEqual(branch_names(self.repo), ["main", "unmerged"])

    def test_limit_of_five_per_run(self):
        for i in range(7):
            git(self.repo, "branch", "feat%d" % i)
        code, out, _ = run_main(["--repo", self.repo, "--delete"])
        self.assertEqual(code, tool.EXIT_OK)
        self.assertEqual(len(branch_names(self.repo)), 1 + 2)  # main + 2 left
        self.assertIn("Lite limit", out)
        self.assertIn(tool.FULL_VERSION_URL, out)

    def test_current_branch_is_protected(self):
        git(self.repo, "checkout", "-q", "-b", "current")
        code, out, _ = run_main(["--repo", self.repo, "--delete"])
        self.assertEqual(code, tool.EXIT_OK)
        self.assertIn("current", branch_names(self.repo))

    def test_bad_base(self):
        code, _, err = run_main(["--repo", self.repo, "--base", "nope"])
        self.assertEqual(code, tool.EXIT_BAD_BASE)
        self.assertIn("does not exist", err)

    def test_detached_head(self):
        git(self.repo, "checkout", "-q", "--detach")
        code, _, err = run_main(["--repo", self.repo])
        self.assertEqual(code, tool.EXIT_ERROR)
        self.assertIn("detached", err)

    def test_not_a_repo(self):
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty, True)
        code, _, err = run_main(["--repo", empty])
        self.assertEqual(code, tool.EXIT_ERROR)
        self.assertIn("not a Git repository", err)

    def test_nothing_to_do(self):
        code, out, _ = run_main(["--repo", self.repo])
        self.assertEqual(code, tool.EXIT_OK)
        self.assertIn("nothing to do", out)


if __name__ == "__main__":
    unittest.main()
