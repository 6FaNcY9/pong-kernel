# pong-kernel: full rootful Kali NetHunter on pong

Date: 2026-11-17. Status: design, awaiting the owner's approval.

## Intent

The owner wants **full rootful Kali NetHunter** running on pong (Nothing Phone 2 / A065, rooted daily driver) —
on the owner's own kernel and root stack, for authorized penetration testing on the owner's own device. Asked which
capabilities they wanted, the owner answered "alles" (everything): the Kali chroot with its full toolset including
`nmap`, **WiFi injection / monitor mode**, and **HID / "BadUSB"**. Asked which way to build it, the owner picked
Weg A and said "so wie du meinst" — minimal, additive, built as a small reviewable delta on the known-good r22,
not a risky monolithic kernel rebuild.

This is phase-independent from the battery/Glyph phases of [2026-11-13-pong-kernel-design.md]; it reuses the same
repo and CI but adds a feature set, it does not change the battery or performance tuning.

## What is true today (from memory + the 2026-11-13 design)

- pong runs Wild **r22** (`5.10.269-android12-Wild`, GKI **android12-5.10**, BakaSU + susfs, Full LTO) on slot `_a`.
- The repo `6FaNcY9/pong-kernel` reproduces r22: its CI (last green run 44011517535, 2026-11-17) builds a kernel whose
  **config is byte-identical to r22** and whose KSU/susfs/KMI match. Nothing from the repo has been flashed.
- The hiding stack: susfs4ksu, ReZygisk, HMA, TrickyStore, Play Integrity Fix. **Play Integrity passes BASIC + DEVICE +
  STRONG today** (owner-confirmed, 2026-11-17). The whole point of the stack is that STRONG keeps passing.
- Established flow for any kernel change: build in GitHub Actions → `fastboot boot` the test image from the laptop
  (nothing flashed) → verify → only then decide a slot. `pkt` writes only the inactive slot, after `boot-backup.sh`,
  with the owner's explicit OK.

## What NetHunter actually needs from the kernel (researched 2026-11-17, Kali docs)

Separating kernel-gated from userspace, so the delta stays minimal:

- **`nmap` and almost the whole Kali toolset**: userspace. Runs under root in the chroot with **no kernel change**.
- **HID / BadUSB**: needs the USB-gadget configfs **HID function** compiled into the kernel
  (`CONFIG_USB_CONFIGFS_F_HID=y`), plus the related gadget functions. Kali's full gadget list (all `=y`):
  `USB_CONFIGFS_SERIAL`, `USB_CONFIGFS_ACM`, `USB_CONFIGFS_OBEX`, `USB_CONFIGFS_NCM`, `USB_CONFIGFS_ECM`,
  `USB_CONFIGFS_ECM_SUBSET`, `USB_CONFIGFS_RNDIS`, `USB_CONFIGFS_EEM`, `USB_CONFIGFS_MASS_STORAGE`,
  `USB_CONFIGFS_F_HID`.
- **WiFi injection / monitor mode**: the internal Qualcomm chip cannot do injection in practice. It needs an
  **external USB WiFi adapter** (owner-supplied) plus its driver — Kimocoder's `rtl88xxau` (RTL8812AU/8814AU/8821AU)
  is the standard injection-capable driver. Buildable as a loadable `.ko` module.
- **MITM / netfilter**: most iptables/netfilter modules NetHunter wants are already in GKI; add only the few missing.

## Goals

1. Full rootful NetHunter on pong: Kali chroot + full toolset incl. `nmap`, usable under root.
2. WiFi injection / monitor mode working with a common external adapter (rtl88xxau family).
3. HID / BadUSB working (phone as USB-C HID device against a target).
4. Kernel delta vs r22 is **minimal and listed**: only the added USB-gadget configs, the driver module(s), and any
   missing netfilter modules. KSU, susfs, hiding, version string, brand, KMI — **all unchanged from r22**.
5. **Play Integrity STRONG still passes** after the change (owner-verified), and root-doctor / 99-root-health stay clean.
6. Built reproducibly in the existing CI; proven via `fastboot boot` before anything is ever flashed.

## Non-goals

- **NetHunter Pro** — it is a standalone OS (native Kali/Debian for PinePhone & select mainline/QCOM devices) that
  *replaces* Android. It does not run on top of pong's kernel/root stack. Out of scope; would mean wiping the daily driver.
