from pydantic import BaseModel, Field, HttpUrl


class RunTestRequest(BaseModel):
    url: HttpUrl
    goal: str = Field(min_length=1)


class PlanStep(BaseModel):
    action: str
    target: str | None = None
    selector: str | None = None
    label: str | None = None
    text: str | None = None
    value: str | None = None
    ms: int | None = None
    selector_strategy: str | None = None
    selector_confidence: float | None = None
    selector_type: str | None = None
    context_url: str | None = None
    context_refresh: bool | None = None
    selector_alternatives: list[str] | None = None


class AssertionResult(BaseModel):
    type: str
    expected: str
    actual: str
    passed: bool
    reason: str | None = None
    duration_ms: int = 0


class ExecutionStep(BaseModel):
    id: str
    step: str
    status: str
    duration_ms: int
    assertions: list[AssertionResult] = Field(default_factory=list)


class ExecutionFailure(BaseModel):
    type: str
    message: str
    severity: str
    expected_element: str | None = None
    selector: str | None = None
    available_context: dict | None = None
    step_id: str | None = None
    action: str | None = None
    target: str | None = None
    expected: str | None = None
    actual: str | None = None
    exception_type: str | None = None
    current_url: str | None = None
    page_title: str | None = None
    planner_source: str | None = None
    screenshot_path: str | None = None
    assertion_results: list[AssertionResult] = Field(default_factory=list)
    website_context_summary: dict | None = None
    timestamp: str | None = None
    category: str | None = None
    user_message: str | None = None


class PlannerMetadata(BaseModel):
    planner_source: str
    planner_version: str
    context_version: str
    generated_at: str
    validation_score: float
    planning_time_ms: int
    provider: str | None = None
    context_refreshes: int = 0
    pages_visited: list[str] = Field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    planner_confidence: float | None = None
    planner_confidence_label: str | None = None
    detected_website_type: str | None = None
    detected_intent: str | None = None
    primary_navigation: list[str] = Field(default_factory=list)
    planner_strategy: str | None = None
    generated_journey: list[str] = Field(default_factory=list)
    website_type: str | None = None
    business_domain: str | None = None
    primary_goal: str | None = None
    target_audience: str | None = None
    recommended_test_flow: list[str] = Field(default_factory=list)
    high_risk_areas: list[str] = Field(default_factory=list)
    testing_priority: list[str] = Field(default_factory=list)
    analysis_confidence: float | None = None
    analysis_reasoning: str | None = None
    testing_strategy: str | None = None
    confidence_breakdown: dict | None = None
    coverage_report: dict | None = None
    execution_priority: list[str] = Field(default_factory=list)
    strategy_reasoning: str | None = None
    estimated_coverage_percent: float | None = None


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
    ai_plan_metadata: PlannerMetadata | None = None
    website_context_summary: dict | None = None
    viewport: str | None = None
    browser: str | None = None
    screenshot_captured_at: str | None = None
    evidence_package: dict | None = None
    diagnosis_report: dict | None = None
    execution_intelligence: dict | None = None
