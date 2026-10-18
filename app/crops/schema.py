from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CropResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)
