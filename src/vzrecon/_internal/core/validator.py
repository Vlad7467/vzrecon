import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar
from .protocol import Endpoint, Protocol, Result

@dataclass(frozen=True, slots=True)
class Timeout:
    connect: float = 3.0
    handshake: float = 6.0

class ProtocolValidator(ABC):
    protocol: ClassVar[Protocol]

    @abstractmethod
    async def validate(self, endpoint: Endpoint, timeout: Timeout) -> Result:
        ...
