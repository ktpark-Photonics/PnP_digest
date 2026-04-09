"""Phase 5.14 closure review 통합 테스트."""

import csv
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import OpsClosureResolutionArtifact, ReviewTaskStatus
from pnp_digest.services.io import read_model, write_model
from tests.integration.test_phase513_closure_export import RUN_ID, _build_closure_report


runner = CliRunner()


def test_review_closure_import_creates_resolution_artifact(tmp_path: Path) -> None:
    """closure-import는 사람이 수정한 CSV를 closure resolution artifact로 저장해야 한다."""

    report_path = tmp_path / "closure_report.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(report_path, _build_closure_report())

    export_result = runner.invoke(
        app,
        [
            "review",
            "closure-export",
            "--closure-report",
            str(report_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = tmp_path / "closure_report.csv"
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        fieldnames = rows[0].keys()

    for row in rows:
        row["verify_channel_state_response"] = "채널 상태 최종 확인"
        row["retry_or_close_response"] = "최종 후속 조치 기록"
        if row["task_group"] == "closed":
            row["resolved_status"] = ReviewTaskStatus.IN_REVIEW
            row["resolution_notes"] = "archive 재검토 필요"
        else:
            row["resolved_status"] = ReviewTaskStatus.APPROVED
            row["resolution_notes"] = "executive-share 종료 확정"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    import_result = runner.invoke(
        app,
        [
            "review",
            "closure-import",
            "--closure-report",
            str(report_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "closure_resolution.json"
    artifact = read_model(resolution_path, OpsClosureResolutionArtifact)

    assert artifact.closed_task_count == 1
    assert artifact.remaining_task_count == 1
    assert {task.status for task in artifact.closed_tasks} == {ReviewTaskStatus.APPROVED}
    assert {task.status for task in artifact.remaining_tasks} == {ReviewTaskStatus.IN_REVIEW}
    assert all(task.checklist[0].response for task in [*artifact.closed_tasks, *artifact.remaining_tasks])
    assert all(task.checklist[1].response for task in [*artifact.closed_tasks, *artifact.remaining_tasks])


def test_review_closure_import_accepts_empty_report(tmp_path: Path) -> None:
    """빈 closure report는 header-only CSV로도 import되어야 한다."""

    report_path = tmp_path / "closure_report.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(report_path, _build_closure_report(empty=True))

    export_result = runner.invoke(
        app,
        [
            "review",
            "closure-export",
            "--closure-report",
            str(report_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = tmp_path / "closure_report.csv"
    import_result = runner.invoke(
        app,
        [
            "review",
            "closure-import",
            "--closure-report",
            str(report_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "closure_resolution.json"
    artifact = read_model(resolution_path, OpsClosureResolutionArtifact)

    assert artifact.closed_tasks == []
    assert artifact.remaining_tasks == []
    assert artifact.closed_task_count == 0
    assert artifact.remaining_task_count == 0
