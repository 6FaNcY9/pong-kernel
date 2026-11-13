# pong-kernel Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public repo `6FaNcY9/pong-kernel` that rebuilds the running kernel (Wild r22, 5.10.269-android12-2026-10, BakaSU + susfs) in GitHub Actions from fully pinned inputs, plus a phone-side check that proves it matches.

**Architecture:** Snapshot of upstream WildKernels/GKI_KernelSU_SUSFS at the r22 tag commit (vendored, not a GitHub fork), trimmed to the build path, with one new `workflow_dispatch` workflow `pong.yml` that calls the vendored reusable `build.yml` with every commit pinned. A Python checker (`ci/check_pins.py`) enforces "everything pinned, no secrets" in CI and locally; `tools/verify.sh` on the phone compares a built zip against the running kernel and runs `pkt check`.

**Tech Stack:** GitHub Actions YAML, bash, Python 3 stdlib (checker + tests with `unittest`), upstream composite actions, `pkt` (`~/projects/pong-kernel-tool`).

**Spec:** `docs/superpowers/specs/2026-11-13-pong-kernel-design.md`

## Global Constraints

- Upstream base: `WildKernels/GKI_KernelSU_SUSFS` commit `8d8e03391f26677b033d3c27face86a738a6a319` (the `r22` tag).
- Target: `android12`, kernel `5.10`, sublevel `269`, os patch level `2026-10`, root flavor BakaSU, brand `Wild`, page size `4k`, `keep_kmi` as upstream used for r22.
- Pins recovered from the r22 release notes and branch tips at the tag time (2026-10-29T06:52:17Z):
  - BakaSU `d5e9e025b8b49155f8014684d64c91742b465f65`
  - susfs (gki-android12-5.10) `eb95da080c76724c4962d0c62e9af3be37d9d439`
  - NoMount `e7f7c67681e19ed1e1ee9c902c030e44647035d4`
  - kernel_patches `c78291aeb0dca025f21e6b197e0aa4fde42e065d`
  - DroidSpaces `4344dc5fc4ab981f1cf2df54c93bf32a6ebbdc85`
  - AnyKernel3 (gki-2.0) `e1e9dce98430c5c6f231f7094a8c7f4ecaf50948`
- Every `uses:` of a third-party action is pinned to a full 40-hex commit SHA, with the tag it came from as a comment.
- No secret is ever committed: no keybox, `tricky_store/{boot_key,hbk,keys}`, certs, tokens. Workflows use only `GITHUB_TOKEN`.
- Triggers: `workflow_dispatch` only. No schedule, no Telegram, no posting anywhere.
- Never build on the phone. Never flash, never reboot, never write a partition in this plan.
- Downloaded zips are untrusted: extract into a new empty directory, never execute anything from them.
- Creating the GitHub repo and the first push need the owner's explicit OK (ask, then wait).

## Review Focus

1. A pin silently not taking effect (input ignored, `main.yml` default re-resolving a branch tip) → the run log must show the pinned SHAs; Task 2's test checks `pong.yml` passes each pin, Task 5 checks the run log.
2. Config diff noise mistaken for sameness or difference → `verify.sh` must list each differing line and only pass when every difference is in `ci/allowed-config-diff.txt` (Task 4 test with a fabricated extra line).
3. A third-party action referenced by tag in a composite action deep under `.github/actions/` → `check_pins.py` scans every YAML under `.github`, not only workflows (Task 1 test).
4. A zip with an unexpected layout (no `Image`, nested dir) → `verify.sh` fails clearly instead of passing on an empty diff (Task 4 test).
5. Secrets creeping in (a `secrets.TELEGRAM_*` reference left in vendored YAML, a `*.pem`/`keybox*.xml` file) → `check_pins.py` rejects both (Task 1 test).

---

### Task 1: Repo seed and the pin/secret checker

**Files:**
- Create: `~/projects/pong-kernel/` git repo (the spec already lives in `docs/superpowers/specs/`)
- Create: vendored tree from upstream `8d8e033…` (all files) then delete: `.github/workflows/{main,managers,release-from-run,sync-matrix,clear-cache,commit-status,opencode}.yml`, `.github/scripts/telegram_digest.py`, `.github/ISSUE_TEMPLATE/`
- Create: `UPSTREAM.md` (base commit, date, list of deleted files and why)
- Create: `ci/check_pins.py`, `ci/test_check_pins.py`

