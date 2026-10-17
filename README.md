
# vzrecon

```

██╗   ██╗███████╗██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗
██║   ██║╚══███╔╝██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║
██║   ██║  ███╔╝ ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║
╚██╗ ██╔╝ ███╔╝  ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║
╚████╔╝ ███████╗██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║
╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝

```

**Protocol-level proxy validator for HTTP, SOCKS4, and SOCKS5.**
Developed by **VZLOI GROUP** — an independent Russian hacker group.

## Why

Most proxy checkers just try to fetch a URL through the proxy and call it a day. That test mixes three different problems: whether the proxy is reachable, whether it speaks the protocol, and whether the target site is actually up.

`vzrecon` separates them. It opens a socket, performs the actual protocol handshake according to the RFC, and measures the round-trip latency of that negotiation. Target server availability is not part of the result.

## Features                                                                 
- **Protocol-accurate validation:** HTTP CONNECT (RFC 7231), SOCKS5 (RFC 1928), and SOCKS4.
- **`--verify` mode:** After a successful handshake, it sends a real HTTP request through the tunnel to ensure the proxy actually forwards traffic, not just agrees to connect.
- **Zero dependencies:** Only the Python standard library is used.
- **Termux-native:** Works perfectly on Android. Wake-locks and notifications included.
- **High concurrency:** Built on `asyncio` with a bounded queue and a fixed worker pool. No memory leaks on large lists.
- **Flexible output:** TXT, JSON (signed by VZLOI GROUP), CSV.

## Install

```sh
pip install vzrecon
```

Verify the build:

```sh
vzrecon --self-test
```

Usage

```sh
vzrecon                          # Scan current directory for *_proxies.txt
vzrecon -d ./lists -o ./out      # Explicit paths
vzrecon --preset stealth         # 200 workers, battery-friendly
vzrecon --preset turbo           # 2400 workers
vzrecon --only http,socks5       # Subset of protocols
vzrecon --verify                 # Real request through the tunnel
vzrecon --plain                  # Pipe-friendly, no alt-screen TUI
```

Source files must be named <protocol>_proxies.txt with one host:port per line.

Protocols

Protocol Standard Notes
HTTP RFC 7231 §4.3.6 CONNECT tunnelling, fallback to forward-GET
SOCKS5 RFC 1928 No-auth greeting, domain ATYP
SOCKS4 Original IPv4 targets only, client-side resolve

Latency is measured using time.perf_counter from the moment the TCP connection is issued to the moment the protocol reply is fully received.

Output

· <proto>_alive.txt — Plain endpoints, one per line.
· <proto>_alive.json — signed_by, owner, contact, support, motto, protocol, count, proxies[].
· <proto>_alive.csv — endpoint,latency_ms.

Exit Codes

· 0 — Scan completed.
· 1 — Self-test failed.
· 2 — Config error.
· 3 — No source files found.

Termux Integration

· Wake-lock is acquired on start and released on exit.
· termux-notification fires when the scan completes.
· Presets tuned for phone CPU and battery limits.

Requires termux-api for notifications.

VZLOI GROUP

```
Development: VZLOI GROUP
Author:      ghost189
Contact:     @foskza
Support:     @foskza
```

We don't ask for permission. We don't report back. We don't apologize.

License

MIT. Copyright (c) 2026 VZLOI GROUP.
