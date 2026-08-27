from typing import Any, Dict

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseContract(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class CamelCaseResponse(BaseContract):
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)
