import argparse, asyncio, contextlib, secrets, sys, time
from pathlib import Path
from . import __codename__, __version__
from .brand import BANNER, CREW, SGR, SUFFIX, TOOL
from .config import PRESETS, Config
from .engine import Scan, discover
from .platform import notify, wake_lock, wake_unlock
from .tui import TUI
from .writers import emit_csv, emit_json, emit_txt
def _parse(a):
    p=argparse.ArgumentParser(prog=TOOL,
        description=f"proxy validator // {CREW} {SUFFIX}")
    p.add_argument("--version",action="version",
                   version=f"{TOOL} {__version__} ({__codename__})")
    p.add_argument("-c","--config",type=Path)
    p.add_argument("-d","--dir",type=Path,default=Path.cwd())
    p.add_argument("-o","--output-dir",type=Path,default=Path("."))
    p.add_argument("-t","--target")
    p.add_argument("-w","--workers",type=int)
    p.add_argument("--format",choices=("txt","json","csv"))
    p.add_argument("--only")
    p.add_argument("--preset",choices=tuple(PRESETS.keys()))
    p.add_argument("--list-presets",action="store_true")
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--plain",action="store_true")
    p.add_argument("--no-notify",action="store_true")
    p.add_argument("--verify",action="store_true",
                   help="send a real request through the tunnel")
    return p.parse_args(a)
def _merge(a):
    c=Config.from_toml(a.config) if a.config else Config()
    if a.preset: c=c.apply_preset(a.preset)
    c.source_dir=str(a.dir); c.output_dir=str(a.output_dir)
    if a.workers is not None: c.workers=a.workers
    if a.format: c.format=a.format
    if a.target:
        h,_,pt=a.target.partition(":")
        c.target_host=h; c.target_port=int(pt) if pt else 443
    if a.only:
        c.protocols=tuple(s.strip() for s in a.only.split(",") if s.strip())
    if a.no_notify: c.notify=False
    if a.verify: c.verify=True
    c.validate(); return c
async def _dispatch(scans,cfg,plain):
    if plain:
        await asyncio.gather(*(s.run() for s in scans)); return
    sid=secrets.token_hex(4).upper()
    tui=TUI(scans,f"{cfg.target_host}:{cfg.target_port}",
            cfg.workers,sid,"balanced")
    tui.attach(); tui.enter()
    ts=[asyncio.create_task(s.run()) for s in scans]
    tick=1.0/cfg.render_hz
    try:
        while not all(t.done() for t in ts):
            for s in scans: s.meter.sample()
            tui.draw(); await asyncio.sleep(tick)
        tui.draw()
    finally:
        for t in ts: t.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(*ts,return_exceptions=True)
        tui.leave()
def _write(scans,cfg,out):
    out.mkdir(parents=True,exist_ok=True)
    for s in scans:
        stem=out/f"{s.kind}_alive"
        if cfg.format=="txt": emit_txt(stem.with_suffix(".txt"),s.hits)
        elif cfg.format=="json": emit_json(stem.with_suffix(".json"),s.kind,s.hits)
        else: emit_csv(stem.with_suffix(".csv"),s.hits)
def _banner():
    return "\n".join(f"  {SGR.CRIM}{l}{SGR.R}" for l in BANNER)
def _presets():
    print(f"\n  {SGR.CRIM}{SGR.B}{CREW} // {SUFFIX}{SGR.R}  ·  presets")
    print(f"  {SGR.DIM}{'─'*46}{SGR.R}")
    for n,v in PRESETS.items():
        print(f"  {SGR.GOLD}{n:<10}{SGR.R} {SGR.STEEL}"
              f"workers={v['workers']:<5} tcp={v['tcp_timeout']}s "
              f"hs={v['hs_timeout']}s hz={v['render_hz']}{SGR.R}")
    print(); return 0
def main(argv=None):
    a=_parse(argv)
    if a.list_presets: return _presets()
    if a.self_test:
        from .selftest import run
        print(f"\n  {SGR.CRIM}{SGR.B}{CREW} // {SUFFIX}{SGR.R}  "
              f"·  protocol self-test")
        print(f"  {SGR.DIM}{'─'*46}{SGR.R}")
        rc=asyncio.run(run()); print(); return rc
    try: cfg=_merge(a)
    except (ValueError,FileNotFoundError) as e:
        print(f"{SGR.CRIM}config:{SGR.R} {e}",file=sys.stderr)
        return 2
    src=discover(cfg)
    if not src:
        print(f"{SGR.CRIM}no sources{SGR.R} in {cfg.source_dir}",
              file=sys.stderr)
        return 3
    print(_banner())
    print(f"  {SGR.STEEL}protocols:{SGR.R} {', '.join(k for k,_ in src)}")
    print(f"  {SGR.STEEL}sources:  {SGR.R} {len(src)} file(s)")
    print(f"  {SGR.STEEL}target:   {SGR.R} {cfg.target_host}:{cfg.target_port}")
    print(f"  {SGR.STEEL}workers:  {SGR.R} {cfg.workers}\n")
    if cfg.wake_lock: wake_lock()
    scans=[]
    Path(cfg.output_dir).mkdir(parents=True,exist_ok=True)
    for k,s in src:
        scans.append(Scan(k,s,Path(cfg.output_dir)/f"{k}_alive.txt",cfg))
    t0=time.monotonic()
    try:
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(_dispatch(scans,cfg,a.plain))
    finally:
        if cfg.wake_lock: wake_unlock()
    dt=time.monotonic()-t0
    _write(scans,cfg,Path(cfg.output_dir))
    print(f"\n  {SGR.CRIM}{SGR.B}{CREW} // {SUFFIX}{SGR.R}  "
          f"·  scan complete")
    print(f"  {SGR.DIM}{'─'*46}{SGR.R}")
    print(f"  {SGR.STEEL}duration:{SGR.R} {dt:.1f}s")
    total=0
    for s in scans:
        m=s.meter
        pct=(m.ok/m.done*100) if m.done else 0
        total+=m.ok
        print(f"  {s.kind:<7} {m.ok:>6} / {m.done:<6}  ({pct:5.1f}%)")
    print(f"  {SGR.DIM}{'─'*46}{SGR.R}")
    print(f"  total  {SGR.GRN}{total}{SGR.R} alive  →  {cfg.output_dir}\n")
    if cfg.notify:
        notify(f"{TOOL} · scan complete",
               f"{total} alive · {sum(s.meter.done for s in scans)} checked · {dt:.0f}s")
    return 0
