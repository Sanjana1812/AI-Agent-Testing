"""Evidence collection for failed test executions."""

from app.services.evidence.collector import EvidenceCollector, collect_evidence_for_run

__all__ = ["EvidenceCollector", "collect_evidence_for_run"]
