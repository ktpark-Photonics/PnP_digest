"""publish stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import ReviewStatus, StageExecutionStatus, StageName
from pnp_digest.domain.models import PublishArtifact, ReleaseReviewResolutionArtifact, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.publishing import build_publish_artifact


def run_publish(
    *,
    run_id: str,
    release_review_resolution_path: Path,
    artifact_root: Path,
) -> PublishArtifact:
    """release review resolution을 읽어 publish stub artifact를 생성한다."""

    resolution = read_model(release_review_resolution_path, ReleaseReviewResolutionArtifact)
    if resolution.run_id != run_id:
        raise ValueError("run_id와 release review resolution의 run_id가 일치해야 합니다.")

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.PUBLISH)
    publish_artifact_path = stage_dir / "publish_artifact.json"

    publish_artifact = build_publish_artifact(
        resolution,
        source_release_review_resolution_path=str(release_review_resolution_path),
    )

    stage_status = StageExecutionStatus.COMPLETED
    message = f"publish stub {len(publish_artifact.publish_records)}건 생성 완료"
    if publish_artifact.review_signoff != ReviewStatus.APPROVED or publish_artifact.blocked_reason is not None:
        stage_status = StageExecutionStatus.SKIPPED
        message = publish_artifact.blocked_reason or "publish가 차단되었다."

    updated_run = resolution.run.model_copy(
        update={
            "stage_status": {
                **resolution.run.stage_status,
                StageName.PUBLISH: StageExecutionState(
                    status=stage_status,
                    artifact_path=str(publish_artifact_path),
                    updated_at=datetime.now(UTC),
                    message=message,
                ),
            }
        }
    )

    artifact = publish_artifact.model_copy(update={"run": updated_run})
    write_model(publish_artifact_path, artifact)
    return artifact
