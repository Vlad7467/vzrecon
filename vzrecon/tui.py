import shutil, sys
from datetime import datetime, timezone
from . import __version__ as _VERSION
from .brand import (BANNER, CODENAME, CREW, OWNER, CONTACT, MOTTO,
                    SUPPORT, SUFFIX, TAGLINE, TOOL, SGR)
from .metrics import fmt_dur, fmt_int, fmt_uptime


def _vis(s):
    n = 0; i = 0
    while i < len(s):
        if s[i] == "\x1b":
            j = s.find("m", i)
            if j == -1: break
            i = j + 1; continue
        n += 1; i += 1
    return n


def _r(s, w):
    v = _vis(s)
    return s + " " * max(0, w - v)


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

    def collect(self, h):
        self._hits.append(h)
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

    # ─── top bar: one line, dense ──────────────────────────────
    def _bar_top(self, W):
        r = SGR.R
        utc = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
        left = (f" {SGR.CRIM}{SGR.B}{CREW}{r}"
                f"{SGR.IRON}  {r}{SGR.STEEL}{SUFFIX}{r}"
                f"{SGR.IRON}  ┃  {r}{SGR.GOLD}{TOOL} {SGR.IRON}{_VERSION}{r}"
                f"{SGR.IRON}  ┃  {r}{SGR.ASH}{CODENAME}{r}")
        right = f"{SGR.IRON}{utc}{r} "
        pad = W - _vis(left) - _vis(right)
        return f"{SGR.BG}{left}{' ' * max(0, pad)}{right}{r}"

    # ─── info strip: two aligned columns ───────────────────────
    def _strip(self, W):
        r = SGR.R
        col = (W - 6) // 2
        L = [
            (f"{SGR.IRON}SESSION{r}", f"{SGR.GOLD}{SGR.B}{self.sid}{r}"),
            (f"{SGR.IRON}POOL{r}   ", f"{SGR.IVORY}{self.workers}{r}"),
            (f"{SGR.IRON}OWNER{r}  ", f"{SGR.CRIM}{OWNER}{r}"),
        ]
        Rt = [
            (f"{SGR.IRON}TARGET{r} ", f"{SGR.IVORY}{self.target}{r}"),
            (f"{SGR.IRON}MODE{r}   ", f"{SGR.AMBER}{self.mode}{r}"),
            (f"{SGR.IRON}CONTACT{r}", f"{SGR.CRIM}{CONTACT}{r}"),
        ]
        out = [""]
        for (lk, lv), (rk, rv) in zip(L, Rt):
            left = f"   {lk}  {lv}"
            right = f"{rk}  {rv}"
            out.append(_r(left, col + 4) + right)
        out.append("")
        return out

    # ─── metrics table ─────────────────────────────────────────
    def _table(self, W):
        r = SGR.R
        o = []
        o.append(f"   {SGR.IRON}PROTO    LIVE    DEAD   RATE     ETA     p95   PROGRESS{r}")
        o.append(f"   {SGR.BLOOD}{'─' * (W - 6)}{r}")

        bar_w = max(8, W - 66)
        for s in self.scans:
            m = s.meter
            k = s.kind.lower().ljust(7)
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
            bar = (f"{SGR.ICE}{'▓' * fill}"
                   f"{SGR.IRON}{'░' * (bar_w - fill)}{r}")
            pct = f"{SGR.ASH}{frac * 100:>3.0f}%{r}"

            o.append(
                f"   {SGR.ASH}{k}{r} "
                f"{live}  {dead}  {rate}  {eta_s}  {p95_s}  "
                f"{bar} {pct}"
            )
        return o

    # ─── live hits ─────────────────────────────────────────────
    def _live(self, W):
        r = SGR.R
        o = []
        if not self._hits:
            return o
        o.append(f"   {SGR.IRON}LIVE{r}")
        o.append(f"   {SGR.BLOOD}{'─' * (W - 6)}{r}")
        for h in self._hits[-self._cap:]:
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            if h.latency_ms < 300:
                c = SGR.VERD
            elif h.latency_ms < 1000:
                c = SGR.AMBER
            else:
                c = SGR.CRIM
            ep = h.endpoint.ljust(30)
            o.append(
                f"   {SGR.CRIM}▌{r} {SGR.IRON}{ts}{r} "
                f"{SGR.ICE}{h.kind:<6}{r}"
                f"{SGR.IVORY}{ep}{r}"
                f"{c}{h.latency_ms:>5.0f}ms{r}"
            )
        return o

    # ─── bottom status ─────────────────────────────────────────
    def _status(self, W):
        r = SGR.R
        ok = sum(s.meter.ok for s in self.scans)
        done = sum(s.meter.done for s in self.scans)
        tot = sum(s.meter.total for s in self.scans)
        pct = (ok / done * 100.0) if done else 0.0
        up = fmt_uptime(self.scans[0].meter.elapsed) if self.scans else "00:00:00"
        left = (f" {SGR.VERD}{SGR.B}{fmt_int(ok)}{r}"
                f"{SGR.IRON} alive  {r}"
                f"{SGR.ASH}{fmt_int(done)}/{fmt_int(tot)}{r}"
                f"{SGR.IRON} checked  {r}"
                f"{SGR.GOLD}{pct:.2f}%{r}"
                f"{SGR.IRON}  {r}"
                f"{SGR.ASH}{up}{r}")
        right = f"{SGR.IRON}ctrl+c quit{r} "
        pad = W - _vis(left) - _vis(right)
        return f"{SGR.BG_BAR}{left}{' ' * max(0, pad)}{right}{r}"

    def _foot(self, W):
        r = SGR.R
        a = f"{CREW} // {OWNER}"
        b = f"{CONTACT}"
        pad = W - _vis(a) - _vis(b) - 6
        return f"   {SGR.BLOOD}{SGR.I}{a}{r}{' ' * max(1, pad)}{SGR.IRON}{b}{r}"

    def _render(self):
        W = self._w()
        H = self._h()
        o = []
        o.append(self._bar_top(W))
        o.append("")
        if H >= 26:
            for ln in BANNER:
                pad = (W - len(ln)) // 2
                o.append(f"{' ' * pad}{SGR.CRIM}{ln}{r}")
            sub = f"{CREW}  ::  {SUFFIX}"
            pad = (W - len(sub)) // 2
            o.append(f"{' ' * pad}{SGR.IRON}{sub}{r}")
            pad = (W - len(MOTTO)) // 2
            o.append(f"{' ' * pad}{SGR.IRON}{SGR.I}{MOTTO}{r}")
            o.append("")
        o += self._strip(W)
        o += self._table(W)
        o.append("")
        o += self._live(W)
        o.append("")
        o.append(f"   {SGR.BLOOD}{'─' * (W - 6)}{r}")
        o.append(self._status(W))
        o.append("")
        o.append(self._foot(W))
        return "\n".join(o)

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
