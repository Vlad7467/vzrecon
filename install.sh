#!/data/data/com.termux/files/usr/bin/bash
# vzrecon bootstrap — VZLOI GROUP ops division
# deploys package tree under ~/VG/proxe_tools/proxcheck_v3.0

set -eu

ROOT="${HOME}/VG/proxe_tools/proxcheck_v3.0"
mkdir -p "${ROOT}/vzrecon"
cd "${ROOT}"

cat > vzrecon/__init__.py <<'EOF'
"""vzrecon — proxy recon engine. VZLOI GROUP // ops division."""
__version__ = "3.0.0"
__codename__ = "IRON VEIL"
__author__ = "VZLOI GROUP"
EOF

cat > vzrecon/__main__.py <<'EOF'
import sys
from .cli import main
sys.exit(main())
EOF

cat > vzrecon/brand.py <<'PYEOF'
"""Brand constants. Signed as VZLOI GROUP."""

BANNER_LINES = (
    "██╗   ██╗███████╗██╗      ██████╗ ██╗",
    "██║   ██║╚══███╔╝██║     ██╔═══██╗██║",
    "██║   ██║  ███╔╝ ██║     ██║   ██║██║",
    "╚██╗ ██╔╝ ███╔╝  ██║     ██║   ██║██║",
    " ╚████╔╝ ███████╗███████╗╚██████╔╝██║",
    "  ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝",
)

SIGNATURE = "VZLOI GROUP // ops"
TOOLNAME  = "vzrecon"
CODNAME   = "IRON VEIL"

# ANSI palette — cold ops theme
class SGR:
    R  = "\x1b[0m"
    B  = "\x1b[1m"
    D  = "\x1b[2m"
    HD = "\x1b[38;5;88m"     # dark blood
    RD = "\x1b[38;5;160m"    # signal red
    AM = "\x1b[38;5;214m"    # amber
    GR = "\x1b[38;5;71m"     # muted green
    CY = "\x1b[38;5;66m"     # steel cyan
    BL = "\x1b[38;5;61m"     # deep blue
    WH = "\x1b[38;5;250m"    # ash
    GY = "\x1b[38;5;238m"    # panel grey
    BG = "\x1b[48;5;233m"    # near black
PYEOF

cat > vzrecon/config.py <<'PYEOF'
"""Config loader. TOML when supplied, dataclass otherwise."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Config:
    workers: int = 1200
    tcp_timeout: float = 3.0
    hs_timeout: float = 6.0

    target_host: str = "api.trongrid.io"
    target_port: int = 443

    render_hz: float = 3.0
    sample_size: int = 10

    source_dir: str = "."
    output_dir: str = "."
    format: str = "txt"
    protocols: tuple[str, ...] = ("http", "socks4", "socks5")

    @classmethod
    def from_toml(cls, path: Path) -> "Config":
        raw: dict[str, Any] = tomllib.loads(path.read_text("utf-8"))
        valid = {f.name for f in fields(cls)}
        unknown = set(raw) - valid
        if unknown:
            raise ValueError(f"unknown keys: {sorted(unknown)}")
        if "protocols" in raw:
            raw["protocols"] = tuple(raw["protocols"])
        return cls(**raw)

    def validate(self) -> None:
        if self.workers < 1:
            raise ValueError("workers must be >= 1")
        if not (1 <= self.target_port <= 65535):
            raise ValueError("target_port out of range")
        if self.format not in {"txt", "json", "csv"}:
            raise ValueError(f"bad format: {self.format}")
        for p in self.protocols:
            if p not in {"http", "socks4", "socks5"}:
                raise ValueError(f"bad protocol: {p}")
PYEOF

cat > vzrecon/protocols.py <<'PYEOF'
"""Protocol-level validation.

Every probe performs a full handshake against the configured target
and returns round-trip latency in milliseconds. Sockets are closed
before return; a failed handshake never leaks an fd.

  http       RFC 7231 sec 4.3.6 — CONNECT tunnelling
  socks5     RFC 1928 + RFC 1929 — no-auth greeting
  socks4     original spec — IPv4 target only
