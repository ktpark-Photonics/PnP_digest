"""Phase 5.6 handoff review 통합 테스트."""

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsHandoffArtifact,
    OpsHandoffResolutionArtifact,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase56-handoff-review-fixture"
runner = CliRunner()


def _build_ops_handoff_artifact(*, empty: bool = False) -> OpsHandoffArtifact:
    """handoff review 입력용 ops handoff fixture를 만든다."""

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
                    ReviewChecklistItem(item_id="verify_channel_state", prompt="실제 채널 상태와 외부 참조값을 확인했는가?"),
                    ReviewChecklistItem(item_id="retry_or_close", prompt="재배포를 수행했거나 불필요 사유를 기록했는가?"),
                ],
                notes="archive 채널 재시도 필요",
                reviewed_at=None,
            ),
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:2",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:pptx-brief:executive-share",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops",
                status=ReviewTaskStatus.OPEN,
                checklist=[
                    ReviewChecklistItem(item_id="verify_channel_state", prompt="실제 채널 상태와 외부 참조값을 확인했는가?"),
                    ReviewChecklistItem(item_id="retry_or_close", prompt="재배포를 수행했거나 불필요 사유를 기록했는가?"),
                ],
                notes="executive-share 상태 확인 필요",
                reviewed_at=None,
            ),
        ]

    return OpsHandoffArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase56-default",
        ),
        run_id=RUN_ID,
        source_retry_manifest_path=f"artifacts/runs/{RUN_ID}/retry/retry_manifest.json",
        handoff_team="ops",
        generated_at=datetime(2026, 4, 9, 16, 0, tzinfo=UTC),
        blocked_reason=None if not empty else "handoff 대상이 없다.",
        open_task_count=len(tasks),
        tasks=tasks,
    )


def test_review_handoff_export_creates_one_row_per_task(tmp_path: Path) -> None:
    """handoff-export는 handoff task 수만큼 CSV row를 만들어야 한다."""

    handoff_path = tmp_path / "ops_handoff.json"
    write_model(handoff_path, _build_ops_handoff_artifact())

    result = runner.invoke(
        app,
        [
            "review",
            "handoff-export",
            "--ops-handoff",
            str(handoff_path),
        ],
    )
    assert result.exit_code == 0

    csv_path = handoff_path.with_suffix(".csv")
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2
    assert {row["resolved_status"] for row in rows} == {ReviewTaskStatus.OPEN}


def test_review_handoff_import_creates_resolution_artifact(tmp_path: Path) -> None:
    """handoff-import는 task 상태와 응답을 resolution artifact로 저장해야 한다."""

    handoff_path = tmp_path / "ops_handoff.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(handoff_path, _build_ops_handoff_artifact())

    export_result = runner.invoke(
        app,
        [
            "review",
            "handoff-export",
            "--ops-handoff",
            str(handoff_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = handoff_path.with_suffix(".csv")
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        fieldnames = rows[0].keys()

    for row in rows:
        row["verify_channel_state_response"] = "외부 채널 상태 확인 완료"
        row["retry_or_close_response"] = "재시도 또는 종료 판단 기록 완료"
        if row["review_task_id"].endswith(":1"):
            row["resolved_status"] = ReviewTaskStatus.APPROVED
            row["resolution_notes"] = "archive 채널 재배포 완료"
        else:
            row["resolved_status"] = ReviewTaskStatus.IN_REVIEW
            row["resolution_notes"] = "executive-share 추가 확인 중"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    import_result = runner.invoke(
        app,
        [
            "review",
            "handoff-import",
            "--ops-handoff",
            str(handoff_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "ops_handoff_resolution.json"
    artifact = read_model(resolution_path, OpsHandoffResolutionArtifact)

    assert artifact.open_task_count == 1
    assert artifact.closed_task_count == 1
    assert {task.status for task in artifact.tasks} == {
        ReviewTaskStatus.APPROVED,
        ReviewTaskStatus.IN_REVIEW,
    }
    assert all(task.checklist[0].response for task in artifact.tasks)
    assert all(task.checklist[1].response for task in artifact.tasks)


def test_review_handoff_import_accepts_empty_handoff_artifact(tmp_path: Path) -> None:
    """empty handoff artifact는 header-only CSV로도 import되어야 한다."""

    handoff_path = tmp_path / "ops_handoff.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(handoff_path, _build_ops_handoff_artifact(empty=True))

    export_result = runner.invoke(
        app,
        [
            "review",
            "handoff-export",
            "--ops-handoff",
            str(handoff_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = handoff_path.with_suffix(".csv")
    import_result = runner.invoke(
        app,
        [
            "review",
            "handoff-import",
            "--ops-handoff",
            str(handoff_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "ops_handoff_resolution.json"
    artifact = read_model(resolution_path, OpsHandoffResolutionArtifact)

    assert artifact.tasks == []
    assert artifact.open_task_count == 0
    assert artifact.closed_task_count == 0
