import asyncio
from .protocol import FailureReason

def classify_exception(exc: Exception) -> FailureReason:
    if isinstance(exc, asyncio.TimeoutError):
        return FailureReason.CONNECT_TIMEOUT
    if isinstance(exc, ConnectionRefusedError):
        return FailureReason.BLOCKED
    if isinstance(exc, OSError):
        return FailureReason.UNKNOWN
    return FailureReason.UNKNOWN
