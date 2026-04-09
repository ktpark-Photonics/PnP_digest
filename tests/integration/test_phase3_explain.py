"""Phase 3.1 explain 통합 테스트."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    AudienceExplanation,
    ExplainArtifact,
    EvidenceSnippet,
    PipelineRun,
    ReviewStatus,
    SummaryArtifact,
    SummaryPayload,
    SummaryRecord,
)
from pnp_digest.services.io import read_json, read_model, write_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "phase3-explain-fixture"
runner = CliRunner()


def _load_snapshot(file_name: str) -> dict:
    """기대 snapshot JSON을 읽는다."""

    snapshot_path = PROJECT_ROOT / "tests" / "fixtures" / file_name
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def _normalize_explain_artifact_snapshot(explain_payload: dict) -> dict:
    """동적 explain stage 필드를 placeholder로 정규화한다."""

    stage_state = explain_payload["run"]["stage_status"]["explain"]
    stage_state["updated_at"] = "__DYNAMIC_UPDATED_AT__"
    stage_state["artifact_path"] = "__DYNAMIC_ARTIFACT_PATH__"
    return explain_payload


def _build_audience_explanation(audience: str, title: str) -> AudienceExplanation:
    """직급별 fixture 설명 블록을 생성한다."""

    return AudienceExplanation(
        purpose=f"{audience} 관점 설명",
        audience_focus=["핵심 아이디어"],
        explanation_text=f"{title}에 대한 {audience} 설명",
        key_points=[title],
        cautions=["fixture 설명"],
        action_prompt="후속 검토",
    )


def _build_summary_record(document_id: str, title: str, note: str | None) -> SummaryRecord:
    """explain 입력용 summary record를 생성한다."""

    return SummaryRecord(
        document_id=document_id,
        document_type="patent",
        document_title=title,
        source_review_status=ReviewStatus.APPROVED,
        summary=SummaryPayload(
            background_context=f"{title} 배경",
            problem_statement="문제 정의",
            purpose="목적 요약",
            core_idea="핵심 아이디어",
            expected_effect="예상 효과",
            limitations_or_unknowns=["placeholder 기반"],
            evidence_links_or_snippets=[
                EvidenceSnippet(
                    source_url="https://example.invalid/doc",
                    locator="abstract",
                    snippet_text=f"{title} 근거 문장",
                    supports_fields=["core_idea", "expected_effect"],
                )
            ],
            entry_level_explanation=_build_audience_explanation("신입", title),
            manager_level_explanation=_build_audience_explanation("과장", title),
            director_level_explanation=_build_audience_explanation("부장", title),
            summary_confidence=0.6,
            human_review_notes=note,
        ),
    )


def _build_summary_artifact() -> SummaryArtifact:
    """explain 입력용 summary artifact fixture를 생성한다."""

    return SummaryArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 6),
            started_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase3-default",
        ),
        summaries=[
            _build_summary_record(
                "patent:number:sample-us-partial-001-a1",
                "[SAMPLE] Stacked CIS readout timing architecture",
                "확인 완료",
            ),
            _build_summary_record(
                "patent:number:sample-us-match-001-a1",
                "[SAMPLE] Pixel isolation structure for CMOS image sensor",
                None,
            ),
        ],
    )


def test_explain_cli_creates_explain_artifact_from_summary_artifact(tmp_path: Path) -> None:
    """explain은 summary artifact의 직급별 설명을 별도 artifact로 저장해야 한다."""

    summary_artifact_path = tmp_path / "summary_artifact.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(summary_artifact_path, _build_summary_artifact())

    result = runner.invoke(
        app,
        [
            "explain",
            "--run-id",
            RUN_ID,
            "--summary-artifact",
            str(summary_artifact_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert result.exit_code == 0

    explain_artifact_path = artifact_root / RUN_ID / "explain" / "explain_artifact.json"
    assert explain_artifact_path.exists()

    artifact = read_model(explain_artifact_path, ExplainArtifact)
    assert artifact.run.stage_status["explain"].artifact_path.endswith("explain_artifact.json")
    assert len(artifact.explanations) == 2

    first = artifact.explanations[0]
    assert first.document_id == "patent:number:sample-us-partial-001-a1"
    assert first.document_title == "[SAMPLE] Stacked CIS readout timing architecture"
    assert first.source_review_status == ReviewStatus.APPROVED
    assert first.summary_confidence == 0.6
    assert "신입 설명" in first.entry_level_explanation.explanation_text
    assert first.human_review_notes == "확인 완료"

    normalized_explain = _normalize_explain_artifact_snapshot(read_json(explain_artifact_path))
    assert normalized_explain == _load_snapshot("phase31_explain_artifact_snapshot.json")
