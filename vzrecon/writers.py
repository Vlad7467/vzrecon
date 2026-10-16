import csv
import json
from pathlib import Path

from .brand import CONTACT, CREW, MOTTO, OWNER, SUPPORT


def emit_txt(path, hits):
    body = "\n".join(e for e, _ in hits)
    Path(path).write_text(body + ("\n" if body else ""), encoding="utf-8")


def emit_json(path, kind, hits):
    payload = {
        "signed_by": CREW,
        "owner": OWNER,
        "contact": CONTACT,
        "support": SUPPORT,
        "motto": MOTTO,
        "protocol": kind,
        "count": len(hits),
        "proxies": [
            {"endpoint": e, "latency_ms": round(l, 2)} for e, l in hits
        ],
    }
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def emit_csv(path, hits):
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["endpoint", "latency_ms"])
        for e, l in hits:
            w.writerow([e, f"{l:.2f}"])
