from http import HTTPMethod
from typing import Any

from src.shared.infraestructure.schema.base import BaseSchemaPyd


class BaseRequest(BaseSchemaPyd):
    method: HTTPMethod
    url: str
    path_segments: list[str] | None = None
    query_params: dict[str, Any] | None = None
    timeout: int = 30
    cookies: dict[str, str] | None = None

    def get_url(self) -> str:
        if not self.path_segments:
            return self.url

        return "/".join([self.url] + self.path_segments)


class JsonRequest(BaseRequest):
    headers: dict[str, Any] | BaseSchemaPyd
    payload: BaseSchemaPyd | None = None


class TypedJsonRequest(BaseRequest):
    headers: BaseSchemaPyd
    payload: BaseSchemaPyd | None = None
