"""핵심 schema 모델 테스트."""

from datetime import UTC, date, datetime

import pytest

from pnp_digest.domain import (
    AudienceExplanation,
    DocumentRecord,
    DocumentType,
    EvidenceSnippet,
    PaperMetadata,
    PipelineRun,
    SummaryPayload,
)


def test_document_record_requires_matching_metadata_type() -> None:
    """document_type과 metadata_type이 다르면 검증에 실패해야 한다."""

    with pytest.raises(ValueError):
        DocumentRecord(
            document_id="paper:doi:test",
            document_type=DocumentType.PAPER,
            canonical_title="Sample Title",
            abstract_text="Sample",
            publication_date=date(2026, 4, 1),
            language="en",
            canonical_url="https://example.invalid/paper",
            source_record_ids=["raw-1"],
            fingerprint="abc123",
            dedup_candidate_keys=["doi:test"],
            metadata={
                "metadata_type": "patent",
                "patent_number": "SAMPLE-US-1",
                "application_number": "SAMPLE-APP-1",
                "jurisdiction": "US",
                "applicants": [],
                "assignees": [],
                "inventors": [],
                "filing_date": "2026-01-01",
                "publication_date": "2026-03-01",
                "grant_date": None,
                "cpc_codes": [],
                "ipc_codes": [],
                "family_id": None,
            },
        )


def test_document_record_accepts_matching_string_document_type() -> None:
    """문자열로 역직렬화된 document_type도 metadata와 일치하면 허용해야 한다."""

    record = DocumentRecord(
        document_id="paper:doi:test",
        document_type="paper",
        canonical_title="Sample Title",
        abstract_text="Sample",
        publication_date=date(2026, 4, 1),
        language="en",
        canonical_url="https://example.invalid/paper",
        source_record_ids=["raw-1"],
        fingerprint="abc123",
        dedup_candidate_keys=["doi:test"],
        metadata=PaperMetadata(
            doi="10.0000/sample",
            authors=["Tester"],
            venue="Fixture Venue",
            publisher="Fixture Publisher",
            publication_type="journal",
            license="fixture",
            pdf_url="https://example.invalid/sample.pdf",
        ),
    )

    assert record.document_type == "paper"


def test_summary_payload_requires_evidence() -> None:
    """SummaryPayload는 최소 하나 이상의 evidence를 가져야 한다."""

    explanation = AudienceExplanation(
        purpose="온보딩",
        audience_focus=["핵심 개념"],
        explanation_text="설명",
        key_points=["포인트"],
        cautions=[],
        action_prompt=None,
    )

    with pytest.raises(ValueError):
        SummaryPayload(
            background_context="배경",
            problem_statement="문제",
            purpose="목적",
            core_idea="핵심",
            expected_effect="효과",
            limitations_or_unknowns=[],
            evidence_links_or_snippets=[],
            entry_level_explanation=explanation,
            manager_level_explanation=explanation,
            director_level_explanation=explanation,
            summary_confidence=0.8,
            human_review_notes=None,
        )


def test_pipeline_run_serializes_stage_status_keys() -> None:
    """PipelineRun은 enum key를 포함한 stage 상태를 직렬화할 수 있어야 한다."""

    run = PipelineRun(
        run_id="phase0-sample",
        domain="cmos_image_sensor",
        week_start=date(2026, 3, 30),
        started_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
        operator="tester",
        config_version="phase0-default",
    )

    dumped = run.model_dump(mode="json")
    assert dumped["run_id"] == "phase0-sample"
