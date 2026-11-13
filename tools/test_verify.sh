#!/bin/sh
# Tests for verify.sh with fabricated zips (an Image with an embedded gzip ikconfig). Run: sh tools/test_verify.sh
cd "$(dirname "$0")/.." || exit 1
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
fail=0
export PKT="echo result: compatible"   # pkt needs the phone; the stub stands in for it

mkzip() {  # $1 zip path, $2 config text, $3 member name (default Image)
  python3 -I - "$1" "$2" "${3:-Image}" <<'EOF'
import gzip, sys, zipfile
path, cfg, name = sys.argv[1:4]
img = b"\0" * 32 + b"Linux version %s (%s)\0" + b"\0" * 32 + b"Linux version 5.10.269-android12-Wild (test) #1\0" + b"IKCFG_ST" + gzip.compress(cfg.encode()) + b"IKCFG_ED" + b"\0" * 64
with zipfile.ZipFile(path, "w") as z:
    z.writestr(name, img)
    z.writestr("anykernel.sh", "# not run\n")
EOF
}
check() {  # $1 name, $2 expected exit, $3 expected text, then the command
  name=$1 want=$2 text=$3; shift 3
  out=$("$@" 2>&1); got=$?
  if [ "$got" = "$want" ] && printf '%s' "$out" | grep -q -- "$text"; then echo "ok   $name"
  else echo "FAIL $name (exit $got, want $want; output: $out)"; fail=1; fi
}

CFG='CONFIG_A=y
CONFIG_B="x"'
printf '%s\n' "$CFG" > "$T/running"
echo "Linux version 5.10.269-android12-Wild (test) #1" > "$T/version"

mkzip "$T/same.zip" "$CFG"
check "same config is SAME" 0 "^SAME" sh tools/verify.sh "$T/same.zip" "$T/running" "$T/version"

mkzip "$T/extra.zip" "$CFG
CONFIG_EXTRA=y"
check "unexplained extra line is DIFFERENT" 1 "CONFIG_EXTRA=y" sh tools/verify.sh "$T/extra.zip" "$T/running" "$T/version"

printf 'CONFIG_EXTRA=y\n' > "$T/allow"
check "allowed extra line is SAME" 0 "^SAME" env ALLOW="$T/allow" sh tools/verify.sh "$T/extra.zip" "$T/running" "$T/version"

mkzip "$T/noimage.zip" "$CFG" "boot/Other"
check "zip without Image is an error" 2 "no Image" sh tools/verify.sh "$T/noimage.zip" "$T/running" "$T/version"

check "version string is shown" 0 "Linux version 5.10.269-android12-Wild" sh tools/verify.sh "$T/same.zip" "$T/running" "$T/version"

printf 'echo "REJECT: identical to the kernel already running"; echo "result: rejected"; exit 1\n' > "$T/pkt-identical"
printf 'echo "REJECT: KMI mismatch"; echo "result: rejected"; exit 1\n' > "$T/pkt-kmi"
check "pkt identical-reject counts as pass" 0 "^SAME" env PKT="sh $T/pkt-identical" sh tools/verify.sh "$T/same.zip" "$T/running" "$T/version"
check "any other pkt reject fails" 1 "REJECT: KMI" env PKT="sh $T/pkt-kmi" sh tools/verify.sh "$T/same.zip" "$T/running" "$T/version"

echo "Linux version 5.10.269-android12-Other (x) #2" > "$T/otherversion"
check "different version string is DIFFERENT" 1 "version differs" sh tools/verify.sh "$T/same.zip" "$T/running" "$T/otherversion"
check "pkt that cannot run is an error" 2 "pkt did not finish" env PKT=false sh tools/verify.sh "$T/same.zip" "$T/running" "$T/version"

exit $fail