**Interfaces:**
- Produces: `check_pins.check(root: Path) -> list[str]` (problem strings, empty = clean); CLI `python3 ci/check_pins.py [root]` exits 1 and prints problems if any.

- [ ] **Step 1: Write failing tests** in `ci/test_check_pins.py` (unittest, temp dirs):
  - `test_tag_ref_rejected`: a YAML under `.github/actions/x/action.yml` with `uses: actions/checkout@v7` → one problem naming the file and `actions/checkout@v7`.
  - `test_sha_ref_ok`: `uses: actions/checkout@<40 hex> # v7` → no problem.
  - `test_local_ref_ok`: `uses: ./.github/actions/foo` → no problem.
  - `test_secret_ref_rejected`: `${{ secrets.TELEGRAM_TOKEN }}` → problem; `${{ secrets.GITHUB_TOKEN }}` → none.
  - `test_secret_files_rejected`: files `keybox.xml`, `a/cert.pem`, `boot_key` anywhere → one problem each.
  - `test_branch_pin_rejected`: in `.github/workflows/pong.yml`, any `*_commit:` value that is not 40 hex → problem.
- [ ] **Step 2: Run** `python3 -m unittest ci/test_check_pins.py -v` → FAIL (module missing).
- [ ] **Step 3: Implement** `ci/check_pins.py`, regex based (no YAML library), scanning `**/*.yml|*.yaml` under `.github` and all file names in the repo (skip `.git`).
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Seed the vendored tree** (download the tree at the pinned commit via the GitHub tarball for that SHA into a new empty dir, copy in, delete the listed files), write `UPSTREAM.md`, `git init`, commit `chore: vendor WildKernels r22 (8d8e033) build path`. Expect `check_pins.py` to report the unpinned upstream actions now; that list is Task 3's input.
- [ ] **Step 6: Commit** checker + tests: `git commit -m "ci: pin and secret checker"`.

### Task 2: `pong.yml`, the one-target workflow

**Files:**
- Create: `.github/workflows/pong.yml`
- Modify: `ci/test_check_pins.py` (add `test_pong_workflow_pins`)

**Interfaces:**
- Consumes: vendored `.github/workflows/build.yml` (`workflow_call` inputs: `version, android_version, kernel_version, sublevel, os_patch_level, variant, feature_set, ksu_branch, susfs_commit, root_flavor, root_commit, nomount_commit, kernel_patches_commit, anykernel3_commit, droidspaces_commit, brand_name, keep_kmi, allow_version_mismatch, page_size, stock_config_artifact`).
- Produces: workflow "Build pong kernel", artifact `5.10.269-android12-2026-10-BakaSU-AnyKernel3` (same name pattern as upstream).

- [ ] **Step 1: Write failing test** `test_pong_workflow_pins`: reads the real `.github/workflows/pong.yml` and asserts it contains each Global-Constraints pin value literally, `android_version: android12`, `kernel_version: "5.10"`, `sublevel: "269"`, `os_patch_level: 2026-10`, `brand_name: Wild`, `on:` has only `workflow_dispatch`.
- [ ] **Step 2: Run** → FAIL (file missing).
- [ ] **Step 3: Write `pong.yml`.** Read upstream `main.yml` at the base commit to copy exactly how it built the r22 BakaSU android12-5.10 row: the `feature_set` string, `variant`, `version`, `ksu_branch`, `keep_kmi`, and whether `prepare.yml` must run first to produce `stock_config_artifact` (if so, call it too, pinned). Values come from upstream, not invention; note each source line in a comment.
- [ ] **Step 4: Run tests and** `python3 ci/check_pins.py` (pong.yml must be clean; vendored actions may still fail until Task 3).
- [ ] **Step 5: Commit** `feat: pong.yml builds only android12-5.10-2026-10 BakaSU`.

### Task 3: Pin every third-party action by SHA

