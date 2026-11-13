# pong-kernel: own kernel build for the Nothing Phone (2), phase 1

Date: 2026-11-13. Status: design, awaiting the owner's approval.

## Intent

The owner wants the phone ("pong", Nothing Phone 2 / A065, rooted daily driver) to run on fully self-controlled
software. Google stays. The kernel is the first piece: a GKI kernel tuned to this phone, later also driving the
Glyph lights. The owner's priorities, in their words: **battery, security, root hiding** ("am wichtigsten ist akku
sicherheit root hide"). Performance comes after battery. Every phase is judged against these three: a change that
costs hiding or security is not worth any battery gain, and phase 1 must keep today's hiding exactly as it is.

Phase 1 (this document) only makes the build the owner's own: the kernel that runs today is rebuilt, reproducibly,
in a public GitHub repo under the owner's account. Nothing is flashed in phase 1. Phases 2 (battery tuning) and
3 (Glyph) get their own designs later and build on this repo.

## What runs today (read from the device on 2026-11-13)

- `Linux version 5.10.269-android12-Wild ... clang 12.0.5 (r416183b) ... #1 SMP PREEMPT Mon Oct 5 04:20:00 UTC 2026`
- Release: WildKernels/GKI_KernelSU_SUSFS **r22** (2026-10-29), asset
  `5.10.269-android12-2026-10-BakaSU-AnyKernel3.zip` (pkt confirms `boot_a` matches it).
- Root BakaSU (manager `com.resukisu.resukisu`), susfs4ksu; Full LTO; CPU governor `walt` on all 3 policies.
- The real values come from `su -c 'cat /proc/version'` and `su -c 'zcat /proc/config.gz'`; `uname -r` is spoofed
  (reports 5.10.237) and must not be used.

## Goals

1. Public repo `6FaNcY9/pong-kernel` whose GitHub Actions workflow builds exactly one target: android12-5.10,
   sublevel 269, os patch level 2026-10, BakaSU + susfs, AnyKernel3 zip, the same feature set as r22.
2. Every input pinned: upstream workflow/source commits, KernelSU/BakaSU, susfs, AnyKernel3, toolchain, and every
   third-party GitHub Action by full commit SHA. A rebuild next month gives the same kernel.
3. Proof of sameness: the built kernel's config equals the running `/proc/config.gz` (the only allowed differences are
   listed and explained), and the version string, KSU/susfs versions and KMI are the same.
4. The artifact passes `pkt`'s existing checks on the phone (`~/projects/pong-kernel-tool`), without installing it.
5. A short README: how to trigger a build, where the zip appears, how to verify it.

## Non-goals (phase 1)

- No tuning, no new patches, no Glyph work.
- No flashing, no slot changes, no reboot.
- Not a general multi-device or multi-variant build (upstream already does that).

## Anti-goals (a failure even if it builds)

- Any secret in the repo: keybox, `tricky_store/{boot_key,hbk,keys}`, attestation certs, tokens. The repo is public.
- A KMI change (must stay android12-5.10) or anything that would break root hiding (susfs, version spoofing).
- Unpinned inputs (`@main`, `@v4`, latest releases) that silently change the kernel between builds.
- Building on the phone (Full LTO on 10 GB RAM is impractical; the owner's rule).

## Constraints

- Owner's device rules apply to everything after the build: downloaded zips are untrusted (extract into a new empty
  directory, inspect, never run); before any later flash `~/.claude/scripts/boot-backup.sh` must verify; flashing
  only via `pkt` and only with the owner's explicit OK for that action. Slot B holds a clean 5.10.237 kernel the
  owner wants left alone unless they say otherwise; resolve how that fits `pkt`'s inactive-slot flow before phase 2.
- Builds run in the public repo's free Actions minutes; the upstream build takes about an hour with Full LTO.
- Creating the GitHub repo and pushing to it are outward actions: the builder prepares everything locally and asks
  the owner before the first push.

## Decided

- Public repo under the owner's account (owner's call; unlimited free minutes, GPL source is public anyway).
- Phase order: reproduce first, then battery (owner's priority), Glyph separately later.

## My calls (owner may override)

- Base on upstream's reusable workflow `WildKernels/GKI_KernelSU_SUSFS/.github/workflows/build.yml` (`workflow_call`,
  inputs such as `android_version`, `kernel_version`, `sublevel`, `os_patch_level`, `root_flavor`, `root_commit`,
  `susfs_commit`, `anykernel3_commit`, `kernel_patches_commit`, `brand_name`, `keep_kmi`). Prefer a vendored copy
  pinned to the upstream commit that produced r22 over calling it remotely, so later phases can add patch steps and
  upstream changes never reach the build unreviewed. The builder decides vendored vs. called after reading it, and
  writes down why.
- Keep the brand string `Wild` and the same version string in phase 1, so the result is directly comparable.
- Triggers: manual (`workflow_dispatch`) only. No schedule.
- "Same" means: same config (diff against `/proc/config.gz`), same version string, same KSU/BakaSU and susfs versions,
  same KMI. A byte-identical Image is a welcome bonus, not the target. If the Image happens to be identical,
  `pkt check`'s reject "identical to the kernel already running" (`pkt/zipcheck.py`) is the expected outcome and
  counts as passing goal 4; any other reject is a failure.
- If r22's exact inputs cannot be recovered (moved branches, deleted commits): first try to read the KSU/susfs
  versions from strings in the r22 Image, then pin the nearest existing commits and list every difference in the
  README. Stop and report to the owner instead if the nearest inputs would change the KMI, the hiding (susfs,
  version spoofing) or the root flavor: those are the owner's priorities and not the builder's to trade.

## Left to the builder

- Finding the exact upstream commits behind r22 (release notes, the run that published it, or its matrix).
- How to compare configs (the zip contains the Image; extract the embedded config, e.g. with `extract-ikconfig`,
  and diff against the phone's `/proc/config.gz`).
- Release vs. artifact for publishing the zip.
