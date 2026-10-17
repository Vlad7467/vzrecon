from pydantic import BaseModel, Field

class Config(BaseModel):
    concurrency: int = Field(default=200, ge=1)
    timeout_connect: float = Field(default=3.0, gt=0)
    timeout_handshake: float = Field(default=6.0, gt=0)
