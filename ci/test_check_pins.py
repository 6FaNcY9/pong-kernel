import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_pins  # noqa: E402

SHA = "a" * 40
REPO = Path(__file__).resolve().parent.parent


def tree(files):
    d = Path(tempfile.mkdtemp())
    for name, text in files.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return d


class CheckPins(unittest.TestCase):
    def test_tag_ref_rejected(self):
        d = tree({".github/actions/x/action.yml": "steps:\n  - uses: actions/checkout@v7\n"})
        p = check_pins.check(d)
        self.assertEqual(len(p), 1)
        self.assertIn(".github/actions/x/action.yml", p[0])
        self.assertIn("actions/checkout@v7", p[0])

    def test_sha_ref_ok(self):
        d = tree({".github/workflows/a.yml": f"steps:\n  - uses: actions/checkout@{SHA} # v7\n"})
        self.assertEqual(check_pins.check(d), [])

    def test_local_ref_ok(self):
        d = tree({".github/workflows/a.yml": "steps:\n  - uses: ./.github/actions/foo\n"})
        self.assertEqual(check_pins.check(d), [])

    def test_secret_ref_rejected(self):
        bad = tree({".github/workflows/a.yml": "env:\n  T: ${{ secrets.TELEGRAM_TOKEN }}\n"})
        ok = tree({".github/workflows/a.yml": "env:\n  T: ${{ secrets.GITHUB_TOKEN }}\n"})
        self.assertEqual(len(check_pins.check(bad)), 1)
        self.assertEqual(check_pins.check(ok), [])

    def test_secret_files_rejected(self):
        d = tree({"keybox.xml": "x", "a/cert.pem": "x", "b/boot_key": "x"})
        self.assertEqual(len(check_pins.check(d)), 3)

    def test_branch_pin_rejected(self):
        d = tree({".github/workflows/pong.yml": f"with:\n  root_commit: main\n  susfs_commit: {SHA}\n"})
        p = check_pins.check(d)
        self.assertEqual(len(p), 1)
        self.assertIn("root_commit", p[0])


if __name__ == "__main__":
    unittest.main()
