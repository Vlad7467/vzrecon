import time
from collections import deque
from dataclasses import dataclass,field
_S="▁▂▃▄▅▆▇█"
@dataclass
class Meter:
    total:int=0
    done:int=0
    ok:int=0
    fail:int=0
    started_at:float=field(default_factory=time.monotonic)
    _w:deque=field(default_factory=lambda:deque(maxlen=60))
    _p:int=0
    _l:deque=field(default_factory=lambda:deque(maxlen=512))
    def tick(self,*,ok,latency_ms=None):
        self.done+=1
        if ok:
            self.ok+=1
            if latency_ms is not None: self._l.append(latency_ms)
        else: self.fail+=1
    def sample(self):
        self._w.append((time.monotonic(),self.done-self._p))
        self._p=self.done
    def rate(self):
        if len(self._w)<2: return 0.0
        t0,_=self._w[0]; t1,_=self._w[-1]
        dt=t1-t0
        if dt<=0: return 0.0
        return sum(n for _,n in self._w)/dt
    def eta(self):
        rem=self.total-self.done; r=self.rate()
        if r<=0 or rem<=0: return None
        return rem/r
    def percentile(self,p):
        if not self._l: return None
        d=sorted(self._l)
        return d[min(len(d)-1,int(p*len(d)))]
    def spark(self,w=24):
        if not self._w: return " "*w
        s=[n for _,n in self._w][-w:]
        hi=max(s) or 1
        return "".join(_S[min(7,(n*8)//hi)] for n in s).rjust(w)
    @property
    def elapsed(self): return time.monotonic()-self.started_at
    @property
    def progress(self): return self.done/self.total if self.total else 0.0
def fmt_dur(s):
    if s is None: return "--:--"
    n=int(s)
    return f"{n//60:02d}:{n%60:02d}" if n<3600 else f"{n//3600}h{(n%3600)//60:02d}m"
def fmt_int(n): return f"{n:,}".replace(","," ")
def fmt_uptime(s):
    s=int(s); h,r=divmod(s,3600); m,sec=divmod(r,60)
    return f"{h:02d}:{m:02d}:{sec:02d}"
