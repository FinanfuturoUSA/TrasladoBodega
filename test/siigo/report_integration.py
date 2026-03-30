from typing import Literal

import pytest

from src.shared.core.dates import last_completed_workweek_range
from src.siigo.infraestructure.services import (
    ServicesSiigoReportClient,
)


def _assert_valid_report_response(resultado) -> None:
    assert resultado.total_count >= 0
    assert isinstance(resultado.data.value.table, list)
    assert resultado.resume.debit >= 0
    assert resultado.resume.credit >= 0


@pytest.mark.asyncio
async def test_movimiento_auxiliar_ultima_semana_laboral() -> None:
    client = ServicesSiigoReportClient()
    fecha_inicial, fecha_final = last_completed_workweek_range()

    filtro_usado: Literal["ALL", "RANGO"] = "ALL"

    try:
        resultado = await client.movimiento_auxiliar(
            fecha_inicial=fecha_inicial,
            fecha_final=fecha_final,
            todas_las_cuentas=True,
        )
    except Exception as error_all:
        filtro_usado = "RANGO"
        print(f"Filtro de cuentas ALL no disponible para este tenant: {error_all}")
        resultado = await client.movimiento_auxiliar(
            fecha_inicial=fecha_inicial,
            fecha_final=fecha_final,
            cuenta_inicial=1,
            cuenta_final=99999999,
        )

    print(
        "Movimiento Auxiliar",
        f"{fecha_inicial.isoformat()} -> {fecha_final.isoformat()}",
        f"filtro={filtro_usado}",
        f"filas={len(resultado.data.value.table)}",
    )

    assert fecha_inicial.weekday() == 0
    assert fecha_final.weekday() == 4
    _assert_valid_report_response(resultado)
