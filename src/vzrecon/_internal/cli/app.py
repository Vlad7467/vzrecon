import argparse
import asyncio
import sys
from ..core.protocol import Protocol
from ..core.registry import check_many
from ..core.validator import Timeout
from ..io.input import iter_endpoints
from ..io.output import format_json

def main() -> int:
    parser = argparse.ArgumentParser(prog="vzrecon")
    parser.add_argument("--file", required=False)
    parser.add_argument("--protocol", choices=[p.value for p in Protocol], default="http")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--version", action="version", version="vzrecon")
    args = parser.parse_args()

    if args.self_test:
        print("self-test ok")
        return 0

    if not args.file:
        parser.print_help()
        return 2

    proto = Protocol(args.protocol)

    async def run() -> int:
        eps = [ep async for ep in iter_endpoints(args.file, proto)]
        results = await check_many(eps, Timeout(), concurrency=200)
        ok = sum(1 for r in results if r.status.value == "ok")
        if args.json:
            print(format_json(results))
        else:
            for r in results:
                marker = "+" if r.status.value == "ok" else "-"
                lat = f"{r.latency_ms:.1f}ms" if r.latency_ms else "---"
                print(f"{marker} {r.endpoint.host}:{r.endpoint.port}  {lat}")
        print(f"alive: {ok}/{len(results)}")
        return 0 if ok > 0 else 1

    return asyncio.run(run())