- Internal-chip WiFi injection (the Qualcomm chip can't; external adapter only).
- NetHunter Lite or Rootless.
- The full Kali kernel-builder patch set (that is Weg B below, rejected).
- Flashing the NetHunter kernel as the permanent everyday kernel — owner chose on-demand; r22 stays the daily kernel.

## Anti-goals (a failure even if NetHunter works)

- Breaking root hiding, or dropping Play Integrity below STRONG.
- Any KMI change (must stay android12-5.10).
- Flashing without a verified `boot-backup.sh` and without a prior successful `fastboot boot` test.
- Building on the phone; or any secret landing in the public repo.
- Touching `boot_b`'s clean stock kernel except by the owner's explicit, separate decision.

## Constraints

- All of CLAUDE.md's device rules apply: build in GitHub Actions only; KMI android12-5.10; downloaded zips/adapters'
  firmware treated as untrusted; `boot-backup.sh` must verify before any flash; flash only via `pkt` to the inactive
  slot, with the owner's explicit OK for that specific action.
- susfs must keep hiding the new driver module(s) the same way it hides the rest of the stack.
- The external WiFi adapter is owner-supplied hardware; the build must not assume a specific one until the owner names it.
- Free GitHub Actions minutes; the Full-LTO build takes ~1 h.

## Approaches

- **Weg A — minimal additive change to `pong-kernel` (chosen).** Start from the repo that already reproduces r22.
  Add only: the USB-gadget configfs symbols (HID + the gadget family) to the defconfig; the rtl88xxau driver as a
  loadable module in the kernel tree; any missing netfilter modules. Everything else stays byte-identical to r22.
  Userspace is layered on top: install the official rootful NetHunter app + chroot. Test via `fastboot boot`, verify
  STRONG + hiding, then decide the slot.
  *Trade-off:* HID on a Qualcomm gadget may need some userspace wiring (the NetHunter app normally handles it);
  injection needs the external adapter. But the kernel delta is tiny, reviewable, reproducible, and reversible, and
  the hiding stack is untouched.
- **Weg B — full Kali kernel-builder patch set (rejected).** Apply Kali's `kali-nethunter-kernel` build-scripts
  wholesale. *Trade-off:* it targets device-specific legacy kernel trees, **not GKI/BakaSU**; high risk of conflicts
  with KSU/susfs, broken hiding, boot failures; pulls in much pong doesn't need; directly against the owner's
  "keep everything like r22" principle and the STRONG requirement. Same end capabilities, far more risk.

## Decided (owner)

- Scope = "alles": Kali chroot + nmap, WiFi injection, HID. Weg A.
- **Residency = on-demand** (2026-11-17): r22 stays the everyday kernel; the NetHunter kernel runs only for authorized
  pentest sessions (`fastboot boot`, optionally parked on the inactive slot for a laptop-free boot). Baseline STRONG is
  never touched; the added attack surface only exists during a session.
- **WiFi adapter = builder's pick** (2026-11-17): owner will acquire one on recommendation → default to an RTL8812AU
  adapter (e.g. Alfa AWUS036ACH), driven by Kimocoder's `rtl88xxau`, no firmware blob. The monitor-mode gate is
  verified once the adapter is in hand.
- Design doc → owner approval → implementation plan.

## My calls (owner may override)

- **Configs to add**: the Kali gadget list above, each only if r22's config doesn't already set it (builder diffs
  first; a symbol already `=y` is left alone). These are generic in-tree GKI options; they don't touch KMI or hiding.
- **Driver**: Kimocoder's `rtl88xxau` (RTL8812AU/8814AU/8821AU) as a **loadable module**, built against the exact
  kernel in the same CI — not built-in, so the Image stays close to r22 and the driver loads on demand. Pin the driver
  source by commit. Add other realtek drivers (rtl8188eus, rtl8187, …) only when the owner names an adapter that needs
  one; note that some realtek drivers conflict and only one may be built at a time.
- **Netfilter**: add only NetHunter-listed modules missing from r22's config; leave the rest.
- **Unchanged from r22**: version string, brand `Wild`, KSU/BakaSU, susfs, all hiding. The only intended differences are
  the added configs + the driver module(s) + any missing netfilter modules — all listed in the plan and the README.
- **Verification gates** after `fastboot boot` (nothing flashed), all must pass before any slot decision: boots;
  root-doctor clean; `99-root-health.sh --now` = ok; all modules load; **Play Integrity STRONG** (owner confirms);
  HID function present and usable; driver module loads and the external adapter reaches monitor mode. Reverting is a
  normal reboot (back to r22 on `_a`).
- **Userspace**: the official rootful NetHunter app + chroot from kali.org / the NetHunter project (treated as untrusted
  download, verified), added to the hiding stack (HMA) like pong's other apps.
- **Operational hiding bar (on-demand)**: baseline (r22) keeps STRONG pristine. During an active NetHunter session,
  STRONG-while-attacking is not a goal; SELinux stays enforcing at baseline and may go permissive only for the session
  if a feature needs it. No permanent susfs hiding of the driver/gadget/chroot is required, since none of them exist at
  baseline.
- **HID profile**: keyboard HID (DuckHunter/BadUSB) is the core; a dedicated temporary "attack mode" that takes over
  USB-C during the HID attack is acceptable, with normal ADB/MTP/charging resuming afterward. Composite
  keyboard+mouse+mass-storage only if the owner later asks.

## Left to the builder

- Read r22's real config (`tools/zipkernel.py config` on the CI zip or the `boot_a` backup) and produce the exact,
  minimal config diff — including which gadget symbols are already set.
- Confirm whether NP2's Qualcomm USB-gadget HAL needs extra userspace wiring for the HID function, or whether the
  NetHunter app sets up the gadget itself; identify that wiring if needed.
- Pin the exact `rtl88xxau` source commit and wire its Kconfig/Makefile into the kernel tree so CI emits the `.ko`.
- Check whether susfs needs the new module(s) added to any hide list to keep Play Integrity STRONG.
- Pick the NetHunter app build + chroot flavor (Full) and confirm it coexists with the existing hiding stack.
- The slot decision, after the `fastboot boot` test (owner's call; `pkt` writes only the inactive slot).
- Confirm against the *real* extracted KSU config that `CONFIG_MODULES=y`, `MODULE_SIG_FORCE` is unset, and the in-tree
  module build keeps the cfg80211/mac80211 symbols despite `TRIM_UNUSED_KSYMS=y` (seen in `config/stock_defconfig`;
  these GKI-base symbols are almost certainly identical in the real config, but verify).

## Risks the owner should know

- **HID on Qualcomm** is the item most likely to need iteration; it may not work on the first build.
- Every kernel change means **STRONG must be re-verified** by the owner before trusting the device for hiding.
- Injection drivers add attack surface vs r22. Acceptable per "alles", but flagged.
- NetHunter's chroot and tools are powerful and for use only against systems the owner is authorized to test.
