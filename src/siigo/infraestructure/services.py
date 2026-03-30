from datetime import date
from enum import Enum, StrEnum
from http import HTTPMethod
from typing import Any, override

import httpx

from src.shared.infraestructure.httpclient.request import JsonRequest, TypedJsonRequest
from src.siigo.infraestructure.base import BaseSiigoClient
from src.siigo.infraestructure.schema.base import SiigoHeadersSchema
from src.siigo.infraestructure.schema.report import (
    FilterCriteriaSchema,
    ReportPayloadSchema,
    ReportResponseSchema,
)


class ServicesSiigoModules(Enum):
    REPORT = "ACReportApi"


class ServicesSiigoClient(BaseSiigoClient):
    def __init__(self, module: ServicesSiigoModules) -> None:
        super().__init__()
        self._root_url = "https://services.siigo.com"
        self._module = module.value


class ServicesSiigoReportPaths(StrEnum):
    REPORT_V1 = "api/v1/Report/post"


class ServicesSiigoReportClient(ServicesSiigoClient):
    def __init__(self) -> None:
        super().__init__(ServicesSiigoModules.REPORT)

    @override
    def _verify(
        self,
        *,
        request: JsonRequest | TypedJsonRequest,
        response: httpx.Response,
        response_data: Any,
    ) -> None:
        return None

    async def movimiento_auxiliar(
        self,
        fecha_inicial: date,
        fecha_final: date,
        incluye_cierre: bool = False,
        todas_las_cuentas: bool = False,
        cuenta_inicial: int = 1,
        cuenta_final: int = 99999999,
    ) -> ReportResponseSchema:
        """Obtiene el reporte de Movimiento Auxiliar de Cuentas Contables (ID 5405).

        Args:
            fecha_inicial: Fecha de inicio del período (ej: date(2026, 3, 1))
            fecha_final:   Fecha de fin del período (ej: date(2026, 3, 31))
            incluye_cierre: Si incluye el período de cierre (usa YYYY13 como tercer valor).
                Solo aplica cuando `fecha_final` es anterior a hoy y cae en 31 de diciembre.
            todas_las_cuentas: Intenta pedir todas las cuentas usando `ALL`.
            cuenta_inicial: Código de cuenta contable inicial (default: 1)
            cuenta_final:   Código de cuenta contable final (default: 99999999)

        Returns:
            ReportResponseSchema con la tabla de movimientos
        """
        fmt_ini = fecha_inicial.strftime("%Y%m%d")
        fmt_fin = fecha_final.strftime("%Y%m%d")
        current_date = date.today()

        date_values: list[str | None] = [fmt_ini, fmt_fin, None]
        if incluye_cierre:
            if fecha_final >= current_date:
                raise ValueError(
                    "No se puede incluir cierre cuando la fecha final es igual o posterior "
                    "a la fecha actual."
                )
            if (fecha_final.month, fecha_final.day) != (12, 31):
                raise ValueError(
                    "No se puede incluir cierre si la fecha final no es 31 de diciembre."
                )
            date_values[-1] = f"{fecha_final.year}13"

        account_values: list[str | None] = ["ALL"]
        if not todas_las_cuentas:
            account_values = [str(cuenta_inicial), str(cuenta_final)]

        # Dejamos solo los tres filtros que realmente demostraron ser
        # necesarios en las pruebas reales: cuenta, periodo y moneda.
        # `Currency` se conserva porque al quitarlo Siigo respondio 500.
        filter_criterias = [
            FilterCriteriaSchema(
                Field="AccountingCode",
                FilterType=67,
                OperatorType=9,
                Value=account_values,
            ),
            FilterCriteriaSchema(
                Field="ElaborationDatePeriod",
                FilterType=66,
                OperatorType=9,
                Value=date_values,
            ),
            FilterCriteriaSchema(
                Field="Currency",
                FilterType=65,
                OperatorType=0,
                Value=["ALL"],
            ),
        ]

        # El payload queda minimo a proposito: `Params`, `AddOns`, `ValueUI` y
        # `Source` no fueron necesarios para obtener respuesta en este reporte.
        # En Python usamos `id=5405` por claridad y tipado; el alias del schema
        # se encarga de serializarlo como `Id` en el request final.
        payload = ReportPayloadSchema(
            id=5405,
            FilterCriterias=filter_criterias,
        )

        response = await self.json_request(
            TypedJsonRequest(
                method=HTTPMethod.POST,
                headers=SiigoHeadersSchema(),
                url=self.build_url(ServicesSiigoReportPaths.REPORT_V1),
                payload=payload,
                timeout=120,
            )
        )

        return ReportResponseSchema(**response)
