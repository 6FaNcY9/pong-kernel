#!/bin/sh
# Is this kernel zip the same kernel as the one running on pong? Reads the zip, never runs anything from it.
#   sh tools/verify.sh <zip> [running-config running-version]
# Defaults read the phone as root: /proc/config.gz and /proc/version.
# Three checks, all must pass (exit 0); 1 = different; 2 = could not check:
#  1. version string: built == running (covers toolchain, branding and build stamp)
#  2. embedded config == /proc/config.gz. NOTE: on this phone both are the stock GKI config shown for hiding
#     (no CONFIG_KSU), so this check only proves the shown config; it says nothing about KSU/susfs/BBG.
#  3. pkt check: the real proof is pkt's "identical to the kernel already running" (same Image sha256);
#     any other REJECT fails, and pkt not finishing is an error.
H=$(cd "$(dirname "$0")" && pwd)
Z=$1
ALLOW=${ALLOW:-$H/../ci/allowed-config-diff.txt}
PKT=${PKT:-$HOME/projects/pong-kernel-tool/bin/pkt check}
[ -f "$Z" ] || { echo "usage: verify.sh <zip> [running-config running-version]" >&2; exit 2; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

python3 -I "$H/zipkernel.py" config "$Z" > "$T/built" || exit 2
python3 -I "$H/zipkernel.py" version "$Z" > "$T/bver" || exit 2
if [ -n "$2" ]; then cp "$2" "$T/running"; cp "${3:?running-version file missing}" "$T/rver"
else
  su -c 'zcat /proc/config.gz' > "$T/running" || { echo "cannot read /proc/config.gz" >&2; exit 2; }
  su -c 'cat /proc/version' > "$T/rver" || { echo "cannot read /proc/version" >&2; exit 2; }
fi

rc=0
echo "built:   $(cat "$T/bver")"
echo "running: $(cat "$T/rver")"
if [ "$(cat "$T/bver")" != "$(cat "$T/rver")" ]; then echo "DIFFERENT: version differs"; rc=1; fi

cfg() { grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$1" | sort -u; }
cfg "$T/built" > "$T/b"; cfg "$T/running" > "$T/r"
allow=/dev/null; [ -f "$ALLOW" ] && { grep -v '^## ' "$ALLOW" > "$T/allow"; allow=$T/allow; }   # "## " lines are reasons
comm -3 "$T/b" "$T/r" | sed 's/^\t//' | grep -vxF -f "$allow" > "$T/diff"
if [ -s "$T/diff" ]; then
  echo "DIFFERENT: config lines only in one of the two (built or running):"; sed 's/^/  /' "$T/diff"; rc=1
else
  echo "SAME config ($(wc -l < "$T/b") lines; this is the shown stock config, see the note at the top)"
fi

$PKT "$Z" > "$T/pkt" 2>&1; prc=$?
sed 's/^/pkt: /' "$T/pkt"
others=$(grep '^REJECT:' "$T/pkt" | grep -v 'identical to the kernel already running')
if [ -n "$others" ]; then echo "$others"; [ $rc = 0 ] && rc=1
elif ! grep -qE '^result: (compatible|rejected)' "$T/pkt" || { [ $prc != 0 ] && [ $prc != 1 ] && [ $prc != 3 ]; }; then
  echo "ERROR: pkt did not finish (exit $prc)"; rc=2
elif grep -q '^REJECT: identical to the kernel already running' "$T/pkt"; then
  echo "IDENTICAL: same Image as the running kernel (pkt sha256)"
fi
exit $rc