"""

from __future__ import annotations

import asyncio
import socket
from time import perf_counter


async def _dial(host: str, port: int, timeout: float):
    return await asyncio.wait_for(
        asyncio.open_connection(host, port), timeout=timeout
    )


async def http_connect(host, port, target_host, target_port, *,
                       tcp_timeout: float, hs_timeout: float):
    r = w = None
    t0 = perf_counter()
    try:
        r, w = await _dial(host, port, tcp_timeout)
        w.write(
            f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
            f"Host: {target_host}:{target_port}\r\n"
            f"Proxy-Connection: keep-alive\r\n\r\n".encode()
        )
        await w.drain()
        line = await asyncio.wait_for(r.readline(), timeout=hs_timeout)
        if not line.startswith(b"HTTP/"):
            return None
        parts = line.split(b" ", 2)
        if len(parts) < 2 or parts[1] != b"200":
            return None
        return (perf_counter() - t0) * 1000.0
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError):
        return None
    finally:
        if w is not None:
            w.close()


async def socks5_connect(host, port, target_host, target_port, *,
                         tcp_timeout: float, hs_timeout: float):
    r = w = None
    t0 = perf_counter()
    try:
        r, w = await _dial(host, port, tcp_timeout)
        w.write(b"\x05\x01\x00")            # version, 1 method, no-auth
        await w.drain()
        greet = await asyncio.wait_for(r.readexactly(2), timeout=hs_timeout)
        if greet != b"\x05\x00":
            return None

        name = target_host.encode("idna")
        if len(name) > 255:
            return None
        w.write(
            b"\x05\x01\x00\x03"
            + bytes((len(name),))
            + name
            + target_port.to_bytes(2, "big")
        )
        await w.drain()

        head = await asyncio.wait_for(r.readexactly(4), timeout=hs_timeout)
        if head[0] != 0x05 or head[1] != 0x00:
            return None
        atyp = head[3]
        if atyp == 0x01:
            tail = 4 + 2
        elif atyp == 0x04:
            tail = 16 + 2
        elif atyp == 0x03:
            ln = await asyncio.wait_for(r.readexactly(1), timeout=hs_timeout)
            tail = ln[0] + 2
        else:
            return None
        await asyncio.wait_for(r.readexactly(tail), timeout=hs_timeout)
        return (perf_counter() - t0) * 1000.0
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError):
        return None
    finally:
        if w is not None:
            w.close()


async def socks4_connect(host, port, target_host, target_port, *,
                         tcp_timeout: float, hs_timeout: float):
    r = w = None
    t0 = perf_counter()
    try:
        try:
            ipv4 = socket.gethostbyname(target_host)
        except OSError:
            return None
        octets = bytes(int(x) for x in ipv4.split("."))
        r, w = await _dial(host, port, tcp_timeout)
        w.write(
            b"\x04\x01"
            + target_port.to_bytes(2, "big")
            + octets
            + b"\x00"
        )
        await w.drain()
        reply = await asyncio.wait_for(r.readexactly(8), timeout=hs_timeout)
        if reply[0] != 0x00 or reply[1] != 0x5A:
            return None
        return (perf_counter() - t0) * 1000.0
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError):
        return None
    finally:
        if w is not None:
            w.close()


REGISTRY = {
    "http":   http_connect,
    "socks4": socks4_connect,
    "socks5": socks5_connect,
}
PYEOF

cat > vzrecon/metrics.py <<'PYEOF'
"""Live throughput meter with rolling window."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

_SPARK = "▁▂▃▄▅▆▇█"


