import shutil, sys
from datetime import datetime, timezone
from .brand import BANNER, CODENAME, CREW, SUFFIX, TAGLINE, TOOL, SGR
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

def _pad(s, w):
    v = _vis(s)
    return s if v >= w else s + " " * (w - v)

def _hr(l, c, r, ch, w):
    return f"{SGR.BLOOD}{l}{ch * w}{r}{SGR.R}"

def _box_top(title, w):
    t = f" {title} "
    pad = w - _vis(t) - 2
    return f"{SGR.BLOOD}┌─{r}{SGR.CRIM}{SGR.B}{t}{SGR.R}{SGR.BLOOD}{'─' * pad}─┐{SGR.R}"

def _box_bot(w):
    return f"{SGR.BLOOD}└{'─' * w}┘{SGR.R}"

def _box_mid(s, w):
    v = _vis(s)
    return f"{SGR.BLOOD}│{SGR.R} {s}{' ' * (w - v - 1)}{SGR.BLOOD}│{SGR.R}"

class TUI:
    def __init__(self, scans, target, workers, sid, mode):
        self.scans = scans
        self.target = target
        self.workers = workers
        self.sid = sid
        self.mode = mode
        self._prev = ""
        self._hits = []
        self._cap = 7

    def collect(self, h):
        self._hits.append(h)
        if len(self._hits) > 200:
            self._hits = self._hits[-200:]

    def attach(self):
        for s in self.scans:
            s.on_hit = self.collect

    def _w(self):
        try:
            return max(64, min(shutil.get_terminal_size((80, 24)).columns - 2, 84))
        except OSError:
            return 78

    def _header(self, W):
        o = []
        r = SGR.R
        cap = f"{SGR.CRIM}{SGR.B}{CREW}{r} {SGR.IRON}·{r} {SGR.GOLD}{TOOL} 3.0.0{r} {SGR.IRON}·{r} {SGR.SLATE}{CODENAME}{r}"
        left = f" {cap} "
        right = f" {SGR.IRON}{TAGLINE}{r} "
        pad = W - _vis(left) - _vis(right) - 2
        o.append(f"{SGR.BLOOD}┌{'─' * (W - 2)}┐{r}")
        o.append(f"{SGR.BLOOD}│{r}{left}{' ' * pad}{right}{SGR.BLOOD}│{r}")
        for ln in BANNER:
            p = (W - 2 - len(ln)) // 2
            o.append(
                f"{SGR.BLOOD}│{r}{' ' * max(0, p)}{SGR.CRIM}{SGR.B}{ln}{r}"
                f"{' ' * max(0, W - 2 - p - len(ln))}{SGR.BLOOD}│{r}"
            )
        sub = f"{CREW} // {SUFFIX}"
        p = (W - 2 - len(sub)) // 2
        o.append(
            f"{SGR.BLOOD}│{r}{' ' * p}{SGR.SLATE}{sub}{r}"
            f"{' ' * (W - 2 - p - len(sub))}{SGR.BLOOD}│{r}"
        )
        o.append(_box_bot(W - 2))
        return o

    def _strip(self, W):
        r = SGR.R
        o = []
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        up = fmt_uptime(self.scans[0].meter.elapsed) if self.scans else "00:00:00"
        row1 = (
            f"{SGR.IRON}session{r}  {SGR.GOLD}{SGR.B}{self.sid}{r}"
            f"     {SGR.IRON}uptime{r}  {SGR.IVORY}{up}{r}"
            f"     {SGR.IRON}utc{r}  {SGR.IVORY}{now}{r}"
        )
        row2 = (
            f"{SGR.IRON}target{r}  {SGR.IVORY}{self.target}{r}"
            f"     {SGR.IRON}pool{r}  {SGR.IVORY}{self.workers}{r}"
            f"     {SGR.IRON}mode{r}  {SGR.AMBER}{self.mode}{r}"
        )
        o.append(f"  {row1}")
        o.append(f"  {row2}")
        o.append("")
        return o

    def _panel(self, s, W):
        r = SGR.R
        o = []
        m = s.meter
        kind = s.kind.upper()
        head = f"── {kind} "
        rule = W - _vis(head) - 4
        o.append(f"  {SGR.CRIM}{SGR.B}{head}{r}{SGR.BLOOD}{'─' * max(0, rule)}{r}")
        bar_w = W - 32
        frac = m.progress
        fill = int(frac * bar_w)
        bar = f"{SGR.ICE}{'█' * fill}{SGR.IRON}{'░' * (bar_w - fill)}{r}"
        p95 = m.percentile(0.95)
        p95s = f"{p95:>5.0f}ms" if p95 is not None else "    --"
        eta = fmt_dur(m.eta())
        o.append(
            f"   {SGR.IRON}live{r} {SGR.GREEN}{SGR.B}{m.ok:>6}{r}"
            f"   {SGR.IRON}dead{r} {SGR.CRIM}{m.fail:>6}{r}"
            f"   {SGR.IRON}rate{r} {SGR.IVORY}{m.rate():>6.0f}/s{r}"
            f"   {SGR.IRON}eta{r} {SGR.IVORY}{eta}{r}"
            f"   {SGR.IRON}p95{r} {SGR.ASH}{p95s}{r}"
        )
        o.append(f"   {bar}  {SGR.ASH}{frac * 100:>5.1f}%{r}")
        o.append(f"   {SGR.ICE}{m.spark(bar_w)}{r}")
        o.append("")
        return o

    def _summary(self, W):
        r = SGR.R
        o = []
        ok_t = sum(s.meter.ok for s in self.scans)
        done_t = sum(s.meter.done for s in self.scans)
        all_t = sum(s.meter.total for s in self.scans)
        pct = (ok_t / done_t * 100.0) if done_t else 0.0
        o.append(f"  {SGR.BLOOD}{'─' * (W - 4)}{r}")
        o.append(
            f"   {SGR.IRON}alive{r} {SGR.VERD}{SGR.B}{fmt_int(ok_t)}{r}"
            f"    {SGR.IRON}checked{r} {SGR.ASH}{fmt_int(done_t)}/{fmt_int(all_t)}{r}"
            f"    {SGR.IRON}hit-rate{r} {SGR.GOLD}{pct:.2f}%{r}"
        )
        o.append("")
        return o

    def _live(self, W):
        r = SGR.R
        o = []
        if not self._hits:
            return o
        head = f"── live hits "
        rule = W - _vis(head) - 4
        o.append(f"  {SGR.CRIM}{SGR.B}{head}{r}{SGR.BLOOD}{'─' * max(0, rule)}{r}")
        for h in self._hits[-self._cap:]:
            if h.latency_ms < 200:
                c = SGR.GREEN
            elif h.latency_ms < 800:
                c = SGR.AMBER
            else:
                c = SGR.CRIM
            o.append(
                f"   {SGR.CRIM}▸{r} {SGR.ICE}{h.kind:<7}{r}"
                f"{SGR.IVORY}{h.endpoint:<28}{r}"
                f"{c}{h.latency_ms:>6.0f} ms{r}"
            )
        o.append("")
        return o

    def _footer(self, W):
        r = SGR.R
        o = []
        sig = f"{CREW} // {SUFFIX}"
        p = (W - _vis(sig)) // 2
        o.append(f"{' ' * max(0, p)}{SGR.BLOOD}{SGR.I}{sig}{r}")
        return o

    def _render(self):
        W = self._w()
        o = []
        o += self._header(W)
        o.append("")
        o += self._strip(W)
        for s in self.scans:
            o += self._panel(s, W)
        o += self._summary(W)
        o += self._live(W)
        o += self._footer(W)
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
