"""Phase 3 summarize 통합 테스트."""

from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    ReviewStatus,
    SummaryArtifact,
    VerificationReviewResolutionArtifact,
    VerificationReviewResolutionItem,
    VerificationStatus,
)
from pnp_digest.services.io import read_model, write_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "phase2-patent-verify"
runner = CliRunner()


def _build_review_resolution_artifact() -> VerificationReviewResolutionArtifact:
    """승인/보류/거절이 섞인 verification review resolution fixture를 만든다."""

    return VerificationReviewResolutionArtifact(
        run_id=RUN_ID,
        source_manifest_path="artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.json",
        imported_csv_path="artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.csv",
        imported_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
        items=[
            VerificationReviewResolutionItem(
                document_id="patent:number:sample-us-match-001-a1",
                provider_name="manual",
                existence_status=VerificationStatus.MATCHED,
                flagged_fields=["title"],
                review_status=ReviewStatus.APPROVED,
                reviewer="qa-user",
                review_notes="초록과 제목 일치 확인 후 summarize 승인",
                resolved_fields=["title"],
                review_reason="partially_matched=title",
                source_artifact_path="artifacts/runs/phase2-patent-verify/verify/verification_report.json",
            ),
            VerificationReviewResolutionItem(
                document_id="patent:number:sample-us-mismatch-001-a1",
                provider_name="manual",
                existence_status=VerificationStatus.MATCHED,
                flagged_fields=["title", "summary"],
                review_status=ReviewStatus.REJECTED,
                reviewer="qa-user",
                review_notes="불일치가 커서 제외",
                resolved_fields=[],
                review_reason="mismatched=title,summary",
                source_artifact_path="artifacts/runs/phase2-patent-verify/verify/verification_report.json",
            ),
            VerificationReviewResolutionItem(
                document_id="patent:number:sample-us-partial-001-a1",
                provider_name="manual",
                existence_status=VerificationStatus.MATCHED,
                flagged_fields=["summary"],
                review_status=ReviewStatus.MANUAL_REVIEW_REQUIRED,
                reviewer="qa-user",
                review_notes="추가 원문 검토 필요",
                resolved_fields=[],
                review_reason="manual_review_required=summary",
                source_artifact_path="artifacts/runs/phase2-patent-verify/verify/verification_report.json",
            ),
        ],
    )


def test_summarize_cli_only_includes_approved_documents(tmp_path: Path) -> None:
    """summarize는 approved review 결과만 summary artifact에 포함해야 한다."""

    normalized_artifact = PROJECT_ROOT / "data" / "sample_inputs" / "phase2_patent_verify_normalized_fixture.json"
    review_resolution_path = tmp_path / "verification_review_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"

    write_model(review_resolution_path, _build_review_resolution_artifact())

    result = runner.invoke(
        app,
        [
            "summarize",
            "--run-id",
            RUN_ID,
            "--normalized-artifact",
            str(normalized_artifact),
            "--verification-review-resolution",
            str(review_resolution_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    summary_artifact_path = artifact_root / RUN_ID / "summarize" / "summary_artifact.json"
    assert summary_artifact_path.exists()

    artifact = read_model(summary_artifact_path, SummaryArtifact)
    assert artifact.run.stage_status["summarize"].artifact_path.endswith("summary_artifact.json")
    assert len(artifact.summaries) == 1

    summary_record = artifact.summaries[0]
    assert summary_record.document_id == "patent:number:sample-us-match-001-a1"
    assert summary_record.document_type == "patent"
    assert summary_record.source_review_status == ReviewStatus.APPROVED
    assert summary_record.summary.evidence_links_or_snippets
    assert summary_record.summary.human_review_notes == "초록과 제목 일치 확인 후 summarize 승인"
    assert "verification review에서 승인" in summary_record.summary.background_context
    assert summary_record.summary.summary_confidence > 0.0
