"""Phase 4 render 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    AudienceExplanation,
    ExplainArtifact,
    ExplainRecord,
    PipelineRun,
    RenderArtifact,
    ReviewStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase4-render-fixture"
runner = CliRunner()


def _build_audience_explanation(audience: str, title: str) -> AudienceExplanation:
    """Markdown 렌더 테스트용 직급 설명 블록을 생성한다."""

    return AudienceExplanation(
        purpose=f"{audience} 관점 설명",
        audience_focus=["핵심 개념", "후속 확인 포인트"],
        explanation_text=f"{title}에 대한 {audience} 설명 본문",
        key_points=[title, f"{audience} 핵심"],
        cautions=["fixture caution"],
        action_prompt="후속 검토",
    )


def _build_explain_artifact() -> ExplainArtifact:
    """render 입력용 explain artifact fixture를 생성한다."""

    return ExplainArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 6),
            started_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase4-default",
        ),
        explanations=[
            ExplainRecord(
                document_id="patent:number:sample-us-partial-001-a1",
                document_type="patent",
                document_title="[SAMPLE] Stacked CIS readout timing architecture",
                source_review_status=ReviewStatus.APPROVED,
                summary_confidence=0.6,
                entry_level_explanation=_build_audience_explanation(
                    "신입",
                    "[SAMPLE] Stacked CIS readout timing architecture",
                ),
                manager_level_explanation=_build_audience_explanation(
                    "과장",
                    "[SAMPLE] Stacked CIS readout timing architecture",
                ),
                director_level_explanation=_build_audience_explanation(
                    "부장",
                    "[SAMPLE] Stacked CIS readout timing architecture",
                ),
                human_review_notes="검토 승인 완료",
            ),
            ExplainRecord(
                document_id="patent:number:sample-us-match-001-a1",
                document_type="patent",
                document_title="[SAMPLE] Pixel isolation structure for CMOS image sensor",
                source_review_status=ReviewStatus.APPROVED,
                summary_confidence=0.55,
                entry_level_explanation=_build_audience_explanation(
                    "신입",
                    "[SAMPLE] Pixel isolation structure for CMOS image sensor",
                ),
                manager_level_explanation=_build_audience_explanation(
                    "과장",
                    "[SAMPLE] Pixel isolation structure for CMOS image sensor",
                ),
                director_level_explanation=_build_audience_explanation(
                    "부장",
                    "[SAMPLE] Pixel isolation structure for CMOS image sensor",
                ),
                human_review_notes=None,
            ),
        ],
    )


def test_render_cli_creates_markdown_brief_and_render_artifact(tmp_path: Path) -> None:
    """render는 explain artifact에서 Markdown brief와 render artifact를 생성해야 한다."""

    explain_artifact_path = tmp_path / "explain_artifact.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(explain_artifact_path, _build_explain_artifact())

    result = runner.invoke(
        app,
        [
            "render",
            "--run-id",
            RUN_ID,
            "--explain-artifact",
            str(explain_artifact_path),
            "--artifact-root",
            str(artifact_root),
            "--title",
            "CIS Weekly Brief",
        ],
    )
    assert result.exit_code == 0

    render_artifact_path = artifact_root / RUN_ID / "render" / "render_artifact.json"
    markdown_path = artifact_root / RUN_ID / "render" / "brief.md"
    assert render_artifact_path.exists()
    assert markdown_path.exists()

    artifact = read_model(render_artifact_path, RenderArtifact)
    assert artifact.run.stage_status["render"].artifact_path.endswith("render_artifact.json")
    assert len(artifact.bundles) == 1

    bundle = artifact.bundles[0]
    assert bundle.output_type == "markdown"
    assert bundle.output_path.endswith("brief.md")
    assert bundle.included_document_ids == [
        "patent:number:sample-us-partial-001-a1",
        "patent:number:sample-us-match-001-a1",
    ]
    assert bundle.approval_status == "draft"

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# CIS Weekly Brief" in markdown
    assert "- run_id: phase4-render-fixture" in markdown
    assert "## [SAMPLE] Stacked CIS readout timing architecture" in markdown
    assert "### 신입 설명" in markdown
    assert "검토 승인 완료" in markdown
