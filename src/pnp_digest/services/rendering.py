"""Markdown brief 렌더링 유틸리티."""

from __future__ import annotations

from pathlib import Path

from pnp_digest.domain.models import AudienceExplanation, ExplainArtifact


def default_markdown_output_path(stage_dir: Path) -> Path:
    """render stage 기본 Markdown 출력 경로를 반환한다."""

    return stage_dir / "brief.md"


def _render_explanation_block(title: str, explanation: AudienceExplanation) -> list[str]:
    """단일 직급 설명 블록을 Markdown 섹션으로 직렬화한다."""

    lines = [
        f"### {title}",
        "",
        f"- purpose: {explanation.purpose}",
        f"- audience_focus: {', '.join(explanation.audience_focus) if explanation.audience_focus else '-'}",
        f"- explanation_text: {explanation.explanation_text}",
        f"- key_points: {', '.join(explanation.key_points) if explanation.key_points else '-'}",
        f"- cautions: {', '.join(explanation.cautions) if explanation.cautions else '-'}",
        f"- action_prompt: {explanation.action_prompt or '-'}",
        "",
    ]
    return lines


def build_markdown_brief(
    explain_artifact: ExplainArtifact,
    *,
    brief_title: str,
) -> str:
    """explain artifact를 사람이 읽는 Markdown brief로 변환한다."""

    lines = [
        f"# {brief_title}",
        "",
        f"- run_id: {explain_artifact.run.run_id}",
        f"- document_count: {len(explain_artifact.explanations)}",
        "",
    ]

    for record in explain_artifact.explanations:
        lines.extend(
            [
                f"## {record.document_title}",
                "",
                f"- document_id: {record.document_id}",
                f"- document_type: {record.document_type}",
                f"- source_review_status: {record.source_review_status}",
                f"- summary_confidence: {record.summary_confidence:.2f}",
                f"- human_review_notes: {record.human_review_notes or '-'}",
                "",
            ]
        )
        lines.extend(_render_explanation_block("신입 설명", record.entry_level_explanation))
        lines.extend(_render_explanation_block("과장 설명", record.manager_level_explanation))
        lines.extend(_render_explanation_block("부장 설명", record.director_level_explanation))

    return "\n".join(lines).rstrip() + "\n"
