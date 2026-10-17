import asyncio
from time import perf_counter
from .classification import classify_exception
from .protocol import Endpoint, FailureReason, Protocol, Result, Status
from .validator import ProtocolValidator, Timeout

class Socks5Validator(ProtocolValidator):
    protocol = Protocol.SOCKS5

    async def validate(self, endpoint: Endpoint, timeout: Timeout) -> Result:
        t0 = perf_counter()
        r = w = None
        try:
            r, w = await asyncio.wait_for(
                asyncio.open_connection(endpoint.host, endpoint.port),
                timeout=timeout.connect,
            )
            w.write(b"\x05\x01\x00")
            await w.drain()
            greet = await asyncio.wait_for(r.readexactly(2), timeout=timeout.handshake)
            if greet != b"\x05\x00":
                return Result(endpoint, Status.FAIL, FailureReason.AUTH_REQUIRED, None)
            host_bytes = endpoint.host.encode("idna")
            req = (
                b"\x05\x01\x00\x03"
                + bytes([len(host_bytes)])
                + host_bytes
                + endpoint.port.to_bytes(2, "big")
            )
            w.write(req)
            await w.drain()
            head = await asyncio.wait_for(r.readexactly(4), timeout=timeout.handshake)
            if head[0] == 0x05 and head[1] == 0x00:
                return Result(endpoint, Status.OK, None, (perf_counter() - t0) * 1000.0)
            return Result(endpoint, Status.FAIL, FailureReason.HANDSHAKE_FAIL, None)
        except Exception as exc:
            return Result(endpoint, Status.FAIL, classify_exception(exc), None)
        finally:
            if w is not None:
                w.close()
