"""normalize stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import StageExecutionStatus, StageName
from pnp_digest.domain.models import (
    IngestArtifact,
    NormalizedArtifact,
    SamplePaperPayload,
    SamplePatentPayload,
    StageExecutionState,
    enum_or_string_value,
)
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.normalization import merge_documents, normalize_document


def run_normalize(
    *,
    run_id: str,
    ingest_artifact_path: Path,
    artifact_root: Path,
) -> NormalizedArtifact:
    """ingest artifact를 읽어 canonical document 목록을 생성한다."""

    ingest_artifact = read_model(ingest_artifact_path, IngestArtifact)
    if ingest_artifact.run.run_id != run_id:
        raise ValueError("run_id와 ingest artifact의 run_id가 일치해야 합니다.")

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.NORMALIZE)

    documents_by_id = {}
    for raw_record in ingest_artifact.raw_records:
        payload_path = Path(raw_record.raw_payload_path)
        if enum_or_string_value(raw_record.document_type) == "paper":
            payload = read_model(payload_path, SamplePaperPayload)
        else:
            payload = read_model(payload_path, SamplePatentPayload)

        normalized_document = normalize_document(raw_record, payload)
        existing = documents_by_id.get(normalized_document.document_id)
        if existing is None:
            documents_by_id[normalized_document.document_id] = normalized_document
        else:
            documents_by_id[normalized_document.document_id] = merge_documents(existing, normalized_document)

    updated_run = ingest_artifact.run.model_copy(
        update={
            "stage_status": {
                **ingest_artifact.run.stage_status,
                StageName.NORMALIZE: StageExecutionState(
                    status=StageExecutionStatus.COMPLETED,
                    artifact_path=str(stage_dir / "normalized_artifact.json"),
                    updated_at=datetime.now(UTC),
                    message=f"{len(documents_by_id)}건 normalize 완료",
                ),
            }
        }
    )
    artifact = NormalizedArtifact(
        run=updated_run,
        documents=sorted(documents_by_id.values(), key=lambda item: item.document_id),
    )
    write_model(stage_dir / "normalized_artifact.json", artifact)
    return artifact
