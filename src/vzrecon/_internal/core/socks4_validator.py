import asyncio
import socket
from time import perf_counter
from .classification import classify_exception
from .protocol import Endpoint, FailureReason, Protocol, Result, Status
from .validator import ProtocolValidator, Timeout

class Socks4Validator(ProtocolValidator):
    protocol = Protocol.SOCKS4

    async def validate(self, endpoint: Endpoint, timeout: Timeout) -> Result:
        t0 = perf_counter()
        r = w = None
        try:
            ip = socket.gethostbyname(endpoint.host)
            octets = bytes(int(x) for x in ip.split("."))
            r, w = await asyncio.wait_for(
                asyncio.open_connection(endpoint.host, endpoint.port),
                timeout=timeout.connect,
            )
            req = b"\x04\x01" + endpoint.port.to_bytes(2, "big") + octets + b"\x00"
            w.write(req)
            await w.drain()
            resp = await asyncio.wait_for(r.readexactly(8), timeout=timeout.handshake)
            if resp[0] == 0x00 and resp[1] == 0x5A:
                return Result(endpoint, Status.OK, None, (perf_counter() - t0) * 1000.0)
            return Result(endpoint, Status.FAIL, FailureReason.HANDSHAKE_FAIL, None)
        except Exception as exc:
            return Result(endpoint, Status.FAIL, classify_exception(exc), None)
        finally:
            if w is not None:
                w.close()
