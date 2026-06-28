import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RunTestRequest, RunTestResponse
from app.services.failures.failure_enricher import enrich_failures
from app.services.planner.context_index import ContextIndex
from app.services.playwright_runner import run_test as execute_test
from app.services.run_persistence import RunPersistenceService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["run"])


@router.post("/run", response_model=RunTestResponse)
async def run_test(payload: RunTestRequest, db: Session = Depends(get_db)) -> RunTestResponse:
    result = await execute_test(str(payload.url), payload.goal)

    website_context = result.pop("_website_context", {})
    source_url = result.pop("_source_url", str(payload.url))
    context_summary = ContextIndex(website_context).summary() if website_context else None
    result["failures"] = enrich_failures(result, context_summary)

    persisted = RunPersistenceService(db).persist(
        result=result,
        website_context=website_context,
        source_url=source_url,
    )
    if persisted is None:
        logger.warning("[Run] Execution completed but persistence failed for run %s", result.get("id"))

    return RunTestResponse(**result)
