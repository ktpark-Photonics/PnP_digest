"""closure report CSV export/import 유틸리티."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from pnp_digest.domain import ReviewTaskStatus
from pnp_digest.domain.models import (
    OpsClosureReport,
    OpsClosureResolutionArtifact,
    ReviewChecklistItem,
    ReviewTask,
)
from pnp_digest.services.io import ensure_directory

_CLOSURE_REVIEW_REQUIRED_COLUMNS = {
    "run_id",
    "closure_team",
    "blocked_reason",
    "task_group",
    "review_task_id",
    "target_type",
    "target_id",
    "assignee",
    "status",
    "task_notes",
    "verify_channel_state_response",
    "retry_or_close_response",
    "resolved_status",
    "resolution_notes",
    "reviewed_at",
}


def default_closure_review_export_path(source_closure_report_path: Path) -> Path:
    """입력 closure report 기준 기본 CSV 경로를 만든다."""

    return source_closure_report_path.with_suffix(".csv")


def _checklist_response(task: ReviewTask, item_id: str) -> str:
    """체크리스트 항목 응답을 안전하게 꺼낸다."""

    checklist_by_id = {item.item_id: item for item in task.checklist}
    item = checklist_by_id.get(item_id, ReviewChecklistItem(item_id="", prompt=""))
    return item.response or ""


def export_closure_report(
    report: OpsClosureReport,
    *,
    source_closure_report_path: Path,
    output_path: Path | None = None,
) -> Path:
    """closure report를 사람이 확인할 CSV로 저장한다."""

    resolved_output_path = output_path or default_closure_review_export_path(source_closure_report_path)
    ensure_directory(resolved_output_path.parent)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "run_id",
            "closure_team",
            "blocked_reason",
            "task_group",
            "review_task_id",
            "target_type",
            "target_id",
            "assignee",
            "status",
            "task_notes",
            "verify_channel_state_response",
            "retry_or_close_response",
            "resolved_status",
            "resolution_notes",
            "reviewed_at",
        ]
    )

    for task_group, tasks in (
        ("closed", report.closed_tasks),
        ("remaining", report.remaining_tasks),
    ):
        for task in tasks:
            writer.writerow(
                [
                    report.run_id,
                    report.closure_team,
                    report.blocked_reason or "",
                    task_group,
                    task.review_task_id,
                    task.target_type,
                    task.target_id,
                    task.assignee or "",
                    task.status,
                    task.notes or "",
                    _checklist_response(task, "verify_channel_state"),
                    _checklist_response(task, "retry_or_close"),
                    task.status,
                    "",
                    task.reviewed_at.isoformat() if task.reviewed_at else "",
                ]
            )

    resolved_output_path.write_text(buffer.getvalue(), encoding="utf-8")
    return resolved_output_path


def _validate_columns(fieldnames: list[str] | None) -> None:
    """CSV header가 필요한 컬럼을 모두 포함하는지 확인한다."""

    actual_columns = set(fieldnames or [])
    missing_columns = sorted(_CLOSURE_REVIEW_REQUIRED_COLUMNS - actual_columns)
    if missing_columns:
        raise ValueError(
            "closure review import CSV에 필요한 컬럼이 없습니다: " + ", ".join(missing_columns)
        )


def _parse_task_status(value: str | None, *, default: ReviewTaskStatus) -> ReviewTaskStatus:
    """CSV task status 값을 enum으로 변환한다."""

    normalized = (value or "").strip().lower()
    if not normalized:
        return default

    try:
        return ReviewTaskStatus(normalized)
    except ValueError as error:
        raise ValueError("resolved_status는 open, in_review, approved, rejected 중 하나여야 합니다.") from error


def _task_map(report: OpsClosureReport) -> dict[str, ReviewTask]:
    """task ID 기준 원본 task 맵을 만든다."""

    tasks = [*report.closed_tasks, *report.remaining_tasks]
    return {task.review_task_id: task for task in tasks}


def _expected_group(task: ReviewTask, report: OpsClosureReport) -> str:
    """task가 원본 report에서 속한 그룹 이름을 반환한다."""

    closed_task_ids = {item.review_task_id for item in report.closed_tasks}
    return "closed" if task.review_task_id in closed_task_ids else "remaining"


def _validate_readonly_columns(report: OpsClosureReport, rows: list[dict[str, str]]) -> None:
    """CSV의 읽기 전용 컬럼이 원본 closure report와 일치하는지 확인한다."""

    task_map = _task_map(report)
    seen_task_ids: set[str] = set()
    for row in rows:
        task_id = (row.get("review_task_id") or "").strip()
        if task_id in seen_task_ids:
            raise ValueError(f"closure review import CSV에 중복 task가 있습니다: {task_id}")
        seen_task_ids.add(task_id)

        if task_id not in task_map:
            raise ValueError(f"closure review import CSV에 원본 report에 없는 task가 있습니다: {task_id}")

        task = task_map[task_id]
        expected_values = {
            "run_id": report.run_id,
            "closure_team": report.closure_team,
            "blocked_reason": report.blocked_reason or "",
            "task_group": _expected_group(task, report),
            "review_task_id": task.review_task_id,
            "target_type": task.target_type,
            "target_id": task.target_id,
            "assignee": task.assignee or "",
            "status": str(task.status),
            "task_notes": task.notes or "",
            "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else "",
        }
        mismatched_columns = [
            column_name
            for column_name, expected_value in expected_values.items()
            if (row.get(column_name) or "").strip() != expected_value
        ]
        if mismatched_columns:
            raise ValueError(
                "closure review import CSV의 읽기 전용 컬럼이 원본 report와 다릅니다: "
                + ", ".join(mismatched_columns)
            )


def build_ops_closure_resolution_artifact(
    report: OpsClosureReport,
    *,
    source_closure_report_path: Path,
    review_csv_path: Path,
) -> OpsClosureResolutionArtifact:
    """사람이 수정한 closure review CSV를 JSON artifact로 변환한다."""

    with review_csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames)
        rows = list(reader)

    original_tasks = _task_map(report)
    total_task_count = len(original_tasks)
    if total_task_count and len(rows) != total_task_count:
        raise ValueError("closure review import CSV row 수가 원본 closure task 수와 다릅니다.")
    if not total_task_count and rows:
        raise ValueError("원본 closure report에 task가 없으므로 CSV에도 데이터 행이 있으면 안 됩니다.")

    _validate_readonly_columns(report, rows)
    imported_at = datetime.now(UTC)

    updated_tasks: list[ReviewTask] = []
    for row in rows:
        original_task = original_tasks[(row.get("review_task_id") or "").strip()]
        resolved_status = _parse_task_status(row.get("resolved_status"), default=original_task.status)
        checklist_by_id = {item.item_id: item for item in original_task.checklist}
        updated_tasks.append(
            original_task.model_copy(
                update={
                    "status": resolved_status,
                    "checklist": [
                        checklist_by_id["verify_channel_state"].model_copy(
                            update={
                                "response": (row.get("verify_channel_state_response") or "").strip() or None
                            }
                        ),
                        checklist_by_id["retry_or_close"].model_copy(
                            update={"response": (row.get("retry_or_close_response") or "").strip() or None}
                        ),
                    ],
                    "notes": (row.get("resolution_notes") or "").strip() or original_task.notes,
                    "reviewed_at": imported_at if resolved_status != ReviewTaskStatus.OPEN else None,
                }
            )
        )

    closed_tasks = [
        task
        for task in updated_tasks
        if task.status in {ReviewTaskStatus.APPROVED, ReviewTaskStatus.REJECTED}
    ]
    remaining_tasks = [
        task
        for task in updated_tasks
        if task.status in {ReviewTaskStatus.OPEN, ReviewTaskStatus.IN_REVIEW}
    ]

    return OpsClosureResolutionArtifact(
        run=report.run,
        run_id=report.run_id,
        source_closure_report_path=str(source_closure_report_path),
        imported_csv_path=str(review_csv_path),
        imported_at=imported_at,
        closure_team=report.closure_team,
        blocked_reason=report.blocked_reason,
        closed_task_count=len(closed_tasks),
        remaining_task_count=len(remaining_tasks),
        closed_tasks=closed_tasks,
        remaining_tasks=remaining_tasks,
    )
