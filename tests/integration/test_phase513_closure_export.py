"""Phase 5.13 closure export 통합 테스트."""

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsClosureReport,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import write_model


RUN_ID = "phase513-closure-export-fixture"
runner = CliRunner()


def _build_closure_report(*, empty: bool = False) -> OpsClosureReport:
    """closure export 입력용 closure report fixture를 만든다."""

    closed_tasks: list[ReviewTask] = []
    remaining_tasks: list[ReviewTask] = []

    if not empty:
        closed_tasks = [
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:1",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:markdown-brief:archive",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops-final",
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
                        response="종결 처리 완료",
                    ),
                ],
                notes="archive 종료",
                reviewed_at=datetime(2026, 4, 10, 9, 0, tzinfo=UTC),
            )
        ]
        remaining_tasks = [
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:2",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:pptx-brief:executive-share",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops-final",
                status=ReviewTaskStatus.IN_REVIEW,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 다시 확인했는가?",
                        response="executive-share 재확인 중",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포 종료 또는 추가 재시도 계획을 남겼는가?",
                        response="추가 대응 계획 필요",
                    ),
                ],
                notes="executive-share 검토 지속",
                reviewed_at=datetime(2026, 4, 10, 9, 5, tzinfo=UTC),
            )
        ]

    return OpsClosureReport(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 10),
            started_at=datetime(2026, 4, 10, 8, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase513-default",
        ),
        run_id=RUN_ID,
        source_escalation_resolution_path=f"artifacts/runs/{RUN_ID}/review/escalation_resolution.json",
        closure_team="ops-final",
        generated_at=datetime(2026, 4, 10, 10, 0, tzinfo=UTC),
        blocked_reason=None if not empty else "closure 대상으로 정리할 task가 없다.",
        closed_task_count=len(closed_tasks),
        remaining_task_count=len(remaining_tasks),
        closed_tasks=closed_tasks,
        remaining_tasks=remaining_tasks,
    )


def test_review_closure_export_creates_csv(tmp_path: Path) -> None:
    """closure-export는 기본 경로에 CSV를 생성해야 한다."""

    report_path = tmp_path / "closure_report.json"
    write_model(report_path, _build_closure_report())

    result = runner.invoke(
        app,
        [
            "review",
            "closure-export",
            "--closure-report",
            str(report_path),
        ],
    )
    assert result.exit_code == 0

    csv_path = tmp_path / "closure_report.csv"
    assert csv_path.exists()

    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2
    assert {row["task_group"] for row in rows} == {"closed", "remaining"}
    assert {row["status"] for row in rows} == {
        ReviewTaskStatus.APPROVED,
        ReviewTaskStatus.IN_REVIEW,
    }
    assert rows[0]["closure_team"] == "ops-final"


def test_review_closure_export_writes_header_only_for_empty_report(tmp_path: Path) -> None:
    """빈 closure report도 header-only CSV를 생성해야 한다."""

    report_path = tmp_path / "closure_report.json"
    write_model(report_path, _build_closure_report(empty=True))

    result = runner.invoke(
        app,
        [
            "review",
            "closure-export",
            "--closure-report",
            str(report_path),
        ],
    )
    assert result.exit_code == 0

    csv_path = tmp_path / "closure_report.csv"
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == []
