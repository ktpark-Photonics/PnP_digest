"""Phase 1 규칙 기반 관련성 판정 통합 테스트."""

import json
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import ManualReviewManifest, RelevanceArtifact, RelevanceDecision
from pnp_digest.services.io import read_json, read_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _load_snapshot(file_name: str) -> dict:
    """기대 snapshot JSON을 읽는다."""

    snapshot_path = PROJECT_ROOT / "tests" / "fixtures" / file_name
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def _normalize_report_snapshot(report_payload: dict) -> dict:
    """동적 stage 필드를 placeholder로 정규화한다."""

    stage_state = report_payload["run"]["stage_status"]["assess_relevance"]
    stage_state["updated_at"] = "__DYNAMIC_UPDATED_AT__"
    stage_state["artifact_path"] = "__DYNAMIC_ARTIFACT_PATH__"
    return report_payload


def test_assess_relevance_cli_creates_report_and_manual_manifest(tmp_path: Path) -> None:
    """고정 fixture에 대해 산출물 계약과 판정 결과를 검증해야 한다."""

    run_id = "phase1-threeway-fixture"
    normalized_path = PROJECT_ROOT / "data" / "sample_inputs" / "phase1_relevance_normalized_fixture.json"
    artifact_root = tmp_path / "artifacts" / "runs"

    result = runner.invoke(
        app,
        [
            "assess-relevance",
            "--run-id",
            run_id,
            "--normalized-artifact",
            str(normalized_path),
            "--artifact-root",
            str(artifact_root),
            "--dictionary-dir",
            str(PROJECT_ROOT / "data" / "dictionaries"),
        ],
    )
    assert result.exit_code == 0

    stage_dir = artifact_root / run_id / "assess_relevance"
    report_path = stage_dir / "relevance_report.json"
    manifest_path = stage_dir / "manual_review_manifest.json"

    assert report_path.exists()
    assert manifest_path.exists()

    report = read_model(report_path, RelevanceArtifact)
    manifest = read_model(manifest_path, ManualReviewManifest)

    assert len(report.assessments) == 3

    decisions = {assessment.document_id: assessment.final_decision for assessment in report.assessments}
    assert decisions["paper:doi:relevant"] == RelevanceDecision.RELEVANT
    assert decisions["paper:doi:borderline"] == RelevanceDecision.BORDERLINE
    assert decisions["paper:doi:not-relevant"] == RelevanceDecision.NOT_RELEVANT

    for assessment in report.assessments:
        assert assessment.evidence_links_or_snippets, "근거 snippet은 비어 있으면 안 된다."

    assert len(manifest.items) == 1
    assert manifest.items[0].document_id == "paper:doi:borderline"

    normalized_report = _normalize_report_snapshot(read_json(report_path))
    manifest_payload = read_json(manifest_path)

    assert normalized_report == _load_snapshot("phase1_relevance_report_snapshot.json")
    assert manifest_payload == _load_snapshot("phase1_manual_review_manifest_snapshot.json")
