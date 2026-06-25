from fastapi import APIRouter

from app.schemas import RunTestRequest, RunTestResponse
from app.services.playwright_runner import run_test as execute_test

router = APIRouter(tags=["run"])


@router.post("/run", response_model=RunTestResponse)
async def run_test(payload: RunTestRequest) -> RunTestResponse:
    result = await execute_test(str(payload.url), payload.goal)
    return RunTestResponse(**result)
