import asyncio, contextlib
from .protocols import http_connect, socks4_connect, socks5_connect
async def _mh(r,w):
    try:
        l=await r.readline()
        if l.startswith(b"CONNECT"):
            w.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            await w.drain()
        while True:
            h=await r.readline()
            if h in (b"\r\n",b"\n",b""): break
    finally: w.close()
async def _m5(r,w):
    try:
        g=await r.readexactly(2)
        if g!=b"\x05\x01": return
        await r.readexactly(1)
        w.write(b"\x05\x00"); await w.drain()
        h=await r.readexactly(4); a=h[3]
        if a==0x01: await r.readexactly(6)
        elif a==0x03:
            n=(await r.readexactly(1))[0]
            await r.readexactly(n+2)
        elif a==0x04: await r.readexactly(18)
        w.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await w.drain()
    finally: w.close()
async def _m4(r,w):
    try:
        await r.readexactly(8)
        w.write(b"\x00\x5a\x00\x00\x00\x00\x00\x00")
        await w.drain()
    finally: w.close()
CASES=[("http",_mh,http_connect),
       ("socks5",_m5,socks5_connect),
       ("socks4",_m4,socks4_connect)]
async def _serve(h):
    srv=await asyncio.start_server(h,"127.0.0.1",0)
    return srv,srv.sockets[0].getsockname()[1]
async def run():
    fail=0
    for name,handler,v in CASES:
        srv,port=await _serve(handler)
        try:
            lat=await v("127.0.0.1",port,"example.com",443,
                        tcp_timeout=2.0,hs_timeout=2.0)
            ok=lat is not None
            print(f"  {name:<7} {'ok  ' if ok else 'FAIL'}  {lat or 0:>7.2f} ms")
            if not ok: fail+=1
        finally:
            srv.close()
            with contextlib.suppress(Exception):
                await srv.wait_closed()
    return 0 if fail==0 else 1
