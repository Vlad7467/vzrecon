from dataclasses import dataclass
from enum import StrEnum

class Protocol(StrEnum):
    HTTP = "http"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

class Status(StrEnum):
    OK = "ok"
    FAIL = "fail"
    UNKNOWN = "unknown"

class FailureReason(StrEnum):
    CONNECT_TIMEOUT = "connect_timeout"
    READ_TIMEOUT = "read_timeout"
    HANDSHAKE_FAIL = "handshake_fail"
    AUTH_REQUIRED = "auth_required"
    PROTOCOL_MISMATCH = "protocol_mismatch"
    BLOCKED = "blocked"
    DNS_ERROR = "dns_error"
    TLS_ERROR = "tls_error"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class Endpoint:
    host: str
    port: int
    protocol: Protocol

@dataclass(frozen=True, slots=True)
class Result:
    endpoint: Endpoint
    status: Status
    reason: FailureReason | None
    latency_ms: float | None
    schema_version: int = 1
