"""Phase 5.1 final release review 통합 테스트."""

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    ApprovalStatus,
    OutputBundle,
    OutputType,
    PipelineRun,
    ReleaseManifest,
    ReleaseReviewResolutionArtifact,
    ReviewStage,
    ReviewStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase51-release-review-fixture"
runner = CliRunner()


def _build_release_manifest() -> ReleaseManifest:
    """최종 배포 검토 입력용 release manifest fixture를 생성한다."""

    return ReleaseManifest(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase51-default",
        ),
        source_render_artifact_path="artifacts/runs/phase51-release-review-fixture/render/render_artifact.json",
        bundles=[
            OutputBundle(
                bundle_id=f"{RUN_ID}:markdown-brief",
                run_id=RUN_ID,
                output_type=OutputType.MARKDOWN,
                template_version="phase4-markdown-v1",
                included_document_ids=["patent:number:sample-us-partial-001-a1"],
                output_path="artifacts/runs/phase51-release-review-fixture/render/brief.md",
                approval_status=ApprovalStatus.APPROVED,
            ),
            OutputBundle(
                bundle_id=f"{RUN_ID}:pptx-brief",
                run_id=RUN_ID,
                output_type=OutputType.PPTX,
                template_version="phase4-pptx-v1",
                included_document_ids=["patent:number:sample-us-partial-001-a1"],
                output_path="artifacts/runs/phase51-release-review-fixture/render/brief.pptx",
                approval_status=ApprovalStatus.DRAFT,
            ),
        ],
        approved_bundle_ids=[f"{RUN_ID}:markdown-brief"],
        approved_output_paths=["artifacts/runs/phase51-release-review-fixture/render/brief.md"],
        release_notes=["최종 배포 전 reviewer signoff 필요"],
        review_signoff=ReviewStatus.PENDING,
        distribution_targets=["internal", "archive"],
        generated_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
        published_at=None,
    )


def test_review_release_export_creates_csv_template(tmp_path: Path) -> None:
    """review release-export는 final release review용 CSV 템플릿을 생성해야 한다."""

    release_manifest_path = tmp_path / "release_manifest.json"
    write_model(release_manifest_path, _build_release_manifest())

    result = runner.invoke(
        app,
        [
            "review",
            "release-export",
            "--release-manifest",
            str(release_manifest_path),
        ],
    )
    assert result.exit_code == 0

    csv_path = tmp_path / "release_manifest.csv"
    assert csv_path.exists()

    csv_text = csv_path.read_text(encoding="utf-8")
    assert "review_signoff" in csv_text
    assert "mark_published" in csv_text
    assert f"{RUN_ID}:markdown-brief" in csv_text
    assert "internal | archive" in csv_text


def test_review_release_import_creates_resolution_artifact(tmp_path: Path) -> None:
    """review release-import는 reviewer가 확정한 signoff를 JSON artifact로 저장해야 한다."""

    release_manifest_path = tmp_path / "release_manifest.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(release_manifest_path, _build_release_manifest())

    export_result = runner.invoke(
        app,
        [
            "review",
            "release-export",
            "--release-manifest",
            str(release_manifest_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = tmp_path / "release_manifest.csv"
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        fieldnames = rows[0].keys()

    rows[0]["review_signoff"] = "approved"
    rows[0]["reviewer"] = "qa-user"
    rows[0]["review_notes"] = "최종 배포 승인"
    rows[0]["mark_published"] = "true"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    import_result = runner.invoke(
        app,
        [
            "review",
            "release-import",
            "--release-manifest",
            str(release_manifest_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "release_review_resolution.json"
    assert resolution_path.exists()

    artifact = read_model(resolution_path, ReleaseReviewResolutionArtifact)
    assert artifact.review_stage == ReviewStage.FINAL_RELEASE
    assert artifact.review_signoff == ReviewStatus.APPROVED
    assert artifact.reviewer == "qa-user"
    assert artifact.review_notes == "최종 배포 승인"
    assert artifact.approved_bundle_ids == [f"{RUN_ID}:markdown-brief"]
    assert artifact.approved_output_paths == [
        "artifacts/runs/phase51-release-review-fixture/render/brief.md"
    ]
    assert artifact.distribution_targets == ["internal", "archive"]
    assert artifact.release_notes == ["최종 배포 전 reviewer signoff 필요"]
    assert artifact.published_at is not None
