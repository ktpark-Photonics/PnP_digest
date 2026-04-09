"""publish stub artifact 생성 유틸리티."""

from __future__ import annotations

from datetime import UTC, datetime

from pnp_digest.domain.enums import PublishStatus, ReviewStatus
from pnp_digest.domain.models import PublishArtifact, PublishRecord, ReleaseReviewResolutionArtifact


def build_publish_artifact(
    release_review_resolution: ReleaseReviewResolutionArtifact,
    *,
    source_release_review_resolution_path: str,
) -> PublishArtifact:
    """release review resolution을 publish stub artifact로 변환한다."""

    blocked_reason: str | None = None
    publish_records: list[PublishRecord] = []

    if release_review_resolution.review_signoff != ReviewStatus.APPROVED:
        blocked_reason = (
            "final release signoff가 approved가 아니므로 publish를 진행하지 않았다: "
            f"{release_review_resolution.review_signoff}"
        )
    elif not release_review_resolution.approved_bundle_ids:
        blocked_reason = "approved bundle이 없어 publish를 진행하지 않았다."
    else:
        approved_bundle_ids = set(release_review_resolution.approved_bundle_ids)
        published_at = datetime.now(UTC)
        for bundle in release_review_resolution.bundles:
            if bundle.bundle_id not in approved_bundle_ids:
                continue
            for target in release_review_resolution.distribution_targets:
                publish_records.append(
                    PublishRecord(
                        bundle_id=bundle.bundle_id,
                        output_type=bundle.output_type,
                        output_path=bundle.output_path,
                        distribution_target=target,
                        status=PublishStatus.SIMULATED,
                        published_at=published_at,
                        external_reference=None,
                        notes="실제 외부 배포 없이 publish stub artifact만 생성했다.",
                    )
                )

    return PublishArtifact(
        run=release_review_resolution.run,
        source_release_review_resolution_path=source_release_review_resolution_path,
        review_signoff=release_review_resolution.review_signoff,
        reviewer=release_review_resolution.reviewer,
        distribution_targets=release_review_resolution.distribution_targets,
        simulation_mode=True,
        blocked_reason=blocked_reason,
        publish_records=publish_records,
    )
