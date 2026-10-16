# Security policy

Do not open a public issue for security problems. Reach the
maintainer through the address in `pyproject.toml`.

Include:

- a description of the issue
- a minimal reproduction
- the output of `vzrecon --version`

Acknowledgement within 72 hours.

## In scope

- unsafe deserialization of list files
- command injection through CLI arguments
- terminal escape injection in the TUI when rendering
  attacker-controlled endpoint strings
- file-descriptor leaks in protocol handlers

## Out of scope

Vulnerabilities in the proxies you point the tool at.
