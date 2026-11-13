# pong-kernel

My own build of the kernel for my Nothing Phone (2) ("pong"). Phase 1 rebuilds, from fully pinned sources, exactly
the kernel the phone runs today: WildKernels r22, `5.10.269-android12-2026-10`, BakaSU + susfs, as an AnyKernel3 zip.
Later phases tune it, in this order of priority: **battery, security, root hiding**. Nothing that weakens hiding or
security goes in for a battery gain.

The build orchestration is a snapshot of [WildKernels/GKI_KernelSU_SUSFS](https://github.com/WildKernels/GKI_KernelSU_SUSFS)
at r22; see [UPSTREAM.md](UPSTREAM.md) for what was removed and how every action is pinned.

## Build

Actions → **Build pong kernel** → Run workflow (or `gh workflow run pong.yml`). It takes about an hour (Full LTO).
The zip appears as the run's artifact `…-AnyKernel3`.

## Pinned sources

| Part | Commit |
|---|---|
| Upstream build path (r22) | `8d8e03391f26677b033d3c27face86a738a6a319` |
| BakaSU | `d5e9e025b8b49155f8014684d64c91742b465f65` |
| KernelSU (ksu_branch) | `10efe6648aa52e0497bbd686f940832ad05848cf` |
| susfs gki-android12-5.10 | `eb95da080c76724c4962d0c62e9af3be37d9d439` |
| NoMount | `e7f7c67681e19ed1e1ee9c902c030e44647035d4` |
| kernel_patches | `c78291aeb0dca025f21e6b197e0aa4fde42e065d` |
| DroidSpaces | `4344dc5fc4ab981f1cf2df54c93bf32a6ebbdc85` |
| AnyKernel3 gki-2.0 | `e1e9dce98430c5c6f231f7094a8c7f4ecaf50948` |

`ci/check_pins.py` (run on every push by **Check pins**) fails if any action or source stops being pinned, or if a
key, keybox or certificate file appears. This repo is public: secrets never go here.

## Verify a build on the phone

Download the zip into a new, empty directory, then:

```sh
sh tools/verify.sh <zip>
```

It reads the zip without running anything from it and checks three things:

1. **Version string** built == running (`/proc/version`): toolchain, branding and build stamp.
2. **Embedded config** == `/proc/config.gz`. On this phone both are the *stock GKI config shown for hiding*
   (it has no `CONFIG_KSU`), so this only proves the shown config, not KSU/susfs/BBG. The build embeds the
   committed `config/stock_defconfig` (taken from the phone) instead of downloading Google's newest one.
3. **pkt check**: the real proof is pkt's "identical to the kernel already running" (same Image sha256), printed
   as `IDENTICAL`. Any other REJECT fails; pkt not finishing is an error.

Allowed config differences, each with a reason, live in `ci/allowed-config-diff.txt` (empty today).

Baseline (2026-11-13): the official r22 zip gives same version, `SAME` config (5426 lines) and `IDENTICAL`.

## Flashing

Not part of this repo. Never flash without `~/.claude/scripts/boot-backup.sh` verifying first, and only through
`pkt` to the inactive slot, with an explicit OK for that flash.

## Tests

```sh
python3 -m unittest ci/test_check_pins.py
sh tools/test_verify.sh
```
