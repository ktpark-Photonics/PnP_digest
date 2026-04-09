"""closure resolution 기반 Markdown 종료 보고서 export 유틸리티."""

from __future__ import annotations

from pathlib import Path

from pnp_digest.domain.models import OpsClosureResolutionArtifact, ReviewTask
from pnp_digest.services.io import ensure_directory


def default_closure_brief_path(source_closure_resolution_path: Path) -> Path:
    """입력 closure resolution 기준 기본 Markdown 경로를 만든다."""

    return source_closure_resolution_path.with_suffix(".md")


def _render_task(task: ReviewTask) -> list[str]:
    """단일 task를 Markdown bullet 묶음으로 렌더링한다."""

    lines = [
        f"- review_task_id: {task.review_task_id}",
        f"  - target: {task.target_type} / {task.target_id}",
        f"  - status: {task.status}",
        f"  - assignee: {task.assignee or '-'}",
        f"  - notes: {task.notes or '-'}",
    ]
    if task.checklist:
        lines.append("  - checklist:")
        for item in task.checklist:
            lines.append(f"    - {item.item_id}: {item.response or '-'}")
    return lines


def build_closure_brief_markdown(
    artifact: OpsClosureResolutionArtifact,
    *,
    title: str = "Ops Closure Resolution Brief",
) -> str:
    """closure resolution을 사람이 공유할 Markdown 보고서로 변환한다."""

    lines = [
        f"# {title}",
        "",
        f"- run_id: {artifact.run_id}",
        f"- closure_team: {artifact.closure_team}",
        f"- blocked_reason: {artifact.blocked_reason or 'none'}",
        f"- closed_task_count: {artifact.closed_task_count}",
        f"- remaining_task_count: {artifact.remaining_task_count}",
        f"- imported_csv_path: {artifact.imported_csv_path}",
        "",
        "## Closed Tasks",
    ]

    if not artifact.closed_tasks:
        lines.append("- 없음")
    else:
        for task in artifact.closed_tasks:
            lines.extend(_render_task(task))

    lines.extend(["", "## Remaining Tasks"])
    if not artifact.remaining_tasks:
        lines.append("- 없음")
    else:
        for task in artifact.remaining_tasks:
            lines.extend(_render_task(task))

    return "\n".join(lines) + "\n"


def export_closure_brief_markdown(
    artifact: OpsClosureResolutionArtifact,
    *,
    source_closure_resolution_path: Path,
    output_path: Path | None = None,
    title: str = "Ops Closure Resolution Brief",
) -> Path:
    """closure resolution Markdown 보고서를 파일로 저장한다."""

    resolved_output_path = output_path or default_closure_brief_path(source_closure_resolution_path)
    ensure_directory(resolved_output_path.parent)
    content = build_closure_brief_markdown(artifact, title=title)
    resolved_output_path.write_text(content, encoding="utf-8")
    return resolved_output_path
