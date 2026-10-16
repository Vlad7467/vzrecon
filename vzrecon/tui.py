import shutil
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
        if s[i] == "\x1b":
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
        return "\n".join(out)

    def draw(self):
        frame = self._render()
        if frame == self._prev:
            return
        self._prev = frame
        sys.stdout.write("\x1b[H\x1b[2J" + frame)
        sys.stdout.flush()

    def enter(self):
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        sys.stdout.flush()

    def leave(self):
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
