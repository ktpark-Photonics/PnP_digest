"""closure report 생성 유틸리티."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain import ReviewTaskStatus
from pnp_digest.domain.models import OpsClosureReport, OpsEscalationResolutionArtifact


def build_ops_closure_report(
    resolution: OpsEscalationResolutionArtifact,
    *,
    source_escalation_resolution_path: Path,
    closure_team: str = "ops-lead",
) -> OpsClosureReport:
    """escalation resolution에서 닫힌 항목과 남은 항목을 나눠 closure report를 만든다."""

    closed_tasks = [
        task
        for task in resolution.tasks
        if task.status in {ReviewTaskStatus.APPROVED, ReviewTaskStatus.REJECTED}
    ]
    remaining_tasks = [
        task
        for task in resolution.tasks
        if task.status in {ReviewTaskStatus.OPEN, ReviewTaskStatus.IN_REVIEW}
    ]

    blocked_reason = resolution.blocked_reason if resolution.tasks else (
        resolution.blocked_reason or "closure 대상으로 정리할 task가 없다."
    )

    return OpsClosureReport(
        run=resolution.run,
        run_id=resolution.run_id,
        source_escalation_resolution_path=str(source_escalation_resolution_path),
        closure_team=closure_team,
        generated_at=datetime.now(UTC),
        blocked_reason=blocked_reason,
        closed_task_count=len(closed_tasks),
        remaining_task_count=len(remaining_tasks),
        closed_tasks=closed_tasks,
        remaining_tasks=remaining_tasks,
    )
