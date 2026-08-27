from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseContract(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class CamelCaseResponse(BaseContract):
    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