@dataclass
class Meter:
    total: int = 0
    done: int = 0
    ok: int = 0
    fail: int = 0
    started_at: float = field(default_factory=time.monotonic)
    _win: deque[tuple[float, int]] = field(
        default_factory=lambda: deque(maxlen=60)
    )
    _prev: int = 0

    def tick(self, *, ok: bool) -> None:
        self.done += 1
        if ok:
            self.ok += 1
        else:
            self.fail += 1

    def sample(self) -> None:
        now = time.monotonic()
        self._win.append((now, self.done - self._prev))
        self._prev = self.done

    def rate(self) -> float:
        if len(self._win) < 2:
            return 0.0
        t0, _ = self._win[0]
        t1, _ = self._win[-1]
        dt = t1 - t0
        if dt <= 0:
            return 0.0
        return sum(n for _, n in self._win) / dt

    def eta(self) -> float | None:
        remain = self.total - self.done
        r = self.rate()
        if r <= 0 or remain <= 0:
            return None
        return remain / r

    def spark(self, width: int = 20) -> str:
        if not self._win:
            return " " * width
        seq = [n for _, n in self._win][-width:]
        hi = max(seq) or 1
        line = "".join(_SPARK[min(7, (n * 8) // hi)] for n in seq)
        return line.rjust(width)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    @property
    def progress(self) -> float:
        return self.done / self.total if self.total else 0.0


def fmt_dur(s: float | None) -> str:
    if s is None:
        return "--:--"
    n = int(s)
    if n < 3600:
        return f"{n // 60:02d}:{n % 60:02d}"
    return f"{n // 3600}h{(n % 3600) // 60:02d}m"


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")
PYEOF

cat > vzrecon/engine.py <<'PYEOF'
"""Async scan engine.

Fixed worker pool pulling from a bounded queue. Sinks are line-buffered
so a scan terminated mid-flight never loses committed results.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Callable, Optional

from .config import Config
from .metrics import Meter
from .protocols import REGISTRY


@dataclass(slots=True)
class Hit:
    endpoint: str
    kind: str
    latency_ms: float


class Scan:
    def __init__(self, kind: str, source: Path, sink: Path, cfg: Config,
                 on_hit: Optional[Callable[[Hit], None]] = None) -> None:
        self.kind = kind
        self.source = source
        self.sink = sink
        self.cfg = cfg
        self.on_hit = on_hit
        self.meter = Meter()
        self._q: asyncio.Queue[str] = asyncio.Queue()
        self._sink_fh = None
        self.hits: list[tuple[str, float]] = []

    def _load(self) -> list[str]:
        if not self.source.exists():
            return []
        seen: set[str] = set()
        out: list[str] = []
        for raw in self.source.read_text("utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if line and line not in seen:
                seen.add(line)
                out.append(line)
        return out

    async def run(self) -> None:
        entries = self._load()
        self.meter.total = len(entries)
        if not entries:
            return

        for e in entries:
            self._q.put_nowait(e)
        self._sink_fh = self.sink.open("w", buffering=1)

        validator = REGISTRY[self.kind]
        cfg = self.cfg

        async def consume() -> None:
            while True:
                try:
                    entry = self._q.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    host, _, port_s = entry.rpartition(":")
                    if not host or not port_s.isdigit():
                        self.meter.tick(ok=False)
                        continue
                    lat = await validator(
                        host, int(port_s),
                        cfg.target_host, cfg.target_port,
                        tcp_timeout=cfg.tcp_timeout,
                        hs_timeout=cfg.hs_timeout,
                    )
                    if lat is None:
                        self.meter.tick(ok=False)
                    else:
                        self.meter.tick(ok=True)
                        self._sink_fh.write(entry + "\n")
                        self.hits.append((entry, lat))
                        if self.on_hit:
                            with contextlib.suppress(Exception):
                                self.on_hit(Hit(entry, self.kind, lat))
                except asyncio.CancelledError:
                    return
                except Exception:
                    self.meter.tick(ok=False)
                finally:
                    self._q.task_done()

        workers = [asyncio.create_task(consume()) for _ in range(cfg.workers)]
        try:
            await asyncio.gather(*workers)
        finally:
            for t in workers:
                t.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            if self._sink_fh is not None:
                self._sink_fh.close()


def discover(cfg: Config) -> list[tuple[str, Path]]:
    base = Path(cfg.source_dir)
    found: list[tuple[str, Path]] = []
    for proto in cfg.protocols:
        src = base / f"{proto}_proxies.txt"
        if src.exists() and src.stat().st_size > 0:
            found.append((proto, src))
    return found
PYEOF

cat > vzrecon/writers.py <<'PYEOF'
"""Output adapters."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def emit_txt(path: Path, hits: list[tuple[str, float]]) -> None:
    body = "\n".join(e for e, _ in hits)
    path.write_text(body + ("\n" if body else ""), encoding="utf-8")


def emit_json(path: Path, kind: str, hits: list[tuple[str, float]]) -> None:
    payload = {
        "signed_by": "VZLOI GROUP",
        "protocol": kind,
        "count": len(hits),
        "proxies": [
            {"endpoint": e, "latency_ms": round(l, 2)} for e, l in hits
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def emit_csv(path: Path, hits: list[tuple[str, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["endpoint", "latency_ms"])
        for e, l in hits:
            w.writerow([e, f"{l:.2f}"])
PYEOF

cat > vzrecon/selftest.py <<'PYEOF'
"""Protocol handlers validated against in-process mock servers.

Any divergence here is a bug in the validator, not the network.
"""

from __future__ import annotations

import asyncio
import contextlib

from .protocols import http_connect, socks4_connect, socks5_connect


async def _mock_http(r, w):
    try:
        line = await r.readline()
        if line.startswith(b"CONNECT"):
            w.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            await w.drain()
        while True:
            h = await r.readline()
            if h in (b"\r\n", b"\n", b""):
                break
    finally:
        w.close()


async def _mock_socks5(r, w):
    try:
        g = await r.readexactly(2)
        if g != b"\x05\x01":
            return
        await r.readexactly(1)
        w.write(b"\x05\x00")
        await w.drain()
        head = await r.readexactly(4)
        atyp = head[3]
        if atyp == 0x01:
            await r.readexactly(6)
        elif atyp == 0x03:
            ln = (await r.readexactly(1))[0]
            await r.readexactly(ln + 2)
        elif atyp == 0x04:
            await r.readexactly(18)
        w.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await w.drain()
    finally:
        w.close()


async def _mock_socks4(r, w):
    try:
        await r.readexactly(8)
        w.write(b"\x00\x5a\x00\x00\x00\x00\x00\x00")
        await w.drain()
    finally:
        w.close()


async def _serve(handler):
    srv = await asyncio.start_server(handler, "127.0.0.1", 0)
    return srv, srv.sockets[0].getsockname()[1]


async def run() -> int:
    failures = 0
    cases = [
        ("http",   _mock_http,   http_connect),
        ("socks5", _mock_socks5, socks5_connect),
        ("socks4", _mock_socks4, socks4_connect),
    ]
    for name, handler, validator in cases:
        srv, port = await _serve(handler)
        try:
            lat = await validator(
                "127.0.0.1", port, "example.com", 443,
                tcp_timeout=2.0, hs_timeout=2.0,
            )
            ok = lat is not None
            mark = "ok  " if ok else "FAIL"
            print(f"  {name:<7} {mark}  {lat or 0:>7.2f} ms")
            if not ok:
                failures += 1
        finally:
            srv.close()
            with contextlib.suppress(Exception):
                await srv.wait_closed()
    return 0 if failures == 0 else 1
PYEOF

cat > vzrecon/tui.py <<'PYEOF'
"""Alt-screen TUI. Diff-rendered; a frame is only flushed on change."""

from __future__ import annotations

import shutil
import sys
import time
from datetime import datetime, timezone

from .brand import BANNER_LINES, SIGNATURE, SGR, TOOLNAME, CODNAME
from .engine import Hit, Scan
from .metrics import fmt_dur, fmt_int


def _visible(s: str) -> int:
    n = 0
    i = 0
    while i < len(s):
        if s[i] == "\x1b":
            j = s.find("m", i)
            if j == -1:
                break
            i = j + 1
            continue
        n += 1
        i += 1
    return n


def _pad(s: str, width: int) -> str:
    w = _visible(s)
    return s if w >= width else s + " " * (width - w)


class TUI:
    def __init__(self, scans: list[Scan], target: str, workers: int,
                 session_id: str) -> None:
        self.scans = scans
        self.target = target
        self.workers = workers
        self.session_id = session_id
        self._prev = ""
        self._hits: list[Hit] = []
        self._cap = 10

    def collect(self, hit: Hit) -> None:
        self._hits.append(hit)
        if len(self._hits) > 100:
            self._hits = self._hits[-100:]

    def attach(self) -> None:
        for s in self.scans:
            s.on_hit = self.collect

    def _width(self) -> int:
        try:
            return max(60, min(shutil.get_terminal_size((80, 24)).columns - 2, 82))
        except OSError:
            return 78

    def _render(self) -> str:
        W = self._width()
        bar_w = W - 30
        out: list[str] = []

        # header banner
        top = f"{SGR.RD}┌{'─' * (W - 2)}┐{SGR.R}"
        out.append(top)
        for line in BANNER_LINES:
            pad = (W - 2 - _visible(line)) // 2
            out.append(
                f"{SGR.RD}│{SGR.R}{' ' * pad}"
                f"{SGR.HD}{line}{SGR.R}"
                f"{' ' * (W - 2 - pad - _visible(line))}{SGR.RD}│{SGR.R}"
            )
        sub = f"{SIGNATURE}  ·  {TOOLNAME} {CODNAME}"
        pad = (W - 2 - len(sub)) // 2
        out.append(
            f"{SGR.RD}│{SGR.R}{' ' * pad}"
            f"{SGR.GY}{sub}{SGR.R}"
            f"{' ' * (W - 2 - pad - len(sub))}{SGR.RD}│{SGR.R}"
        )
        out.append(f"{SGR.RD}└{'─' * (W - 2)}┘{SGR.R}")
        out.append("")

        # session strip
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        left = f" session {SGR.AM}{self.session_id}{SGR.R}"
        right = f"{SGR.GY}{now}{SGR.R} "
        gap = W - _visible(left) - _visible(right)
        out.append(left + " " * max(0, gap) + right)
        out.append(
            f" {SGR.GY}target{SGR.R} {SGR.WH}{self.target}{SGR.R}"
            f"   {SGR.GY}workers{SGR.R} {SGR.WH}{self.workers}{SGR.R}"
        )
        out.append(f"{SGR.GY}{'─' * W}{SGR.R}")

        # per-scan panels
        ok_total = done_total = all_total = 0
        for s in self.scans:
            m = s.meter
            ok_total += m.ok
            done_total += m.done
            all_total += m.total

            frac = m.progress
            fill = int(frac * bar_w)
            bar = f"{SGR.CY}{'█' * fill}{SGR.GY}{'░' * (bar_w - fill)}{SGR.R}"

            kind = s.kind.upper().ljust(7)
            out.append(
                f" {SGR.B}{kind}{SGR.R} "
                f"{SGR.GR}ok {m.ok:>5}{SGR.R}  "
                f"{SGR.RD}dead {m.fail:>6}{SGR.R}  "
                f"{SGR.GY}rate {m.rate():>6.0f}/s{SGR.R}  "
                f"{SGR.GY}eta {fmt_dur(m.eta())}{SGR.R}"
            )
            out.append(f"    {bar}  {SGR.WH}{frac * 100:>5.1f}%{SGR.R}")
            out.append(f"    {SGR.CY}{m.spark(24)}{SGR.R}")
            out.append("")

        # summary
        out.append(f"{SGR.GY}{'─' * W}{SGR.R}")
        pct = (ok_total / done_total * 100.0) if done_total else 0.0
        out.append(
            f" {SGR.B}alive{SGR.R} {SGR.GR}{fmt_int(ok_total)}{SGR.R}"
            f"   {SGR.GY}checked {fmt_int(done_total)}/{fmt_int(all_total)}"
            f"   hit-rate {pct:.2f}%{SGR.R}"
        )
        out.append("")

        # ticker
        if self._hits:
            out.append(f" {SGR.GY}── hits ──{SGR.R}")
            for h in self._hits[-self._cap:]:
                out.append(
                    f"   {SGR.GR}▸{SGR.R} "
                    f"{SGR.CY}{h.kind:<7}{SGR.R}"
                    f"{h.endpoint:<26} "
                    f"{SGR.GY}{h.latency_ms:>6.0f} ms{SGR.R}"
                )

        # footer
        out.append("")
        out.append(
            f"{SGR.GY} signed {SGR.R}{SGR.AM}{SIGNATURE}{SGR.R}"
            f"{SGR.GY}   ·   q to abort{SGR.R}"
        )

        return "\n".join(out)

    def draw(self) -> None:
        f = self._render()
        if f == self._prev:
            return
        self._prev = f
        sys.stdout.write("\x1b[H\x1b[2J" + f)
        sys.stdout.flush()

    def enter(self) -> None:
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        sys.stdout.flush()

    def leave(self) -> None:
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
PYEOF

cat > vzrecon/cli.py <<'PYEOF'
"""CLI orchestration."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import secrets
import signal
import sys
import time
from pathlib import Path

from . import __version__, __codename__
from .brand import BANNER_LINES, SIGNATURE, SGR, TOOLNAME
from .config import Config
from .engine import Scan, discover
from .tui import TUI
from .writers import emit_csv, emit_json, emit_txt


def _args(argv):
    p = argparse.ArgumentParser(
        prog=TOOLNAME,
        description="proxy recon engine // VZLOI GROUP ops",
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOLNAME} {__version__} ({__codename__})")
    p.add_argument("-c", "--config", type=Path, help="TOML config")
    p.add_argument("-d", "--dir", type=Path, default=Path.cwd(),
                   help="source directory (default: cwd)")
    p.add_argument("-o", "--output-dir", type=Path, default=Path("."),
                   help="output directory")
    p.add_argument("-t", "--target",
                   help="override target host:port")
    p.add_argument("-w", "--workers", type=int)
    p.add_argument("--format", choices=("txt", "json", "csv"))
    p.add_argument("--only", help="comma-separated protocols (http,socks4,socks5)")
    p.add_argument("--self-test", action="store_true",
                   help="run protocol self-test and exit")
    p.add_argument("--plain", action="store_true",
                   help="no alt-screen, plain output")
    return p.parse_args(argv)


def _merge(args) -> Config:
    cfg = Config.from_toml(args.config) if args.config else Config()
    cfg.source_dir = str(args.dir)
    cfg.output_dir = str(args.output_dir)
    if args.workers is not None:
        cfg.workers = args.workers
    if args.format is not None:
        cfg.format = args.format
    if args.target:
        h, _, pt = args.target.partition(":")
        cfg.target_host = h
        cfg.target_port = int(pt) if pt else 443
    if args.only:
        cfg.protocols = tuple(s.strip() for s in args.only.split(",") if s.strip())
    cfg.validate()
    return cfg


def _banner() -> str:
    lines = []
    for line in BANNER_LINES:
        lines.append(f"  {SGR.HD}{line}{SGR.R}")
    return "\n".join(lines)


async def _dispatch(scans, cfg, plain):
    if plain:
        await asyncio.gather(*(s.run() for s in scans))
        return

    sid = secrets.token_hex(4).upper()
    tui = TUI(scans, f"{cfg.target_host}:{cfg.target_port}", cfg.workers, sid)
    tui.attach()
    tui.enter()

    tasks = [asyncio.create_task(s.run()) for s in scans]
    tick = 1.0 / cfg.render_hz
    try:
        while not all(t.done() for t in tasks):
            tui.draw()
            await asyncio.sleep(tick)
        tui.draw()
    finally:
        for t in tasks:
            t.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(*tasks, return_exceptions=True)
        tui.leave()


def _write(scans, cfg, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, int] = {}
    for s in scans:
        entries = s.hits
        summary[s.kind] = len(entries)
        stem = out_dir / f"{s.kind}_alive"
        if cfg.format == "txt":
            emit_txt(stem.with_suffix(".txt"), entries)
        elif cfg.format == "json":
            emit_json(stem.with_suffix(".json"), s.kind, entries)
        else:
            emit_csv(stem.with_suffix(".csv"), entries)
    return summary


def main(argv=None) -> int:
    args = _args(argv)

    if args.self_test:
        from .selftest import run
        print()
        print(f"  {SGR.RD}{SIGNATURE}{SGR.R}  ·  protocol self-test")
        print(f"  {SGR.GY}{'─' * 46}{SGR.R}")
        rc = asyncio.run(run())
        print()
        return rc

    try:
        cfg = _merge(args)
    except (ValueError, FileNotFoundError) as e:
        print(f"{SGR.RD}config:{SGR.R} {e}", file=sys.stderr)
        return 2

    sources = discover(cfg)
    if not sources:
        print(f"{SGR.RD}no sources{SGR.R} in {cfg.source_dir}",
              file=sys.stderr)
        return 3

    print(_banner())
    print(f"  {SGR.GY}protocols:{SGR.R} {', '.join(k for k, _ in sources)}")
    print(f"  {SGR.GY}sources:{SGR.R} {len(sources)} file(s)")
    print(f"  {SGR.GY}target:{SGR.R} {cfg.target_host}:{cfg.target_port}")
    print(f"  {SGR.GY}workers:{SGR.R} {cfg.workers}")
    print()

    scans = []
    for kind, src in sources:
        sink = Path(cfg.output_dir) / f"{kind}_alive.txt"
        scans.append(Scan(kind, src, sink, cfg))

    t0 = time.monotonic()
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_dispatch(scans, cfg, args.plain))
    dt = time.monotonic() - t0

    summary = _write(scans, cfg, Path(cfg.output_dir))

    print()
    print(f"  {SGR.RD}{SIGNATURE}{SGR.R}  ·  scan complete")
    print(f"  {SGR.GY}{'─' * 46}{SGR.R}")
    print(f"  {SGR.GY}duration:{SGR.R} {dt:.1f}s")
    total = 0
    for s in scans:
        m = s.meter
        pct = (m.ok / m.done * 100) if m.done else 0
        total += m.ok
        print(f"  {s.kind:<7} {m.ok:>6} / {m.done:<6}  ({pct:5.1f}%)")
    print(f"  {SGR.GY}{'─' * 46}{SGR.R}")
    print(f"  total  {SGR.GR}{total}{SGR.R} alive  →  {cfg.output_dir}")
    print()
    return 0
PYEOF

cat > pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "vzrecon"
version = "3.0.0"
description = "Protocol-level proxy validator — VZLOI GROUP ops"
requires-python = ">=3.11"
authors = [{name = "VZLOI GROUP"}]
license = {text = "MIT"}
readme = "README.md"
keywords = ["proxy", "socks", "recon", "vzloi"]

[project.scripts]
vzrecon = "vzrecon.cli:main"

[tool.setuptools.packages.find]
include = ["vzrecon*"]
EOF

cat > config.toml <<'EOF'
# vzrecon runtime config
workers       = 1200
tcp_timeout   = 3.0
hs_timeout    = 6.0

target_host   = "api.trongrid.io"
target_port   = 443

render_hz     = 3.0
sample_size   = 10

source_dir    = "."
output_dir    = "."
format        = "txt"
protocols     = ["http", "socks4", "socks5"]
EOF

cat > README.md <<'EOF'
# vzrecon

    VZLOI GROUP // ops
    protocol-level proxy validator

## install

    pip install -e .
    vzrecon --self-test

## usage

    vzrecon                            # scan cwd for *_proxies.txt
    vzrecon -d /path/to/lists          # explicit source directory
    vzrecon -c config.toml             # load TOML config
    vzrecon --only http,socks5         # subset of protocols
    vzrecon --self-test                # verify protocol handlers
    vzrecon --plain                    # pipe-friendly output

## protocol handling

  HTTP    CONNECT per RFC 7231 §4.3.6. Accepts a 200 status line;
          anything else is a failure.

  SOCKS5  RFC 1928. Greeting offers no-auth only — user/pass auth
          would add a full round-trip per probe with no gain in
          accuracy for the recon use case. Domain ATYP.

  SOCKS4  Original spec, IPv4 targets only. The hostname is resolved
          on the client side before the request is placed on the wire.

Latency is measured from the moment the TCP connection is issued to
the moment the protocol reply is received, monotonic clock.

## outputs

  <proto>_alive.txt     plain endpoints, one per line
  <proto>_alive.json    {signed_by, protocol, count, proxies[]}
  <proto>_alive.csv     endpoint,latency_ms

Selection via --format or the `format` key in TOML.

## exit codes

  0   scan completed
  1   self-test failed
  2   config error
  3   no source files found

## design notes

- worker pool is a fixed set of coroutines pulling from a bounded
  queue. no per-connection task creation, no semaphore crutches.

- sinks open with line buffering. an interrupted scan never
  truncates committed results.

- transport failures are silent by design. scanning thousands of
  dead endpoints produces noise, not signal.

- TUI runs in the alternate screen buffer and restores the terminal
  on every exit path including SIGINT.

- result JSON files carry a `signed_by` field. downstream tooling
  can fingerprint which crew produced the list.

## license

MIT. see LICENSE.
EOF

cat > LICENSE <<'EOF'
MIT License

Copyright (c) 2026 VZLOI GROUP

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
EOF

touch .vzloi
cat > .vzloi <<'EOF'
crew: VZLOI GROUP
tool: vzrecon
codename: IRON VEIL
sig: 0x7F3A9C21
EOF

echo "[3/3] installing package…"
pip install -e . >/dev/null 2>&1 || {
    echo "pip install -e . failed — run it manually"
    exit 1
}

cat > vzrecon.sh <<'WRAP'
#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
python -m vzrecon "$@"
WRAP
chmod +x vzrecon.sh

echo ""
echo "  install path : $ROOT"
echo "  entrypoint   : vzrecon    (or ./vzrecon.sh)"
echo "  self-test    : vzrecon --self-test"
echo ""
