"""One-shot release pipeline. Rewrites source, builds, uploads, tags, pushes.

Run from repository root. Requires ~/.netrc with upload.pypi.org credentials.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
VERSION = "3.1.0"


def write(rel: str, body: str) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    print(f"  w {rel}")


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=False)


# ─── source ───────────────────────────────────────────────────────

write("vzrecon/brand.py", '''BANNER = (
    "  ██╗   ██╗███████╗██╗      ██████╗ ██╗",
    "  ██║   ██║╚══███╔╝██║     ██╔═══██╗██║",
    "  ██║   ██║  ███╔╝ ██║     ██║   ██║██║",
    "  ╚██╗ ██╔╝ ███╔╝  ██║     ██║   ██║██║",
    "   ╚████╔╝ ███████╗███████╗╚██████╔╝██║",
    "    ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝",
)

CREW     = "VZLOI GROUP"
SUFFIX   = "ops"
TOOL     = "vzrecon"
CODENAME = "IRON VEIL"
TAGLINE  = "recon division"
OWNER    = "ghost189"
CONTACT  = "@foskza"
MOTTO    = "no gods, no masters, no logs"
SUPPORT  = "bot support"


class SGR:
    R     = "\\x1b[0m"
    B     = "\\x1b[1m"
    D     = "\\x1b[2m"
    I     = "\\x1b[3m"

    IRON  = "\\x1b[38;5;238m"
    STEEL = "\\x1b[38;5;242m"
    ASH   = "\\x1b[38;5;248m"
    IVORY = "\\x1b[38;5;252m"

    BLOOD = "\\x1b[38;5;88m"
    CRIM  = "\\x1b[38;5;160m"
    GOLD  = "\\x1b[38;5;220m"
    AMBER = "\\x1b[38;5;214m"

    ICE   = "\\x1b[38;5;117m"
    VERD  = "\\x1b[38;5;77m"

    BG     = "\\x1b[48;5;233m"
    BG_BAR = "\\x1b[48;5;236m"
''')

write("vzrecon/__init__.py", f'''__version__ = "{VERSION}"
__codename__ = "IRON VEIL"
__author__ = "VZLOI GROUP"
__owner__ = "ghost189"
__contact__ = "@foskza"
__motto__ = "no gods, no masters, no logs"
__all__ = ["Config", "Scan", "Meter", "Hit"]
''')

write("vzrecon/writers.py", '''import csv
import json
from pathlib import Path

from .brand import CONTACT, CREW, MOTTO, OWNER, SUPPORT


def emit_txt(path, hits):
    body = "\\n".join(e for e, _ in hits)
    Path(path).write_text(body + ("\\n" if body else ""), encoding="utf-8")


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
''')

write("vzrecon/tui.py", '''import shutil
import sys
from datetime import datetime, timezone

from . import __version__
from .brand import (
    BANNER, CODENAME, CONTACT, CREW, MOTTO, OWNER, SUFFIX, SGR, TOOL,
)
from .metrics import fmt_dur, fmt_int, fmt_uptime


def _visible(s):
    n = 0
    i = 0
    while i < len(s):
        if s[i] == "\\x1b":
            j = s.find("m", i)
            if j == -1:
                break
            i = j + 1
            continue
        n += 1
        i += 1
    return n


def _pad_right(s, w):
    return s + " " * max(0, w - _visible(s))


class TUI:
    def __init__(self, scans, target, workers, sid, mode):
        self.scans = scans
        self.target = target
        self.workers = workers
        self.sid = sid
        self.mode = mode
        self._prev = ""
        self._hits = []
        self._cap = 6

    def collect(self, hit):
        self._hits.append(hit)
        if len(self._hits) > 200:
            self._hits = self._hits[-200:]

    def attach(self):
        for s in self.scans:
            s.on_hit = self.collect

    def _w(self):
        try:
            return max(64, min(shutil.get_terminal_size((80, 24)).columns - 2, 96))
        except OSError:
            return 78

    def _h(self):
        try:
            return shutil.get_terminal_size((80, 24)).lines
        except OSError:
            return 24

    def _top(self, W):
        r = SGR.R
        utc = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
        left = (
            f" {SGR.CRIM}{SGR.B}{CREW}{r}"
            f"{SGR.IRON}  {SGR.STEEL}{SUFFIX}{r}"
            f"{SGR.IRON}  ┃  {r}{SGR.GOLD}{TOOL} {__version__}{r}"
            f"{SGR.IRON}  ┃  {r}{SGR.ASH}{CODENAME}{r}"
        )
        right = f"{SGR.IRON}{utc}{r} "
        pad = W - _visible(left) - _visible(right)
        return f"{SGR.BG}{left}{' ' * max(0, pad)}{right}{r}"

    def _strip(self, W):
        r = SGR.R
        col = (W - 6) // 2
        left = [
            (f"{SGR.IRON}SESSION{r}", f"{SGR.GOLD}{SGR.B}{self.sid}{r}"),
            (f"{SGR.IRON}POOL   {r}", f"{SGR.IVORY}{self.workers}{r}"),
            (f"{SGR.IRON}OWNER  {r}", f"{SGR.CRIM}{OWNER}{r}"),
        ]
        right = [
            (f"{SGR.IRON}TARGET {r}", f"{SGR.IVORY}{self.target}{r}"),
            (f"{SGR.IRON}MODE   {r}", f"{SGR.AMBER}{self.mode}{r}"),
            (f"{SGR.IRON}CONTACT{r}", f"{SGR.CRIM}{CONTACT}{r}"),
        ]
        out = [""]
        for (lk, lv), (rk, rv) in zip(left, right):
            row = f"   {lk}  {lv}"
            out.append(_pad_right(row, col + 4) + f"{rk}  {rv}")
        out.append("")
        return out

    def _table(self, W):
        r = SGR.R
        out = []
        out.append(
            f"   {SGR.IRON}PROTO    LIVE    DEAD   RATE     ETA     p95   PROGRESS{r}"
        )
        out.append(f"   {SGR.BLOOD}{'─' * (W - 6)}{r}")
        bar_w = max(8, W - 66)
        for s in self.scans:
            m = s.meter
            live = f"{SGR.VERD}{SGR.B}{m.ok:>5}{r}"
            dead = f"{SGR.STEEL}{m.fail:>7}{r}"
            rate = f"{SGR.IVORY}{m.rate():>5.0f}/s{r}"
            eta = fmt_dur(m.eta())
            eta_c = SGR.IVORY if eta != "--:--" else SGR.IRON
            eta_s = f"{eta_c}{eta:>5}{r}"
            p95 = m.percentile(0.95)
            if p95 is None:
                p95_s = f"{SGR.IRON}  -- {r}"
            elif p95 < 500:
                p95_s = f"{SGR.VERD}{p95:>4.0f}ms{r}"
            elif p95 < 1500:
                p95_s = f"{SGR.AMBER}{p95:>4.0f}ms{r}"
            else:
                p95_s = f"{SGR.CRIM}{p95:>4.0f}ms{r}"
            frac = m.progress
            fill = int(frac * bar_w)
            bar = f"{SGR.ICE}{'▓' * fill}{SGR.IRON}{'░' * (bar_w - fill)}{r}"
            pct = f"{SGR.ASH}{frac * 100:>3.0f}%{r}"
            out.append(
                f"   {SGR.ASH}{s.kind.lower():<7}{r} "
                f"{live}  {dead}  {rate}  {eta_s}  {p95_s}  {bar} {pct}"
            )
        return out

    def _live(self, W):
        r = SGR.R
        if not self._hits:
            return []
        out = [
            f"   {SGR.IRON}LIVE{r}",
            f"   {SGR.BLOOD}{'─' * (W - 6)}{r}",
        ]
        for h in self._hits[-self._cap:]:
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            if h.latency_ms < 300:
                c = SGR.VERD
            elif h.latency_ms < 1000:
                c = SGR.AMBER
            else:
                c = SGR.CRIM
            out.append(
                f"   {SGR.CRIM}▌{r} {SGR.IRON}{ts}{r} "
                f"{SGR.ICE}{h.kind:<6}{r}"
                f"{SGR.IVORY}{h.endpoint.ljust(30)}{r}"
                f"{c}{h.latency_ms:>5.0f}ms{r}"
            )
        return out

    def _status(self, W):
        r = SGR.R
        ok = sum(s.meter.ok for s in self.scans)
        done = sum(s.meter.done for s in self.scans)
        total = sum(s.meter.total for s in self.scans)
        pct = (ok / done * 100.0) if done else 0.0
        up = fmt_uptime(self.scans[0].meter.elapsed) if self.scans else "00:00:00"
        left = (
            f" {SGR.VERD}{SGR.B}{fmt_int(ok)}{r}"
            f"{SGR.IRON} alive  {r}"
            f"{SGR.ASH}{fmt_int(done)}/{fmt_int(total)}{r}"
            f"{SGR.IRON} checked  {r}"
            f"{SGR.GOLD}{pct:.2f}%{r}"
            f"{SGR.IRON}  {r}{SGR.ASH}{up}{r}"
        )
        right = f"{SGR.IRON}ctrl+c quit{r} "
        pad = W - _visible(left) - _visible(right)
        return f"{SGR.BG_BAR}{left}{' ' * max(0, pad)}{right}{r}"

    def _foot(self, W):
        r = SGR.R
        a = f"{CREW} // {OWNER}"
        b = f"{CONTACT}"
        pad = W - _visible(a) - _visible(b) - 6
        return (
            f"   {SGR.BLOOD}{SGR.I}{a}{r}"
            f"{' ' * max(1, pad)}{SGR.IRON}{b}{r}"
        )

    def _render(self):
        W = self._w()
        H = self._h()
        out = [self._top(W), ""]
        if H >= 26:
            for ln in BANNER:
                pad = (W - len(ln)) // 2
                out.append(f"{' ' * pad}{SGR.CRIM}{ln}{SGR.R}")
            sub = f"{CREW}  ::  {SUFFIX}"
            out.append(f"{' ' * ((W - len(sub)) // 2)}{SGR.IRON}{sub}{SGR.R}")
            out.append(f"{' ' * ((W - len(MOTTO)) // 2)}{SGR.IRON}{SGR.I}{MOTTO}{SGR.R}")
            out.append("")
        out += self._strip(W)
        out += self._table(W)
        out.append("")
        out += self._live(W)
        out.append("")
        out.append(f"   {SGR.BLOOD}{'─' * (W - 6)}{SGR.R}")
        out.append(self._status(W))
        out.append("")
        out.append(self._foot(W))
        return "\\n".join(out)

    def draw(self):
        frame = self._render()
        if frame == self._prev:
            return
        self._prev = frame
        sys.stdout.write("\\x1b[H\\x1b[2J" + frame)
        sys.stdout.flush()

    def enter(self):
        sys.stdout.write("\\x1b[?1049h\\x1b[?25l")
        sys.stdout.flush()

    def leave(self):
        sys.stdout.write("\\x1b[?25h\\x1b[?1049l")
        sys.stdout.flush()
''')

write("vzrecon/cli.py", '''import argparse
import asyncio
import contextlib
import secrets
import sys
import time
from pathlib import Path

from . import __codename__, __version__
from .brand import (
    BANNER, CODENAME, CONTACT, CREW, MOTTO, OWNER, SUFFIX, SGR, TAGLINE, TOOL,
)
from .config import PRESETS, Config
from .engine import Scan, discover
from .platform import notify, wake_lock, wake_unlock
from .tui import TUI
from .writers import emit_csv, emit_json, emit_txt


def _args(argv):
    p = argparse.ArgumentParser(
        prog=TOOL,
        description=f"proxy validator // {CREW} // {OWNER}",
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOL} {__version__} ({__codename__})")
    p.add_argument("-c", "--config", type=Path)
    p.add_argument("-d", "--dir", type=Path, default=Path.cwd())
    p.add_argument("-o", "--output-dir", type=Path, default=Path("."))
    p.add_argument("-t", "--target")
    p.add_argument("-w", "--workers", type=int)
    p.add_argument("--format", choices=("txt", "json", "csv"))
    p.add_argument("--only")
    p.add_argument("--preset", choices=tuple(PRESETS.keys()))
    p.add_argument("--list-presets", action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--plain", action="store_true")
    p.add_argument("--no-notify", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--about", action="store_true")
    return p.parse_args(argv)


def _merge(a):
    c = Config.from_toml(a.config) if a.config else Config()
    if a.preset:
        c = c.apply_preset(a.preset)
    c.source_dir = str(a.dir)
    c.output_dir = str(a.output_dir)
    if a.workers is not None:
        c.workers = a.workers
    if a.format:
        c.format = a.format
    if a.target:
        host, _, port = a.target.partition(":")
        c.target_host = host
        c.target_port = int(port) if port else 443
    if a.only:
        c.protocols = tuple(p.strip() for p in a.only.split(",") if p.strip())
    if a.no_notify:
        c.notify = False
    if a.verify:
        c.verify = True
    c.validate()
    return c


async def _dispatch(scans, cfg, plain):
    if plain:
        await asyncio.gather(*(s.run() for s in scans))
        return
    sid = secrets.token_hex(4).upper()
    tui = TUI(scans, f"{cfg.target_host}:{cfg.target_port}",
              cfg.workers, sid, "balanced")
    tui.attach()
    tui.enter()
    tasks = [asyncio.create_task(s.run()) for s in scans]
    tick = 1.0 / cfg.render_hz
    try:
        while not all(t.done() for t in tasks):
            for s in scans:
                s.meter.sample()
            tui.draw()
            await asyncio.sleep(tick)
        tui.draw()
    finally:
        for t in tasks:
            t.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(*tasks, return_exceptions=True)
        tui.leave()


def _write(scans, cfg, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in scans:
        stem = out_dir / f"{s.kind}_alive"
        if cfg.format == "txt":
            emit_txt(stem.with_suffix(".txt"), s.hits)
        elif cfg.format == "json":
            emit_json(stem.with_suffix(".json"), s.kind, s.hits)
        else:
            emit_csv(stem.with_suffix(".csv"), s.hits)


def _splash():
    print()
    for ln in BANNER:
        print(f"  {SGR.CRIM}{ln}{SGR.R}")
    print(f"  {SGR.IRON}{CREW}  ::  {SUFFIX}{SGR.R}")
    print(f"  {SGR.IRON}{SGR.I}{MOTTO}{SGR.R}")
    print()


def _about():
    print(f"""
  {SGR.CRIM}{SGR.B}{CREW}{SGR.R} {SGR.IRON}// {SUFFIX}{SGR.R}
  {SGR.IRON}{TAGLINE} // {MOTTO}{SGR.R}

  {SGR.IRON}owner    {SGR.R}{SGR.CRIM}{OWNER}{SGR.R}
  {SGR.IRON}contact  {SGR.R}{SGR.CRIM}{CONTACT}{SGR.R}
  {SGR.IRON}support  {SGR.R}{SGR.CRIM}bot support{SGR.R}
  {SGR.IRON}tool     {SGR.R}{TOOL} {__version__} ({CODENAME}){SGR.R}
