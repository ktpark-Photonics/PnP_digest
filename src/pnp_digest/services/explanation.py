"""summary 결과를 explain artifact로 변환하는 유틸리티."""

from __future__ import annotations

from pnp_digest.domain.models import ExplainRecord, SummaryRecord


def build_explain_record(summary_record: SummaryRecord) -> ExplainRecord:
    """summary record를 explain stage용 레코드로 변환한다."""

    return ExplainRecord(
        document_id=summary_record.document_id,
        document_type=summary_record.document_type,
        document_title=summary_record.document_title,
        source_review_status=summary_record.source_review_status,
        summary_confidence=summary_record.summary.summary_confidence,
        entry_level_explanation=summary_record.summary.entry_level_explanation,
        manager_level_explanation=summary_record.summary.manager_level_explanation,
        director_level_explanation=summary_record.summary.director_level_explanation,
        human_review_notes=summary_record.summary.human_review_notes,
    )
