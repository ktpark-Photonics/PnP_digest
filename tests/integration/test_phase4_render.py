"""Phase 4 render 통합 테스트."""

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from zipfile import ZipFile

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
from pnp_digest.services.io import read_json, read_model, write_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "phase4-render-fixture"
runner = CliRunner()


def _load_snapshot(file_name: str) -> dict:
    """기대 snapshot JSON을 읽는다."""

    snapshot_path = PROJECT_ROOT / "tests" / "fixtures" / file_name
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def _normalize_render_artifact_snapshot(render_payload: dict) -> dict:
    """동적 render stage 필드를 placeholder로 정규화한다."""

    stage_state = render_payload["run"]["stage_status"]["render"]
    stage_state["updated_at"] = "__DYNAMIC_UPDATED_AT__"
    stage_state["artifact_path"] = "__DYNAMIC_ARTIFACT_PATH__"
    for bundle in render_payload["bundles"]:
        bundle["output_path"] = "__DYNAMIC_OUTPUT_PATH__"
    return render_payload


def _summarize_docx_output(docx_path: Path) -> dict:
    """DOCX 출력의 핵심 구조를 snapshot 비교용 dict로 정리한다."""

    with ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
        archive_entries = sorted(archive.namelist())
        return {
            "archive_entries": archive_entries,
            "entry_sha256": {
                entry_name: hashlib.sha256(archive.read(entry_name)).hexdigest()
                for entry_name in archive_entries
            },
            "document_xml_sha256": hashlib.sha256(document_xml.encode("utf-8")).hexdigest(),
            "has_title": "CIS Weekly Brief DOCX" in document_xml,
            "has_primary_document": "[SAMPLE] Stacked CIS readout timing architecture" in document_xml,
            "has_secondary_document": "[SAMPLE] Pixel isolation structure for CMOS image sensor" in document_xml,
        }


def _summarize_pdf_output(pdf_path: Path) -> dict:
    """PDF 출력의 핵심 구조를 snapshot 비교용 dict로 정리한다."""

    pdf_bytes = pdf_path.read_bytes()
    return {
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "size": len(pdf_bytes),
        "has_pdf_header": pdf_bytes.startswith(b"%PDF-1.4"),
        "has_eof": b"%%EOF" in pdf_bytes,
        "has_font_marker": b"HYGoThic-Medium" in pdf_bytes,
        "has_page_marker": b"/Type /Page" in pdf_bytes,
    }


def _summarize_pptx_output(pptx_path: Path) -> dict:
    """PPTX 출력의 핵심 구조를 snapshot 비교용 dict로 정리한다."""

    with ZipFile(pptx_path) as archive:
        archive_entries = sorted(archive.namelist())
        slide_entries = sorted(
            name
            for name in archive_entries
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
        presentation_xml = archive.read("ppt/presentation.xml").decode("utf-8")
        slide_xml_by_name = {
            slide_name: archive.read(slide_name).decode("utf-8")
            for slide_name in slide_entries
        }
        return {
            "archive_entries": archive_entries,
            "entry_sha256": {
                entry_name: hashlib.sha256(archive.read(entry_name)).hexdigest()
                for entry_name in archive_entries
            },
            "presentation_xml_sha256": hashlib.sha256(
                presentation_xml.encode("utf-8")
            ).hexdigest(),
            "slide_xml_sha256": {
                slide_name: hashlib.sha256(slide_xml.encode("utf-8")).hexdigest()
                for slide_name, slide_xml in slide_xml_by_name.items()
            },
            "slide_count": len(slide_entries),
            "has_title": "CIS Weekly Brief PPTX" in slide_xml_by_name["ppt/slides/slide1.xml"],
            "has_primary_document": (
                "[SAMPLE] Stacked CIS readout timing architecture"
                in slide_xml_by_name["ppt/slides/slide1.xml"]
            ),
            "has_secondary_document": (
                "[SAMPLE] Pixel isolation structure for CMOS image sensor"
                in slide_xml_by_name["ppt/slides/slide2.xml"]
            ),
        }


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

    snapshots = _load_snapshot("phase4_render_snapshots.json")
    assert _normalize_render_artifact_snapshot(read_json(render_artifact_path)) == snapshots["markdown"]["artifact"]
    assert {"brief_text": markdown} == snapshots["markdown"]["output"]


def test_render_cli_creates_docx_brief_and_render_artifact(tmp_path: Path) -> None:
    """render는 DOCX brief도 생성해야 한다."""

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
            "--output-type",
            "docx",
            "--title",
            "CIS Weekly Brief DOCX",
        ],
    )
    assert result.exit_code == 0

    render_artifact_path = artifact_root / RUN_ID / "render" / "render_artifact.json"
    docx_path = artifact_root / RUN_ID / "render" / "brief.docx"
    assert render_artifact_path.exists()
    assert docx_path.exists()

    artifact = read_model(render_artifact_path, RenderArtifact)
    bundle = artifact.bundles[0]
    assert bundle.output_type == "docx"
    assert bundle.output_path.endswith("brief.docx")
    assert bundle.template_version == "phase4-docx-v1"

    with ZipFile(docx_path) as archive:
        names = set(archive.namelist())
        assert "[Content_Types].xml" in names
        assert "word/document.xml" in names
        assert "word/styles.xml" in names
        document_xml = archive.read("word/document.xml").decode("utf-8")

    assert "CIS Weekly Brief DOCX" in document_xml
    assert "[SAMPLE] Stacked CIS readout timing architecture" in document_xml

    snapshots = _load_snapshot("phase4_render_snapshots.json")
    assert _normalize_render_artifact_snapshot(read_json(render_artifact_path)) == snapshots["docx"]["artifact"]
    assert _summarize_docx_output(docx_path) == snapshots["docx"]["output"]


