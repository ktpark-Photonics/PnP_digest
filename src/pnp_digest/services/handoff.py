"""retry 결과를 운영 handoff task로 변환하는 유틸리티."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain import ReviewStage, ReviewTaskStatus
from pnp_digest.domain.models import OpsHandoffArtifact, PublishRetryManifest, ReviewChecklistItem, ReviewTask


def _build_task_notes(bundle_target: str, retry_reason: str, recommended_action: str, output_path: str) -> str:
    """운영 전달용 task 메모를 구성한다."""

    return (
        f"대상: {bundle_target}\n"
        f"재시도 사유: {retry_reason}\n"
        f"권장 조치: {recommended_action}\n"
        f"출력 경로: {output_path}"
    )


def build_ops_handoff_artifact(
    retry_manifest: PublishRetryManifest,
    *,
    source_retry_manifest_path: Path,
    handoff_team: str = "ops",
) -> OpsHandoffArtifact:
    """retry manifest를 운영 전달용 handoff artifact로 변환한다."""

    tasks = [
        ReviewTask(
            review_task_id=f"{retry_manifest.run_id}:handoff:{index}",
            target_type="publish_retry",
            target_id=f"{item.bundle_id}:{item.distribution_target}",
            review_stage=ReviewStage.PUBLISH,
            assignee=handoff_team,
            status=ReviewTaskStatus.OPEN,
            checklist=[
                ReviewChecklistItem(
                    item_id="verify_channel_state",
                    prompt="실제 채널 상태와 외부 참조값을 확인했는가?",
                ),
                ReviewChecklistItem(
                    item_id="retry_or_close",
                    prompt="재배포를 수행했거나 불필요 사유를 기록했는가?",
                ),
            ],
            notes=_build_task_notes(
                f"{item.bundle_id} / {item.distribution_target}",
                item.retry_reason,
                item.recommended_action,
                item.output_path,
            ),
        )
        for index, item in enumerate(retry_manifest.items, start=1)
    ]

    return OpsHandoffArtifact(
        run=retry_manifest.run,
        run_id=retry_manifest.run_id,
        source_retry_manifest_path=str(source_retry_manifest_path),
        handoff_team=handoff_team,
        generated_at=datetime.now(UTC),
        blocked_reason=retry_manifest.blocked_reason,
        open_task_count=len(tasks),
        tasks=tasks,
    )
