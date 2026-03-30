from datetime import date

from pydantic import Field, field_serializer

from src.siigo.infraestructure.schema.base import SiigoBaseSchema


class WarehouseTransferHeadersSchema(SiigoBaseSchema):
    pass


class WarehouseTransferItemSchema(SiigoBaseSchema):
    product_code: int = Field(alias="ProductCode")
    warehouse_code: int = Field(alias="WarehouseCode")
    destination_warehouse_code: int = Field(alias="DestinationWarehouseCode")
    quantity: int | float = Field(alias="Quantity")


class WarehouseTransferEntrySchema(SiigoBaseSchema):
    doc_date: date = Field(alias="DocDate")

    @field_serializer("doc_date", when_used="always")
    def serialize_doc_date(self, value: date) -> str:
        return value.strftime("%Y%m%d")


class WarehouseTransferPayloadSchema(SiigoBaseSchema):
    items: list[WarehouseTransferItemSchema] = Field(
        alias="Items",
        min_length=1,
    )
    entry: WarehouseTransferEntrySchema = Field(alias="Entry")


class WarehouseTransferResponseSchema(SiigoBaseSchema):
    transfer_id: int
