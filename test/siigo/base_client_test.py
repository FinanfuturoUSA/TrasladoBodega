import asyncio
from datetime import date
from http import HTTPMethod
from time import perf_counter

import httpx
import pytest

from src.shared.infraestructure.httpclient.base import ClientException, TypedClient
from src.shared.infraestructure.httpclient.request import JsonRequest, TypedJsonRequest
from src.shared.infraestructure.schema.base import BaseSchemaPyd


class HeadersSchema(BaseSchemaPyd):
    authorization: str = "token"


class PayloadSchema(BaseSchemaPyd):
    value: str = "demo"


class DummyTypedClient(TypedClient):
    def _verify(
        self,
        *,
        request: JsonRequest | TypedJsonRequest,
        response: httpx.Response,
        response_data,
    ) -> None:
        return None


class BusinessErrorTypedClient(TypedClient):
    def _verify(
        self,
        *,
        request: JsonRequest | TypedJsonRequest,
        response: httpx.Response,
        response_data,
    ) -> None:
        if response_data.get("success") is False:
            raise ClientException.from_httpx_response(
                payload=request.payload.model_dump(exclude_none=True)
                if request.payload
                else None,
                url=request.get_url(),
                response=response,
                response_data=response_data,
                msg="La API respondió 200 pero indicó error de negocio",
            )


@pytest.mark.anyio
async def test_json_request_lanza_client_exception_en_http_error(monkeypatch):
    async def fake_request(self, *args, **kwargs):
        return httpx.Response(500, json={"message": "boom"})

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    client = DummyTypedClient()

    with pytest.raises(ClientException) as exc_info:
        await client.json_request(
            TypedJsonRequest(
                method=HTTPMethod.POST,
                headers=HeadersSchema(),
                url="https://example.com/test",
                payload=PayloadSchema(),
            )
        )

    assert exc_info.value.response == {"message": "boom"}
    assert exc_info.value.status_code == 500
    assert exc_info.value.response_type == "dict"
    assert exc_info.value.headers is not None
    assert exc_info.value.msg == "HTTP 500: Internal Server Error"


@pytest.mark.anyio
async def test_json_request_lanza_client_exception_en_error_de_negocio(monkeypatch):
    async def fake_request(self, *args, **kwargs):
        return httpx.Response(200, json={"success": False, "message": "boom"})

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    client = BusinessErrorTypedClient()

    with pytest.raises(ClientException) as exc_info:
        await client.json_request(
            TypedJsonRequest(
                method=HTTPMethod.POST,
                headers=HeadersSchema(),
                url="https://example.com/test",
                payload=PayloadSchema(),
            )
        )

    assert exc_info.value.status_code == 200
    assert exc_info.value.response == {"success": False, "message": "boom"}
    assert exc_info.value.msg == "La API respondió 200 pero indicó error de negocio"


def test_client_exception_publica_y_repr_interna():
    exception = ClientException(
        payload={"demo": True},
        url="https://example.com/test",
        response={"message": "boom"},
        status_code=500,
        headers={"authorization": "secret", "content-type": "application/json"},
        response_type="dict",
        msg="HTTP 500: Internal Server Error",
    )

    public_repr = str(exception)
    debug_repr = repr(exception)

    assert "status_code: 500" in public_repr
    assert "response_type: dict" in public_repr
    assert "headers:" not in public_repr

    assert "status_code: 500" in debug_repr
    assert "response_type: dict" in debug_repr
    assert 'headers: {"authorization": "secret"' in debug_repr


def test_client_exception_normaliza_response_json_no_dict():
    response = httpx.Response(400, json=["boom"])

    exception = ClientException.from_httpx_response(
        payload=None,
        url="https://example.com/test",
        response=response,
        response_data=["boom"],
        msg="HTTP 400: Bad Request",
    )

    assert exception.response == '["boom"]'
    assert exception.response_type == "list"
    assert "response_type: list" in str(exception)


def test_client_exception_no_falla_con_payload_no_serializable_nativo():
    exception = ClientException(
        payload={"fecha": date(2026, 3, 29)},
        url="https://example.com/test",
        response={"message": "boom"},
        status_code=500,
        headers={"authorization": "secret"},
        response_type="dict",
        msg="HTTP 500: Internal Server Error",
    )

    public_repr = str(exception)
    debug_repr = repr(exception)

    assert 'payload: {"fecha": "2026-03-29"}' in public_repr
    assert 'headers: {"authorization": "secret"}' in debug_repr


@pytest.mark.anyio
async def test_rate_limit_es_seguro_con_requests_concurrentes(monkeypatch):
    timestamps: list[float] = []

    async def fake_request(self, *args, **kwargs):
        timestamps.append(perf_counter())
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    client = DummyTypedClient(min_interval=0.05)

    await asyncio.gather(
        *[
            client.json_request(
                TypedJsonRequest(
                    method=HTTPMethod.POST,
                    headers=HeadersSchema(),
                    url="https://example.com/test",
                    payload=PayloadSchema(),
                )
            )
            for _ in range(3)
        ]
    )

    deltas = [timestamps[index + 1] - timestamps[index] for index in range(2)]

    assert len(timestamps) == 3
    assert all(delta >= 0.04 for delta in deltas)
