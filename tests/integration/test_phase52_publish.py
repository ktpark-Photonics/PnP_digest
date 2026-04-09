"""Phase 5.2 publish stub 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    ApprovalStatus,
    OutputBundle,
    OutputType,
    PipelineRun,
    PublishArtifact,
    PublishStatus,
    ReleaseReviewResolutionArtifact,
    ReviewStage,
    ReviewStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase52-publish-fixture"
runner = CliRunner()


def _build_release_review_resolution(*, approved: bool) -> ReleaseReviewResolutionArtifact:
    """publish 입력용 release review resolution fixture를 생성한다."""

    review_signoff = ReviewStatus.APPROVED if approved else ReviewStatus.PENDING
    published_at = datetime(2026, 4, 9, 12, 0, tzinfo=UTC) if approved else None

    return ReleaseReviewResolutionArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase52-default",
        ),
        run_id=RUN_ID,
        source_release_manifest_path="artifacts/runs/phase52-publish-fixture/release/release_manifest.json",
        imported_csv_path="artifacts/runs/phase52-publish-fixture/release/release_manifest.csv",
        imported_at=datetime(2026, 4, 9, 12, 1, tzinfo=UTC),
        bundles=[
            OutputBundle(
                bundle_id=f"{RUN_ID}:markdown-brief",
                run_id=RUN_ID,
                output_type=OutputType.MARKDOWN,
                template_version="phase4-markdown-v1",
                included_document_ids=["patent:number:sample-us-partial-001-a1"],
                output_path="artifacts/runs/phase52-publish-fixture/render/brief.md",
                approval_status=ApprovalStatus.APPROVED,
            ),
            OutputBundle(
                bundle_id=f"{RUN_ID}:pptx-brief",
                run_id=RUN_ID,
                output_type=OutputType.PPTX,
                template_version="phase4-pptx-v1",
                included_document_ids=["patent:number:sample-us-partial-001-a1"],
                output_path="artifacts/runs/phase52-publish-fixture/render/brief.pptx",
                approval_status=ApprovalStatus.DRAFT,
            ),
        ],
        approved_bundle_ids=[f"{RUN_ID}:markdown-brief"],
        approved_output_paths=["artifacts/runs/phase52-publish-fixture/render/brief.md"],
        distribution_targets=["internal", "archive"],
        release_notes=["publish stub smoke"],
        review_signoff=review_signoff,
        reviewer="qa-user" if approved else None,
        review_notes="최종 배포 승인" if approved else "승인 대기",
        published_at=published_at,
    )


def test_publish_cli_creates_stub_records_for_approved_release_review(tmp_path: Path) -> None:
    """approved release review resolution이면 채널별 publish stub record를 생성해야 한다."""

    release_review_resolution_path = tmp_path / "release_review_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(release_review_resolution_path, _build_release_review_resolution(approved=True))

    result = runner.invoke(
        app,
        [
            "publish",
            "--run-id",
            RUN_ID,
            "--release-review-resolution",
            str(release_review_resolution_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    publish_artifact_path = artifact_root / RUN_ID / "publish" / "publish_artifact.json"
    assert publish_artifact_path.exists()

    artifact = read_model(publish_artifact_path, PublishArtifact)
    assert artifact.run.stage_status["publish"].artifact_path.endswith("publish_artifact.json")
    assert artifact.run.stage_status["publish"].status == "completed"
    assert artifact.review_signoff == ReviewStatus.APPROVED
    assert artifact.blocked_reason is None
    assert artifact.simulation_mode is True
    assert len(artifact.publish_records) == 2
    assert {record.distribution_target for record in artifact.publish_records} == {"internal", "archive"}
    assert all(record.bundle_id == f"{RUN_ID}:markdown-brief" for record in artifact.publish_records)
    assert all(record.status == PublishStatus.SIMULATED for record in artifact.publish_records)


def test_publish_cli_creates_blocked_artifact_when_signoff_is_not_approved(tmp_path: Path) -> None:
    """approved signoff가 아니면 publish stub artifact만 만들고 stage를 skipped로 남겨야 한다."""

    release_review_resolution_path = tmp_path / "release_review_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(release_review_resolution_path, _build_release_review_resolution(approved=False))

    result = runner.invoke(
        app,
        [
            "publish",
            "--run-id",
            RUN_ID,
            "--release-review-resolution",
            str(release_review_resolution_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    publish_artifact_path = artifact_root / RUN_ID / "publish" / "publish_artifact.json"
    artifact = read_model(publish_artifact_path, PublishArtifact)

    assert artifact.run.stage_status["publish"].status == "skipped"
    assert artifact.review_signoff == ReviewStatus.PENDING
    assert artifact.publish_records == []
    assert artifact.blocked_reason is not None
