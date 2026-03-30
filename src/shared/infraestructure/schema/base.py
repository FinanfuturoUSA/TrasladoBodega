from pydantic import BaseModel, ConfigDict


class BaseSchemaPyd(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        validate_by_name=True,
        validate_by_alias=True,
    )
