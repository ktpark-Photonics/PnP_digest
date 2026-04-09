"""Phase 5.10 escalation manifest 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsEscalationManifest,
    OpsFollowupResolutionArtifact,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase510-escalation-fixture"
runner = CliRunner()


def _build_followup_resolution(*, all_closed: bool = False) -> OpsFollowupResolutionArtifact:
    """escalation 입력용 followup resolution fixture를 만든다."""

    tasks = [
        ReviewTask(
            review_task_id=f"{RUN_ID}:handoff:1",
            target_type="publish_retry",
            target_id=f"{RUN_ID}:markdown-brief:archive",
            review_stage=ReviewStage.PUBLISH,
            assignee="ops",
            status=ReviewTaskStatus.APPROVED if all_closed else ReviewTaskStatus.APPROVED,
            checklist=[
                ReviewChecklistItem(
                    item_id="verify_channel_state",
                    prompt="실제 채널 상태와 외부 참조값을 확인했는가?",
                    response="확인 완료",
                ),
                ReviewChecklistItem(
                    item_id="retry_or_close",
                    prompt="재배포를 수행했거나 불필요 사유를 기록했는가?",
                    response="종료 처리",
                ),
            ],
            notes="archive 종료",
            reviewed_at=datetime(2026, 4, 9, 20, 0, tzinfo=UTC),
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
                    response="추가 판단 필요",
                ),
            ],
            notes="executive-share 에스컬레이션 후보",
            reviewed_at=datetime(2026, 4, 9, 20, 5, tzinfo=UTC),
        ),
    ]

    open_count = sum(1 for task in tasks if task.status == ReviewTaskStatus.OPEN)
    in_review_count = sum(1 for task in tasks if task.status == ReviewTaskStatus.IN_REVIEW)
    closed_count = sum(
        1 for task in tasks if task.status in {ReviewTaskStatus.APPROVED, ReviewTaskStatus.REJECTED}
    )

    return OpsFollowupResolutionArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase510-default",
        ),
        run_id=RUN_ID,
        source_followup_manifest_path=f"artifacts/runs/{RUN_ID}/followup/followup_manifest.json",
        imported_csv_path=f"artifacts/runs/{RUN_ID}/followup/ops_daily_queue.csv",
        imported_at=datetime(2026, 4, 9, 21, 0, tzinfo=UTC),
        followup_team="ops",
        blocked_reason=None if not all_closed else "escalation 대상이 없다.",
        open_task_count=open_count,
        in_review_task_count=in_review_count,
        closed_task_count=closed_count,
        tasks=tasks,
    )


def test_escalation_cli_keeps_only_in_review_tasks(tmp_path: Path) -> None:
    """escalation은 in_review task만 남겨야 한다."""

    resolution_path = tmp_path / "followup_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(resolution_path, _build_followup_resolution())

    result = runner.invoke(
        app,
        [
            "escalation",
            "--run-id",
            RUN_ID,
            "--followup-resolution",
            str(resolution_path),
            "--artifact-root",
            str(artifact_root),
            "--escalation-team",
            "ops-lead-apac",
        ],
    )
    assert result.exit_code == 0

    manifest_path = artifact_root / RUN_ID / "escalation" / "escalation_manifest.json"
    artifact = read_model(manifest_path, OpsEscalationManifest)

    assert artifact.run.stage_status["escalation"].status == "completed"
    assert artifact.escalation_team == "ops-lead-apac"
    assert artifact.in_review_task_count == 1
    assert len(artifact.tasks) == 1
    assert artifact.tasks[0].status == ReviewTaskStatus.IN_REVIEW


def test_escalation_cli_skips_when_in_review_task_does_not_exist(tmp_path: Path) -> None:
    """in_review task가 없으면 escalation stage는 skipped로 남아야 한다."""

    resolution_path = tmp_path / "followup_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(resolution_path, _build_followup_resolution(all_closed=True))

    result = runner.invoke(
        app,
        [
            "escalation",
            "--run-id",
            RUN_ID,
            "--followup-resolution",
            str(resolution_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    manifest_path = artifact_root / RUN_ID / "escalation" / "escalation_manifest.json"
    artifact = read_model(manifest_path, OpsEscalationManifest)

    assert artifact.run.stage_status["escalation"].status == "skipped"
    assert artifact.tasks == []
    assert artifact.in_review_task_count == 0
