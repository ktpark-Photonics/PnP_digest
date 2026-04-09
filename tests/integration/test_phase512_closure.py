"""Phase 5.12 closure report 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsClosureReport,
    OpsEscalationResolutionArtifact,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase512-closure-fixture"
runner = CliRunner()


def _build_escalation_resolution(*, empty: bool = False) -> OpsEscalationResolutionArtifact:
    """closure 입력용 escalation resolution fixture를 만든다."""

    tasks = []
    if not empty:
        tasks = [
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:1",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:markdown-brief:archive",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops-lead",
                status=ReviewTaskStatus.APPROVED,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 다시 확인했는가?",
                        response="archive 종료 확인",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포 종료 또는 추가 재시도 계획을 남겼는가?",
                        response="종료 처리 완료",
                    ),
                ],
                notes="archive 종료",
                reviewed_at=datetime(2026, 4, 9, 23, 0, tzinfo=UTC),
            ),
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:2",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:pptx-brief:executive-share",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops-lead",
                status=ReviewTaskStatus.REJECTED,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 다시 확인했는가?",
                        response="executive-share 종료 불가",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포 종료 또는 추가 재시도 계획을 남겼는가?",
                        response="재시도 종료 판단",
                    ),
                ],
                notes="executive-share 종료",
                reviewed_at=datetime(2026, 4, 9, 23, 5, tzinfo=UTC),
            ),
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:3",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:pdf-brief:executive-share",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops-lead",
                status=ReviewTaskStatus.OPEN,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 다시 확인했는가?",
                        response="추가 상태 확인 필요",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포 종료 또는 추가 재시도 계획을 남겼는가?",
                        response="추가 대응 계획 필요",
                    ),
                ],
                notes="pdf 후속 확인 필요",
                reviewed_at=None,
            ),
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:4",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:docx-brief:archive",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops-lead",
                status=ReviewTaskStatus.IN_REVIEW,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 다시 확인했는가?",
                        response="archive 재검토 중",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포 종료 또는 추가 재시도 계획을 남겼는가?",
                        response="결론 대기 중",
                    ),
                ],
                notes="docx 재검토 중",
                reviewed_at=datetime(2026, 4, 9, 23, 10, tzinfo=UTC),
            ),
        ]

    open_count = sum(1 for task in tasks if task.status == ReviewTaskStatus.OPEN)
    in_review_count = sum(1 for task in tasks if task.status == ReviewTaskStatus.IN_REVIEW)
    closed_count = sum(
        1 for task in tasks if task.status in {ReviewTaskStatus.APPROVED, ReviewTaskStatus.REJECTED}
    )

    return OpsEscalationResolutionArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase512-default",
        ),
        run_id=RUN_ID,
        source_escalation_manifest_path=f"artifacts/runs/{RUN_ID}/escalation/escalation_manifest.json",
        imported_csv_path=f"artifacts/runs/{RUN_ID}/escalation/ops_escalation_queue.csv",
        imported_at=datetime(2026, 4, 9, 23, 30, tzinfo=UTC),
        escalation_team="ops-lead",
        blocked_reason=None if not empty else "closure 대상으로 정리할 task가 없다.",
        open_task_count=open_count,
        in_review_task_count=in_review_count,
        closed_task_count=closed_count,
        tasks=tasks,
    )


def test_closure_cli_splits_closed_and_remaining_tasks(tmp_path: Path) -> None:
    """closure는 종결 task와 남은 task를 분리한 report를 저장해야 한다."""

    resolution_path = tmp_path / "escalation_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(resolution_path, _build_escalation_resolution())

    result = runner.invoke(
        app,
        [
            "closure",
            "--run-id",
            RUN_ID,
            "--escalation-resolution",
            str(resolution_path),
            "--artifact-root",
            str(artifact_root),
            "--closure-team",
            "ops-final",
        ],
    )
    assert result.exit_code == 0

    report_path = artifact_root / RUN_ID / "closure" / "closure_report.json"
    artifact = read_model(report_path, OpsClosureReport)

    assert artifact.run.stage_status["closure"].status == "completed"
    assert artifact.closure_team == "ops-final"
    assert artifact.closed_task_count == 2
    assert artifact.remaining_task_count == 2
    assert {task.status for task in artifact.closed_tasks} == {
        ReviewTaskStatus.APPROVED,
        ReviewTaskStatus.REJECTED,
    }
    assert {task.status for task in artifact.remaining_tasks} == {
        ReviewTaskStatus.OPEN,
        ReviewTaskStatus.IN_REVIEW,
    }


def test_closure_cli_skips_when_escalation_resolution_has_no_tasks(tmp_path: Path) -> None:
    """task가 없으면 closure stage는 skipped로 남아야 한다."""

    resolution_path = tmp_path / "escalation_resolution.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(resolution_path, _build_escalation_resolution(empty=True))

    result = runner.invoke(
        app,
        [
            "closure",
            "--run-id",
            RUN_ID,
            "--escalation-resolution",
            str(resolution_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    report_path = artifact_root / RUN_ID / "closure" / "closure_report.json"
    artifact = read_model(report_path, OpsClosureReport)

    assert artifact.run.stage_status["closure"].status == "skipped"
    assert artifact.closed_tasks == []
    assert artifact.remaining_tasks == []
    assert artifact.closed_task_count == 0
    assert artifact.remaining_task_count == 0