**Files:**
- Modify: every vendored YAML that `check_pins.py` flags (e.g. `build.yml`: `actions/checkout@v7`, `actions/download-artifact@v7`, `actions/upload-artifact@v7`, `endersonmenezes/free-disk-space@v4`, `pierotofy/set-swap-space@master`).

- [ ] **Step 1:** Resolve each tag/branch to its commit SHA with the GitHub API (`/repos/<o>/<r>/commits/<ref>`), as of today; record `tag → sha` in `UPSTREAM.md`.
- [ ] **Step 2:** Replace refs with `@<sha> # <tag>`.
- [ ] **Step 3: Run** `python3 ci/check_pins.py` → no problems; `python3 -m unittest ci/test_check_pins.py` → PASS; upstream's own `python3 .github/scripts/validate_workflows.py` (if it runs without network) → PASS.
- [ ] **Step 4:** Add `.github/workflows/check.yml` (on push/pull_request) running the checker and its tests, its own actions SHA-pinned.
- [ ] **Step 5: Commit** `ci: pin all third-party actions by commit`.

### Task 4: Phone-side verification `tools/verify.sh`

**Files:**
- Create: `tools/verify.sh`, `tools/test_verify.sh`, `ci/allowed-config-diff.txt`

**Interfaces:**
- Produces: `sh tools/verify.sh <zip> [running-config]` → prints `SAME` or `DIFFERENT` plus each unexplained line; exit 0 only for SAME. `running-config` defaults to `su -c 'zcat /proc/config.gz'`. Also prints the Image's `Linux version` string and the result of `pkt check <zip>` (from `~/projects/pong-kernel-tool`).

- [ ] **Step 1: Write failing tests** `tools/test_verify.sh` (POSIX sh, fixtures built in a temp dir: a tiny zip with an `Image` containing an embedded ikconfig made with `scripts/extract-ikconfig`'s markers `IKCFG_ST`/`IKCFG_ED` around gzip data):
  - same config → `SAME`, exit 0
  - one extra line not in the allow list → `DIFFERENT`, the line printed, exit 1
  - extra line listed in `ci/allowed-config-diff.txt` → `SAME`
  - zip without `Image` → clear error, exit 2
- [ ] **Step 2: Run** `sh tools/test_verify.sh` → FAIL.
- [ ] **Step 3: Implement** `verify.sh`: unzip into a fresh `mktemp -d`, never execute zip content, extract config with the vendored `.github/scripts/extract-ikconfig`, `sort`+`comm` against the running config, filter by the allow list, `strings Image | grep -m1 'Linux version'`, then `pkt check`. Treat `pkt`'s reject "identical to the kernel already running" as pass (spec); any other reject → exit 1.
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Real baseline:** download the official r22 `5.10.269-android12-2026-10-BakaSU-AnyKernel3.zip` into a new empty dir and run `verify.sh` on it against the phone. Expected: `SAME`, version string equals the running `/proc/version` minus nothing; `pkt` gives only the "identical" reject. Any difference here goes into the allow list only with a one-line reason.
- [ ] **Step 6: Commit** `feat: verify a built zip against the running kernel`.

### Task 5: README, publish, first build, proof

**Files:**
- Create: `README.md` (what this is, owner's priorities battery/security/hiding, how to run "Build pong kernel", where the artifact appears, how to run `verify.sh`, the pin table, "never flash without boot-backup.sh and pkt")

- [ ] **Step 1:** Write README; commit `docs: README`.
- [ ] **Step 2: Ask the owner** for OK to create public repo `6FaNcY9/pong-kernel` and push (`gh repo create 6FaNcY9/pong-kernel --public --source . --push`). Wait for the OK.
- [ ] **Step 3:** Trigger `gh workflow run pong.yml`; watch with `gh run watch`. Expected: success in roughly an hour; the log shows each pinned SHA being checked out.
- [ ] **Step 4:** `gh run download` the AnyKernel3 artifact into a new empty dir on the phone; `sh tools/verify.sh <zip>` → `SAME`.
- [ ] **Step 5:** Record the run URL, artifact sha256, and the verify output in README under "Last verified build"; commit and push.
- [ ] **Step 6:** Update shared memory `projects/pong-phone` (project `main`): repo URL, how to build, verify result. No secrets.
