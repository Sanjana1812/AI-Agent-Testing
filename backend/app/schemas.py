from pydantic import BaseModel, Field, HttpUrl


class RunTestRequest(BaseModel):
    url: HttpUrl
    goal: str = Field(min_length=1)


class RunTestResponse(BaseModel):
    id: str
    status: str
    title: str
    url: str
    http_status: int
    duration_ms: int
    screenshot: str
