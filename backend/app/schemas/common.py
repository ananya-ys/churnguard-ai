from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))  # ceiling division


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: object = None
    request_id: str


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    model_loaded: bool
    version: str = "1.0.0"
