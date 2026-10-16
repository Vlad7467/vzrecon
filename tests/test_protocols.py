import asyncio
import contextlib

import pytest

from vzrecon.protocols import (
    http_connect,
    socks4_connect,
    socks5_connect,
)
from vzrecon.selftest import _mh, _m4, _m5

async def _serve(h):
    srv = await asyncio.start_server(h, "127.0.0.1", 0)
    return srv, srv.sockets[0].getsockname()[1]

async def _run(handler, validator):
    srv, port = await _serve(handler)
    try:
        return await validator(
            "127.0.0.1", port, "example.com", 443,
            tcp_timeout=2.0, hs_timeout=2.0,
        )
    finally:
        srv.close()
        with contextlib.suppress(Exception):
            await srv.wait_closed()

@pytest.mark.asyncio
async def test_http():
    lat = await _run(_mh, http_connect)
    assert lat is not None and lat > 0

@pytest.mark.asyncio
async def test_socks5():
    lat = await _run(_m5, socks5_connect)
    assert lat is not None and lat > 0

@pytest.mark.asyncio
async def test_socks4():
    lat = await _run(_m4, socks4_connect)
    assert lat is not None and lat > 0

@pytest.mark.asyncio
async def test_refused():
    lat = await http_connect(
        "127.0.0.1", 1, "example.com", 443,
        tcp_timeout=0.5, hs_timeout=0.5,
    )
    assert lat is None
