from pydantic import BaseModel, ConfigDict


class RequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
