# Protocol reference

Exact bytes vzrecon places on the wire.

## HTTP CONNECT

    CONNECT target.example:443 HTTP/1.1\r\n
    Host: target.example:443\r\n
    Proxy-Connection: keep-alive\r\n
    \r\n

Success: `HTTP/1.1 200 ...`. Any other status — 403, 407, 502
— is a failure. No authentication is attempted; adding it would
change the measurement from "is this proxy usable" to "is this
proxy usable with the credentials I have".

### Forward fallback

If CONNECT fails:

    GET http://target.example/ HTTP/1.1\r\n
    Host: target.example\r\n
    User-Agent: vzrecon/3.0\r\n
    Connection: close\r\n
    \r\n

Any line starting with `HTTP/` counts as success. Captures the
large subset of open proxies that speak HTTP forward but do not
implement CONNECT.

## SOCKS5 (RFC 1928)

Greeting:

    05 01 00
    |  |  +--- no-auth
    |  +------ 1 method
    +--------- version

Method selection, required:

    05 00

CONNECT with domain ATYP:

    05 01 00 03 <len> <hostname> <port:2>

Reply head:

    05 00 <RSV> <ATYP>

Only `REP = 0x00` accepted. Tail length by ATYP:

    0x01  IPv4:  4 + 2
    0x03  domain: 1 + len + 2
    0x04  IPv6:  16 + 2

## SOCKS4

No greeting. Hostname resolved client-side:

    04 01 <port:2> <ipv4:4> 00
    |  |                   +--- USERID null
    |  +---------------------- CONNECT
    +------------------------- version

Reply:

    00 5A <port:2> <ipv4:4>

Only `00 5A` accepted. `00 5B` is a rejection.
