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

Tags and branches resolved to commits on 2026-11-13; every `uses:` now names the commit, the tag stays as a comment.

| Was | Pinned to |
|---|---|
| `actions/cache/restore@v6` | `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` |
| `actions/cache/save@v6` | `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` |
| `actions/checkout@v7` | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/download-artifact@v7` | `37930b1c2abaa49bbe596cd826c3c89aef350131` |
| `actions/setup-python@v7` | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` |
| `actions/upload-artifact@v7` | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| `endersonmenezes/free-disk-space@v4` | `8b8cd4e2277836962939a8f3b4ea0ee4bc006156` |
| `jetsung/setup-zig@v0.0.4` | `ece60a5f01428e90311476245667dc49e3f84513` |
| `pierotofy/set-swap-space@master` | `fc79b3f67fa8a838184ce84a674ca12238d2c761` |
