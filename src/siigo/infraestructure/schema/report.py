from typing import Any

from pydantic import Field, RootModel, field_serializer

from src.siigo.infraestructure.schema.base import SiigoBaseSchema

# ==================== PAYLOAD (Request) ====================


class FilterCriteriaSchema(SiigoBaseSchema):
    """Filtro individual aplicado al reporte."""

    field: str = Field(
        alias="Field",
        description="Campo sobre el que se filtra (AccountingCode, ElaborationDatePeriod, Currency)",
    )
    filter_type: int = Field(
        alias="FilterType", description="Tipo de filtro interno de Siigo"
    )
    operator_type: int = Field(
        alias="OperatorType",
        description="Tipo de operador (9 = rango, 0 = igual, etc.)",
    )
    value: list[str | None] = Field(alias="Value", description="Valor(es) del filtro")
    value_ui: str | None = Field(
        default=None,
        alias="ValueUI",
        description="Texto legible mostrado al usuario",
    )
    source: Any | None = Field(
        default=None,
        alias="Source",
        description="Fuente adicional (usado especialmente en períodos contables)",
    )


# Este alias tipado existe solo para aprovechar `model_dump_json()` de Pydantic
# y producir el string JSON compacto que Siigo espera en `FilterCriterias`.
FilterCriteriaListSchema = RootModel[list[FilterCriteriaSchema]]


class ReportPayloadSchema(SiigoBaseSchema):
    """Payload minimo para solicitar el reporte de Movimiento Auxiliar."""

    id: int = Field(
        validation_alias="Id",
        serialization_alias="Id",
        description="ID del reporte en Siigo. Cada metodo especifico debe proveerlo.",
    )
    filter_criterias: list[FilterCriteriaSchema] = Field(
        alias="FilterCriterias",
        description="Filtros requeridos: cuenta, periodo y moneda.",
    )

    @field_serializer("filter_criterias", when_used="always")
    def serialize_filter_criterias(
        self,
        value: list[FilterCriteriaSchema],
    ) -> str:
        # Ojo: este endpoint NO acepta `FilterCriterias` como arreglo JSON
        # normal (`[{...}]`). Si se envia asi, Siigo responde 500. Necesita que
        # el campo viaje como string JSON (`"[{...}]"`) porque asi lo consume
        # internamente su motor de reportes.
        return FilterCriteriaListSchema(value).model_dump_json(
            exclude_none=True,
        )


# ==================== RESPONSE ====================


# region Response
class MovementRowSchema(SiigoBaseSchema):
    """Fila individual de movimiento del reporte de Cuentas Auxiliares.

    Algunos campos son opcionales porque existen filas de resumen (solo saldos)
    que no tienen comprobante, tercero, ni fecha.
    """

    accounting_code: str = Field(
        alias="AccountingCode", description="Código de la cuenta contable"
    )
    accounting_concept: str = Field(
        alias="AccountingConcept", description="Nombre del concepto de la cuenta"
    )
    accounting_concept_group: str = Field(
        alias="AccountingConceptGroup",
        description="Concatenación código + concepto",
    )
    voucher_id: int | None = Field(
        default=None, alias="VoucherID", description="ID interno del comprobante"
    )
    voucher: str | None = Field(
        default=None,
        alias="Voucher",
        description="Número del documento (FV, DS, RC, CC, etc.)",
    )
    sequence: int | None = Field(
        default=None, alias="Sequence", description="Secuencia dentro del comprobante"
    )
    elaboration_date: str | None = Field(
        default=None,
        alias="ElaborationDate",
        description="Fecha de elaboración del movimiento",
    )
    identification: str | None = Field(
        default=None,
        alias="Identification",
        description="Identificación del tercero (NIT/CC)",
    )
    branch_office: str = Field(alias="BranchOffice", description="Sucursal")
    third_name: str = Field(alias="ThirdName", description="Nombre del tercero")
    description: str = Field(
        alias="Description", description="Descripción del movimiento"
    )
    detail: str | None = Field(
        default=None, alias="Detail", description="Detalle adicional"
    )
    cost_center: str = Field(alias="CostCenter", description="Centro de costo")
    initial_balance_hidden: float = Field(
        alias="InitialBalanceHidden",
        description="Saldo inicial oculto de la cuenta",
    )
    account_id_hidden: int | None = Field(
        default=None,
        alias="AccountIDHidden",
        description="ID interno de la cuenta en Siigo",
    )
    debit: float = Field(alias="Debit", description="Valor débito del movimiento")
    credit: float = Field(alias="Credit", description="Valor crédito del movimiento")
    balance_value: float = Field(
        alias="BalanceValue",
        description="Saldo acumulado después de este movimiento",
    )
    movement_balance: float = Field(
        alias="MovementBalance", description="Saldo del movimiento acumulado"
    )


class ReportResumeSchema(SiigoBaseSchema):
    """Resumen de totales del reporte."""

    credit: float = Field(alias="Credit", description="Total general de créditos")
    debit: float = Field(alias="Debit", description="Total general de débitos")


class ReportValueSchema(SiigoBaseSchema):
    """Estructura interna que contiene la tabla de movimientos."""

    table: list[MovementRowSchema] = Field(
        alias="Table", description="Lista de todos los movimientos del reporte"
    )


class ReportDataWrapperSchema(SiigoBaseSchema):
    """Wrapper intermedio: data contiene campos opcionales + Value con la tabla."""

    content_type: str | None = Field(
        default=None, alias="ContentType", description="Content-Type (siempre null)"
    )
    serializer_settings: str | None = Field(
        default=None,
        alias="SerializerSettings",
        description="Serializer settings (siempre null)",
    )
    status_code: int | None = Field(
        default=None,
        alias="StatusCode",
        description="Status code interno (siempre null)",
    )
    value: ReportValueSchema = Field(
        alias="Value", description="Contenedor de la tabla de movimientos"
    )


class ReportResponseSchema(SiigoBaseSchema):
    """Respuesta completa del endpoint /Report/post."""

    data: ReportDataWrapperSchema = Field(
        alias="data", description="Contenedor principal de la respuesta"
    )
    total_count: int = Field(
        alias="totalCount",
        description="Conteo total de registros (generalmente 0 en este reporte)",
    )
    resume: ReportResumeSchema = Field(
        alias="resume", description="Resumen de totales (Debit debe ≈ Credit)"
    )

    # Campos opcionales
    success: bool | None = Field(
        default=None, alias="success", description="Indica éxito de la operación"
    )
    message: str | None = Field(
        default=None, alias="message", description="Mensaje adicional"
    )


# endregion Response
