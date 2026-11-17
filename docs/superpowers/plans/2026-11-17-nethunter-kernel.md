# NetHunter kernel for pong — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an on-demand NetHunter variant of the pong kernel — r22 plus the USB-gadget configs (HID/BadUSB), the rtl88xxau injection driver as a loadable module, and any missing netfilter modules — and stand up rootful Kali NetHunter on top, without touching the daily r22 kernel or its hiding.

**Architecture:** The NetHunter kernel is a **separate build target**, not a change to the r22 build. The existing `feature_set` mechanism in `build.yml` gets a new `NetHunter` token that gates two new composite actions (config additions + driver integration); a new `pong-nethunter.yml` workflow (a clone of `pong.yml`) requests that feature. `pong.yml` keeps building byte-identical r22. The NetHunter kernel is only ever `fastboot boot`-ed for authorized sessions; r22 stays flashed as the everyday kernel. Userspace (NetHunter app + Full chroot) is installed device-side and hidden via HMA.

**Tech Stack:** GitHub Actions (reusable `prepare.yml`/`build.yml`), AOSP `kernel/common` android12-5.10 GKI, `scripts/config` via `.github/actions/set-kernel-config`, Kimocoder `rtl88xxau` out-of-tree driver built in-tree as a module, `tools/zipkernel.py`/`pkt` for the test boot image, Kali NetHunter rootful app + chroot.

**Spec:** `docs/superpowers/specs/2026-11-17-nethunter-kernel-design.md` (read it alongside this plan).

## Global Constraints

- KMI stays **android12-5.10**; `keep_kmi: false` as in `pong.yml` (do not change it).
- Build in **GitHub Actions only** — never compile on the phone.
- `pong.yml` (the exact r22 reproduction) must stay unchanged and keep building a config-identical-to-r22 kernel. NetHunter is additive and lives in its own workflow.
- Keep **KSU/BakaSU, susfs, all hiding, and the version-spoofing** exactly as r22; the only intended kernel differences are the added gadget configs, the driver module, and missing netfilter modules — each listed in `ci/allowed-config-diff.txt` with a `## why`.
- **No flashing anywhere in this plan.** The NetHunter kernel is proven and used via `fastboot boot`; reverting is a normal reboot to r22 on `_a`. Any future slot decision is a separate owner action via `pkt` after `boot-backup.sh`.
- Every third-party source is **pinned to a full commit SHA** (the driver included), or `ci/check_pins.py` fails. No secret/key file in the public repo.
- Pushing to the repo triggers CI and is an outward action: get the owner's OK before each push.
- The external WiFi adapter is owner-supplied; monitor-mode verification (Task 6) waits until it is in hand.

## Review Focus

- **Collateral config drift:** `set-kernel-config` does a plain `sed` on `gki_defconfig`; a symbol name that is a prefix of another could rewrite the wrong line and silently alter r22's KMI/hiding. → Task 2's verification diffs the built config against r22 and asserts *only* the intended lines changed.
- **Module vermagic mismatch:** `CONFIG_MODVERSIONS=y` means a `.ko` built against the wrong tree won't load. → Task 4 loads the module on the test-booted kernel and checks `modinfo` vermagic.
- **Symbol stripping:** `CONFIG_TRIM_UNUSED_KSYMS=y` can strip the cfg80211/mac80211 symbols the driver imports. → Task 3's build must link green with the driver in-tree; Task 4 confirms the module binds.
- **Unpinned/non-reproducible driver source:** a floating branch would break `check_pins.py` and reproducibility. → Task 3 pins `rtl88xxau_commit` as a workflow input and clones that exact SHA; `check.yml` stays green.
- **Baseline contamination:** if the NetHunter additions leak into the r22 build, even the daily kernel's hiding drifts. → Task 2 verifies `pong.yml`'s artifact is still config-identical to r22.

---

### Task 1: Capture the real r22 baseline and the exact config delta

Read-only recon on the device and the CI zip; it decides exactly which symbols Tasks 2–3 add. Needs the owner's OK to read the phone.

**Files:**
- Create: `docs/superpowers/nethunter-recon.md` (config-symbol names only — not secret; no keys, no device IDs)

**Interfaces:**
- Produces: the pruned gadget-config list, the missing-netfilter list, the driver Kconfig symbol, and the SELinux/NetHunter-install baseline that Tasks 2–5 consume.

- [ ] **Step 1: Extract r22's real config** with `python3 -I ~/projects/pong-kernel/tools/zipkernel.py config <r22 zip or boot_a backup>` and save it. (The spoofed `/proc/config.gz` and `config/stock_defconfig` must not be used as the source of truth.)
- [ ] **Step 2: Record which of the 10 Kali gadget symbols are already set** (`USB_CONFIGFS_{SERIAL,ACM,OBEX,NCM,ECM,ECM_SUBSET,RNDIS,EEM,MASS_STORAGE,F_HID}`) — grep each in the extracted config; the delta is the ones to add.
- [ ] **Step 3: Record the netfilter gap** — from Kali's NetHunter kernel config list, note which modules r22 lacks (most are present in GKI).
- [ ] **Step 4: Confirm the module facts against the real config:** `CONFIG_MODULES=y`, `MODULE_SIG_FORCE` unset, `CFG80211`/`MAC80211` present, `TRIM_UNUSED_KSYMS` value.
- [ ] **Step 5: Record device baseline:** current SELinux mode (`getenforce`), whether a NetHunter app/chroot is already installed and where, and which USB-gadget functions the NP2 configfs already exposes (`su -c 'ls /config/usb_gadget/*/functions/'`).
- [ ] **Step 6: Write `docs/superpowers/nethunter-recon.md`** with those findings, and commit (owner OK to push).
- [ ] **Verification:** the file answers each of steps 2–5 with concrete values; the gadget-add list and netfilter-add list are explicit.

