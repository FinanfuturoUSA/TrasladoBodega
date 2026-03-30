import json
from abc import ABC, abstractmethod
from asyncio import Lock, sleep
from time import time
from typing import Any

import httpx

from src.shared.infraestructure.httpclient.request import JsonRequest, TypedJsonRequest
from src.shared.infraestructure.schema.base import BaseSchemaPyd

JsonRequestLike = JsonRequest | TypedJsonRequest


class ClientException(Exception):
    """Excepción rica en contexto para depuración y mantenimiento de clientes HTTP."""

    def __init__(
        self,
        *,
        payload: dict | None = None,
        url: str | None = None,
        response: dict[str, Any] | str | bytes | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        response_type: str | None = None,
        msg: str | None = None,
    ):
        self.url = url
        self.payload = payload
        self.response = response
        self.status_code = status_code
        self.headers = headers
        self.response_type = response_type or type(response).__name__
        self.msg = msg
        super().__init__(msg)

    @classmethod
    def from_httpx_response(
        cls,
        *,
        payload: dict | None,
        url: str,
        response: httpx.Response,
        msg: str,
        response_data: Any | None = None,
    ) -> "ClientException":
        # La normalización vive aquí para que BaseClient solo decida cuándo
        # fallar y no cómo representar cada tipo de respuesta en la excepción.
        normalized_response, response_type = cls._normalize_response_data(
            response_data=response_data,
            response=response,
        )

        return cls(
            payload=payload,
            url=url,
            response=normalized_response,
            status_code=response.status_code,
            headers=dict(response.headers),
            response_type=response_type,
            msg=msg,
        )

    @staticmethod
    def _normalize_response_data(
        *,
        response_data: Any | None,
        response: httpx.Response,
    ) -> tuple[dict[str, Any] | str | bytes, str]:
        # Conservamos `dict`, `str` y `bytes` tal como vienen. El resto se
        # serializa a texto para que la excepción tenga una representación estable.
        if response_data is None:
            return response.text, "str"

        if isinstance(response_data, dict):
            return response_data, "dict"

        if isinstance(response_data, bytes):
            return response_data, "bytes"

        if isinstance(response_data, str):
            return response_data, "str"

        return ClientException._safe_json_dumps(response_data), type(
            response_data
        ).__name__

    @staticmethod
    def _safe_json_dumps(value: Any) -> str:
        try:
            return json.dumps(value)
        except TypeError:
            # La excepción nunca debería romper al intentar representarse, aun si
            # el payload o la respuesta contienen tipos Python no serializables.
            return json.dumps(value, default=str)

    @staticmethod
    def _format_value(value: dict[str, Any] | str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            return ClientException._safe_json_dumps(value)
        if isinstance(value, bytes):
            return repr(value)
        return value

    def _to_lines(self, *, include_headers: bool) -> list[str]:
        lines = []
        if self.msg:
            lines.append(f"msg: {self.msg}")
        if self.url:
            lines.append(f"url: {self.url}")
        if self.status_code is not None:
            lines.append(f"status_code: {self.status_code}")
        if self.response_type:
            lines.append(f"response_type: {self.response_type}")
        if self.payload:
            lines.append(f"payload: {self._safe_json_dumps(self.payload)}")
        if self.response is not None:
            lines.append(f"response: {self._format_value(self.response)}")
        # Los headers solo se agregan en `__repr__` porque pueden contener
        # secretos; `__str__` queda como vista pública más segura.
        if include_headers and self.headers:
            lines.append(f"headers: {self._safe_json_dumps(self.headers)}")
        return lines

    def __str__(self):
        return "\n".join(self._to_lines(include_headers=False))

    def __repr__(self):
        return "\n".join(self._to_lines(include_headers=True))


class BaseClient(ABC):
    def __init__(self, min_interval: float = 0):
        self.__last_request_time: float = 0
        self._min_interval = min_interval  # Segundos
        self._rate_limit_lock: Lock = Lock()

    async def _rate_limit(self):
        """Aplica rate limiting cuando sea necesario."""
        async with self._rate_limit_lock:
            current_time = time()
            time_since_last_request = current_time - self.__last_request_time

            if time_since_last_request < self._min_interval:
                sleep_time = self._min_interval - time_since_last_request
                await sleep(sleep_time)

            # Reservamos el instante de salida del request dentro del lock para
            # que dos corutinas concurrentes no pasen juntas el rate limit.
            self.__last_request_time = time()

    async def _execute_request(self, request: JsonRequestLike) -> httpx.Response:
        if self._min_interval > 0:
            await self._rate_limit()

        method = (
            request.method.value if hasattr(request.method, "value") else request.method
        )
        headers_data = (
            request.headers.model_dump(exclude_none=True)
            if isinstance(request.headers, BaseSchemaPyd)
            else request.headers
        )
        payload_data = (
            request.payload.model_dump(exclude_none=True) if request.payload else None
        )
        timeout_config = httpx.Timeout(float(request.timeout))

        async with httpx.AsyncClient(timeout=timeout_config) as client:
            return await client.request(
                method,
                request.get_url(),
                params=request.query_params,
                headers=headers_data,
                json=payload_data,
                cookies=request.cookies,
            )

    def _verify_http_success(
        self,
        *,
        request: JsonRequestLike,
        response: httpx.Response,
        response_data: Any,
    ) -> None:
        if not response.is_success:
            raise ClientException.from_httpx_response(
                payload=request.payload.model_dump(exclude_none=True)
                if request.payload
                else None,
                url=request.get_url(),
                response=response,
                response_data=response_data,
                msg=f"HTTP {response.status_code}: {response.reason_phrase}",
            )

    def _verify_json_object(
        self,
        *,
        request: JsonRequestLike,
        response: httpx.Response,
        response_data: Any,
    ) -> None:
        if not isinstance(response_data, dict):
            raise ClientException.from_httpx_response(
                payload=request.payload.model_dump(exclude_none=True)
                if request.payload
                else None,
                url=request.get_url(),
                response=response,
                response_data=response_data,
                msg=(
                    f"La respuesta JSON no es un objeto: {type(response_data).__name__}"
                ),
            )

    @abstractmethod
    def _verify(
        self,
        *,
        request: JsonRequestLike,
        response: httpx.Response,
        response_data: Any,
    ) -> None:
        """Permite validar errores de negocio en APIs que responden 200 con fallo."""

    async def _json_request(
        self,
        request: JsonRequestLike,
        *,
        verify: bool = True,
    ) -> dict[str, Any]:
        payload_data = (
            request.payload.model_dump(exclude_none=True) if request.payload else None
        )
        response = await self._execute_request(request)

        try:
            response_data = response.json()
        except Exception as exc:
            raise ClientException.from_httpx_response(
                payload=payload_data,
                url=request.get_url(),
                response=response,
                msg=f"Respuesta JSON inválida: {type(exc).__name__}",
            ) from exc

        self._verify_http_success(
            request=request,
            response=response,
            response_data=response_data,
        )

        if verify:
            # La verificación de negocio corre antes de exigir `dict` para que un
            # cliente concreto pueda detectar APIs que devuelven 200 con errores
            # semánticos incluso si el cuerpo no tiene la forma final esperada.
            self._verify(
                request=request,
                response=response,
                response_data=response_data,
            )

        self._verify_json_object(
            request=request,
            response=response,
            response_data=response_data,
        )

        return response_data


class TypedClient(BaseClient):
    async def json_request(self, request: TypedJsonRequest) -> dict[str, Any]:
        return await super()._json_request(request)


class AuthenticatedClient(BaseClient):
    def __init__(self, min_interval: float = 0) -> None:
        super().__init__(min_interval=min_interval)
        self._auth_headers: BaseSchemaPyd | None = None

    @abstractmethod
    async def auth(self) -> BaseSchemaPyd:
        """Realiza la autenticación del cliente y actualiza su estado interno."""

    @abstractmethod
    async def _ensure_credentials(self) -> None:
        """Garantiza que el cliente tenga credenciales válidas antes del request."""

    def build_headers(
        self,
        auth_headers: BaseSchemaPyd,
        headers: BaseSchemaPyd | None = None,
    ) -> dict[str, Any]:
        # Los headers concretos se mezclan primero y los de autenticación van al
        # final para asegurar que credenciales activas no sean pisadas por
        # defaults o valores vacíos del schema del request.
        built_headers = headers.model_dump(exclude_none=True) if headers else {}
        built_headers.update(auth_headers.model_dump(exclude_none=True))
        return built_headers

    def _get_auth_headers(self) -> BaseSchemaPyd:
        if self._auth_headers is None:
            raise ClientException(msg="El cliente no tiene headers de autenticación")
        return self._auth_headers

    async def json_request(self, request: TypedJsonRequest) -> dict[str, Any]:
        await self._ensure_credentials()

        # El contrato público mantiene headers tipados. Solo aquí se materializa
        # el merge a `dict` porque es el punto donde ya conocemos la auth activa.
        request_with_auth = JsonRequest(
            method=request.method,
            url=request.url,
            path_segments=request.path_segments,
            query_params=request.query_params,
            headers=self.build_headers(self._get_auth_headers(), request.headers),
            payload=request.payload,
            timeout=request.timeout,
            cookies=request.cookies,
        )

        return await super()._json_request(request_with_auth)

    async def _json_request_without_auth(
        self,
        request: TypedJsonRequest,
    ) -> dict[str, Any]:
        # La autenticación necesita reutilizar el flujo común de transporte y
        # parsing, pero no debe pasar por la verificación de negocio del cliente.
        return await super()._json_request(request, verify=False)
