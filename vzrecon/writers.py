import csv, json
from pathlib import Path
from .brand import CREW
def emit_txt(p,hits):
    b="\n".join(e for e,_ in hits)
    Path(p).write_text(b+("\n" if b else ""),encoding="utf-8")
def emit_json(p,kind,hits):
    payload={"signed_by":CREW,"protocol":kind,"count":len(hits),
             "proxies":[{"endpoint":e,"latency_ms":round(l,2)} for e,l in hits]}
    Path(p).write_text(json.dumps(payload,indent=2),encoding="utf-8")
def emit_csv(p,hits):
    with Path(p).open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["endpoint","latency_ms"])
        for e,l in hits: w.writerow([e,f"{l:.2f}"])
