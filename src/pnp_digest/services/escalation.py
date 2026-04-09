"""followup resolution 결과에서 escalation manifest를 생성하는 유틸리티."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain import ReviewTaskStatus
from pnp_digest.domain.models import OpsEscalationManifest, OpsFollowupResolutionArtifact


def build_ops_escalation_manifest(
    resolution: OpsFollowupResolutionArtifact,
    *,
    source_followup_resolution_path: Path,
    escalation_team: str = "ops-lead",
) -> OpsEscalationManifest:
    """followup resolution에서 in_review task만 추린 escalation manifest를 만든다."""

    escalation_tasks = [
        task
        for task in resolution.tasks
        if task.status == ReviewTaskStatus.IN_REVIEW
    ]

    return OpsEscalationManifest(
        run=resolution.run,
        run_id=resolution.run_id,
        source_followup_resolution_path=str(source_followup_resolution_path),
        escalation_team=escalation_team,
        generated_at=datetime.now(UTC),
        blocked_reason=resolution.blocked_reason,
        in_review_task_count=len(escalation_tasks),
        tasks=escalation_tasks,
    )
