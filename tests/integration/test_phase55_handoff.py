"""Phase 5.5 ops handoff 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsHandoffArtifact,
    OutputType,
    PipelineRun,
    PublishRetryItem,
    PublishRetryManifest,
    PublishStatus,
    ReviewTaskStatus,
    ReviewStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase55-handoff-fixture"
runner = CliRunner()


def _build_retry_manifest(*, empty: bool = False) -> PublishRetryManifest:
    """handoff 입력용 retry manifest fixture를 만든다."""

    items = []
    if not empty:
        items = [
            PublishRetryItem(
                bundle_id=f"{RUN_ID}:markdown-brief",
                output_type=OutputType.MARKDOWN,
                output_path=f"artifacts/runs/{RUN_ID}/render/brief.md",
                distribution_target="archive",
                current_status=PublishStatus.FAILED,
                external_reference=None,
                retry_reason="archive 업로드 실패",
                recommended_action="권한과 업로드 경로를 점검한 뒤 archive 채널만 다시 publish한다.",
                review_notes="archive 권한 오류",
            ),
            PublishRetryItem(
                bundle_id=f"{RUN_ID}:pptx-brief",
                output_type=OutputType.PPTX,
                output_path=f"artifacts/runs/{RUN_ID}/render/brief.pptx",
                distribution_target="executive-share",
                current_status=PublishStatus.SIMULATED,
                external_reference=None,
                retry_reason="게시 여부 추가 확인 필요",
                recommended_action="실제 게시 여부를 확인하고 미게시 상태면 executive-share 채널만 다시 publish한다.",
                review_notes="게시 여부 확인 필요",
            ),
        ]

    return PublishRetryManifest(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase55-default",
        ),
        run_id=RUN_ID,
        source_publish_review_resolution_path=f"artifacts/runs/{RUN_ID}/review/publish_review_resolution.json",
        review_signoff=ReviewStatus.APPROVED,
        reviewer="ops-user",
        generated_at=datetime(2026, 4, 9, 15, 0, tzinfo=UTC),
        blocked_reason=None if not empty else "retry 대상이 없다.",
        retry_count=len(items),
        items=items,
    )


def test_handoff_cli_creates_open_tasks_for_retry_items(tmp_path: Path) -> None:
    """handoff는 retry item 수만큼 open task를 만들어야 한다."""

    retry_manifest_path = tmp_path / "retry_manifest.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(retry_manifest_path, _build_retry_manifest())

    result = runner.invoke(
        app,
        [
            "handoff",
            "--run-id",
            RUN_ID,
            "--retry-manifest",
            str(retry_manifest_path),
            "--artifact-root",
            str(artifact_root),
            "--handoff-team",
            "ops-eu",
        ],
    )
    assert result.exit_code == 0

    handoff_artifact_path = artifact_root / RUN_ID / "handoff" / "ops_handoff.json"
    artifact = read_model(handoff_artifact_path, OpsHandoffArtifact)

    assert artifact.run.stage_status["handoff"].status == "completed"
    assert artifact.handoff_team == "ops-eu"
    assert artifact.open_task_count == 2
    assert len(artifact.tasks) == 2
    assert all(task.status == ReviewTaskStatus.OPEN for task in artifact.tasks)
    assert all(task.assignee == "ops-eu" for task in artifact.tasks)
    assert {task.target_id for task in artifact.tasks} == {
        f"{RUN_ID}:markdown-brief:archive",
        f"{RUN_ID}:pptx-brief:executive-share",
    }


def test_handoff_cli_creates_skipped_artifact_when_retry_items_are_empty(tmp_path: Path) -> None:
    """retry 대상이 없으면 handoff stage는 skipped로 남아야 한다."""

    retry_manifest_path = tmp_path / "retry_manifest.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(retry_manifest_path, _build_retry_manifest(empty=True))

    result = runner.invoke(
        app,
        [
            "handoff",
            "--run-id",
            RUN_ID,
            "--retry-manifest",
            str(retry_manifest_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    handoff_artifact_path = artifact_root / RUN_ID / "handoff" / "ops_handoff.json"
    artifact = read_model(handoff_artifact_path, OpsHandoffArtifact)

    assert artifact.run.stage_status["handoff"].status == "skipped"
    assert artifact.open_task_count == 0
    assert artifact.tasks == []
