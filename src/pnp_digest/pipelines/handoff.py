"""handoff stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import OpsHandoffArtifact, PublishRetryManifest, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.handoff import build_ops_handoff_artifact
from pnp_digest.services.io import read_model, write_model


def run_handoff(
    *,
    run_id: str,
    retry_manifest_path: Path,
    artifact_root: Path,
    handoff_team: str = "ops",
) -> OpsHandoffArtifact:
    """retry manifest를 운영 handoff artifact로 저장한다."""

    retry_manifest = read_model(retry_manifest_path, PublishRetryManifest)
    if retry_manifest.run_id != run_id:
        raise ValueError("run_id와 retry manifest의 run_id가 일치해야 합니다.")

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.HANDOFF)
    handoff_artifact_path = stage_dir / "ops_handoff.json"

    handoff_artifact = build_ops_handoff_artifact(
        retry_manifest,
        source_retry_manifest_path=retry_manifest_path,
        handoff_team=handoff_team,
    )

    stage_status = StageExecutionStatus.COMPLETED
    message = f"handoff task {handoff_artifact.open_task_count}건 생성 완료"
    if handoff_artifact.open_task_count == 0:
        stage_status = StageExecutionStatus.SKIPPED
        message = handoff_artifact.blocked_reason or "handoff 대상이 없다."

    updated_run = retry_manifest.run.model_copy(
        update={
            "stage_status": {
                **retry_manifest.run.stage_status,
                StageName.HANDOFF: StageExecutionState(
                    status=stage_status,
                    artifact_path=str(handoff_artifact_path),
                    updated_at=datetime.now(UTC),
                    message=message,
                ),
            }
        }
    )

    artifact = handoff_artifact.model_copy(update={"run": updated_run})
    write_model(handoff_artifact_path, artifact)
    return artifact
