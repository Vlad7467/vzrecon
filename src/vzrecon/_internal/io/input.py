from typing import AsyncIterator
from ..core.protocol import Endpoint, Protocol

async def iter_endpoints(path: str, protocol: Protocol) -> AsyncIterator[Endpoint]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            host, _, port_str = line.rpartition(":")
            if host and port_str.isdigit():
                yield Endpoint(host, int(port_str), protocol)
