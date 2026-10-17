import pytest
from vzrecon._internal.core.protocol import Endpoint, Protocol, Status
from vzrecon._internal.core.registry import check_many
from vzrecon._internal.core.validator import Timeout

@pytest.mark.asyncio
async def test_empty():
    results = await check_many([], Timeout())
    assert results == []

@pytest.mark.asyncio
async def test_http_fail():
    ep = Endpoint("127.0.0.1", 1, Protocol.HTTP)
    results = await check_many([ep], Timeout(connect=0.2, handshake=0.2))
    assert len(results) == 1
    assert results[0].status == Status.FAIL
