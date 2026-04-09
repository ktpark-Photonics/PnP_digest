"""retry stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import PublishReviewResolutionArtifact, PublishRetryManifest, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.retry_manifest import build_publish_retry_manifest


def run_retry(
    *,
    run_id: str,
    publish_review_resolution_path: Path,
    artifact_root: Path,
) -> PublishRetryManifest:
    """publish review resolution을 읽어 retry manifest를 생성한다."""

    resolution = read_model(publish_review_resolution_path, PublishReviewResolutionArtifact)
    if resolution.run_id != run_id:
        raise ValueError("run_id와 publish review resolution의 run_id가 일치해야 합니다.")

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.RETRY)
    retry_manifest_path = stage_dir / "retry_manifest.json"

    retry_manifest = build_publish_retry_manifest(
        resolution,
        source_publish_review_resolution_path=publish_review_resolution_path,
    )

    stage_status = StageExecutionStatus.COMPLETED
    message = f"retry 대상 {retry_manifest.retry_count}건 정리 완료"
    if retry_manifest.retry_count == 0:
        stage_status = StageExecutionStatus.SKIPPED
        message = retry_manifest.blocked_reason or "retry 대상이 없다."

    updated_run = resolution.run.model_copy(
        update={
            "stage_status": {
                **resolution.run.stage_status,
                StageName.RETRY: StageExecutionState(
                    status=stage_status,
                    artifact_path=str(retry_manifest_path),
                    updated_at=datetime.now(UTC),
                    message=message,
                ),
            }
        }
    )

    artifact = retry_manifest.model_copy(update={"run": updated_run})
    write_model(retry_manifest_path, artifact)
    return artifact
