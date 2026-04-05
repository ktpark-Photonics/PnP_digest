"""Phase 0 샘플 파이프라인 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from pnp_digest.domain import PipelineRun
from pnp_digest.pipelines.ingest import run_ingest
from pnp_digest.pipelines.normalize import run_normalize


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_sample_fixture_ingest_and_normalize(tmp_path: Path) -> None:
    """샘플 fixture가 ingest 후 4개의 canonical document로 정규화되어야 한다."""

    run = PipelineRun(
        run_id="phase0-sample",
        domain="cmos_image_sensor",
        week_start=date(2026, 3, 30),
        started_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
        operator="tester",
        config_version="phase0-default",
    )
    input_path = PROJECT_ROOT / "data/sample_inputs/cis_weekly_fixture.json"
    artifact_root = tmp_path / "artifacts" / "runs"

    ingest_artifact = run_ingest(run=run, input_path=input_path, artifact_root=artifact_root)
    assert len(ingest_artifact.raw_records) == 5

    normalized_artifact = run_normalize(
        run_id=run.run_id,
        ingest_artifact_path=artifact_root / run.run_id / "ingest" / "ingest_artifact.json",
        artifact_root=artifact_root,
    )
    assert len(normalized_artifact.documents) == 4

    patent_document = next(
        document
        for document in normalized_artifact.documents
        if document.document_id == "patent:number:sample-us-000001-a1"
    )
    assert patent_document.source_record_ids == ["raw-patent-cis-001", "raw-patent-cis-001-dup"]
