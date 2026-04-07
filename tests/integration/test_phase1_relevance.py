"""Phase 1 규칙 기반 관련성 판정 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    DocumentRecord,
    DocumentType,
    ManualReviewManifest,
    NormalizedArtifact,
    PaperMetadata,
    PipelineRun,
    RelevanceArtifact,
    RelevanceDecision,
)
from pnp_digest.services.io import read_model, write_model


runner = CliRunner()


def _build_paper_document(document_id: str, title: str, abstract_text: str) -> DocumentRecord:
    """테스트용 논문 문헌을 생성한다."""

    return DocumentRecord(
        document_id=document_id,
        document_type=DocumentType.PAPER,
        canonical_title=title,
        abstract_text=abstract_text,
        publication_date=date(2026, 4, 1),
        language="en",
        canonical_url=f"https://example.invalid/{document_id}",
        source_record_ids=[f"raw-{document_id}"],
        fingerprint=f"fingerprint-{document_id}",
        dedup_candidate_keys=[f"title_hash:{document_id}"],
        metadata=PaperMetadata(
            doi=f"10.0000/{document_id}",
            authors=["Tester"],
            venue="Fixture Venue",
            publisher="Fixture Publisher",
            publication_type="journal",
            license="fixture",
            pdf_url=f"https://example.invalid/{document_id}.pdf",
        ),
    )


def test_assess_relevance_cli_creates_report_and_manual_manifest(tmp_path: Path) -> None:
    """관련/경계/비관련 샘플에 대해 판정 결과와 수동 검토 manifest를 생성해야 한다."""

    run = PipelineRun(
        run_id="phase1-relevance",
        domain="cmos_image_sensor",
        week_start=date(2026, 3, 30),
        started_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
        operator="tester",
        config_version="phase1-default",
    )

    relevant_doc = _build_paper_document(
        document_id="paper:doi:relevant",
        title="Low-noise CMOS image sensor with backside illumination",
        abstract_text="Stacked CIS readout chain with quantum efficiency enhancement",
    )
    borderline_doc = _build_paper_document(
        document_id="paper:doi:borderline",
        title="Readout chain optimization for mixed-signal camera front-end",
        abstract_text="Synthetic fixture only.",
    )
    not_relevant_doc = _build_paper_document(
        document_id="paper:doi:not-relevant",
        title="Battery electrode interface for lithium plating stability",
        abstract_text="Cathode and anode balancing in electrolyte system",
    )

    normalized_artifact = NormalizedArtifact(
        run=run,
        documents=[relevant_doc, borderline_doc, not_relevant_doc],
    )
    normalized_path = tmp_path / "artifacts" / "runs" / run.run_id / "normalize" / "normalized_artifact.json"
    write_model(normalized_path, normalized_artifact)

    result = runner.invoke(
        app,
        [
            "assess-relevance",
            "--run-id",
            run.run_id,
            "--normalized-artifact",
            str(normalized_path),
            "--artifact-root",
            str(tmp_path / "artifacts" / "runs"),
            "--dictionary-dir",
            "data/dictionaries",
        ],
    )
    assert result.exit_code == 0

    stage_dir = tmp_path / "artifacts" / "runs" / run.run_id / "assess_relevance"
    report = read_model(stage_dir / "relevance_report.json", RelevanceArtifact)
    manifest = read_model(stage_dir / "manual_review_manifest.json", ManualReviewManifest)

    assert len(report.assessments) == 3

    decisions = {assessment.document_id: assessment.final_decision for assessment in report.assessments}
    assert decisions["paper:doi:relevant"] == RelevanceDecision.RELEVANT
    assert decisions["paper:doi:borderline"] == RelevanceDecision.BORDERLINE
    assert decisions["paper:doi:not-relevant"] == RelevanceDecision.NOT_RELEVANT

    for assessment in report.assessments:
        assert assessment.evidence_links_or_snippets, "근거 snippet은 비어 있으면 안 된다."

    assert len(manifest.items) == 1
    assert manifest.items[0].document_id == "paper:doi:borderline"
