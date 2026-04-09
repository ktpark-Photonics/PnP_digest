"""Phase 5.8 followup export 통합 테스트."""

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsFollowupManifest,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import write_model


RUN_ID = "phase58-followup-export-fixture"
runner = CliRunner()


def _build_followup_manifest(*, empty: bool = False) -> OpsFollowupManifest:
    """followup export 입력용 followup manifest fixture를 만든다."""

    tasks = []
    if not empty:
        tasks = [
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:1",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:markdown-brief:archive",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops",
                status=ReviewTaskStatus.OPEN,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 확인했는가?",
                        response="archive 채널 상태 확인 완료",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포를 수행했거나 불필요 사유를 기록했는가?",
                        response="archive 재배포 필요",
                    ),
                ],
                notes="archive 채널 후속 작업",
                reviewed_at=None,
            ),
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:2",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:pptx-brief:executive-share",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops",
                status=ReviewTaskStatus.IN_REVIEW,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 확인했는가?",
                        response="executive-share 추가 확인 중",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포를 수행했거나 불필요 사유를 기록했는가?",
                        response="상태 확인 후 재배포 여부 결정",
                    ),
                ],
                notes="executive-share 진행 중",
                reviewed_at=datetime(2026, 4, 9, 18, 0, tzinfo=UTC),
            ),
        ]

    return OpsFollowupManifest(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase58-default",
        ),
        run_id=RUN_ID,
        source_ops_handoff_resolution_path=f"artifacts/runs/{RUN_ID}/review/ops_handoff_resolution.json",
        followup_team="ops",
        generated_at=datetime(2026, 4, 9, 19, 0, tzinfo=UTC),
        blocked_reason=None if not empty else "followup 대상이 없다.",
        open_task_count=1 if not empty else 0,
        in_review_task_count=1 if not empty else 0,
        tasks=tasks,
    )


def test_review_followup_export_creates_ops_daily_queue_csv(tmp_path: Path) -> None:
    """followup-export는 기본 경로에 ops_daily_queue.csv를 생성해야 한다."""

    manifest_path = tmp_path / "followup_manifest.json"
    write_model(manifest_path, _build_followup_manifest())

    result = runner.invoke(
        app,
        [
            "review",
            "followup-export",
            "--followup-manifest",
            str(manifest_path),
        ],
    )
    assert result.exit_code == 0

    csv_path = tmp_path / "ops_daily_queue.csv"
    assert csv_path.exists()

    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2
    assert {row["initial_status"] for row in rows} == {ReviewTaskStatus.OPEN, ReviewTaskStatus.IN_REVIEW}
    assert {row["resolved_status"] for row in rows} == {ReviewTaskStatus.OPEN, ReviewTaskStatus.IN_REVIEW}
    assert rows[0]["followup_team"] == "ops"


def test_review_followup_export_writes_header_only_for_empty_manifest(tmp_path: Path) -> None:
    """빈 followup manifest도 header-only CSV를 생성해야 한다."""

    manifest_path = tmp_path / "followup_manifest.json"
    write_model(manifest_path, _build_followup_manifest(empty=True))

    result = runner.invoke(
        app,
        [
            "review",
            "followup-export",
            "--followup-manifest",
            str(manifest_path),
        ],
    )
    assert result.exit_code == 0

    csv_path = tmp_path / "ops_daily_queue.csv"
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == []
