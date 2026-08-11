from __future__ import annotations

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    RootModel
)
from typing import TypeVar, Generic

# Here we defined the response model for the REST API
# There is a strong similarity with the sqlalchemy tables types,
# but their might be deviations - mainly to augment fields
# or to facilitate processing.
#
# Augmented / computed fields will be marked as 'computed field'

class SimpleModel(BaseModel):
    # https://docs.pydantic.dev/2.10/api/config/#pydantic.config.ConfigDict.from_attributes
    model_config = ConfigDict(from_attributes=True)

class TimestampedModel(SimpleModel):
    time: AwareDatetime = Field(description="Timezone Aware timestamp")

class ErrorMessageResponse(BaseModel):
    cluster: str = Field(description="Name of the cluster")
    node: str = Field(description="Name of the node (in the cluster)")

    details: str = Field(description="Details of the reported error")
    time: str = Field(description="Time at which this error occurred")

class UserSettingsResponse(BaseModel):
    user: str
    settings: dict = Field(default={})
    time_modified: AwareDatetime | None = Field(default=None)
