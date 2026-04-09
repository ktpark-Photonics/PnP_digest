"""escalation stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import OpsEscalationManifest, OpsFollowupResolutionArtifact, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.escalation import build_ops_escalation_manifest
from pnp_digest.services.io import read_model, write_model


def run_escalation(
    *,
    run_id: str,
    followup_resolution_path: Path,
    artifact_root: Path,
    escalation_team: str = "ops-lead",
) -> OpsEscalationManifest:
    """followup resolution을 읽어 escalation manifest를 생성한다."""

    resolution = read_model(followup_resolution_path, OpsFollowupResolutionArtifact)
    if resolution.run_id != run_id:
        raise ValueError("run_id와 followup resolution의 run_id가 일치해야 합니다.")

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.ESCALATION)
    manifest_path = stage_dir / "escalation_manifest.json"

    manifest = build_ops_escalation_manifest(
        resolution,
        source_followup_resolution_path=followup_resolution_path,
        escalation_team=escalation_team,
    )

    stage_status = StageExecutionStatus.COMPLETED
    message = f"escalation task {len(manifest.tasks)}건 정리 완료"
    if not manifest.tasks:
        stage_status = StageExecutionStatus.SKIPPED
        message = manifest.blocked_reason or "escalation 대상이 없다."

    updated_run = resolution.run.model_copy(
        update={
            "stage_status": {
                **resolution.run.stage_status,
                StageName.ESCALATION: StageExecutionState(
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
