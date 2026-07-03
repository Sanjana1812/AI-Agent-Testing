"""Evidence Foundation — structured packages for AI diagnosis (Sprint 4.1B)."""

from app.services.evidence.collector import (
    EvidenceCollector,
    build_evidence_package,
    collect_evidence_for_run,
)
from app.services.evidence.models import EVIDENCE_VERSION, EvidencePackage, FailureEvidence
from app.services.evidence.serializer import evidence_package_to_json, serialize_evidence_package
from app.services.evidence.snapshot import ExecutionEvidenceBuffer

__all__ = [
    "EVIDENCE_VERSION",
    "EvidenceCollector",
    "EvidencePackage",
    "ExecutionEvidenceBuffer",
    "FailureEvidence",
    "build_evidence_package",
    "collect_evidence_for_run",
    "evidence_package_to_json",
    "serialize_evidence_package",
]
