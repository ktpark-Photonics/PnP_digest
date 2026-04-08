"""Phase 2 특허 검증 통합 테스트."""

import csv
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    ReviewStatus,
    VerificationArtifact,
    VerificationReport,
    VerificationReviewManifest,
    VerificationReviewResolutionArtifact,
    VerificationResult,
    VerificationStatus,
)
from pnp_digest.services.io import read_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "phase2-patent-verify"
runner = CliRunner()


def _run_verify(
    tmp_path: Path,
    provider: str,
    provider_data_name: str,
) -> tuple[VerificationArtifact, VerificationReviewManifest | None]:
    """verify CLI를 실행하고 artifact를 읽는다."""

    artifact_root = tmp_path / "artifacts" / "runs"
    normalized_artifact = PROJECT_ROOT / "data" / "sample_inputs" / "phase2_patent_verify_normalized_fixture.json"
    provider_data = PROJECT_ROOT / "data" / "sample_inputs" / provider_data_name

    result = runner.invoke(
        app,
        [
            "verify",
            "--run-id",
            RUN_ID,
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

    artifact_path = artifact_root / RUN_ID / "verify" / "verification_report.json"
    manifest_path = artifact_root / RUN_ID / "verify" / "verification_review_manifest.json"
    assert artifact_path.exists()

    manifest = None
    if manifest_path.exists():
        manifest = read_model(manifest_path, VerificationReviewManifest)
    return read_model(artifact_path, VerificationArtifact), manifest


def _report_map(artifact: VerificationArtifact) -> dict[str, VerificationReport]:
    """문헌 ID 기준 report map을 만든다."""

    return {report.document_id: report for report in artifact.reports}


def _field_map(report: VerificationReport) -> dict[str, VerificationResult]:
    """verification_field 기준 결과 map을 만든다."""

    return {result.verification_field: result for result in report.results}


def _review_manifest_path(tmp_path: Path) -> Path:
    """verify 단계 review manifest 경로를 반환한다."""

    return (
        tmp_path
        / "artifacts"
        / "runs"
        / RUN_ID
        / "verify"
        / "verification_review_manifest.json"
    )


def _review_csv_path(tmp_path: Path) -> Path:
    """review export CSV 경로를 반환한다."""

    return (
        tmp_path
        / "artifacts"
        / "runs"
        / RUN_ID
        / "verify"
        / "verification_review_manifest.csv"
    )


def _write_review_csv_updates(
    csv_path: Path,
    updates: dict[str, dict[str, str]],
) -> None:
    """export된 CSV에 reviewer 입력값을 반영한다."""

    with csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    for row in rows:
        row.update(updates.get(row["document_id"], {}))

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_verify_cli_with_mock_provider_supports_match_partial_and_mismatch(tmp_path: Path) -> None:
    """mock provider는 완전 일치/부분 일치/불일치/존재 실패 기본 동작을 생성해야 한다."""

    artifact, review_manifest = _run_verify(
        tmp_path=tmp_path,
        provider="mock",
        provider_data_name="phase2_patent_verification_mock_fixture.json",
    )
    assert len(artifact.reports) == 4
    assert artifact.run.stage_status["verify"].artifact_path.endswith("verification_report.json")
    assert review_manifest is not None
    review_items = {item.document_id: item for item in review_manifest.items}
    assert "patent:number:sample-us-match-001-a1" not in review_items
    assert "patent:number:sample-us-partial-001-a1" in review_items
    assert "patent:number:sample-us-mismatch-001-a1" in review_items
    assert "patent:number:sample-us-manual-001-a1" in review_items
    assert review_items["patent:number:sample-us-partial-001-a1"].provider_name == "mock"
    assert review_items["patent:number:sample-us-partial-001-a1"].overall_pass is False
    assert review_items["patent:number:sample-us-partial-001-a1"].source_artifact_path.endswith("verification_report.json")
    assert review_items["patent:number:sample-us-partial-001-a1"].recommended_action
    assert review_items["patent:number:sample-us-partial-001-a1"].flagged_fields
    assert "title" in review_items["patent:number:sample-us-partial-001-a1"].flagged_fields
    assert "title" in review_items["patent:number:sample-us-mismatch-001-a1"].flagged_fields
    assert "patent_existence" in review_items["patent:number:sample-us-manual-001-a1"].flagged_fields

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

    artifact, review_manifest = _run_verify(
        tmp_path=tmp_path,
        provider="manual",
        provider_data_name="phase2_patent_verification_manual_fixture.json",
    )
    reports = _report_map(artifact)
    assert review_manifest is not None
    review_items = {item.document_id: item for item in review_manifest.items}

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
    assert "patent:number:sample-us-manual-001-a1" in review_items
    assert "applicant_or_assignee" in review_items["patent:number:sample-us-manual-001-a1"].flagged_fields
    assert "summary" in review_items["patent:number:sample-us-manual-001-a1"].flagged_fields


def test_review_export_cli_writes_csv_from_verification_manifest(tmp_path: Path) -> None:
    """review export는 verification review manifest를 CSV로 내보내야 한다."""

    _, review_manifest = _run_verify(
        tmp_path=tmp_path,
        provider="mock",
        provider_data_name="phase2_patent_verification_mock_fixture.json",
    )
    assert review_manifest is not None

    manifest_path = _review_manifest_path(tmp_path)
    result = runner.invoke(
        app,
        [
            "review",
            "export",
            "--verification-review-manifest",
            str(manifest_path),
        ],
    )
    assert result.exit_code == 0

    output_path = _review_csv_path(tmp_path)
    assert output_path.exists()

    with output_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert [row["document_id"] for row in rows] == [
        "patent:number:sample-us-manual-001-a1",
        "patent:number:sample-us-mismatch-001-a1",
        "patent:number:sample-us-partial-001-a1",
    ]
    assert all(row["flagged_fields"] for row in rows)
    assert rows[0]["existence_status"] == VerificationStatus.MISSING
    assert "patent_existence" in rows[0]["flagged_fields"]
    assert rows[1]["provider_name"] == "mock"
    assert rows[0]["review_status"] == ""
    assert rows[0]["reviewer"] == ""
    assert rows[0]["review_notes"] == ""
    assert rows[0]["resolved_fields"] == ""


def test_review_export_cli_writes_markdown_with_explicit_output_path(tmp_path: Path) -> None:
    """review export는 Markdown 형식과 사용자 지정 출력 경로를 지원해야 한다."""

    _, review_manifest = _run_verify(
        tmp_path=tmp_path,
        provider="manual",
        provider_data_name="phase2_patent_verification_manual_fixture.json",
    )
    assert review_manifest is not None

    manifest_path = _review_manifest_path(tmp_path)
    output_path = tmp_path / "exports" / "verification_review_manifest.md"
    result = runner.invoke(
        app,
        [
            "review",
            "export",
            "--verification-review-manifest",
            str(manifest_path),
            "--format",
            "markdown",
            "--output-path",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "# Verification Review Manifest" in content
    assert f"- run_id: {RUN_ID}" in content
    assert "| document_id | provider_name | existence_status | flagged_fields | overall_pass | review_reason | recommended_action | source_artifact_path |" in content
    assert "patent:number:sample-us-match-001-a1" not in content
    assert "patent:number:sample-us-manual-001-a1" in content
    assert "applicant_or_assignee" in content


def test_review_import_cli_creates_resolution_artifact_from_review_csv(tmp_path: Path) -> None:
    """review import는 사람이 수정한 CSV를 JSON artifact로 반영해야 한다."""

    _, review_manifest = _run_verify(
        tmp_path=tmp_path,
        provider="mock",
        provider_data_name="phase2_patent_verification_mock_fixture.json",
    )
    assert review_manifest is not None

    manifest_path = _review_manifest_path(tmp_path)
    export_result = runner.invoke(
        app,
        [
            "review",
            "export",
            "--verification-review-manifest",
            str(manifest_path),
        ],
    )
    assert export_result.exit_code == 0

    review_csv_path = _review_csv_path(tmp_path)
    _write_review_csv_updates(
        review_csv_path,
        {
            "patent:number:sample-us-manual-001-a1": {
                "review_status": ReviewStatus.REJECTED,
                "reviewer": "qa-user",
                "review_notes": "존재 여부를 재확인할 때까지 제외",
                "resolved_fields": "",
            },
            "patent:number:sample-us-mismatch-001-a1": {
                "review_status": ReviewStatus.MANUAL_REVIEW_REQUIRED,
                "reviewer": "qa-user",
                "review_notes": "원문 대조 필요",
                "resolved_fields": "title",
            },
            "patent:number:sample-us-partial-001-a1": {
                "review_status": ReviewStatus.APPROVED,
                "reviewer": "qa-user",
                "review_notes": "부분 일치 확인 후 승인",
                "resolved_fields": "title | applicant_or_assignee | summary",
            },
        },
    )

    artifact_root = tmp_path / "artifacts" / "runs"
    import_result = runner.invoke(
        app,
        [
            "review",
            "import",
            "--verification-review-manifest",
            str(manifest_path),
            "--review-csv",
            str(review_csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    imported_artifact_path = artifact_root / RUN_ID / "review" / "verification_review_resolution.json"
    assert imported_artifact_path.exists()

    imported_artifact = read_model(imported_artifact_path, VerificationReviewResolutionArtifact)
    assert imported_artifact.run_id == RUN_ID
    assert imported_artifact.source_manifest_path.endswith("verification_review_manifest.json")
    assert imported_artifact.imported_csv_path.endswith("verification_review_manifest.csv")
    assert len(imported_artifact.items) == 3

    imported_items = {item.document_id: item for item in imported_artifact.items}
    assert imported_items["patent:number:sample-us-manual-001-a1"].review_status == ReviewStatus.REJECTED
    assert imported_items["patent:number:sample-us-manual-001-a1"].review_notes == "존재 여부를 재확인할 때까지 제외"
    assert imported_items["patent:number:sample-us-mismatch-001-a1"].review_status == ReviewStatus.MANUAL_REVIEW_REQUIRED
    assert imported_items["patent:number:sample-us-mismatch-001-a1"].resolved_fields == ["title"]
    assert imported_items["patent:number:sample-us-partial-001-a1"].review_status == ReviewStatus.APPROVED
    assert imported_items["patent:number:sample-us-partial-001-a1"].resolved_fields == [
        "title",
        "applicant_or_assignee",
        "summary",
    ]
