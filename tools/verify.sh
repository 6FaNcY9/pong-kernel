#!/bin/sh
# Is this kernel zip the same kernel as the one running on pong? Reads the zip, never runs anything from it.
#   sh tools/verify.sh <zip> [running-config]
# running-config defaults to the phone's real config (su -c 'zcat /proc/config.gz'; uname is spoofed).
# Prints SAME or DIFFERENT with every unexplained config line, the version strings, and pkt's check.
# Exit 0 = same and pkt has no reject except "identical to the kernel already running"; 1 = different; 2 = error.
H=$(cd "$(dirname "$0")" && pwd)
Z=$1
ALLOW=${ALLOW:-$H/../ci/allowed-config-diff.txt}
PKT=${PKT:-$HOME/projects/pong-kernel-tool/bin/pkt check}
[ -f "$Z" ] || { echo "usage: verify.sh <zip> [running-config]" >&2; exit 2; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

python3 -I "$H/zipkernel.py" config "$Z" > "$T/built" || exit 2
if [ -n "$2" ]; then cp "$2" "$T/running"
else su -c 'zcat /proc/config.gz' > "$T/running" || { echo "cannot read /proc/config.gz" >&2; exit 2; }; fi

echo "built:   $(python3 -I "$H/zipkernel.py" version "$Z")"
[ -z "$2" ] && echo "running: $(su -c 'cat /proc/version')"

cfg() { grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$1" | sort -u; }
cfg "$T/built" > "$T/b"; cfg "$T/running" > "$T/r"
allow=/dev/null; [ -f "$ALLOW" ] && { grep -v '^## ' "$ALLOW" > "$T/allow"; allow=$T/allow; }   # "## " lines are reasons
comm -3 "$T/b" "$T/r" | sed 's/^\t//' | grep -vxF -f "$allow" > "$T/diff"

rc=0
if [ -s "$T/diff" ]; then
  echo "DIFFERENT: config lines only in one of the two (built or running):"; sed 's/^/  /' "$T/diff"; rc=1
else
  echo "SAME config ($(wc -l < "$T/b") lines)"
fi

$PKT "$Z" > "$T/pkt" 2>&1
sed 's/^/pkt: /' "$T/pkt"
if grep '^REJECT:' "$T/pkt" | grep -qv 'identical to the kernel already running'; then
  grep '^REJECT:' "$T/pkt" | grep -v 'identical to the kernel already running'; rc=1
fi
exit $rc
