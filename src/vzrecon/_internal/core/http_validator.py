import asyncio
from time import perf_counter
from .classification import classify_exception
from .protocol import Endpoint, FailureReason, Protocol, Result, Status
from .validator import ProtocolValidator, Timeout

class HttpValidator(ProtocolValidator):
    protocol = Protocol.HTTP

    async def validate(self, endpoint: Endpoint, timeout: Timeout) -> Result:
        t0 = perf_counter()
        r = w = None
        try:
            r, w = await asyncio.wait_for(
                asyncio.open_connection(endpoint.host, endpoint.port),
                timeout=timeout.connect,
            )
            req = (
                f"CONNECT {endpoint.host}:{endpoint.port} HTTP/1.1\r\n"
                f"Host: {endpoint.host}:{endpoint.port}\r\n\r\n"
            )
            w.write(req.encode())
            await w.drain()
            line = await asyncio.wait_for(r.readline(), timeout=timeout.handshake)
            if line.startswith(b"HTTP/") and b" 200" in line:
                return Result(endpoint, Status.OK, None, (perf_counter() - t0) * 1000.0)
            return Result(endpoint, Status.FAIL, FailureReason.HANDSHAKE_FAIL, None)
        except Exception as exc:
            return Result(endpoint, Status.FAIL, classify_exception(exc), None)
        finally:
            if w is not None:
                w.close()
