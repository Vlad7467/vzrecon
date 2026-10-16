# vzrecon

Protocol-level validator for HTTP, SOCKS4 and SOCKS5 proxies.
Zero dependencies. Termux-native.

Signed: VZLOI GROUP // ops

## Install

    pip install -e .
    vzrecon --self-test

## Use

    vzrecon                          # scan cwd for *_proxies.txt
    vzrecon -d ./lists -o ./out      # explicit paths
    vzrecon --preset stealth         # 200 workers
    vzrecon --preset turbo           # 2400 workers
    vzrecon --only http,socks5
    vzrecon --plain

## Protocols

- HTTP    RFC 7231 CONNECT + forward GET fallback
- SOCKS5  RFC 1928, no-auth greeting
- SOCKS4  original spec, IPv4 targets only

## Output

- `<proto>_alive.txt` — endpoints, one per line
- `<proto>_alive.json` — signed_by, protocol, count, proxies[]
- `<proto>_alive.csv` — endpoint, latency_ms

## Exit codes

- 0 scan completed
- 1 self-test failed
- 2 config error
- 3 no source files found

## License

MIT. Copyright (c) 2026 VZLOI GROUP.
