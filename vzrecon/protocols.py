import asyncio, socket
from time import perf_counter
async def _d(h,p,t):
    return await asyncio.wait_for(asyncio.open_connection(h,p),timeout=t)
async def _tun(host,port,th,tp,tt,ht,verify=False):
    r=w=None; t0=perf_counter()
    try:
        r,w=await _d(host,port,tt)
        req=(f"CONNECT {th}:{tp} HTTP/1.1\r\nHost: {th}:{tp}\r\n"
             f"Proxy-Connection: keep-alive\r\n\r\n")
        w.write(req.encode()); await w.drain()
        line=await asyncio.wait_for(r.readline(),timeout=ht)
        if not line.startswith(b"HTTP/"): return None
        parts=line.split(b" ",2)
        if len(parts)<2 or parts[1]!=b"200": return None
        # ── verify phase: real request through the tunnel ──
        if verify:
            v = await _verify_through(r,w,th,tp,ht)
            if v is None: return None
        return (perf_counter()-t0)*1000.0
    except (OSError,asyncio.TimeoutError,asyncio.IncompleteReadError): return None
    finally:
        if w is not None: w.close()
async def _verify_through(r,w,th,tp,ht):
    """Send a real HTTP/1.0 request through the established tunnel.
    Any HTTP status line at all means the proxy is actually forwarding."""
    try:
        req=(f"HEAD / HTTP/1.0\r\nHost: {th}\r\n"
             f"User-Agent: vzrecon/3.0\r\n\r\n")
        w.write(req.encode()); await w.drain()
        line=await asyncio.wait_for(r.readline(),timeout=ht)
        if not line.startswith(b"HTTP/"): return None
        return 1
    except (OSError,asyncio.TimeoutError,asyncio.IncompleteReadError):
        return None
async def _fwd(host,port,th,tt,ht):
    r=w=None; t0=perf_counter()
    try:
        r,w=await _d(host,port,tt)
        req=(f"GET http://{th}/ HTTP/1.1\r\nHost: {th}\r\n"
             f"User-Agent: vzrecon/3.0\r\nConnection: close\r\n\r\n")
        w.write(req.encode()); await w.drain()
        line=await asyncio.wait_for(r.readline(),timeout=ht)
        if not line.startswith(b"HTTP/"): return None
        return (perf_counter()-t0)*1000.0
    except (OSError,asyncio.TimeoutError,asyncio.IncompleteReadError): return None
    finally:
        if w is not None: w.close()
async def http_connect(host,port,th,tp,*,tcp_timeout,hs_timeout,verify=False):
    r=await _tun(host,port,th,tp,tcp_timeout,hs_timeout,verify=verify)
    if r is not None: return r
    # forward-GET is already a real request; no extra verify needed
    return await _fwd(host,port,th,tcp_timeout,hs_timeout)
async def socks5_connect(host,port,th,tp,*,tcp_timeout,hs_timeout,verify=False):
    r=w=None; t0=perf_counter()
    try:
        r,w=await _d(host,port,tcp_timeout)
        w.write(b"\x05\x01\x00"); await w.drain()
        g=await asyncio.wait_for(r.readexactly(2),timeout=hs_timeout)
        if g!=b"\x05\x00": return None
        n=th.encode("idna")
        if len(n)>255: return None
        w.write(b"\x05\x01\x00\x03"+bytes((len(n),))+n+tp.to_bytes(2,"big"))
        await w.drain()
        h=await asyncio.wait_for(r.readexactly(4),timeout=hs_timeout)
        if h[0]!=0x05 or h[1]!=0x00: return None
        a=h[3]
        if a==0x01: tail=6
        elif a==0x04: tail=18
        elif a==0x03:
            ln=await asyncio.wait_for(r.readexactly(1),timeout=hs_timeout)
            tail=ln[0]+2
        else: return None
        await asyncio.wait_for(r.readexactly(tail),timeout=hs_timeout)
        if verify:
            v = await _verify_through(r,w,th,tp,hs_timeout)
            if v is None: return None
        return (perf_counter()-t0)*1000.0
    except (OSError,asyncio.TimeoutError,asyncio.IncompleteReadError): return None
    finally:
        if w is not None: w.close()
async def socks4_connect(host,port,th,tp,*,tcp_timeout,hs_timeout,verify=False):
    r=w=None; t0=perf_counter()
    try:
        try: ipv4=socket.gethostbyname(th)
        except OSError: return None
        octets=bytes(int(x) for x in ipv4.split("."))
        r,w=await _d(host,port,tcp_timeout)
        w.write(b"\x04\x01"+tp.to_bytes(2,"big")+octets+b"\x00")
        await w.drain()
        rep=await asyncio.wait_for(r.readexactly(8),timeout=hs_timeout)
        if rep[0]!=0x00 or rep[1]!=0x5A: return None
        if verify:
            v = await _verify_through(r,w,th,tp,hs_timeout)
            if v is None: return None
        return (perf_counter()-t0)*1000.0
    except (OSError,asyncio.TimeoutError,asyncio.IncompleteReadError): return None
    finally:
        if w is not None: w.close()
REGISTRY={"http":http_connect,"socks4":socks4_connect,"socks5":socks5_connect}
