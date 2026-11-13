# Upstream base

This repo starts from a snapshot of [WildKernels/GKI_KernelSU_SUSFS](https://github.com/WildKernels/GKI_KernelSU_SUSFS)
at commit `8d8e03391f26677b033d3c27face86a738a6a319` (tag `r22`, 2026-10-29T06:52:17Z), the release that built the
kernel running on pong (`5.10.269-android12-2026-10-BakaSU-AnyKernel3.zip`). License: see `LICENSE` and
`THIRD_PARTY_NOTICES.md`. Upstream's README and docs are kept as `UPSTREAM-README.md` and `docs/upstream/`.

## Removed from the snapshot

| Path | Why |
|---|---|
| `.github/workflows/main.yml` | builds every family and flavor; replaced by `pong.yml` with one pinned target |
| `.github/workflows/{managers,release-from-run,sync-matrix,clear-cache,commit-status,opencode}.yml` | publishing, maintenance and bot workflows this repo does not run |
| `.github/scripts/telegram_digest.py` | posts to Telegram; this repo posts nowhere |
| `.github/ISSUE_TEMPLATE/` | upstream's issue forms |

## Action pins

Filled in by "pin all third-party actions" (see below).
