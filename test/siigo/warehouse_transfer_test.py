from datetime import date
from http import HTTPMethod
from time import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.shared.infraestructure.httpclient.base import ClientException
from src.shared.infraestructure.httpclient.request import TypedJsonRequest
from src.siigo.infraestructure.schema.base import SiigoAuthorizationHeadersSchema
from src.siigo.infraestructure.schema.warehouse_transfer import (
    WarehouseTransferEntrySchema,
    WarehouseTransferHeadersSchema,
    WarehouseTransferItemSchema,
    WarehouseTransferPayloadSchema,
    WarehouseTransferResponseSchema,
)
from src.siigo.infraestructure.servicespd import (
    ServicesPdSiigoWarehouseTransferClient,
    ServicesPdSiigoWarehouseTransferPaths,
)


@pytest.fixture
def client() -> ServicesPdSiigoWarehouseTransferClient:
    return ServicesPdSiigoWarehouseTransferClient()


@pytest.mark.anyio
async def test_crear_traslado_bodega_envia_payload_minimo_correcto(
    client: ServicesPdSiigoWarehouseTransferClient,
):
    with patch.object(
        ServicesPdSiigoWarehouseTransferClient,
        "scalar_json_request",
        new_callable=AsyncMock,
    ) as mock_req:
        mock_req.return_value = 1039623

        resultado = await client.crear_traslado_bodega(
            fecha=date(2026, 3, 30),
            codigo_producto=161151,
            cantidad=1,
            warehouse_code=37,
            destination_warehouse_code=-1,
        )

        mock_req.assert_called_once()
        (request,), _ = mock_req.call_args

        assert request.method == HTTPMethod.POST
        assert request.url == client.build_url(
            ServicesPdSiigoWarehouseTransferPaths.SAVE_V1
        )

        serialized_payload = request.payload.model_dump(exclude_none=True)
        assert serialized_payload == {
            "Items": [
                {
                    "ProductCode": 161151,
                    "WarehouseCode": 37,
                    "DestinationWarehouseCode": -1,
                    "Quantity": 1,
                }
            ],
            "Entry": {"DocDate": "20260330"},
        }
        assert "EntryType" not in serialized_payload
        assert "ModelType" not in serialized_payload

        assert isinstance(resultado, WarehouseTransferResponseSchema)
        assert resultado.transfer_id == 1039623


@pytest.mark.anyio
async def test_scalar_json_request_acepta_respuesta_json_escalar(
    client: ServicesPdSiigoWarehouseTransferClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_request(self, method, url, **kwargs):
        assert method == HTTPMethod.POST.value
        assert url == client.build_url(ServicesPdSiigoWarehouseTransferPaths.SAVE_V1)
        assert kwargs["headers"] == {"Authorization": "token-demo"}
        assert kwargs["json"] == {
            "Items": [
                {
                    "ProductCode": 161151,
                    "WarehouseCode": 37,
                    "DestinationWarehouseCode": -1,
                    "Quantity": 1,
                }
            ],
            "Entry": {"DocDate": "20260330"},
        }
        return httpx.Response(200, json=1039623)

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    client._auth_headers = SiigoAuthorizationHeadersSchema(Authorization="token-demo")
    client._expires_at = time() + 3600

    response = await client.scalar_json_request(
        TypedJsonRequest(
            method=HTTPMethod.POST,
            headers=WarehouseTransferHeadersSchema(),
            url=client.build_url(ServicesPdSiigoWarehouseTransferPaths.SAVE_V1),
            payload=WarehouseTransferPayloadSchema(
                Items=[
                    WarehouseTransferItemSchema(
                        ProductCode=161151,
                        WarehouseCode=37,
                        DestinationWarehouseCode=-1,
                        Quantity=1,
                    )
                ],
                Entry=WarehouseTransferEntrySchema(DocDate=date(2026, 3, 30)),
            ),
        )
    )

    assert response == 1039623


@pytest.mark.anyio
async def test_scalar_json_request_preserva_error_texto_http(
    client: ServicesPdSiigoWarehouseTransferClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_request(self, method, url, **kwargs):
        return httpx.Response(406, text="El objeto enviado no es valido")

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    client._auth_headers = SiigoAuthorizationHeadersSchema(Authorization="token-demo")
    client._expires_at = time() + 3600

    with pytest.raises(ClientException) as exc_info:
        await client.scalar_json_request(
            TypedJsonRequest(
                method=HTTPMethod.POST,
                headers=WarehouseTransferHeadersSchema(),
                url=client.build_url(ServicesPdSiigoWarehouseTransferPaths.SAVE_V1),
                payload=WarehouseTransferPayloadSchema(
                    Items=[
                        WarehouseTransferItemSchema(
                            ProductCode=161151,
                            WarehouseCode=37,
                            DestinationWarehouseCode=-1,
                            Quantity=1,
                        )
                    ],
                    Entry=WarehouseTransferEntrySchema(DocDate=date(2026, 3, 30)),
                ),
            )
        )

    assert exc_info.value.status_code == 406
    assert exc_info.value.response == "El objeto enviado no es valido"
    assert exc_info.value.msg == "HTTP 406: Not Acceptable"
