"""ingest stage 구현."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.adapters.local_files import LocalFixtureAdapter
from pnp_digest.domain.enums import DocumentType, StageExecutionStatus, StageName
from pnp_digest.domain.models import IngestArtifact, PipelineRun, RawSourceRecord, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import write_json, write_model


def run_ingest(
    *,
    run: PipelineRun,
    input_path: Path,
    artifact_root: Path,
) -> IngestArtifact:
    """로컬 fixture를 읽어 ingest artifact를 생성한다."""

    adapter = LocalFixtureAdapter()
    records = adapter.load_records(input_path)
    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run.run_id, StageName.INGEST)
    raw_payload_dir = stage_dir / "raw_payloads"
    raw_payload_dir.mkdir(parents=True, exist_ok=True)

    raw_records: list[RawSourceRecord] = []
    for record in records:
        raw_id = f"raw-{record.fixture_id}"
        payload_dump = record.payload.model_dump(mode="json")
        checksum = hashlib.sha256(
            json.dumps(payload_dump, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        payload_path = raw_payload_dir / f"{raw_id}.json"
        write_json(payload_path, payload_dump)

        raw_records.append(
            RawSourceRecord(
                raw_id=raw_id,
                document_type=DocumentType(record.payload.document_type),
                source_type=record.source_type,
                source_name=record.source_name,
                query=record.query,
                source_url=record.source_url,
                fetched_at=record.fetched_at,
                raw_payload_path=str(payload_path),
                checksum=checksum,
            )
        )

    updated_run = run.model_copy(
        update={
            "stage_status": {
                **run.stage_status,
                StageName.INGEST: StageExecutionState(
                    status=StageExecutionStatus.COMPLETED,
                    artifact_path=str(stage_dir / "ingest_artifact.json"),
                    updated_at=datetime.now(UTC),
                    message=f"{len(raw_records)}건 ingest 완료",
                ),
            }
        }
    )
    artifact = IngestArtifact(run=updated_run, raw_records=raw_records)
    write_model(stage_dir / "ingest_artifact.json", artifact)
    return artifact
