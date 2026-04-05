"""schema export 계약 테스트."""

import json
from pathlib import Path

from pnp_digest.domain import DocumentRecord, SummaryPayload


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_schema_summary_snapshot_matches_models() -> None:
    """핵심 모델의 상위 schema shape가 snapshot과 일치해야 한다."""

    snapshot_path = PROJECT_ROOT / "tests/fixtures/schema_summary_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    document_schema = DocumentRecord.model_json_schema()
    summary_schema = SummaryPayload.model_json_schema()

    current = {
        "DocumentRecord": {
            "required": document_schema.get("required", []),
            "properties": list(document_schema.get("properties", {}).keys()),
        },
        "SummaryPayload": {
            "required": summary_schema.get("required", []),
            "properties": list(summary_schema.get("properties", {}).keys()),
        },
    }

    assert current == snapshot
