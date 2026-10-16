# Changelog

Format: Keep a Changelog. Versioning: SemVer.

## [Unreleased]

## [3.0.0] — 2026-10-16

Initial public release. Codename: IRON VEIL.

### Added
- Protocol validators for HTTP CONNECT, SOCKS5 (RFC 1928) and
  SOCKS4. Each performs a full handshake against the target.
- HTTP forward-GET fallback for proxies that refuse tunnelling.
- Alternate-screen TUI with per-protocol panels, throughput
  sparklines, p95 latency and a live hit ticker.
- Termux integration: wake-lock management and completion
  notifications.
- Presets: stealth, balanced, turbo.
- Strict TOML config, unknown keys rejected.
- Output formats: txt, JSON (with `signed_by`), CSV.
- Exit codes for CI integration.
- In-process self-test used as the CI gate.