""")
    return 0


def _presets():
    print(f"\\n  {SGR.CRIM}{SGR.B}{CREW} // {SUFFIX}{SGR.R}  ·  presets")
    print(f"  {SGR.IRON}{'─' * 46}{SGR.R}")
    for n, v in PRESETS.items():
        print(
            f"  {SGR.GOLD}{n:<10}{SGR.R} {SGR.STEEL}"
            f"workers={v['workers']:<5} tcp={v['tcp_timeout']}s "
            f"hs={v['hs_timeout']}s hz={v['render_hz']}{SGR.R}"
        )
    print()
    return 0


def main(argv=None):
    a = _args(argv)
    if a.about:
        return _about()
    if a.list_presets:
        return _presets()
    if a.self_test:
        from .selftest import run
        print(f"\\n  {SGR.CRIM}{SGR.B}{CREW} // {SUFFIX}{SGR.R}  ::  protocol self-test")
        print(f"  {SGR.IRON}owner {OWNER}  ::  {CONTACT}{SGR.R}")
        print(f"  {SGR.IRON}{'─' * 46}{SGR.R}")
        rc = asyncio.run(run())
        print()
        return rc
    try:
        cfg = _merge(a)
    except (ValueError, FileNotFoundError) as e:
        print(f"{SGR.CRIM}config:{SGR.R} {e}", file=sys.stderr)
        return 2
    sources = discover(cfg)
    if not sources:
        print(f"{SGR.CRIM}no sources{SGR.R} in {cfg.source_dir}", file=sys.stderr)
        return 3
    _splash()
    print(f"  {SGR.IRON}crew     {SGR.R}{SGR.CRIM}{CREW}  //  {OWNER}{SGR.R}")
    print(f"  {SGR.IRON}contact  {SGR.R}{SGR.CRIM}{CONTACT}{SGR.R}")
    print(f"  {SGR.IRON}protocols{SGR.R} {', '.join(k for k, _ in sources)}")
    print(f"  {SGR.IRON}sources  {SGR.R} {len(sources)} file(s)")
    print(f"  {SGR.IRON}target   {SGR.R} {cfg.target_host}:{cfg.target_port}")
    print(f"  {SGR.IRON}workers  {SGR.R} {cfg.workers}\\n")
    if cfg.wake_lock:
        wake_lock()
    scans = []
    Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)
    for kind, src in sources:
        scans.append(Scan(kind, src, Path(cfg.output_dir) / f"{kind}_alive.txt", cfg))
    t0 = time.monotonic()
    try:
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(_dispatch(scans, cfg, a.plain))
    finally:
        if cfg.wake_lock:
            wake_unlock()
    dt = time.monotonic() - t0
    _write(scans, cfg, Path(cfg.output_dir))
    print(f"\\n  {SGR.CRIM}{SGR.B}{CREW}  ::  scan complete{SGR.R}")
    print(f"  {SGR.IRON}{'─' * 46}{SGR.R}")
    print(f"  {SGR.IRON}duration{SGR.R}  {dt:.1f}s")
    total = 0
    for s in scans:
        m = s.meter
        pct = (m.ok / m.done * 100) if m.done else 0
        total += m.ok
        print(f"  {s.kind:<7} {m.ok:>6} / {m.done:<6}  ({pct:5.1f}%)")
    print(f"  {SGR.IRON}{'─' * 46}{SGR.R}")
    print(f"  {SGR.VERD}{SGR.B}{total}{SGR.R} alive  ->  {cfg.output_dir}")
    print(f"  {SGR.IRON}{OWNER}  ::  {CONTACT}  ::  bot support{SGR.R}\\n")
    if cfg.notify:
        notify(
            f"{TOOL} · scan complete",
            f"{total} alive · {sum(s.meter.done for s in scans)} checked · {dt:.0f}s",
        )
    return 0
''')


# ─── version bump ─────────────────────────────────────────────────

pp = ROOT / "pyproject.toml"
text = pp.read_text()
text = re.sub(r'version = "[^"]+"', f'version = "{VERSION}"', text, count=1)
pp.write_text(text)
print(f"  w pyproject.toml  ->  {VERSION}")


# ─── build + upload + push ────────────────────────────────────────

for d in ("dist", "build", "vzrecon.egg-info"):
    shutil.rmtree(ROOT / d, ignore_errors=True)

print("\\n[build]")
run([sys.executable, "-m", "build"])

print("\\n[upload]")
up = ROOT / "upload.py"
if up.exists():
    run([sys.executable, str(up), "pypi"], check=False)
else:
    print("  upload.py missing, skipping")

print("\\n[git]")
run(["git", "add", "-A"])
run([
    "git", "-c", "user.name=ghost189",
    "-c", "user.email=ghost189@vzloi.group",
    "commit", "-m", f"{VERSION} :: release",
], check=False)
run(["git", "push"], check=False)

print(f"\\n{VERSION} released")
