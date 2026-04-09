"""Phase 5.7 followup manifest 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsHandoffResolutionArtifact,
    OpsFollowupManifest,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase57-followup-fixture"
runner = CliRunner()


def _build_ops_handoff_resolution(*, all_closed: bool = False) -> OpsHandoffResolutionArtifact:
    """followup 입력용 handoff resolution fixture를 만든다."""

    tasks = [
        ReviewTask(
            review_task_id=f"{RUN_ID}:handoff:1",
            target_type="publish_retry",
            target_id=f"{RUN_ID}:markdown-brief:archive",
            review_stage=ReviewStage.PUBLISH,
            assignee="ops",
            status=ReviewTaskStatus.APPROVED if all_closed else ReviewTaskStatus.OPEN,
            checklist=[
                ReviewChecklistItem(
                    item_id="verify_channel_state",
                    prompt="실제 채널 상태와 외부 참조값을 확인했는가?",
                    response="확인 완료",
                ),
                ReviewChecklistItem(
                    item_id="retry_or_close",
                    prompt="재배포를 수행했거나 불필요 사유를 기록했는가?",
                    response="archive 재시도 필요",
                ),
            ],
            notes="archive 채널 followup 필요",
            reviewed_at=datetime(2026, 4, 9, 17, 0, tzinfo=UTC) if all_closed else None,
        ),
        ReviewTask(
            review_task_id=f"{RUN_ID}:handoff:2",
            target_type="publish_retry",
            target_id=f"{RUN_ID}:pptx-brief:executive-share",
            review_stage=ReviewStage.PUBLISH,
            assignee="ops",
            status=ReviewTaskStatus.REJECTED if all_closed else ReviewTaskStatus.IN_REVIEW,
            checklist=[
                ReviewChecklistItem(
                    item_id="verify_channel_state",
                    prompt="실제 채널 상태와 외부 참조값을 확인했는가?",
                    response="추가 확인 중",
                ),
                ReviewChecklistItem(
                    item_id="retry_or_close",
                    prompt="재배포를 수행했거나 불필요 사유를 기록했는가?",
                    response="executive-share 추가 확인 필요",
                ),
            ],
            notes="executive-share 확인 중",
            reviewed_at=datetime(2026, 4, 9, 17, 5, tzinfo=UTC) if all_closed else datetime(2026, 4, 9, 17, 5, tzinfo=UTC),
        ),
    ]

    open_count = sum(1 for task in tasks if task.status in {ReviewTaskStatus.OPEN, ReviewTaskStatus.IN_REVIEW})
    closed_count = sum(1 for task in tasks if task.status in {ReviewTaskStatus.APPROVED, ReviewTaskStatus.REJECTED})

    return OpsHandoffResolutionArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase57-default",
        ),
        run_id=RUN_ID,
        source_ops_handoff_path=f"artifacts/runs/{RUN_ID}/handoff/ops_handoff.json",
        imported_csv_path=f"artifacts/runs/{RUN_ID}/handoff/ops_handoff.csv",
        imported_at=datetime(2026, 4, 9, 18, 0, tzinfo=UTC),
        handoff_team="ops",
        blocked_reason=None if not all_closed else "followup 대상이 없다.",
        open_task_count=open_count,
        closed_task_count=closed_count,
        tasks=tasks,
    )


def test_followup_cli_keeps_only_open_and_in_review_tasks(tmp_path: Path) -> None:
    """followup은 open/in_review task만 남겨야 한다."""

    resolution_path = tmp_path / "ops_handoff_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(resolution_path, _build_ops_handoff_resolution())

    result = runner.invoke(
        app,
        [
            "followup",
            "--run-id",
            RUN_ID,
            "--ops-handoff-resolution",
            str(resolution_path),
            "--artifact-root",
            str(artifact_root),
            "--followup-team",
            "ops-apac",
        ],
    )
    assert result.exit_code == 0

    manifest_path = artifact_root / RUN_ID / "followup" / "followup_manifest.json"
    artifact = read_model(manifest_path, OpsFollowupManifest)

    assert artifact.run.stage_status["followup"].status == "completed"
    assert artifact.followup_team == "ops-apac"
    assert artifact.open_task_count == 1
    assert artifact.in_review_task_count == 1
    assert {task.status for task in artifact.tasks} == {
        ReviewTaskStatus.OPEN,
        ReviewTaskStatus.IN_REVIEW,
    }


def test_followup_cli_skips_when_all_tasks_are_closed(tmp_path: Path) -> None:
    """모든 handoff task가 닫혀 있으면 followup stage는 skipped로 남아야 한다."""

    resolution_path = tmp_path / "ops_handoff_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(resolution_path, _build_ops_handoff_resolution(all_closed=True))

    result = runner.invoke(
        app,
        [
            "followup",
            "--run-id",
            RUN_ID,
            "--ops-handoff-resolution",
            str(resolution_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    manifest_path = artifact_root / RUN_ID / "followup" / "followup_manifest.json"
    artifact = read_model(manifest_path, OpsFollowupManifest)

    assert artifact.run.stage_status["followup"].status == "skipped"
    assert artifact.tasks == []
    assert artifact.open_task_count == 0
    assert artifact.in_review_task_count == 0
