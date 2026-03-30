from asyncio import Lock
from enum import StrEnum
from http import HTTPMethod
from time import time
from turtle import st
from typing import cast, override

from src.shared.infraestructure.httpclient.base import AuthenticatedClient
from src.shared.infraestructure.httpclient.request import TypedJsonRequest
from src.siigo.infraestructure.schema.base import (
    AuthResponseSchema,
    SiigoAuthHeadersSchema,
    SiigoAuthorizationHeadersSchema,
    SiigoAuthSchema,
)


class BaseSiigoClient(AuthenticatedClient):
    AUTH_URL = "https://api.siigo.com/auth"

    def __init__(self, token_type: bool = False) -> None:
        # Siigo tiene un límite de request de máximo 100 peticiones por minuto => 0.6 segundos entre peticiones
        # https://siigoapi.docs.apiary.io/#introduction/limite-de-solicitudes
        super().__init__(min_interval=0.6)
        self._expires_at: float = 0
        self._type_token = token_type

        # Lock para proteger el refresh del token de forma segura
        self._auth_lock: Lock = Lock()

        self._root_url: str = ""
        self._module: str = ""

    def build_url(self, path: StrEnum) -> str:
        return f"{self._root_url}/{self._module}/{path.value}"

    @property
    def authorization(self) -> str:
        auth_headers = cast(SiigoAuthorizationHeadersSchema | None, self._auth_headers)
        if auth_headers is None:
            return ""

        return auth_headers.authorization

    def _has_valid_token(self) -> bool:
        return bool(self.authorization) and self._expires_at > time()

    async def _ensure_valid_token(self) -> None:
        """Asegura que el token sea válido."""
        async with self._auth_lock:
            if self._has_valid_token():
                return

            await self.auth()

    @override
    async def _ensure_credentials(self) -> None:
        await self._ensure_valid_token()

    async def auth(self) -> AuthResponseSchema:
        """
        Obtiene el access_token y lo almacena en el estado interno del cliente
        Calcula el tiempo en el que expira el access_token y lo almacena en self.__expires_at
        """
        # La autenticacion usa un schema propio porque necesita `Partner-Id`,
        # mientras que los requests de reporte deben conservar headers minimos.
        response = await self._json_request_without_auth(
            TypedJsonRequest(
                method=HTTPMethod.POST,
                headers=SiigoAuthHeadersSchema(),
                url=self.AUTH_URL,
                payload=SiigoAuthSchema(),  # SiigoAuthSchema ya trae los valores por defecto de las variables de entorno
            )
        )
        auth_response = AuthResponseSchema(**response)
        if self._type_token:
            authorization = f"{auth_response.token_type} {auth_response.access_token}"
        else:
            authorization = auth_response.access_token

        self._auth_headers = SiigoAuthorizationHeadersSchema(
            Authorization=authorization
        )
        # Se restan 60 segundos para asegurar que el access_token no expire
        self._expires_at = time() + auth_response.expires_in - 60
        return auth_response
