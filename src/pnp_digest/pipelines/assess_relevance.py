"""assess-relevance stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.config import load_relevance_rules
from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import (
    ManualReviewItem,
    ManualReviewManifest,
    NormalizedArtifact,
    RelevanceArtifact,
    StageExecutionState,
)
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.relevance import assess_document_relevance


def run_assess_relevance(
    *,
    run_id: str,
    normalized_artifact_path: Path,
    artifact_root: Path,
    dictionary_dir: Path,
) -> tuple[RelevanceArtifact, ManualReviewManifest]:
    """normalized artifact를 읽어 관련성 판정 결과를 생성한다."""

    normalized_artifact = read_model(normalized_artifact_path, NormalizedArtifact)
    if normalized_artifact.run.run_id != run_id:
        raise ValueError("run_id와 normalized artifact의 run_id가 일치해야 합니다.")

    rules = load_relevance_rules(dictionary_dir)

    assessments = [
        assess_document_relevance(document, rules) for document in normalized_artifact.documents
    ]

    review_items = [
        ManualReviewItem(
            document_id=assessment.document_id,
            final_decision=assessment.final_decision,
            rule_score=assessment.rule_score,
            decision_reason=assessment.decision_reason,
            evidence_locators=[item.locator for item in assessment.evidence_links_or_snippets],
        )
        for assessment in assessments
        if assessment.review_required
    ]

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.ASSESS_RELEVANCE)

    updated_run = normalized_artifact.run.model_copy(
        update={
            "stage_status": {
                **normalized_artifact.run.stage_status,
                StageName.ASSESS_RELEVANCE: StageExecutionState(
                    status=StageExecutionStatus.COMPLETED,
                    artifact_path=str(stage_dir / "relevance_report.json"),
                    updated_at=datetime.now(UTC),
                    message=f"관련성 판정 {len(assessments)}건, 수동 검토 {len(review_items)}건",
                ),
            }
        }
    )

    relevance_artifact = RelevanceArtifact(run=updated_run, assessments=assessments)
    review_manifest = ManualReviewManifest(run_id=run_id, items=review_items)

    write_model(stage_dir / "relevance_report.json", relevance_artifact)
    write_model(stage_dir / "manual_review_manifest.json", review_manifest)

    return relevance_artifact, review_manifest
