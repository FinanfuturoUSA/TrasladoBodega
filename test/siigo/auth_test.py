"""
Test de autenticación contra la API de Siigo usando BaseSiigoClient.

Valida que:
  1. El método `auth()` retorne un AuthResponseSchema válido.
  2. El token se almacene correctamente en los headers internos.
  3. `_ensure_valid_token()` reutilice el token mientras no haya expirado.
"""

from time import time

import pytest
import httpx

from src.siigo.infraestructure.base import BaseSiigoClient
from src.siigo.infraestructure.schema.base import AuthResponseSchema
from src.shared.infraestructure.httpclient.request import JsonRequest, TypedJsonRequest


class DummySiigoClient(BaseSiigoClient):
    def _verify(
        self,
        *,
        request: JsonRequest | TypedJsonRequest,
        response: httpx.Response,
        response_data,
    ) -> None:
        return None


@pytest.fixture
def client() -> BaseSiigoClient:
    """Cliente Siigo con token_type=True (incluye 'Bearer' en el header)."""
    return DummySiigoClient(token_type=True)


@pytest.fixture
def client_raw_token() -> BaseSiigoClient:
    """Cliente Siigo con token_type=False (token sin prefijo)."""
    return DummySiigoClient(token_type=False)


# ── Pruebas de auth() ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_auth_returns_valid_response(client: BaseSiigoClient):
    """auth() debe retornar un AuthResponseSchema con todos los campos."""
    response = await client.auth()
    print(response)

    assert isinstance(response, AuthResponseSchema)
    assert response.access_token, "access_token no debe estar vacío"
    assert response.expires_in > 0, "expires_in debe ser positivo"
    assert response.token_type, "token_type no debe estar vacío"
    assert response.scope is not None, "scope debe existir"


@pytest.mark.anyio
async def test_auth_sets_bearer_header(client: BaseSiigoClient):
    """Con token_type=True, el header Authorization debe tener 'Bearer <token>'."""
    response = await client.auth()

    expected = f"{response.token_type} {response.access_token}"

    assert client.authorization == expected


@pytest.mark.anyio
async def test_auth_sets_raw_token_header(client_raw_token: BaseSiigoClient):
    """Con token_type=False, el header Authorization solo debe contener el token."""
    response = await client_raw_token.auth()

    assert client_raw_token.authorization == response.access_token
    assert (
        "Bearer" not in client_raw_token.authorization.split(" ")[0]
        or client_raw_token.authorization == response.access_token
    )


@pytest.mark.anyio
async def test_auth_sets_expiration(client: BaseSiigoClient):
    """auth() debe fijar __expires_at en el futuro (con 60 s de margen)."""
    before = time()
    response = await client.auth()
    after = time()

    expires_at = client._expires_at  # type: ignore[attr-defined]

    # El tiempo de expiración debe ser aproximadamente: ahora + expires_in - 60
    assert expires_at >= before + response.expires_in - 60
    assert expires_at <= after + response.expires_in - 60


# ── Pruebas de _ensure_valid_token() ──────────────────────────────────


@pytest.mark.anyio
async def test_ensure_valid_token_authenticates_when_empty(client: BaseSiigoClient):
    """Si no hay token, _ensure_valid_token() debe llamar a auth()."""
    assert client.authorization == "", "Al inicio no debe haber token"

    await client._ensure_valid_token()

    assert client.authorization != "", "Debe haberse obtenido un token"


@pytest.mark.anyio
async def test_ensure_valid_token_reuses_existing(client: BaseSiigoClient):
    """Si el token es válido, _ensure_valid_token() no debe cambiarlo."""
    await client._ensure_valid_token()

    token_after_first = client.authorization

    await client._ensure_valid_token()

    assert client.authorization == token_after_first, (
        "El token no debe cambiar si sigue vigente"
    )
