"""schema export 계약 테스트."""

import json
from pathlib import Path

from pnp_digest.domain import (
    DocumentRecord,
    ManualReviewManifest,
    RelevanceArtifact,
    SummaryPayload,
    VerificationArtifact,
    VerificationReport,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _schema_summary(model: type) -> dict[str, list[str]]:
    """모델의 상위 schema shape를 요약한다."""

    schema = model.model_json_schema()
    return {
        "required": schema.get("required", []),
        "properties": list(schema.get("properties", {}).keys()),
    }


def test_schema_summary_snapshot_matches_models() -> None:
    """핵심 모델의 상위 schema shape가 snapshot과 일치해야 한다."""

    snapshot_path = PROJECT_ROOT / "tests/fixtures/schema_summary_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    current = {
        "DocumentRecord": _schema_summary(DocumentRecord),
        "SummaryPayload": _schema_summary(SummaryPayload),
        "RelevanceArtifact": _schema_summary(RelevanceArtifact),
        "ManualReviewManifest": _schema_summary(ManualReviewManifest),
        "VerificationReport": _schema_summary(VerificationReport),
        "VerificationArtifact": _schema_summary(VerificationArtifact),
    }

    assert current == snapshot
