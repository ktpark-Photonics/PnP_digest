"""Phase 2 특허 검증 통합 테스트."""

from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    VerificationArtifact,
    VerificationReport,
    VerificationResult,
    VerificationStatus,
)
from pnp_digest.services.io import read_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _run_verify(tmp_path: Path, provider: str, provider_data_name: str) -> VerificationArtifact:
    """verify CLI를 실행하고 artifact를 읽는다."""

    run_id = "phase2-patent-verify"
    artifact_root = tmp_path / "artifacts" / "runs"
    normalized_artifact = PROJECT_ROOT / "data" / "sample_inputs" / "phase2_patent_verify_normalized_fixture.json"
    provider_data = PROJECT_ROOT / "data" / "sample_inputs" / provider_data_name

    result = runner.invoke(
        app,
        [
            "verify",
            "--run-id",
            run_id,
            "--normalized-artifact",
            str(normalized_artifact),
            "--artifact-root",
            str(artifact_root),
            "--provider",
            provider,
            "--provider-data",
            str(provider_data),
        ],
    )
    assert result.exit_code == 0

    artifact_path = artifact_root / run_id / "verify" / "verification_report.json"
    assert artifact_path.exists()
    return read_model(artifact_path, VerificationArtifact)


def _report_map(artifact: VerificationArtifact) -> dict[str, VerificationReport]:
    """문헌 ID 기준 report map을 만든다."""

    return {report.document_id: report for report in artifact.reports}


def _field_map(report: VerificationReport) -> dict[str, VerificationResult]:
    """verification_field 기준 결과 map을 만든다."""

    return {result.verification_field: result for result in report.results}


def test_verify_cli_with_mock_provider_supports_match_partial_and_mismatch(tmp_path: Path) -> None:
    """mock provider는 완전 일치/부분 일치/불일치/존재 실패 기본 동작을 생성해야 한다."""

    artifact = _run_verify(
        tmp_path=tmp_path,
        provider="mock",
        provider_data_name="phase2_patent_verification_mock_fixture.json",
    )
    assert len(artifact.reports) == 4
    assert artifact.run.stage_status["verify"].artifact_path.endswith("verification_report.json")

    reports = _report_map(artifact)

    match_report = reports["patent:number:sample-us-match-001-a1"]
    assert match_report.provider_name == "mock"
    assert match_report.existence_check.verification_field == "patent_existence"
    assert match_report.existence_check.status == VerificationStatus.MATCHED
    assert match_report.overall_pass is True
    assert match_report.review_required is False
    assert all(result.status == VerificationStatus.MATCHED for result in match_report.results)

    partial_report = reports["patent:number:sample-us-partial-001-a1"]
    partial_fields = _field_map(partial_report)
    assert partial_report.existence_check.status == VerificationStatus.MATCHED
    assert partial_report.overall_pass is False
    assert partial_report.review_required is True
    assert partial_fields["title"].status == VerificationStatus.PARTIALLY_MATCHED
    assert partial_fields["applicant_or_assignee"].status == VerificationStatus.PARTIALLY_MATCHED
    assert partial_fields["summary"].status == VerificationStatus.PARTIALLY_MATCHED

    mismatch_report = reports["patent:number:sample-us-mismatch-001-a1"]
    mismatch_fields = _field_map(mismatch_report)
    assert mismatch_report.existence_check.status == VerificationStatus.MATCHED
    assert mismatch_report.review_required is True
    assert mismatch_fields["title"].status == VerificationStatus.MISMATCHED
    assert mismatch_fields["filing_date"].status == VerificationStatus.MISMATCHED
    assert mismatch_fields["publication_date"].status == VerificationStatus.MISMATCHED

    missing_report = reports["patent:number:sample-us-manual-001-a1"]
    assert missing_report.existence_check.status == VerificationStatus.MISSING
    assert all(result.status == VerificationStatus.NOT_CHECKED for result in missing_report.results)


def test_verify_cli_with_manual_provider_supports_manual_review(tmp_path: Path) -> None:
    """manual provider는 수동 검토 필요 상태를 그대로 artifact에 반영해야 한다."""

    artifact = _run_verify(
        tmp_path=tmp_path,
        provider="manual",
        provider_data_name="phase2_patent_verification_manual_fixture.json",
    )
    reports = _report_map(artifact)

    manual_report = reports["patent:number:sample-us-manual-001-a1"]
    manual_fields = _field_map(manual_report)

    assert manual_report.provider_name == "manual"
    assert manual_report.existence_check.status == VerificationStatus.MATCHED
    assert manual_report.overall_pass is False
    assert manual_report.review_required is True
    assert manual_fields["applicant_or_assignee"].status == VerificationStatus.MANUAL_REVIEW_REQUIRED
    assert manual_fields["summary"].status == VerificationStatus.MANUAL_REVIEW_REQUIRED
    assert manual_fields["applicant_or_assignee"].expected_value == "Vision Fixture Co."
    assert manual_fields["applicant_or_assignee"].observed_value is None
    assert manual_fields["summary"].evidence_text == "요약 근거가 불충분함"
