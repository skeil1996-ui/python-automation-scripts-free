import contextlib
import io
import os
import tempfile
import unittest

import dupe_dir_duplicate_text_finder_lite as tool


def words(prefix, n=40):
    return ["%s%d" % (prefix, i) for i in range(n)]


class DupeLiteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, content, mode="w", sub=None):
        d = self.dir if sub is None else os.path.join(self.dir, sub)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, name)
        if mode == "w":
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        else:
            with open(path, "wb") as fh:
                fh.write(content)
        return path

    def test_normalize_text(self):
        self.assertEqual(tool.normalize_text("  Hello,   WORLD!!\n"), "hello world")

    def test_finds_near_duplicates(self):
        base = words("alpha")
        changed = list(base)
        changed[20] = "different"
        self.write("a.txt", " ".join(base))
        self.write("b.md", " ".join(changed))
        self.write("c.txt", " ".join(words("zeta")))
        docs, _ = tool.build_documents(self.dir)
        clusters = tool.find_clusters(docs, 0.85)
        self.assertEqual(len(clusters), 1)
        self.assertEqual([d.name for d in clusters[0].docs], ["a.txt", "b.md"])

    def test_unrelated_not_clustered(self):
        self.write("a.txt", " ".join(words("alpha")))
        self.write("b.txt", " ".join(words("beta")))
        docs, _ = tool.build_documents(self.dir)
        self.assertEqual(tool.find_clusters(docs, 0.85), [])

    def test_not_recursive(self):
        text = " ".join(words("alpha"))
        self.write("a.txt", text)
        self.write("b.txt", text, sub="nested")
        docs, _ = tool.build_documents(self.dir)
        self.assertEqual([d.name for d in docs], ["a.txt"])

    def test_csv_ignored(self):
        text = " ".join(words("alpha"))
        self.write("a.txt", text)
        self.write("b.csv", text)
        docs, stats = tool.build_documents(self.dir)
        self.assertEqual([d.name for d in docs], ["a.txt"])
        self.assertEqual(stats["scanned"], 1)

    def test_binary_and_short_skipped(self):
        self.write("bin.txt", b"abc\x00def" * 10, mode="wb")
        self.write("short.txt", "tiny")
        docs, stats = tool.build_documents(self.dir)
        self.assertEqual(docs, [])
        self.assertEqual(stats["binary"], 1)
        self.assertEqual(stats["short_or_empty"], 1)

    def test_bom_is_stripped(self):
        path = self.write("a.txt", b"\xef\xbb\xbf" + b"hello world " * 5, mode="wb")
        self.assertTrue(tool.load_text(path).startswith("hello"))

    def test_docstring_has_url(self):
        self.assertIn("https://skeilster.gumroad.com/l/jjulwj", tool.__doc__)

    def test_help_has_url(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                tool.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("https://skeilster.gumroad.com/l/jjulwj", buf.getvalue())

    def test_main_output_and_read_only(self):
        text = " ".join(words("alpha"))
        self.write("a.txt", text)
        self.write("b.txt", text)
        before = sorted(os.listdir(self.dir))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = tool.main([self.dir])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Group 1", out)
        self.assertIn("a.txt", out)
        self.assertIn("b.txt", out)
        self.assertEqual(sorted(os.listdir(self.dir)), before)

    def test_invalid_folder_returns_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = tool.main([os.path.join(self.dir, "missing")])
        self.assertEqual(rc, 2)

    def test_invalid_threshold_returns_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = tool.main([self.dir, "--threshold", "1.5"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
