from pydantic import ConfigDict, Field

from src.config import Config
from src.shared.infraestructure.schema.base import BaseSchemaPyd


class SiigoBaseSchema(BaseSchemaPyd):
    # https://docs.pydantic.dev/latest/concepts/config/
    # If you provide configuration to the subclasses, it will be merged with the parent configuration:
    model_config = ConfigDict(serialize_by_alias=True)


class SiigoHeadersSchema(SiigoBaseSchema):
    # Usamos el alias en minuscula para mantener el header exactamente igual
    # al request funcional que validamos contra Siigo.
    content_type: str = Field(default="application/json", alias="content-type")


class SiigoAuthorizationHeadersSchema(SiigoBaseSchema):
    authorization: str = Field(alias="Authorization")


class SiigoAuthHeadersSchema(SiigoHeadersSchema):
    # `Partner-Id` se conserva solo para autenticacion. En los reportes ya
    # comprobamos que no hace falta y asi el schema runtime queda minimo.
    partner_id: str | None = Field(default=Config.partner_id, alias="Partner-Id")


class SiigoAuthSchema(SiigoBaseSchema):
    username: str = Config.siigo_api_user
    access_key: str = Config.siigo_api_key


class AuthResponseSchema(SiigoBaseSchema):
    access_token: str
    expires_in: int
    token_type: str
    scope: str
