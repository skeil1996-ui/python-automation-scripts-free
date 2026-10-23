import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import organizer  # noqa: E402


class LiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def touch(self, name, text="x"):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_sort_and_undo(self):
        for n in ["a.JPG", "b.pdf", "c.zip", "d.weird"]:
            self.touch(n)
        self.assertEqual(organizer.main([str(self.root)]), 0)
        self.assertTrue((self.root / "Images" / "a.JPG").exists())
        self.assertTrue((self.root / "Documents" / "b.pdf").exists())
        self.assertTrue((self.root / "Archives" / "c.zip").exists())
        self.assertTrue((self.root / "Other" / "d.weird").exists())
        self.assertEqual(organizer.main(["--undo", str(self.root)]), 0)
        self.assertEqual(sorted(p.name for p in self.root.iterdir() if p.is_file()),
                         ["a.JPG", "b.pdf", "c.zip", "d.weird"])
        self.assertFalse((self.root / "Images").exists())

    def test_dry_run(self):
        self.touch("a.png")
        organizer.main([str(self.root), "--dry-run"])
        self.assertTrue((self.root / "a.png").exists())

    def test_no_overwrite(self):
        self.touch("Images/a.png", "old")
        self.touch("a.png", "new")
        organizer.main([str(self.root)])
        self.assertEqual((self.root / "Images" / "a.png").read_text(), "old")
        self.assertEqual((self.root / "Images" / "a (1).png").read_text(), "new")

    def test_hidden_files_untouched(self):
        self.touch(".env")
        organizer.main([str(self.root)])
        self.assertTrue((self.root / ".env").exists())


if __name__ == "__main__":
    unittest.main()
