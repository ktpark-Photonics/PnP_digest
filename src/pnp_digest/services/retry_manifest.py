"""publish review 결과에서 retry manifest를 생성하는 유틸리티."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain import PublishStatus
from pnp_digest.domain.models import PublishRetryItem, PublishRetryManifest, PublishReviewResolutionArtifact


def _retry_reason_for_status(status: PublishStatus, review_notes: str | None) -> str:
    """채널 상태에 맞는 재시도 사유를 만든다."""

    if review_notes:
        return review_notes
    if status == PublishStatus.FAILED:
        return "채널 상태가 failed로 확정되어 재시도가 필요하다."
    return "채널 상태가 아직 simulated로 남아 있어 게시 여부 확인 또는 재시도가 필요하다."


def _recommended_action_for_status(status: PublishStatus) -> str:
    """채널 상태에 맞는 권장 후속 조치를 반환한다."""

    if status == PublishStatus.FAILED:
        return "권한, 업로드 경로, 외부 참조값을 점검한 뒤 해당 채널만 다시 publish한다."
    return "실제 게시 여부를 먼저 확인하고, 미게시 상태면 해당 채널만 다시 publish한다."


def build_publish_retry_manifest(
    resolution: PublishReviewResolutionArtifact,
    *,
    source_publish_review_resolution_path: Path,
) -> PublishRetryManifest:
    """publish review resolution에서 retry 대상만 추린 manifest를 만든다."""

    items = [
        PublishRetryItem(
            bundle_id=record.bundle_id,
            output_type=record.output_type,
            output_path=record.output_path,
            distribution_target=record.distribution_target,
            current_status=record.reviewed_status,
            external_reference=record.external_reference,
            retry_reason=_retry_reason_for_status(record.reviewed_status, record.record_notes),
            recommended_action=_recommended_action_for_status(record.reviewed_status),
            review_notes=record.record_notes,
        )
        for record in resolution.records
        if record.reviewed_status in {PublishStatus.FAILED, PublishStatus.SIMULATED}
    ]

    return PublishRetryManifest(
        run=resolution.run,
        run_id=resolution.run_id,
        source_publish_review_resolution_path=str(source_publish_review_resolution_path),
        review_signoff=resolution.review_signoff,
        reviewer=resolution.reviewer,
        generated_at=datetime.now(UTC),
        blocked_reason=resolution.blocked_reason,
        retry_count=len(items),
        items=items,
    )
