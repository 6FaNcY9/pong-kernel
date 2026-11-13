"""Fails the build if anything in the repo can change the kernel without a commit here, or if a secret slipped in.
- every third-party `uses:` under .github is pinned to a full commit SHA
- every `*_commit:` input in pong.yml is a full commit SHA
- no `secrets.*` other than GITHUB_TOKEN
- no file that looks like a key, keybox or certificate (the repo is public)
Usage: python3 ci/check_pins.py [repo-root]"""
import re
import sys
from pathlib import Path

USES = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^\s'\"#]+)", re.M)
SECRET = re.compile(r"secrets\.([A-Za-z0-9_]+)")
COMMIT_INPUT = re.compile(r"^\s*(\w+_commit):\s*['\"]?([^\s'\"#]*)", re.M)
SHA = re.compile(r"^[0-9a-f]{40}$")
SECRET_FILE = re.compile(r"(^keybox.*\.xml$|\.pem$|\.p12$|\.jks$|\.keystore$|^boot_key$|^hbk$|^kb.*\.xml$)", re.I)


def check(root):
    root = Path(root)
    problems = []
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root).as_posix()
        if ".git" in f.relative_to(root).parts[:1] or not f.is_file():
            continue
        if SECRET_FILE.search(f.name):
            problems.append(f"{rel}: looks like a key or certificate; never commit it")
        if not rel.startswith(".github/") or f.suffix not in (".yml", ".yaml"):
            continue
        text = f.read_text(errors="replace")
        for ref in USES.findall(text):
            if ref.startswith("./") or ref.startswith("docker://"):
                continue
            if "@" not in ref or not SHA.match(ref.rsplit("@", 1)[1]):
                problems.append(f"{rel}: {ref} is not pinned to a commit SHA")
        for name in sorted(set(SECRET.findall(text)) - {"GITHUB_TOKEN"}):
            problems.append(f"{rel}: uses secrets.{name}; only GITHUB_TOKEN is allowed")
        if f.name == "pong.yml":
            for name, value in COMMIT_INPUT.findall(text):
                if not SHA.match(value):
                    problems.append(f"{rel}: {name} is '{value}', not a commit SHA")
    return problems


if __name__ == "__main__":
    found = check(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    print("\n".join(found) or "all pinned, no secrets")
    sys.exit(1 if found else 0)
