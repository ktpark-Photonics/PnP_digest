"""closure stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import OpsClosureReport, OpsEscalationResolutionArtifact, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.closure import build_ops_closure_report
from pnp_digest.services.io import read_model, write_model


def run_closure(
    *,
    run_id: str,
    escalation_resolution_path: Path,
    artifact_root: Path,
    closure_team: str = "ops-lead",
) -> OpsClosureReport:
    """escalation resolution을 읽어 closure report를 생성한다."""

    resolution = read_model(escalation_resolution_path, OpsEscalationResolutionArtifact)
    if resolution.run_id != run_id:
        raise ValueError("run_id와 escalation resolution의 run_id가 일치해야 합니다.")

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.CLOSURE)
    report_path = stage_dir / "closure_report.json"

    report = build_ops_closure_report(
        resolution,
        source_escalation_resolution_path=escalation_resolution_path,
        closure_team=closure_team,
    )

    stage_status = StageExecutionStatus.COMPLETED
    message = (
        f"closure report 정리 완료: closed {report.closed_task_count}건, "
        f"remaining {report.remaining_task_count}건"
    )
    if not resolution.tasks:
        stage_status = StageExecutionStatus.SKIPPED
        message = report.blocked_reason or "closure 대상으로 정리할 task가 없다."

    updated_run = resolution.run.model_copy(
        update={
            "stage_status": {
                **resolution.run.stage_status,
                StageName.CLOSURE: StageExecutionState(
                    status=stage_status,
                    artifact_path=str(report_path),
                    updated_at=datetime.now(UTC),
                    message=message,
                ),
            }
        }
    )

    artifact = report.model_copy(update={"run": updated_run})
    write_model(report_path, artifact)
    return artifact