### Task 2: Add the `NetHunter` feature — USB-gadget + netfilter configs, in a separate workflow

**Files:**
- Create: `.github/actions/nethunter-config/action.yml` (composite; calls the same `scripts/config` pattern as `.github/actions/set-kernel-config`)
- Modify: `.github/workflows/build.yml` — add a step `if: contains(inputs.feature_set, 'NetHunter')` that runs the new action (place it with the other feature steps, after Misc/BPF)
- Create: `.github/workflows/pong-nethunter.yml` — a copy of `pong.yml` with `feature_set: SUSFS+NoMount+BBG+NET+DS+NTSync+Ptrace+Unicode+BPF+NetHunter` and a distinct artifact/`variant` label (e.g. `BakaSU-NetHunter`); keep brand/version string identical to r22
- Modify: `ci/allowed-config-diff.txt` — add each new `CONFIG_…=y` line with a `## why`

**Interfaces:**
- Consumes: Task 1's pruned gadget list + missing-netfilter list.
- Produces: a green `pong-nethunter` run whose stock config differs from r22 by exactly the added lines.

- [ ] **Step 1: Write `.github/actions/nethunter-config/action.yml`** that patches `arch/arm64/configs/gki_defconfig` with the pruned gadget list (`CONFIG_USB_CONFIGFS_F_HID=y`, …) and the missing netfilter modules (`=m` where modular). Follow the exact structure of `.github/actions/set-kernel-config/action.yml`; no unpinned `uses:`.
- [ ] **Step 2: Add the gated step to `build.yml`** next to the other feature actions.
- [ ] **Step 3: Create `pong-nethunter.yml`** from `pong.yml`, adding `+NetHunter` to `feature_set` and the distinct variant label; every `*_commit` input stays the pinned r22 value.
- [ ] **Step 4: Add the new config lines to `ci/allowed-config-diff.txt`** with `## why` each.
- [ ] **Step 5: Run `check.yml` logic locally** — `python3 ci/check_pins.py .` and `python3 -m unittest ci/test_check_pins.py` — Expected: PASS (no unpinned refs, no secrets).
- [ ] **Step 6: Commit; push (owner OK); run `pong-nethunter.yml`.** Expected: build GREEN.
- [ ] **Step 7: Verify the delta** — extract the NetHunter artifact's config, diff against r22's real config (Task 1): Expected: the diff is exactly the lines from `allowed-config-diff.txt`, nothing else.
- [ ] **Step 8: Verify baseline is untouched** — run `pong.yml`; diff its config against r22: Expected: no differences (`pkt check` would say "identical").
- [ ] **Step 9: Commit** the recon-pruned final config list if it changed.

### Task 3: Integrate the rtl88xxau injection driver as a loadable module

**Files:**
- Create: `.github/actions/nethunter-wifi/action.yml` (composite; clones Kimocoder `rtl88xxau` at a pinned SHA, places it under `kernel/common/drivers/net/wireless/realtek/rtl88xxau`, wires its `Kconfig`/`Makefile` into the realtek tree, sets `CONFIG_88XXAU=m`)
- Modify: `.github/workflows/build.yml` — add `rtl88xxau_commit` input and a step `if: contains(inputs.feature_set, 'NetHunter')` running the action
- Modify: `.github/workflows/pong-nethunter.yml` — pass `rtl88xxau_commit: <full SHA>`
- Modify: `ci/allowed-config-diff.txt` — add `CONFIG_88XXAU=m` with `## why`

**Interfaces:**
- Consumes: Task 2's NetHunter workflow + feature gate.
- Produces: a NetHunter artifact that contains `88XXAU.ko` built against the exact kernel.

