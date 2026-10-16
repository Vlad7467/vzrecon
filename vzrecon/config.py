from __future__ import annotations
import tomllib
from dataclasses import dataclass,fields,replace
from pathlib import Path
PRESETS={
    "stealth": {"workers":200,"tcp_timeout":4.0,"hs_timeout":8.0,"render_hz":2.0},
    "balanced":{"workers":1200,"tcp_timeout":3.0,"hs_timeout":6.0,"render_hz":3.0},
    "turbo":   {"workers":2400,"tcp_timeout":2.0,"hs_timeout":5.0,"render_hz":4.0},
}
@dataclass(slots=True)
class Config:
    workers:int=1200
    tcp_timeout:float=3.0
    hs_timeout:float=6.0
    target_host:str="api.trongrid.io"
    target_port:int=443
    render_hz:float=3.0
    sample_size:int=10
    source_dir:str="."
    output_dir:str="."
    format:str="txt"
    protocols:tuple=("http","socks4","socks5")
    notify:bool=True
    wake_lock:bool=True
    verify:bool=False
    @classmethod
    def from_toml(cls,path):
        raw=tomllib.loads(Path(path).read_text("utf-8"))
        valid={f.name for f in fields(cls)}
        unknown=set(raw)-valid
        if unknown: raise ValueError(f"unknown keys: {sorted(unknown)}")
        if "protocols" in raw: raw["protocols"]=tuple(raw["protocols"])
        return cls(**raw)
    def apply_preset(self,name):
        if name not in PRESETS: raise ValueError(f"unknown preset: {name}")
        return replace(self,**PRESETS[name])
    def validate(self):
        if self.workers<1: raise ValueError("workers must be >= 1")
        if not (1<=self.target_port<=65535): raise ValueError("target_port out of range")
        if self.format not in {"txt","json","csv"}: raise ValueError(f"bad format: {self.format}")
        for p in self.protocols:
            if p not in {"http","socks4","socks5"}: raise ValueError(f"bad protocol: {p}")
