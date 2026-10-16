# Troubleshooting

## `vzrecon: command not found`

Editable install did not complete, or the script directory is
not on `PATH`. Verify:

    pip show vzrecon
    python -m vzrecon --version

## `Too many open files`

Default pool is 1200 workers. Raise the descriptor limit:

    ulimit -n 4096
    vzrecon -d . -o out

Or lower the pool:

    vzrecon --preset stealth

## Scan finishes in under a second with 0 / 0

Source lists are empty. Check:

    wc -l *_proxies.txt

## Everything is dead

That is normal for open proxy lists. A live ratio of 1-3% is
expected. Confirm the build is sane:

    vzrecon --self-test

If all three print `ok`, the null result is a property of the
input, not the validator.

## SOCKS5 rejects with 0x05 0xFF

Proxy requires username/password auth. vzrecon does not offer
credentials — see `docs/PROTOCOLS.md` for the reasoning. Counted
as dead.

## Process killed on Android

The OS may terminate background processes when the device enters
Doze. vzrecon takes a wake-lock via `termux-wake-lock` when it
detects Termux. Install `termux-api`:

    pkg install termux-api
