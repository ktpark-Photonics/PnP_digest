"""Phase 5.9 followup review 통합 테스트."""

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsFollowupManifest,
    OpsFollowupResolutionArtifact,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase59-followup-review-fixture"
runner = CliRunner()


def _build_followup_manifest(*, empty: bool = False) -> OpsFollowupManifest:
    """followup review 입력용 manifest fixture를 만든다."""

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
                        response="archive 상태 확인 필요",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포를 수행했거나 불필요 사유를 기록했는가?",
                        response="archive 재배포 필요",
                    ),
                ],
                notes="archive followup 필요",
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
                        response="executive-share 확인 중",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포를 수행했거나 불필요 사유를 기록했는가?",
                        response="확인 후 재배포 여부 결정",
                    ),
                ],
                notes="executive-share 진행 중",
                reviewed_at=datetime(2026, 4, 9, 19, 0, tzinfo=UTC),
            ),
        ]

    return OpsFollowupManifest(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase59-default",
        ),
        run_id=RUN_ID,
        source_ops_handoff_resolution_path=f"artifacts/runs/{RUN_ID}/review/ops_handoff_resolution.json",
        followup_team="ops",
        generated_at=datetime(2026, 4, 9, 20, 0, tzinfo=UTC),
        blocked_reason=None if not empty else "followup 대상이 없다.",
        open_task_count=1 if not empty else 0,
        in_review_task_count=1 if not empty else 0,
        tasks=tasks,
    )


def test_review_followup_import_creates_resolution_artifact(tmp_path: Path) -> None:
    """followup-import는 task 상태와 응답을 resolution artifact로 저장해야 한다."""

    manifest_path = tmp_path / "followup_manifest.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(manifest_path, _build_followup_manifest())

    export_result = runner.invoke(
        app,
        [
            "review",
            "followup-export",
            "--followup-manifest",
            str(manifest_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = tmp_path / "ops_daily_queue.csv"
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        fieldnames = rows[0].keys()

    for row in rows:
        row["verify_channel_state_response"] = "채널 상태 재확인 완료"
        row["retry_or_close_response"] = "후속 조치 기록 완료"
        if row["review_task_id"].endswith(":1"):
            row["resolved_status"] = ReviewTaskStatus.APPROVED
            row["resolution_notes"] = "archive followup 종료"
        else:
            row["resolved_status"] = ReviewTaskStatus.IN_REVIEW
            row["resolution_notes"] = "executive-share 계속 확인"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    import_result = runner.invoke(
        app,
        [
            "review",
            "followup-import",
            "--followup-manifest",
            str(manifest_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "followup_resolution.json"
    artifact = read_model(resolution_path, OpsFollowupResolutionArtifact)

    assert artifact.open_task_count == 0
    assert artifact.in_review_task_count == 1
    assert artifact.closed_task_count == 1
    assert {task.status for task in artifact.tasks} == {
        ReviewTaskStatus.APPROVED,
        ReviewTaskStatus.IN_REVIEW,
    }
    assert all(task.checklist[0].response for task in artifact.tasks)
    assert all(task.checklist[1].response for task in artifact.tasks)


def test_review_followup_import_accepts_empty_manifest(tmp_path: Path) -> None:
    """빈 followup manifest는 header-only CSV로도 import되어야 한다."""

    manifest_path = tmp_path / "followup_manifest.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(manifest_path, _build_followup_manifest(empty=True))

    export_result = runner.invoke(
        app,
        [
            "review",
            "followup-export",
            "--followup-manifest",
            str(manifest_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = tmp_path / "ops_daily_queue.csv"
    import_result = runner.invoke(
        app,
        [
            "review",
            "followup-import",
            "--followup-manifest",
            str(manifest_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "followup_resolution.json"
    artifact = read_model(resolution_path, OpsFollowupResolutionArtifact)

    assert artifact.tasks == []
    assert artifact.open_task_count == 0
    assert artifact.in_review_task_count == 0
    assert artifact.closed_task_count == 0
