"""Phase 5.11 escalation review 통합 테스트."""

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OpsEscalationManifest,
    OpsEscalationResolutionArtifact,
    PipelineRun,
    ReviewChecklistItem,
    ReviewStage,
    ReviewTask,
    ReviewTaskStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase511-escalation-review-fixture"
runner = CliRunner()


def _build_escalation_manifest(*, empty: bool = False) -> OpsEscalationManifest:
    """escalation review 입력용 manifest fixture를 만든다."""

    tasks = []
    if not empty:
        tasks = [
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:1",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:markdown-brief:archive",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops-lead",
                status=ReviewTaskStatus.IN_REVIEW,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 다시 확인했는가?",
                        response="archive 확인 중",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포 종료 또는 추가 재시도 계획을 남겼는가?",
                        response="archive 종료 여부 판단 필요",
                    ),
                ],
                notes="archive 에스컬레이션 검토",
                reviewed_at=datetime(2026, 4, 9, 22, 0, tzinfo=UTC),
            ),
            ReviewTask(
                review_task_id=f"{RUN_ID}:handoff:2",
                target_type="publish_retry",
                target_id=f"{RUN_ID}:pptx-brief:executive-share",
                review_stage=ReviewStage.PUBLISH,
                assignee="ops-lead",
                status=ReviewTaskStatus.IN_REVIEW,
                checklist=[
                    ReviewChecklistItem(
                        item_id="verify_channel_state",
                        prompt="실제 채널 상태와 외부 참조값을 다시 확인했는가?",
                        response="executive-share 추가 확인 중",
                    ),
                    ReviewChecklistItem(
                        item_id="retry_or_close",
                        prompt="재배포 종료 또는 추가 재시도 계획을 남겼는가?",
                        response="추가 재시도 여부 판단 필요",
                    ),
                ],
                notes="executive-share 에스컬레이션 검토",
                reviewed_at=datetime(2026, 4, 9, 22, 5, tzinfo=UTC),
            ),
        ]

    return OpsEscalationManifest(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase511-default",
        ),
        run_id=RUN_ID,
        source_followup_resolution_path=f"artifacts/runs/{RUN_ID}/review/followup_resolution.json",
        escalation_team="ops-lead",
        generated_at=datetime(2026, 4, 9, 22, 30, tzinfo=UTC),
        blocked_reason=None if not empty else "escalation 대상이 없다.",
        in_review_task_count=len(tasks),
        tasks=tasks,
    )


def test_review_escalation_export_creates_csv(tmp_path: Path) -> None:
    """escalation-export는 기본 경로에 CSV를 생성해야 한다."""

    manifest_path = tmp_path / "escalation_manifest.json"
    write_model(manifest_path, _build_escalation_manifest())

    result = runner.invoke(
        app,
        [
            "review",
            "escalation-export",
            "--escalation-manifest",
            str(manifest_path),
        ],
    )
    assert result.exit_code == 0

    csv_path = tmp_path / "ops_escalation_queue.csv"
    assert csv_path.exists()

    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2
    assert {row["initial_status"] for row in rows} == {ReviewTaskStatus.IN_REVIEW}
    assert {row["resolved_status"] for row in rows} == {ReviewTaskStatus.IN_REVIEW}
    assert rows[0]["escalation_team"] == "ops-lead"


def test_review_escalation_import_creates_resolution_artifact(tmp_path: Path) -> None:
    """escalation-import는 task 상태를 resolution artifact로 저장해야 한다."""

    manifest_path = tmp_path / "escalation_manifest.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(manifest_path, _build_escalation_manifest())

    export_result = runner.invoke(
        app,
        [
            "review",
            "escalation-export",
            "--escalation-manifest",
            str(manifest_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = tmp_path / "ops_escalation_queue.csv"
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        fieldnames = rows[0].keys()

    for row in rows:
        row["verify_channel_state_response"] = "채널 상태 재확인 완료"
        row["retry_or_close_response"] = "종결 또는 추가 대응 메모 기록"
        if row["review_task_id"].endswith(":1"):
            row["resolved_status"] = ReviewTaskStatus.APPROVED
            row["resolution_notes"] = "archive escalation 종료"
        else:
            row["resolved_status"] = ReviewTaskStatus.IN_REVIEW
            row["resolution_notes"] = "executive-share 추가 확인 유지"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    import_result = runner.invoke(
        app,
        [
            "review",
            "escalation-import",
            "--escalation-manifest",
            str(manifest_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "escalation_resolution.json"
    artifact = read_model(resolution_path, OpsEscalationResolutionArtifact)

    assert artifact.open_task_count == 0
    assert artifact.in_review_task_count == 1
    assert artifact.closed_task_count == 1
    assert {task.status for task in artifact.tasks} == {
        ReviewTaskStatus.APPROVED,
        ReviewTaskStatus.IN_REVIEW,
    }
    assert all(task.checklist[0].response for task in artifact.tasks)
    assert all(task.checklist[1].response for task in artifact.tasks)


def test_review_escalation_import_accepts_empty_manifest(tmp_path: Path) -> None:
    """빈 escalation manifest는 header-only CSV로도 import되어야 한다."""

    manifest_path = tmp_path / "escalation_manifest.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(manifest_path, _build_escalation_manifest(empty=True))

    export_result = runner.invoke(
        app,
        [
            "review",
            "escalation-export",
            "--escalation-manifest",
            str(manifest_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = tmp_path / "ops_escalation_queue.csv"
    import_result = runner.invoke(
        app,
        [
            "review",
            "escalation-import",
            "--escalation-manifest",
            str(manifest_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "escalation_resolution.json"
    artifact = read_model(resolution_path, OpsEscalationResolutionArtifact)

    assert artifact.tasks == []
    assert artifact.open_task_count == 0
    assert artifact.in_review_task_count == 0
    assert artifact.closed_task_count == 0
