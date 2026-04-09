"""followup stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import OpsFollowupManifest, OpsHandoffResolutionArtifact, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.followup import build_ops_followup_manifest
from pnp_digest.services.io import read_model, write_model


def run_followup(
    *,
    run_id: str,
    ops_handoff_resolution_path: Path,
    artifact_root: Path,
    followup_team: str = "ops",
) -> OpsFollowupManifest:
    """ops handoff resolution을 읽어 followup manifest를 생성한다."""

    resolution = read_model(ops_handoff_resolution_path, OpsHandoffResolutionArtifact)
    if resolution.run_id != run_id:
        raise ValueError("run_id와 ops handoff resolution의 run_id가 일치해야 합니다.")

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.FOLLOWUP)
    manifest_path = stage_dir / "followup_manifest.json"

    manifest = build_ops_followup_manifest(
        resolution,
        source_ops_handoff_resolution_path=ops_handoff_resolution_path,
        followup_team=followup_team,
    )

    stage_status = StageExecutionStatus.COMPLETED
    message = f"followup task {len(manifest.tasks)}건 정리 완료"
    if not manifest.tasks:
        stage_status = StageExecutionStatus.SKIPPED
        message = manifest.blocked_reason or "followup 대상이 없다."

    updated_run = resolution.run.model_copy(
        update={
            "stage_status": {
                **resolution.run.stage_status,
                StageName.FOLLOWUP: StageExecutionState(
                    status=stage_status,
                    artifact_path=str(manifest_path),
                    updated_at=datetime.now(UTC),
                    message=message,
                ),
            }
        }
    )

    artifact = manifest.model_copy(update={"run": updated_run})
    write_model(manifest_path, artifact)
    return artifact
