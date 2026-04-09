"""followup manifest를 운영용 CSV 큐로 내보내는 유틸리티."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from pnp_digest.domain.models import OpsFollowupManifest
from pnp_digest.services.io import ensure_directory


def default_followup_queue_export_path(source_followup_manifest_path: Path) -> Path:
    """입력 followup manifest 기준 기본 CSV 경로를 만든다."""

    return source_followup_manifest_path.with_name("ops_daily_queue.csv")


def export_ops_daily_queue(
    manifest: OpsFollowupManifest,
    *,
    source_followup_manifest_path: Path,
    output_path: Path | None = None,
) -> Path:
    """followup manifest를 운영용 CSV 큐로 저장한다."""

    resolved_output_path = output_path or default_followup_queue_export_path(source_followup_manifest_path)
    ensure_directory(resolved_output_path.parent)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "run_id",
            "followup_team",
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
                manifest.followup_team,
                manifest.blocked_reason or "",
                task.review_task_id,
                task.target_type,
                task.target_id,
                task.assignee or "",
                task.status,
                task.notes or "",
                checklist_by_id.get("verify_channel_state", None).response if "verify_channel_state" in checklist_by_id else "",
                checklist_by_id.get("retry_or_close", None).response if "retry_or_close" in checklist_by_id else "",
                task.status,
                "",
                task.reviewed_at.isoformat() if task.reviewed_at else "",
            ]
        )

    resolved_output_path.write_text(buffer.getvalue(), encoding="utf-8")
    return resolved_output_path
