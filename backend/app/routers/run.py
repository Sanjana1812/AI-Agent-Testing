import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RunTestRequest, RunTestResponse
from app.services.failures.failure_enricher import enrich_failures
from app.services.planner.plan_presentation import build_website_analysis
from app.services.playwright_runner import run_test as execute_test
from app.services.run_persistence import RunPersistenceService
from app.services.evidence import build_evidence_package
from app.services.website_context.context_utils import is_context_empty
from app.services.diagnosis import build_diagnosis_report

logger = logging.getLogger(__name__)

router = APIRouter(tags=["run"])


@router.post("/run", response_model=RunTestResponse)
async def run_test(payload: RunTestRequest, db: Session = Depends(get_db)) -> RunTestResponse:
    try:
        result = await execute_test(str(payload.url), payload.goal)
    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt as exc:
        logger.warning("[Run] Test interrupted by server reload for %s", payload.url)
        raise HTTPException(
            status_code=503,
            detail="The server restarted while your test was running. Wait a few seconds and try again.",
        ) from exc
    except Exception as exc:
        logger.exception("[Run] Test execution failed for %s", payload.url)
        raise HTTPException(
            status_code=500,
            detail=f"Test execution failed: {exc}",
        ) from exc

    website_context = result.pop("_website_context", {})
    website_analysis = result.pop("_website_analysis", None)
    testing_strategy = result.pop("_testing_strategy", None)
    execution_evidence = result.pop("_execution_evidence", None)
    source_url = result.pop("_source_url", str(payload.url))
    context_extracted = not is_context_empty(website_context)
    context_summary = build_website_analysis(website_context, context_extracted=context_extracted) if website_context else None
    if context_summary and website_analysis and context_extracted:
        context_summary.update(
            {
                "website_type": website_analysis.get("website_type"),
                "business_domain": website_analysis.get("business_domain"),
                "primary_goal": website_analysis.get("primary_goal"),
                "target_audience": website_analysis.get("target_audience"),
                "recommended_test_flow": website_analysis.get("recommended_test_flow"),
                "critical_user_journeys": website_analysis.get("critical_user_journeys"),
                "high_risk_areas": website_analysis.get("high_risk_areas"),
                "testing_priority": website_analysis.get("testing_priority"),
                "analysis_confidence": website_analysis.get("confidence"),
                "analysis_reasoning": result.get("ai_plan_metadata", {}).get("analysis_reasoning")
                or website_analysis.get("reasoning"),
                "testing_strategy": result.get("ai_plan_metadata", {}).get("testing_strategy"),
                "confidence_breakdown": result.get("ai_plan_metadata", {}).get("confidence_breakdown"),
                "coverage_report": result.get("ai_plan_metadata", {}).get("coverage_report"),
                "execution_priority": result.get("ai_plan_metadata", {}).get("execution_priority"),
                "strategy_reasoning": result.get("ai_plan_metadata", {}).get("strategy_reasoning"),
                "estimated_coverage_percent": result.get("ai_plan_metadata", {}).get("estimated_coverage_percent"),
            }
        )
    elif context_summary and website_analysis and not context_extracted:
        context_summary["analysis_reasoning"] = website_analysis.get("reasoning")
    result["website_context_summary"] = context_summary
    result["failures"] = enrich_failures(result, context_summary)
    result["evidence_package"] = build_evidence_package(
        result,
        website_context=website_context,
        website_analysis=website_analysis,
        testing_strategy=testing_strategy,
        execution_evidence=execution_evidence,
        website_context_summary=context_summary,
    )
    result["diagnosis_report"] = build_diagnosis_report(
        result["evidence_package"],
        goal=payload.goal,
    )

    persisted = RunPersistenceService(db).persist(
        result=result,
        website_context=website_context,
        source_url=source_url,
    )
    if persisted is None:
        logger.warning("[Run] Execution completed but persistence failed for run %s", result.get("id"))

    try:
        return RunTestResponse(**result)
    except ValidationError as exc:
        logger.exception("[Run] Response validation failed for run %s", result.get("id"))
        raise HTTPException(
            status_code=500,
            detail="Test completed but response formatting failed. Check server logs.",
        ) from exc
