import shutil
import sys
from datetime import datetime, timezone

from . import __version__
from .brand import (
    CONTACT, CODENAME, CREW, GROUP_BANNER, OWNER, RU_CONTACT, RU_DEV,
    RU_OWNER, RU_SUPPORT, SGR, TAG_LINE, TOOL, VZLOI_CYR, render_version,
)
from .metrics import fmt_dur, fmt_int, fmt_uptime


def _w(s):
    n = i = 0
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


def _rpad(s, width):
    return s + " " * max(0, width - _w(s))


def _bar(frac, width):
    fill = int(frac * width)
    return f"{SGR.ICE}{'█' * fill}{SGR.IRON}{'░' * (width - fill)}{SGR.R}"


def _lat(ms):
    if ms is None:
        return f"{SGR.IRON}   --{SGR.R}"
    if ms < 500:
        return f"{SGR.VERD}{ms:>5.0f}ms{SGR.R}"
    if ms < 1500:
        return f"{SGR.AMBER}{ms:>5.0f}ms{SGR.R}"
    return f"{SGR.CRIM}{ms:>5.0f}ms{SGR.R}"


class TUI:
    def __init__(self, scans, target, workers, sid, mode):
        self.scans = scans
        self.target = target
        self.workers = workers
        self.sid = sid
        self.mode = mode
        self._prev = ""
        self._hits = []

    def collect(self, h):
        self._hits.append(h)
        if len(self._hits) > 200:
            self._hits = self._hits[-200:]

    def attach(self):
        for s in self.scans:
            s.on_hit = self.collect

    def _render(self):
        try:
            t = shutil.get_terminal_size((80, 24))
            cols, lines = t.columns, t.lines
        except OSError:
            cols, lines = 80, 24
        W = max(52, min(cols - 2, 100))
        r = SGR.R

        utc = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
        up = fmt_uptime(self.scans[0].meter.elapsed) if self.scans else "00:00:00"

        out = []

        # full branding only when terminal has vertical room
        if lines >= 48:
            for ln in GROUP_BANNER:
                out.append(f"  {SGR.CRIM}{ln}{r}")
            out.append("")
            for ln in VZLOI_CYR:
                out.append(f"  {SGR.CRIM}{ln}{r}")
            out.append("")
            out.append(f"  {SGR.ASH}{TAG_LINE}{r}")
            out.append("")
            for ln in render_version(__version__):
                out.append(f"  {SGR.GOLD}{ln}{r}")
            out.append("")
            wmax = max(len(RU_DEV), len(RU_OWNER), len(RU_CONTACT), len(RU_SUPPORT)) + 1
            out.append(f"  {SGR.IRON}{RU_DEV + ':':<{wmax}}{r} {SGR.CRIM}{CREW}{r}")
            out.append(f"  {SGR.IRON}{RU_OWNER + ':':<{wmax}}{r} {SGR.CRIM}{OWNER}{r}")
            out.append(f"  {SGR.IRON}{RU_CONTACT + ':':<{wmax}}{r} {SGR.CRIM}{CONTACT}{r}")
            out.append(f"  {SGR.IRON}{RU_SUPPORT + ':':<{wmax}}{r} {SGR.CRIM}{CONTACT}{r}")
            out.append("")

        left = f"  {SGR.CRIM}{SGR.B}{CREW}{r}  {SGR.IRON}·  {r}{SGR.GOLD}{TOOL} {__version__}{r}"
        right = f"{SGR.IRON}{utc}{r}  "
        out.append(_rpad(left, W - len(right)) + right)
        out.append(f"  {SGR.BLOOD}{'─' * (W - 4)}{r}")
        out.append("")

        out.append(
            f"  {SGR.IRON}target {SGR.IVORY}{self.target}{r}"
            f"   {SGR.IRON}uptime {SGR.IVORY}{up}{r}"
        )
        out.append(
            f"  {SGR.IRON}session {SGR.GOLD}{self.sid}{r}"
            f"   {SGR.IRON}pool {SGR.IVORY}{self.workers}{r}"
            f"   {SGR.IRON}mode {SGR.AMBER}{self.mode}{r}"
        )
        out.append("")

        bar_w = max(10, W - 34)
        for s in self.scans:
            m = s.meter
            frac = m.progress
            bar = _bar(frac, bar_w)
            name = s.kind.lower().ljust(7)
            out.append(f"  {SGR.ASH}{name}{r}{bar}  {SGR.IVORY}{frac * 100:>3.0f}%{r}")
            live = f"{SGR.VERD}{SGR.B}{fmt_int(m.ok):>5}{r}"
            dead = f"{SGR.STEEL}{fmt_int(m.fail):>7}{r}"
            rate = f"{SGR.IVORY}{m.rate():>5.0f}/s{r}"
            eta = fmt_dur(m.eta())
            eta_c = SGR.IVORY if eta != "--:--" else SGR.IRON
            eta_s = f"{eta_c}{eta:>5}{r}"
            p95 = m.percentile(0.95)
            out.append(
                f"         {live} live  {dead} dead  {rate}  {eta_s}  {_lat(p95)}"
            )
            out.append("")

        ok = sum(s.meter.ok for s in self.scans)
        done = sum(s.meter.done for s in self.scans)
        total = sum(s.meter.total for s in self.scans)
        pct = (ok / done * 100.0) if done else 0.0
        out.append(f"  {SGR.BLOOD}{'─' * (W - 4)}{r}")
        out.append(
            f"  {SGR.IRON}alive {SGR.VERD}{SGR.B}{fmt_int(ok)}{r}"
            f"   {SGR.IRON}checked {SGR.ASH}{fmt_int(done)}/{fmt_int(total)}{r}"
            f"   {SGR.IRON}hit {SGR.GOLD}{pct:.2f}%{r}"
        )
        out.append("")

        for h in self._hits[-5:]:
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            ep = h.endpoint.ljust(min(30, W - 34))
            out.append(
                f"  {SGR.IRON}{ts}{r}  {SGR.ICE}{h.kind:<7}{r}"
                f"{SGR.IVORY}{ep}{r} {_lat(h.latency_ms)}"
            )

        out.append("")
        wmax = max(len(RU_DEV), len(RU_OWNER), len(RU_CONTACT)) + 1
        out.append(
            f"  {SGR.IRON}{RU_DEV + ':':<{wmax}}{r} {SGR.CRIM}{CREW}{r}"
            f"    {SGR.IRON}{RU_OWNER + ':':<{wmax}}{r} {SGR.CRIM}{OWNER}{r}"
            f"    {SGR.IRON}{RU_CONTACT + ':':<{wmax}}{r} {SGR.CRIM}{CONTACT}{r}"
        )
        return "\n".join(out)

    def draw(self):
        f = self._render()
        if f == self._prev:
            return
        self._prev = f
        sys.stdout.write("\x1b[H\x1b[2J" + f)
        sys.stdout.flush()

    def enter(self):
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        sys.stdout.flush()

    def leave(self):
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
