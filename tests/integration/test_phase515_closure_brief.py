"""Phase 5.15 closure brief 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsClosureResolutionArtifact,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import write_model


RUN_ID = "phase515-closure-brief-fixture"
runner = CliRunner()


def _build_closure_resolution(*, empty: bool = False) -> OpsClosureResolutionArtifact:
    """closure brief 입력용 closure resolution fixture를 만든다."""

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
                reviewed_at=datetime(2026, 4, 10, 10, 0, tzinfo=UTC),
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
                reviewed_at=datetime(2026, 4, 10, 10, 5, tzinfo=UTC),
            )
        ]

    return OpsClosureResolutionArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 10),
            started_at=datetime(2026, 4, 10, 8, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase515-default",
        ),
        run_id=RUN_ID,
        source_closure_report_path=f"artifacts/runs/{RUN_ID}/closure/closure_report.json",
        imported_csv_path=f"artifacts/runs/{RUN_ID}/closure/closure_report.csv",
        imported_at=datetime(2026, 4, 10, 10, 30, tzinfo=UTC),
        closure_team="ops-final",
        blocked_reason=None if not empty else "closure 대상으로 정리할 task가 없다.",
        closed_task_count=len(closed_tasks),
        remaining_task_count=len(remaining_tasks),
        closed_tasks=closed_tasks,
        remaining_tasks=remaining_tasks,
    )


def test_review_closure_brief_creates_markdown_with_default_path(tmp_path: Path) -> None:
    """closure-brief는 기본 경로에 Markdown 보고서를 생성해야 한다."""

    resolution_path = tmp_path / "closure_resolution.json"
    write_model(resolution_path, _build_closure_resolution())

    result = runner.invoke(
        app,
        [
            "review",
            "closure-brief",
            "--closure-resolution",
            str(resolution_path),
        ],
    )
    assert result.exit_code == 0

    markdown_path = tmp_path / "closure_resolution.md"
    assert markdown_path.exists()

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Ops Closure Resolution Brief" in markdown
    assert f"- run_id: {RUN_ID}" in markdown
    assert "## Closed Tasks" in markdown
    assert "## Remaining Tasks" in markdown
    assert f"{RUN_ID}:handoff:1" in markdown
    assert f"{RUN_ID}:handoff:2" in markdown


def test_review_closure_brief_handles_empty_resolution(tmp_path: Path) -> None:
    """빈 closure resolution도 Markdown 보고서를 생성해야 한다."""

    resolution_path = tmp_path / "closure_resolution.json"
    write_model(resolution_path, _build_closure_resolution(empty=True))

    result = runner.invoke(
        app,
        [
            "review",
            "closure-brief",
            "--closure-resolution",
            str(resolution_path),
            "--title",
            "Closure Status Brief",
        ],
    )
    assert result.exit_code == 0

    markdown_path = tmp_path / "closure_resolution.md"
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Closure Status Brief" in markdown
    assert "- closed_task_count: 0" in markdown
    assert "- remaining_task_count: 0" in markdown
    assert "## Closed Tasks" in markdown
    assert "## Remaining Tasks" in markdown
    assert markdown.count("- 없음") == 2
