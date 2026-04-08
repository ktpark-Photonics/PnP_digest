"""summarize stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain import ReviewStatus
from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import (
    NormalizedArtifact,
    StageExecutionState,
    SummaryArtifact,
    VerificationReviewResolutionArtifact,
)
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.summarization import build_summary_record


def run_summarize(
    *,
    run_id: str,
    normalized_artifact_path: Path,
    verification_review_resolution_path: Path,
    artifact_root: Path,
) -> SummaryArtifact:
    """승인된 verification review 결과만 요약 artifact로 변환한다."""

    normalized_artifact = read_model(normalized_artifact_path, NormalizedArtifact)
    review_resolution = read_model(
        verification_review_resolution_path,
        VerificationReviewResolutionArtifact,
    )

    if normalized_artifact.run.run_id != run_id:
        raise ValueError("run_id와 normalized artifact의 run_id가 일치해야 합니다.")
    if review_resolution.run_id != run_id:
        raise ValueError("run_id와 verification review resolution의 run_id가 일치해야 합니다.")

    approved_items = {
        item.document_id: item
        for item in review_resolution.items
        if item.review_status == ReviewStatus.APPROVED
    }
    documents_by_id = {document.document_id: document for document in normalized_artifact.documents}

    missing_document_ids = sorted(set(approved_items) - set(documents_by_id))
    if missing_document_ids:
        raise ValueError(
            "approved review 결과에 대응하는 normalized document가 없습니다: "
            + ", ".join(missing_document_ids)
        )

    summaries = [
        build_summary_record(documents_by_id[document_id], approved_items[document_id])
        for document_id in sorted(approved_items)
    ]

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.SUMMARIZE)
    artifact_path = stage_dir / "summary_artifact.json"

    updated_run = normalized_artifact.run.model_copy(
        update={
            "stage_status": {
                **normalized_artifact.run.stage_status,
                StageName.SUMMARIZE: StageExecutionState(
                    status=StageExecutionStatus.COMPLETED,
                    artifact_path=str(artifact_path),
                    updated_at=datetime.now(UTC),
                    message=(
                        f"승인 문헌 {len(summaries)}건에 대한 placeholder summary 생성 완료"
                    ),
                ),
            }
        }
    )
    artifact = SummaryArtifact(run=updated_run, summaries=summaries)
    write_model(artifact_path, artifact)
    return artifact
