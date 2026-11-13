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

    def test_pong_workflow_pins(self):
        text = (REPO / ".github/workflows/pong.yml").read_text()
        for pin in ("d5e9e025b8b49155f8014684d64c91742b465f65", "eb95da080c76724c4962d0c62e9af3be37d9d439",
                    "e7f7c67681e19ed1e1ee9c902c030e44647035d4", "c78291aeb0dca025f21e6b197e0aa4fde42e065d",
                    "4344dc5fc4ab981f1cf2df54c93bf32a6ebbdc85", "e1e9dce98430c5c6f231f7094a8c7f4ecaf50948",
                    "028ff7fd509e2104596da7cc1ef8e6ce2a0c9082"):
            self.assertIn(pin, text)
        for line in ("config_file: .github/config/android12-5.10.json", "os_patch_level: 2026-10",
                     "root_flavor: bakasu", "brand_name: Wild", "page_size: 4k"):
            self.assertIn(line, text)
        import json
        rows = [r for r in json.loads((REPO / ".github/config/android12-5.10.json").read_text())["include"]
                if r.get("date") == "2026-10"]
        self.assertEqual(rows, [{"sublevel": "269", "date": "2026-10"}])   # exactly one target: 5.10.269
        on = text.split("\non:", 1)[1].split("\njobs:", 1)[0]
        self.assertIn("workflow_dispatch", on)
        for trigger in ("push", "schedule", "pull_request", "workflow_run"):
            self.assertNotIn(trigger, on)
        self.assertEqual([p for p in check_pins.check(REPO) if "pong.yml" in p], [])

    def test_bbg_is_pinned_end_to_end(self):
        # BBG is in pong.yml's feature_set; upstream piped setup.sh from main into bash
        action = (REPO / ".github/actions/bbg/action.yml").read_text()
        self.assertNotIn("/main/setup.sh", action)
        self.assertIn("${{ inputs.commit }}/setup.sh", action)
        self.assertIn('rev-parse HEAD)" = "${{ inputs.commit }}"', action)
        build = (REPO / ".github/workflows/build.yml").read_text()
        self.assertIn("commit: ${{ inputs.bbg_commit }}", build)
        prepare = (REPO / ".github/workflows/prepare.yml").read_text()
        self.assertIn("bbg_commit: ${{ inputs.bbg_commit }}", prepare)

    def test_stock_config_is_committed(self):
        # stock-config/action.yml prefers config/stock_defconfig over a live download from AOSP main;
        # it is the config the kernel shows in /proc/config.gz (no KSU lines), not the build's real one
        cfg = (REPO / "config/stock_defconfig").read_text()
        self.assertIn("CONFIG_LOCALVERSION_AUTO=y", cfg)
        self.assertNotIn("CONFIG_KSU", cfg)
        self.assertGreater(len(cfg.splitlines()), 5000)


if __name__ == "__main__":
    unittest.main()
