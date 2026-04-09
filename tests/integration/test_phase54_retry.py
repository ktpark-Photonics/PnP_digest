"""Phase 5.4 retry manifest 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OutputType,
    PipelineRun,
    PublishReviewResolutionArtifact,
    PublishReviewResolutionRecord,
    PublishRetryManifest,
    PublishStatus,
    ReviewStage,
    ReviewStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase54-retry-fixture"
runner = CliRunner()


def _build_publish_review_resolution(*, all_published: bool = False) -> PublishReviewResolutionArtifact:
    """retry 입력용 publish review resolution fixture를 만든다."""

    records = [
        PublishReviewResolutionRecord(
            bundle_id=f"{RUN_ID}:markdown-brief",
            output_type=OutputType.MARKDOWN,
            output_path=f"artifacts/runs/{RUN_ID}/render/brief.md",
            distribution_target="internal",
            initial_status=PublishStatus.SIMULATED,
            reviewed_status=PublishStatus.PUBLISHED,
            external_reference="internal://brief/2026-04-09",
            record_notes="사내 채널 게시 완료",
        ),
        PublishReviewResolutionRecord(
            bundle_id=f"{RUN_ID}:markdown-brief",
            output_type=OutputType.MARKDOWN,
            output_path=f"artifacts/runs/{RUN_ID}/render/brief.md",
            distribution_target="archive",
            initial_status=PublishStatus.SIMULATED,
            reviewed_status=PublishStatus.PUBLISHED if all_published else PublishStatus.FAILED,
            external_reference=None,
            record_notes="archive 업로드 실패" if not all_published else "archive 업로드 완료",
        ),
        PublishReviewResolutionRecord(
            bundle_id=f"{RUN_ID}:pptx-brief",
            output_type=OutputType.PPTX,
            output_path=f"artifacts/runs/{RUN_ID}/render/brief.pptx",
            distribution_target="executive-share",
            initial_status=PublishStatus.SIMULATED,
            reviewed_status=PublishStatus.PUBLISHED if all_published else PublishStatus.SIMULATED,
            external_reference=None,
            record_notes="게시 여부 추가 확인 필요" if not all_published else "배포 완료",
        ),
    ]

    published_count = sum(1 for record in records if record.reviewed_status == PublishStatus.PUBLISHED)
    failed_count = sum(1 for record in records if record.reviewed_status == PublishStatus.FAILED)
    unresolved_count = sum(1 for record in records if record.reviewed_status == PublishStatus.SIMULATED)

    return PublishReviewResolutionArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase54-default",
        ),
        run_id=RUN_ID,
        review_stage=ReviewStage.PUBLISH,
        source_publish_artifact_path=f"artifacts/runs/{RUN_ID}/publish/publish_artifact.json",
        imported_csv_path=f"artifacts/runs/{RUN_ID}/publish/publish_artifact.csv",
        imported_at=datetime(2026, 4, 9, 14, 0, tzinfo=UTC),
        simulation_mode=True,
        review_signoff=ReviewStatus.APPROVED,
        reviewer="ops-user",
        review_notes="archive 후속 확인",
        blocked_reason=None,
        published_record_count=published_count,
        failed_record_count=failed_count,
        unresolved_record_count=unresolved_count,
        records=records,
    )


def test_retry_cli_creates_manifest_for_failed_and_unresolved_records(tmp_path: Path) -> None:
    """retry는 failed/simulated 채널만 retry manifest에 담아야 한다."""

    resolution_path = tmp_path / "publish_review_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(resolution_path, _build_publish_review_resolution())

    result = runner.invoke(
        app,
        [
            "retry",
            "--run-id",
            RUN_ID,
            "--publish-review-resolution",
            str(resolution_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    retry_manifest_path = artifact_root / RUN_ID / "retry" / "retry_manifest.json"
    artifact = read_model(retry_manifest_path, PublishRetryManifest)

    assert artifact.run.stage_status["retry"].status == "completed"
    assert artifact.retry_count == 2
    assert {item.distribution_target for item in artifact.items} == {"archive", "executive-share"}
    assert {item.current_status for item in artifact.items} == {
        PublishStatus.FAILED,
        PublishStatus.SIMULATED,
    }


def test_retry_cli_creates_skipped_manifest_when_retry_targets_do_not_exist(tmp_path: Path) -> None:
    """모든 채널이 published면 retry stage는 skipped로 남아야 한다."""

    resolution_path = tmp_path / "publish_review_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(resolution_path, _build_publish_review_resolution(all_published=True))

    result = runner.invoke(
        app,
        [
            "retry",
            "--run-id",
            RUN_ID,
            "--publish-review-resolution",
            str(resolution_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    retry_manifest_path = artifact_root / RUN_ID / "retry" / "retry_manifest.json"
    artifact = read_model(retry_manifest_path, PublishRetryManifest)

    assert artifact.run.stage_status["retry"].status == "skipped"
    assert artifact.retry_count == 0
    assert artifact.items == []
