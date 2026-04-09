"""handoff resolution 결과에서 followup manifest를 생성하는 유틸리티."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain import ReviewTaskStatus
from pnp_digest.domain.models import OpsFollowupManifest, OpsHandoffResolutionArtifact


def build_ops_followup_manifest(
    resolution: OpsHandoffResolutionArtifact,
    *,
    source_ops_handoff_resolution_path: Path,
    followup_team: str = "ops",
) -> OpsFollowupManifest:
    """handoff resolution에서 아직 남아 있는 task만 추린 manifest를 만든다."""

    followup_tasks = [
        task
        for task in resolution.tasks
        if task.status in {ReviewTaskStatus.OPEN, ReviewTaskStatus.IN_REVIEW}
    ]

    return OpsFollowupManifest(
        run=resolution.run,
        run_id=resolution.run_id,
        source_ops_handoff_resolution_path=str(source_ops_handoff_resolution_path),
        followup_team=followup_team,
        generated_at=datetime.now(UTC),
        blocked_reason=resolution.blocked_reason,
        open_task_count=sum(1 for task in followup_tasks if task.status == ReviewTaskStatus.OPEN),
        in_review_task_count=sum(1 for task in followup_tasks if task.status == ReviewTaskStatus.IN_REVIEW),
        tasks=followup_tasks,
    )
