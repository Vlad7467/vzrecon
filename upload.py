"""Minimal PyPI uploader. No twine, no Rust."""
import sys, os, re, hashlib, requests
from pathlib import Path

REPO = sys.argv[1] if len(sys.argv) > 1 else "pypi"
TOKEN = os.environ.get("PYPI_TOKEN", "").strip()
if not TOKEN:
    try:
        import netrc
        a = netrc.netrc().authenticators("upload.pypi.org")
        if a: TOKEN = a[2]
    except Exception:
        pass
if not TOKEN:
    TOKEN = input("token> ").strip()

URLS = {
    "pypi":     "https://upload.pypi.org/legacy/",
    "testpypi": "https://test.pypi.org/legacy/",
}
url = URLS[REPO]

files = sorted(Path("dist").glob("*"))
if not files:
    print("dist/ пуст — сначала python -m build"); sys.exit(1)

for f in files:
    data = f.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    meta = {
        ":action": "file_upload",
        "protocol_version": "1",
        "name": "vzrecon",
        "version": re.match(r"vzrecon-(\d+\.\d+\.\d+)", f.name).group(1),
        "filetype": "bdist_wheel" if f.suffix == ".whl" else "sdist",
        "sha256_digest": digest,
        "metadata_version": "2.1",
        "pyversion": "py3" if f.suffix == ".whl" else "source",
    }
    with f.open("rb") as fh:
        r = requests.post(
            url,
            auth=("__token__", TOKEN),
            data=meta,
            files={"content": (f.name, fh)},
            timeout=120,
        )
    if r.status_code in (200, 201):
        print(f"  ok  {f.name}")
    else:
        print(f"  FAIL {f.name}  {r.status_code}")
        print(r.text[:500])
        sys.exit(1)
print(f"\ndone")
