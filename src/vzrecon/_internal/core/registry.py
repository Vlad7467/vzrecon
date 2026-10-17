import asyncio
from .http_validator import HttpValidator
from .protocol import Endpoint, Protocol, Result
from .socks4_validator import Socks4Validator
from .socks5_validator import Socks5Validator
from .validator import ProtocolValidator, Timeout

VALIDATORS: dict[Protocol, ProtocolValidator] = {
    Protocol.HTTP: HttpValidator(),
    Protocol.SOCKS4: Socks4Validator(),
    Protocol.SOCKS5: Socks5Validator(),
}

async def check_many(
    endpoints: list[Endpoint],
    timeout: Timeout = Timeout(),
    concurrency: int = 100,
) -> list[Result]:
    if not endpoints:
        return []

    queue: asyncio.Queue[Endpoint] = asyncio.Queue()
    for ep in endpoints:
        queue.put_nowait(ep)

    results: list[Result] = []

    async def worker() -> None:
        while True:
            try:
                ep = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            validator = VALIDATORS.get(ep.protocol)
            if validator is not None:
                res = await validator.validate(ep, timeout)
                results.append(res)
            queue.task_done()

    async with asyncio.TaskGroup() as tg:
        for _ in range(min(concurrency, len(endpoints))):
            tg.create_task(worker())

    return results
