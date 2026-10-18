from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LivestockResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)
