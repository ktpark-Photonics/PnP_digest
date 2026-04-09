"""escalation manifest 수동 확인 CSV export/import 유틸리티."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from pnp_digest.domain import ReviewTaskStatus
from pnp_digest.domain.models import (
    OpsEscalationManifest,
    OpsEscalationResolutionArtifact,
    ReviewChecklistItem,
    ReviewTask,
)
from pnp_digest.services.io import ensure_directory

ESCALATION_REVIEW_REQUIRED_COLUMNS = {
    "run_id",
    "escalation_team",
    "blocked_reason",
    "review_task_id",
    "target_type",
    "target_id",
    "assignee",
    "initial_status",
    "task_notes",
    "verify_channel_state_response",
    "retry_or_close_response",
    "resolved_status",
    "resolution_notes",
    "reviewed_at",
}


def default_escalation_review_export_path(source_escalation_manifest_path: Path) -> Path:
    """입력 escalation manifest 기준 기본 CSV 경로를 만든다."""

    return source_escalation_manifest_path.with_name("ops_escalation_queue.csv")


def export_escalation_review_manifest(
    manifest: OpsEscalationManifest,
    *,
    source_escalation_manifest_path: Path,
    output_path: Path | None = None,
) -> Path:
    """escalation manifest를 사람이 수정할 CSV 큐로 저장한다."""

    resolved_output_path = output_path or default_escalation_review_export_path(
        source_escalation_manifest_path
    )
    ensure_directory(resolved_output_path.parent)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "run_id",
            "escalation_team",
            "blocked_reason",
            "review_task_id",
            "target_type",
            "target_id",
            "assignee",
            "initial_status",
            "task_notes",
            "verify_channel_state_response",
            "retry_or_close_response",
            "resolved_status",
            "resolution_notes",
            "reviewed_at",
        ]
    )

    for task in manifest.tasks:
        checklist_by_id = {item.item_id: item for item in task.checklist}
        writer.writerow(
            [
                manifest.run_id,
                manifest.escalation_team,
                manifest.blocked_reason or "",
                task.review_task_id,
                task.target_type,
                task.target_id,
                task.assignee or "",
                task.status,
                task.notes or "",
                checklist_by_id.get("verify_channel_state", ReviewChecklistItem(item_id="", prompt="")).response
                or "",
                checklist_by_id.get("retry_or_close", ReviewChecklistItem(item_id="", prompt="")).response or "",
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
    missing_columns = sorted(ESCALATION_REVIEW_REQUIRED_COLUMNS - actual_columns)
    if missing_columns:
        raise ValueError(
            "escalation review import CSV에 필요한 컬럼이 없습니다: "
            + ", ".join(missing_columns)
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


def _task_map(manifest: OpsEscalationManifest) -> dict[str, ReviewTask]:
    """task ID 기준 원본 task 맵을 만든다."""

    return {task.review_task_id: task for task in manifest.tasks}


def _validate_readonly_columns(manifest: OpsEscalationManifest, rows: list[dict[str, str]]) -> None:
    """CSV의 읽기 전용 컬럼이 원본 escalation manifest와 일치하는지 확인한다."""

    task_map = _task_map(manifest)
    seen_task_ids: set[str] = set()
    for row in rows:
        task_id = (row.get("review_task_id") or "").strip()
        if task_id in seen_task_ids:
            raise ValueError(f"escalation review import CSV에 중복 task가 있습니다: {task_id}")
        seen_task_ids.add(task_id)

        if task_id not in task_map:
            raise ValueError(
                f"escalation review import CSV에 원본 manifest에 없는 task가 있습니다: {task_id}"
            )

        task = task_map[task_id]
        expected_values = {
            "run_id": manifest.run_id,
            "escalation_team": manifest.escalation_team,
            "blocked_reason": manifest.blocked_reason or "",
            "review_task_id": task.review_task_id,
            "target_type": task.target_type,
            "target_id": task.target_id,
            "assignee": task.assignee or "",
            "initial_status": str(task.status),
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
                "escalation review import CSV의 읽기 전용 컬럼이 원본 manifest와 다릅니다: "
                + ", ".join(mismatched_columns)
            )


def build_ops_escalation_resolution_artifact(
    manifest: OpsEscalationManifest,
    *,
    source_escalation_manifest_path: Path,
    review_csv_path: Path,
) -> OpsEscalationResolutionArtifact:
    """사람이 수정한 escalation review CSV를 JSON artifact로 변환한다."""

    with review_csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames)
        rows = list(reader)

    if manifest.tasks and len(rows) != len(manifest.tasks):
        raise ValueError("escalation review import CSV row 수가 원본 escalation task 수와 다릅니다.")
    if not manifest.tasks and rows:
        raise ValueError("원본 escalation manifest에 task가 없으므로 CSV에도 데이터 행이 있으면 안 됩니다.")

    _validate_readonly_columns(manifest, rows)
    original_tasks = _task_map(manifest)
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

    open_task_count = sum(1 for task in updated_tasks if task.status == ReviewTaskStatus.OPEN)
    in_review_task_count = sum(1 for task in updated_tasks if task.status == ReviewTaskStatus.IN_REVIEW)
    closed_task_count = sum(
        1 for task in updated_tasks if task.status in {ReviewTaskStatus.APPROVED, ReviewTaskStatus.REJECTED}
    )

    return OpsEscalationResolutionArtifact(
        run=manifest.run,
        run_id=manifest.run_id,
        source_escalation_manifest_path=str(source_escalation_manifest_path),
        imported_csv_path=str(review_csv_path),
        imported_at=imported_at,
        escalation_team=manifest.escalation_team,
        blocked_reason=manifest.blocked_reason,
        open_task_count=open_task_count,
        in_review_task_count=in_review_task_count,
        closed_task_count=closed_task_count,
        tasks=updated_tasks,
    )
