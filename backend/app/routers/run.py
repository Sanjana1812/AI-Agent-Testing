from fastapi import APIRouter, HTTPException

from app.schemas import RunTestRequest, RunTestResponse
from app.services.playwright_runner import PlaywrightRunError, run_test as execute_test

router = APIRouter(tags=["run"])

ERROR_STATUS_CODES = {
    "timeout": 504,
    "invalid_url": 400,
    "browser_launch_failure": 503,
    "execution_error": 500,
}


@router.post("/run", response_model=RunTestResponse)
async def run_test(payload: RunTestRequest) -> RunTestResponse:
    try:
        result = await execute_test(str(payload.url), payload.goal)
        return RunTestResponse(**result)
    except PlaywrightRunError as exc:
        status_code = ERROR_STATUS_CODES.get(exc.error_type, 500)
        raise HTTPException(status_code=status_code, detail=exc.message) from exc