- [ ] **Step 1: Pick and pin the driver commit** — resolve a specific Kimocoder `rtl88xxau` commit that supports android12-5.10; record the SHA (the exact symbol may be `CONFIG_88XXAU` — confirm from the driver's `Kconfig`).
- [ ] **Step 2: Write `.github/actions/nethunter-wifi/action.yml`** — clone at the pinned SHA, copy into the realtek wireless dir, append the driver's `source`/`obj-$(CONFIG_88XXAU)` lines to the realtek `Kconfig`/`Makefile`, and enable `CONFIG_88XXAU=m` via the config pattern. In-tree build so Kbuild keeps the cfg80211/mac80211 symbols (defeats `TRIM_UNUSED_KSYMS`).
- [ ] **Step 3: Add the input + gated step to `build.yml`; pass the SHA in `pong-nethunter.yml`.**
- [ ] **Step 4: `python3 ci/check_pins.py .`** — Expected: PASS (driver pinned; `rtl88xxau_commit` is a 40-hex SHA).
- [ ] **Step 5: Commit; push (owner OK); run `pong-nethunter.yml`.** Expected: build GREEN, no patch rejects for the realtek tree.
- [ ] **Step 6: Verify the module is in the artifact** — the AnyKernel zip / modules output contains `88XXAU.ko`; `modinfo 88XXAU.ko` shows a vermagic matching the built kernel. (Load-on-device is Task 4.)

### Task 4: Build the test boot image and pass the baseline verification gates

No repo changes. Builds a boot image from the NetHunter AnyKernel zip the way the existing `pong-ci-*-boot.img` was made (swap only the kernel into the r22 `boot_a` backup, keep the ramdisk), then `fastboot boot` from the laptop. Needs the owner + laptop. **Nothing is flashed.**

**Interfaces:**
- Consumes: Task 3's NetHunter artifact.
- Produces: a confirmed-bootable NetHunter kernel and the gate results that justify installing the userspace.

- [ ] **Step 1: Build the test image** with the existing method (`tools/zipkernel.py` / the pong-ci image recipe in the memory note): ramdisk sha must stay identical to the r22 backup; only the kernel differs.
- [ ] **Step 2: `fastboot boot` the image** from the laptop (`nix shell nixpkgs#android-tools -c fastboot boot <img>`). Expected: device boots to Android.
- [ ] **Step 3: Confirm the NetHunter kernel is the running one** via the GNU build-id (`su -c 'cat /sys/kernel/notes' | od -An -tx1 | tr -d ' \n'`), not `/proc/version` (spoofed).
- [ ] **Step 4: Run the hiding/health gates** — `root-doctor`; `su -c 'sh /data/adb/service.d/99-root-health.sh --now'` = ok; all modules load; owner runs Play Integrity → Expected: **BASIC + DEVICE + STRONG**.
- [ ] **Step 5: Confirm the new kernel features are present** — HID gadget function available (`su -c 'ls /config/usb_gadget/*/functions/' | grep hid`, or the gadget can be created); `88XXAU` module present (`su -c 'modprobe 88XXAU'` loads with no error, or it is listed in `/lib/modules`).
- [ ] **Step 6: Record the result; reboot** → back to r22 on `_a` (the revert). If any gate fails, stop and fix the owning task before proceeding.

### Task 5: Install rootful NetHunter userspace and verify the toolset + HID

Device-side, while the NetHunter kernel is `fastboot boot`-ed. Treat the NetHunter download as untrusted (verify signature/hash; install into the hiding stack).

**Interfaces:**
- Consumes: Task 4's booted NetHunter kernel.
- Produces: a working rootful NetHunter (chroot + app) with nmap and HID confirmed.

- [ ] **Step 1: Install the official rootful NetHunter app + Full chroot** from the NetHunter project; add the NetHunter app(s) to HMA like pong's other apps.
- [ ] **Step 2: Verify the toolset** — in the chroot, `nmap --version` runs and `nmap -sS <a host you are authorized to scan>` completes (raw-socket SYN scan under root). Expected: scan runs.
- [ ] **Step 3: Verify HID/BadUSB** — the NetHunter app's kernel/feature check shows HID available; a DuckHunter payload types a benign string on a PC the phone is cabled to (phone in the temporary HID "attack mode"; normal ADB/MTP resumes after). Expected: the keystrokes appear.
- [ ] **Step 4: Record what works and what needed iteration** (HID on Qualcomm is the likely rough spot) in the recon/notes file and the project memory.

### Task 6: Verify WiFi injection with the external adapter (hardware-gated)

Runs once the RTL8812AU adapter is in hand, with the NetHunter kernel `fastboot boot`-ed.

**Interfaces:**
- Consumes: Task 4's kernel (driver loads) + Task 5's chroot.

- [ ] **Step 1: Plug the adapter via USB-C OTG;** confirm `88XXAU` binds and a `wlanX` interface appears (`su -c 'dmesg | tail'`, `ip link`).
- [ ] **Step 2: Monitor mode** — `airmon-ng start wlanX`; Expected: a monitor interface is created.
- [ ] **Step 3: Injection test** — `aireplay-ng --test <mon iface>`; Expected: it reports injection working. Scope to networks the owner is authorized to test.
- [ ] **Step 4: Record the confirmed adapter + driver commit** in the project memory; this closes the "alles" set.

---

## Notes for the executor

- The repo already proves r22 reproducibly (phase-1 design, `pong.yml`). This plan never edits that path; if a change would touch `pong.yml`'s r22 output, stop — it belongs in a separate decision.
- "Tests" in this domain are build-green + config-diff + on-device gates, not unit tests; each task's verification step is the checkable result.
- Order dependency: Task 1 → 2 → 3 are the CI/engineering core and must land green before Task 4. Tasks 4/5 need the owner + laptop; Task 6 needs the adapter. Do not flash; `fastboot boot` only.
