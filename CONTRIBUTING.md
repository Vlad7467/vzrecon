# Contributing

## Setup

    git clone https://github.com/vzloi/vzrecon.git
    cd vzrecon
    pip install -e ".[dev]"
    vzrecon --self-test
    pytest -q

If either command fails, the build is broken. Do not proceed.

## Adding a protocol

1. Add an async validator to `vzrecon/protocols.py` with the
   signature `(host, port, target_host, target_port, *,
   tcp_timeout, hs_timeout) -> float | None`.
2. Register it in `REGISTRY`.
3. Add a mock in `vzrecon/selftest.py` and append the case to
   `CASES`.
4. Add a test in `tests/test_protocols.py`.
5. Update `docs/PROTOCOLS.md` with the wire format.
6. Add a CHANGELOG entry under `[Unreleased]`.

PRs without a mock and a passing self-test will not be merged.

## Style

- Line width 88.
- Comments explain why, not what.
- No emoji in source files.
- Prefer the standard library. A dependency needs a reason that
  survives the next refactor.
