"""
Pruebas unitarias para los métodos de ReportClient (Siigo).

Se enfoca en validar la construcción correcta del payload para el reporte
de Movimiento Auxiliar (ID 5405) y el manejo de errores en periodos de cierre.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import json
import pytest

from src.siigo.infraestructure.report import ServicesClient
from src.siigo.infraestructure.schema.report import ReportResponseSchema


@pytest.fixture
def client():
    """Retorna una instancia de ReportClient."""
    return ServicesClient()


@pytest.mark.asyncio
async def test_movimiento_auxiliar_envia_payload_correcto(client: ServicesClient):
    """Verifica que el payload enviado a Siigo tenga la estructura requerida (ID 5405)."""

    # Mock de la respuesta mínima válida de Siigo
    mock_response = {
        "data": {"Value": {"Table": []}},
        "totalCount": 0,
        "resume": {"Credit": 0.0, "Debit": 0.0},
    }

    with patch.object(ServicesClient, "json_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response

        fecha_ini = date(2025, 12, 1)
        fecha_fin = date(2025, 12, 31)

        resultado = await client.movimiento_auxiliar(
            fecha_inicial=fecha_ini,
            fecha_final=fecha_fin,
            cuenta_inicial=1,
            cuenta_final=99999999,
        )

        # 1. Validar que se llamó a la API
        mock_req.assert_called_once()

        # 2. Extraer el payload enviado para inspeccionarlo
        (request,), _ = mock_req.call_args
        payload = request.payload

        # 3. Aserciones sobre el payload
        assert payload.id == 5405

        # Verificar filtro de fechas
        filtro_fechas = next(
            f for f in payload.filter_criterias if f.field == "ElaborationDatePeriod"
        )
        assert "20251201" in filtro_fechas.value
        assert "20251231" in filtro_fechas.value
        assert filtro_fechas.value[-1] is None

        # Verificar filtro de cuentas
        filtro_cuentas = next(
            f for f in payload.filter_criterias if f.field == "AccountingCode"
        )
        assert "1" in filtro_cuentas.value
        assert "99999999" in filtro_cuentas.value

        serialized_payload = payload.model_dump(exclude_none=True)
        assert isinstance(serialized_payload["FilterCriterias"], str)
        assert "Params" not in serialized_payload
        assert "AddOns" not in serialized_payload

        filter_criterias_json = json.loads(serialized_payload["FilterCriterias"])
        assert len(filter_criterias_json) == 3
        assert all("ValueUI" not in item for item in filter_criterias_json)
        assert all("Source" not in item for item in filter_criterias_json)

        assert isinstance(resultado, ReportResponseSchema)


@pytest.mark.asyncio
async def test_movimiento_auxiliar_usa_all_cuando_se_piden_todas_las_cuentas(
    client: ServicesClient,
):
    mock_response = {
        "data": {"Value": {"Table": []}},
        "totalCount": 0,
        "resume": {"Credit": 0.0, "Debit": 0.0},
    }

    with patch.object(ServicesClient, "json_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response

        await client.movimiento_auxiliar(
            fecha_inicial=date(2025, 12, 1),
            fecha_final=date(2025, 12, 5),
            todas_las_cuentas=True,
        )

        (request,), _ = mock_req.call_args
        filtro_cuentas = next(
            f for f in request.payload.filter_criterias if f.field == "AccountingCode"
        )

        assert filtro_cuentas.value == ["ALL"]


@pytest.mark.asyncio
async def test_movimiento_auxiliar_incluye_periodo_13_en_cierre(client: ServicesClient):
    """Si incluye_cierre es True para un año pasado, debe añadir el periodo 'YYYY13'."""

    mock_response = {
        "data": {"Value": {"Table": []}},
        "totalCount": 0,
        "resume": {"Credit": 0, "Debit": 0},
    }

    with patch.object(ServicesClient, "json_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        closed_year = date.today().year - 1

        await client.movimiento_auxiliar(
            fecha_inicial=date(closed_year, 12, 1),
            fecha_final=date(closed_year, 12, 31),
            incluye_cierre=True,
        )

        (request,), _ = mock_req.call_args
        filtro_fechas = next(
            f
            for f in request.payload.filter_criterias
            if f.field == "ElaborationDatePeriod"
        )

        # Debe contener fecha ini, fecha fin y el periodo de cierre (13)
        assert f"{closed_year}1231" in filtro_fechas.value
        assert f"{closed_year}13" in filtro_fechas.value


@pytest.mark.asyncio
async def test_movimiento_auxiliar_falla_con_cierre_si_fecha_final_no_es_anterior_a_hoy(
    client: ServicesClient,
):
    """Debe fallar si `fecha_final` no pertenece a un año ya cerrado."""

    fecha_hoy = date.today()

    with pytest.raises(
        ValueError,
        match="No se puede incluir cierre cuando la fecha final es igual o posterior",
    ):
        await client.movimiento_auxiliar(
            fecha_inicial=date(fecha_hoy.year, 1, 1),
            fecha_final=fecha_hoy,
            incluye_cierre=True,
        )


@pytest.mark.asyncio
async def test_movimiento_auxiliar_falla_con_cierre_si_fecha_final_no_es_31_de_diciembre(
    client: ServicesClient,
):
    """Debe fallar si se pide cierre para una fecha distinta al ultimo dia del año."""

    closed_year = date.today().year - 1

    with pytest.raises(
        ValueError,
        match="No se puede incluir cierre si la fecha final no es 31 de diciembre",
    ):
        await client.movimiento_auxiliar(
            fecha_inicial=date(closed_year, 12, 1),
            fecha_final=date(closed_year, 12, 30),
            incluye_cierre=True,
        )
