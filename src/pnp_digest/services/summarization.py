"""placeholder 기반 summarize 유틸리티."""

from __future__ import annotations

from pnp_digest.domain import ReviewStatus
from pnp_digest.domain.models import (
    AudienceExplanation,
    DocumentRecord,
    EvidenceSnippet,
    SummaryPayload,
    SummaryRecord,
    VerificationReviewResolutionItem,
)

SUMMARY_SUPPORTED_FIELDS = [
    "background_context",
    "problem_statement",
    "purpose",
    "core_idea",
    "expected_effect",
]


def _build_evidence(document: DocumentRecord) -> list[EvidenceSnippet]:
    """문헌 메타데이터 기반 최소 evidence snippet을 생성한다."""

    has_abstract = bool(document.abstract_text)
    return [
        EvidenceSnippet(
            source_url=document.canonical_url,
            locator="abstract" if has_abstract else "title",
            snippet_text=document.abstract_text or document.canonical_title,
            supports_fields=SUMMARY_SUPPORTED_FIELDS,
        )
    ]


def _build_audience_explanation(
    *,
    title: str,
    detail: str,
    audience_label: str,
) -> AudienceExplanation:
    """직급별 placeholder 설명 블록을 생성한다."""

    return AudienceExplanation(
        purpose=f"{audience_label} 관점에서 문헌 핵심을 빠르게 공유한다.",
        audience_focus=["핵심 아이디어", "후속 검토 포인트"],
        explanation_text=f"{title} 문헌의 현재 요약 초안은 {detail}",
        key_points=[title, detail],
        cautions=["현재 단계는 placeholder 기반 요약이며 후속 보강이 필요하다."],
        action_prompt="원문과 수동 검토 메모를 함께 확인해 후속 설명을 보강한다.",
    )


def build_summary_record(
    document: DocumentRecord,
    review_resolution: VerificationReviewResolutionItem,
) -> SummaryRecord:
    """승인된 문헌에 대한 placeholder 요약 레코드를 생성한다."""

    if review_resolution.review_status != ReviewStatus.APPROVED:
        raise ValueError("summary 생성 대상은 approved review 결과여야 합니다.")

    title = document.canonical_title
    abstract_text = document.abstract_text or f"{title} 문헌의 상세 초록이 없어 제목 기반으로 요약을 시작한다."
    detail = abstract_text if document.abstract_text else "초록이 없어 제목과 검토 메모를 기반으로 구성된 상태다."

    summary = SummaryPayload(
        background_context=f"{title} 문헌은 verification review에서 승인되어 summarize 단계로 전달되었다.",
        problem_statement="현재 구현은 원문 전체 파싱 없이 검토 완료 문헌만 선별해 placeholder 요약을 생성한다.",
        purpose=abstract_text,
        core_idea=abstract_text,
        expected_effect=f"{title} 문헌의 핵심 포인트를 후속 explain/render 단계에서 재사용할 수 있다.",
        limitations_or_unknowns=[
            "현재 Phase 3 첫 구현으로 placeholder 기반 요약만 제공한다.",
        ],
        evidence_links_or_snippets=_build_evidence(document),
        entry_level_explanation=_build_audience_explanation(
            title=title,
            detail=detail,
            audience_label="신입",
        ),
        manager_level_explanation=_build_audience_explanation(
            title=title,
            detail="검토 승인된 초록 기반 핵심을 빠르게 파악할 수 있는 상태다.",
            audience_label="과장",
        ),
        director_level_explanation=_build_audience_explanation(
            title=title,
            detail="배치형 후속 단계 연결을 위한 승인 문헌 요약 초안 상태다.",
            audience_label="부장",
        ),
        summary_confidence=0.55 if document.abstract_text else 0.35,
        human_review_notes=review_resolution.review_notes,
    )
    return SummaryRecord(
        document_id=document.document_id,
        document_type=document.document_type,
        document_title=document.canonical_title,
        source_review_status=review_resolution.review_status,
        summary=summary,
    )
