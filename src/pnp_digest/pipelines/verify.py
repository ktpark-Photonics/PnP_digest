"""verify stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import StageExecutionStatus, StageName, VerificationStatus
from pnp_digest.domain.models import (
    NormalizedArtifact,
    StageExecutionState,
    VerificationArtifact,
    VerificationReport,
)
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.verification import load_patent_verification_provider


def _build_report_review_flags(report: VerificationReport) -> tuple[bool, bool]:
    """report의 전체 통과 여부와 수동 검토 필요 여부를 계산한다."""

    statuses = [report.existence_check.status, *[result.status for result in report.results]]
    overall_pass = all(status == VerificationStatus.MATCHED for status in statuses)
    review_required = any(status != VerificationStatus.MATCHED for status in statuses)
    return overall_pass, review_required


def run_verify(
    *,
    run_id: str,
    normalized_artifact_path: Path,
    artifact_root: Path,
    provider_name: str,
    provider_data_path: Path,
) -> VerificationArtifact:
    """normalized artifact를 읽어 특허 검증 artifact를 생성한다."""

    normalized_artifact = read_model(normalized_artifact_path, NormalizedArtifact)
    if normalized_artifact.run.run_id != run_id:
        raise ValueError("run_id와 normalized artifact의 run_id가 일치해야 합니다.")

    provider = load_patent_verification_provider(provider_name, provider_data_path)
    patent_documents = [
        document for document in normalized_artifact.documents if document.document_type == "patent"
    ]

    reports: list[VerificationReport] = []
    for document in patent_documents:
        outcome = provider.verify_patent(document)
        provisional_report = VerificationReport(
            document_id=document.document_id,
            provider_name=outcome.provider_name,
            overall_pass=False,
            review_required=False,
            existence_check=outcome.existence_check,
            results=outcome.field_results,
        )
        overall_pass, review_required = _build_report_review_flags(provisional_report)
        reports.append(
            provisional_report.model_copy(
                update={
                    "overall_pass": overall_pass,
                    "review_required": review_required,
                }
            )
        )

    reports = sorted(reports, key=lambda item: item.document_id)

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.VERIFY)
    artifact_path = stage_dir / "verification_report.json"

    updated_run = normalized_artifact.run.model_copy(
        update={
            "stage_status": {
                **normalized_artifact.run.stage_status,
                StageName.VERIFY: StageExecutionState(
                    status=StageExecutionStatus.COMPLETED,
                    artifact_path=str(artifact_path),
                    updated_at=datetime.now(UTC),
                    message=(
                        f"특허 검증 {len(reports)}건 완료 "
                        f"(provider={provider.provider_name})"
                    ),
                ),
            }
        }
    )

    artifact = VerificationArtifact(run=updated_run, reports=reports)
    write_model(artifact_path, artifact)
    return artifact