def test_render_cli_creates_pdf_brief_and_render_artifact(tmp_path: Path) -> None:
    """render는 PDF brief도 생성해야 한다."""

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
            "--output-type",
            "pdf",
            "--title",
            "CIS Weekly Brief PDF",
        ],
    )
    assert result.exit_code == 0

    render_artifact_path = artifact_root / RUN_ID / "render" / "render_artifact.json"
    pdf_path = artifact_root / RUN_ID / "render" / "brief.pdf"
    assert render_artifact_path.exists()
    assert pdf_path.exists()

    artifact = read_model(render_artifact_path, RenderArtifact)
    bundle = artifact.bundles[0]
    assert bundle.output_type == "pdf"
    assert bundle.output_path.endswith("brief.pdf")
    assert bundle.template_version == "phase4-pdf-v1"

    pdf_bytes = pdf_path.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes
    assert b"HYGoThic-Medium" in pdf_bytes
    assert b"/Type /Page" in pdf_bytes

    snapshots = _load_snapshot("phase4_render_snapshots.json")
    assert _normalize_render_artifact_snapshot(read_json(render_artifact_path)) == snapshots["pdf"]["artifact"]
    assert _summarize_pdf_output(pdf_path) == snapshots["pdf"]["output"]


def test_render_cli_creates_pptx_brief_and_render_artifact(tmp_path: Path) -> None:
    """render는 PPTX brief도 생성해야 한다."""

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
            "--output-type",
            "pptx",
            "--title",
            "CIS Weekly Brief PPTX",
        ],
    )
    assert result.exit_code == 0

    render_artifact_path = artifact_root / RUN_ID / "render" / "render_artifact.json"
    pptx_path = artifact_root / RUN_ID / "render" / "brief.pptx"
    assert render_artifact_path.exists()
    assert pptx_path.exists()

    artifact = read_model(render_artifact_path, RenderArtifact)
    bundle = artifact.bundles[0]
    assert bundle.output_type == "pptx"
    assert bundle.output_path.endswith("brief.pptx")
    assert bundle.template_version == "phase4-pptx-v1"

    with ZipFile(pptx_path) as archive:
        names = set(archive.namelist())
        assert "[Content_Types].xml" in names
        assert "ppt/presentation.xml" in names
        assert "ppt/slides/slide1.xml" in names
        assert "ppt/theme/theme1.xml" in names
        slide_xml = archive.read("ppt/slides/slide1.xml").decode("utf-8")

    assert "CIS Weekly Brief PPTX" in slide_xml
    assert "[SAMPLE] Stacked CIS readout timing architecture" in slide_xml

    snapshots = _load_snapshot("phase4_render_snapshots.json")
    assert _normalize_render_artifact_snapshot(read_json(render_artifact_path)) == snapshots["pptx"]["artifact"]
    assert _summarize_pptx_output(pptx_path) == snapshots["pptx"]["output"]
