from datetime import date
from enum import Enum, StrEnum
from http import HTTPMethod
from typing import Any, override

import httpx

from src.shared.infraestructure.httpclient.base import ClientException
from src.shared.infraestructure.httpclient.request import JsonRequest, TypedJsonRequest
from src.siigo.infraestructure.base import BaseSiigoClient
from src.siigo.infraestructure.schema.warehouse_transfer import (
    WarehouseTransferEntrySchema,
    WarehouseTransferHeadersSchema,
    WarehouseTransferItemSchema,
    WarehouseTransferPayloadSchema,
    WarehouseTransferResponseSchema,
)


class ServicesPdSiigoModules(Enum):
    ENTRY = "ACEntryApi"


class ServicesPdSiigoClient(BaseSiigoClient):
    def __init__(self, module: ServicesPdSiigoModules) -> None:
        super().__init__()
        self._root_url = "https://servicespd.siigo.com"
        self._module = module.value

    async def scalar_json_request(self, request: TypedJsonRequest) -> Any:
        await self._ensure_credentials()

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
        payload_data = (
            request_with_auth.payload.model_dump(exclude_none=True)
            if request_with_auth.payload
            else None
        )
        response = await self._execute_request(request_with_auth)

        try:
            response_data = response.json()
        except Exception as exc:
            if not response.is_success:
                raise ClientException.from_httpx_response(
                    payload=payload_data,
                    url=request_with_auth.get_url(),
                    response=response,
                    response_data=response.text,
                    msg=f"HTTP {response.status_code}: {response.reason_phrase}",
                ) from exc

            raise ClientException.from_httpx_response(
                payload=payload_data,
                url=request_with_auth.get_url(),
                response=response,
                msg=f"Respuesta JSON invalida: {type(exc).__name__}",
            ) from exc

        self._verify_http_success(
            request=request_with_auth,
            response=response,
            response_data=response_data,
        )
        self._verify(
            request=request_with_auth,
            response=response,
            response_data=response_data,
        )

        return response_data


class ServicesPdSiigoWarehouseTransferPaths(StrEnum):
    SAVE_V1 = "api/v1/WarehouseTransfer/Save/"


class ServicesPdSiigoWarehouseTransferClient(ServicesPdSiigoClient):
    def __init__(self) -> None:
        super().__init__(ServicesPdSiigoModules.ENTRY)

    @override
    def _verify(
        self,
        *,
        request: JsonRequest | TypedJsonRequest,
        response: httpx.Response,
        response_data: Any,
    ) -> None:
        return None

    async def crear_traslado_bodega(
        self,
        fecha: date,
        items: list[WarehouseTransferItemSchema],
    ) -> WarehouseTransferResponseSchema | None:
        if not items:
            return None

        payload = WarehouseTransferPayloadSchema(
            Items=items,
            Entry=WarehouseTransferEntrySchema(DocDate=fecha),
        )
        request = TypedJsonRequest(
            method=HTTPMethod.POST,
            headers=WarehouseTransferHeadersSchema(),
            url=self.build_url(ServicesPdSiigoWarehouseTransferPaths.SAVE_V1),
            payload=payload,
            timeout=120,
        )
        response_data = await self.scalar_json_request(request)

        try:
            transfer_id = int(response_data)
        except (TypeError, ValueError) as exc:
            raise ClientException(
                payload=payload.model_dump(exclude_none=True),
                url=request.get_url(),
                response=response_data,
                response_type=type(response_data).__name__,
                msg="Respuesta inesperada al crear traslado de bodega",
            ) from exc

        return WarehouseTransferResponseSchema(transfer_id=transfer_id)
