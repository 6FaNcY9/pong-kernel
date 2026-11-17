# NetHunter recon — r22 baseline (Task 1)

Date: 2026-11-17. Source of truth: the real r22 kernel config extracted from the BakaSU AnyKernel3 zip
(`tools/zipkernel.py config`, 6781 lines; per project memory the CI config is byte-identical to r22).
Not the spoofed `/proc/config.gz` and not `config/stock_defconfig`. Only config-symbol names here — no secrets, no device IDs.

## USB gadget (Kali's NetHunter list) — what r22 already has

Already `=y` in r22: `SERIAL`, `ACM`, `NCM`, `ECM`, `EEM`, `MASS_STORAGE`, **`F_HID`**, `F_FS`
(parents `USB_CONFIGFS=y`, `USB_GADGET=y`).

**HID is already enabled in r22** — so HID/BadUSB needs no kernel change; only userspace gadget wiring (the NetHunter app).

Missing (to add for the NetHunter variant):
- `CONFIG_USB_CONFIGFS_OBEX` — not set
- `CONFIG_USB_CONFIGFS_ECM_SUBSET` — not set
- `CONFIG_USB_CONFIGFS_RNDIS` — not set  (the useful one: USB tether / MITM)

## Module / WiFi base facts (loadable-module path is sound)

- `CONFIG_MODULES=y`, `CONFIG_MODULE_SIG=y`, **`CONFIG_MODULE_SIG_FORCE` not set** (a root-loaded unsigned `.ko` loads)
- `CONFIG_MODVERSIONS=y` (vermagic must match — CI builds the exact kernel, fine)
- `CONFIG_TRIM_UNUSED_KSYMS=y` (defeated by building the driver **in-tree** as a module, so Kbuild keeps the symbols)
- `CONFIG_CFG80211=y`, `CONFIG_MAC80211=y` (built in)

## Netfilter / MITM — r22 already covers almost everything

Already `=y`: `NF_NAT`, `NF_CONNTRACK`, `IP_NF_IPTABLES`, `IP_NF_NAT`, `IP_NF_MANGLE`, `IP_NF_RAW`,
`NETFILTER_XT_TARGET_{TEE,TPROXY,REDIRECT,NETMAP}`, `NETFILTER_XT_MATCH_{SOCKET,COMMENT}`, `BRIDGE=y`.

Missing:
- `CONFIG_BRIDGE_NETFILTER` — not set  (add it: bridge/ebtables MITM)
- `CONFIG_NF_TABLES` — not set  (nftables; **not added** — NetHunter works with iptables-legacy; adding it is scope creep)

## The full kernel delta vs r22 (final)

```
CONFIG_USB_CONFIGFS_OBEX=y
CONFIG_USB_CONFIGFS_ECM_SUBSET=y
CONFIG_USB_CONFIGFS_RNDIS=y
CONFIG_BRIDGE_NETFILTER=y
CONFIG_88XXAU=m      # rtl88xxau injection driver, Task 3
```

## Deferred to owner-present tasks (not needed to write the kernel code)

Device-side recon — current SELinux mode (`getenforce`), whether a NetHunter app/chroot is already installed,
and which gadget functions the live NP2 configfs exposes — moves to Task 4/5 (needs the phone with the owner present).
The config-driven decisions above do not depend on it.
