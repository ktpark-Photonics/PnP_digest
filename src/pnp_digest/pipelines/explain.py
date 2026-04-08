"""explain stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import ExplainArtifact, StageExecutionState, SummaryArtifact
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.explanation import build_explain_record
from pnp_digest.services.io import read_model, write_model


def run_explain(
    *,
    run_id: str,
    summary_artifact_path: Path,
    artifact_root: Path,
) -> ExplainArtifact:
    """summary artifact를 읽어 explain artifact를 생성한다."""

    summary_artifact = read_model(summary_artifact_path, SummaryArtifact)
    if summary_artifact.run.run_id != run_id:
        raise ValueError("run_id와 summary artifact의 run_id가 일치해야 합니다.")

    explanations = [
        build_explain_record(summary_record)
        for summary_record in summary_artifact.summaries
    ]

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.EXPLAIN)
    artifact_path = stage_dir / "explain_artifact.json"

    updated_run = summary_artifact.run.model_copy(
        update={
            "stage_status": {
                **summary_artifact.run.stage_status,
                StageName.EXPLAIN: StageExecutionState(
                    status=StageExecutionStatus.COMPLETED,
                    artifact_path=str(artifact_path),
                    updated_at=datetime.now(UTC),
                    message=f"직급별 설명 {len(explanations)}건 생성 완료",
                ),
            }
        }
    )

    artifact = ExplainArtifact(run=updated_run, explanations=explanations)
    write_model(artifact_path, artifact)
    return artifact
