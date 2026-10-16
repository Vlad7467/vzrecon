import asyncio, contextlib
from dataclasses import dataclass
from pathlib import Path
from .metrics import Meter
from .protocols import REGISTRY
@dataclass(slots=True)
class Hit:
    endpoint:str
    kind:str
    latency_ms:float
class Scan:
    def __init__(self,kind,source,sink,cfg,on_hit=None):
        self.kind=kind; self.source=source; self.sink=sink; self.cfg=cfg
        self.on_hit=on_hit; self.meter=Meter()
        self._q=asyncio.Queue(); self._fh=None; self.hits=[]
    def _load(self):
        if not self.source.exists(): return []
        seen=set(); out=[]
        for raw in self.source.read_text("utf-8",errors="ignore").splitlines():
            l=raw.strip()
            if l and l not in seen:
                seen.add(l); out.append(l)
        return out
    async def run(self):
        e=self._load(); self.meter.total=len(e)
        if not e: return
        for x in e: self._q.put_nowait(x)
        self._fh=self.sink.open("w",buffering=1)
        v=REGISTRY[self.kind]; cfg=self.cfg
        async def consume():
            while True:
                try: entry=self._q.get_nowait()
                except asyncio.QueueEmpty: return
                try:
                    h,_,ps=entry.rpartition(":")
                    if not h or not ps.isdigit():
                        self.meter.tick(ok=False); continue
                    lat=await v(h,int(ps),cfg.target_host,cfg.target_port,
                               tcp_timeout=cfg.tcp_timeout,
                               hs_timeout=cfg.hs_timeout,
                               verify=cfg.verify)
                    if lat is None:
                        self.meter.tick(ok=False)
                    else:
                        self.meter.tick(ok=True,latency_ms=lat)
                        self._fh.write(entry+"\n")
                        self.hits.append((entry,lat))
                        if self.on_hit:
                            with contextlib.suppress(Exception):
                                self.on_hit(Hit(entry,self.kind,lat))
                except asyncio.CancelledError: return
                except Exception: self.meter.tick(ok=False)
                finally: self._q.task_done()
        ws=[asyncio.create_task(consume()) for _ in range(cfg.workers)]
        try: await asyncio.gather(*ws)
        finally:
            for t in ws: t.cancel()
            await asyncio.gather(*ws,return_exceptions=True)
            if self._fh is not None: self._fh.close()
def discover(cfg):
    base=Path(cfg.source_dir); found=[]
    for p in cfg.protocols:
        s=base/f"{p}_proxies.txt"
        if s.exists() and s.stat().st_size>0:
            found.append((p,s))
    return found
