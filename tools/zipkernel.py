"""Read a kernel zip without running anything from it.
  python3 -I zipkernel.py config <zip>    print the kernel config embedded in Image (CONFIG_IKCONFIG)
  python3 -I zipkernel.py version <zip>   print the "Linux version ..." string
Exit 2 with a message if the zip has no Image or the Image has no embedded config.
(Upstream's extract-ikconfig writes to /tmp, which Android does not have.)"""
import gzip
import posixpath
import re
import sys
import zipfile
import zlib

MAX = 256 << 20   # an arm64 GKI Image is ~40 MB; refuse anything absurd


def image(path):
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if posixpath.basename(info.filename) in ("Image", "Image.gz") and info.file_size <= MAX:
                data = z.read(info)
                return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
    sys.exit("no Image in zip")


def config(img):
    pos = img.find(b"IKCFG_ST\x1f\x8b\x08")
    if pos < 0:
        sys.exit("no embedded config in Image")
    return zlib.decompressobj(31).decompress(img[pos + 8:]).decode()


def version(img):
    m = re.search(rb"Linux version \d[^\0\n]+", img)   # \d skips the printf format "Linux version %s"
    return m.group().decode(errors="replace") if m else "Linux version: not found"


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("config", "version"):
        sys.exit(__doc__)
    img = image(sys.argv[2])
    print(config(img) if sys.argv[1] == "config" else version(img), end="" if sys.argv[1] == "config" else "\n")
