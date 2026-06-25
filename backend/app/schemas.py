from pydantic import BaseModel, Field, HttpUrl


class RunTestRequest(BaseModel):
    url: HttpUrl
    goal: str = Field(min_length=1)


class PlanStep(BaseModel):
    action: str
    target: str | None = None
    text: str | None = None
    ms: int | None = None


class ExecutionStep(BaseModel):
    id: str
    step: str
    status: str
    duration_ms: int


class ExecutionFailure(BaseModel):
    type: str
    message: str
    severity: str


class ExecutionSummary(BaseModel):
    total_steps: int
    passed_steps: int
    failed_steps: int
    health: str


class RunTestResponse(BaseModel):
    id: str
    goal: str
    status: str
    title: str
    url: str
    http_status: int
    duration_ms: int
    screenshot: str
    ai_plan: list[PlanStep]
    ai_plan_source: str
    steps: list[ExecutionStep]
    failures: list[ExecutionFailure]
    summary: ExecutionSummary
