"""render stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import ApprovalStatus, OutputType, StageExecutionStatus, StageName
from pnp_digest.domain.models import ExplainArtifact, OutputBundle, RenderArtifact, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.rendering import (
    build_docx_brief,
    build_markdown_brief,
    build_pdf_brief,
    build_pptx_brief,
    default_render_output_path,
)


def run_render(
    *,
    run_id: str,
    explain_artifact_path: Path,
    artifact_root: Path,
    output_type: OutputType,
    output_path: Path | None = None,
    brief_title: str = "PnP Digest Brief",
) -> tuple[RenderArtifact, Path]:
    """explain artifact를 읽어 지정 형식의 brief와 render artifact를 생성한다."""

    explain_artifact = read_model(explain_artifact_path, ExplainArtifact)
    if explain_artifact.run.run_id != run_id:
        raise ValueError("run_id와 explain artifact의 run_id가 일치해야 합니다.")
    if output_type not in {
        OutputType.MARKDOWN,
        OutputType.DOCX,
        OutputType.PDF,
        OutputType.PPTX,
    }:
        raise ValueError("현재 render output_type은 markdown, docx, pdf 또는 pptx만 지원합니다.")

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.RENDER)
    resolved_output_path = output_path or default_render_output_path(stage_dir, output_type)
    render_artifact_path = stage_dir / "render_artifact.json"

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    template_version = "phase4-markdown-v1"
    if output_type == OutputType.MARKDOWN:
        resolved_output_path.write_text(
            build_markdown_brief(explain_artifact, brief_title=brief_title),
            encoding="utf-8",
        )
    elif output_type == OutputType.DOCX:
        resolved_output_path.write_bytes(
            build_docx_brief(explain_artifact, brief_title=brief_title)
        )
        template_version = "phase4-docx-v1"
    elif output_type == OutputType.PDF:
        resolved_output_path.write_bytes(
            build_pdf_brief(explain_artifact, brief_title=brief_title)
        )
        template_version = "phase4-pdf-v1"
    else:
        resolved_output_path.write_bytes(
            build_pptx_brief(explain_artifact, brief_title=brief_title)
        )
        template_version = "phase4-pptx-v1"

    bundle = OutputBundle(
        bundle_id=f"{run_id}:{output_type}-brief",
        run_id=run_id,
        output_type=output_type,
        template_version=template_version,
        included_document_ids=[
            explanation.document_id for explanation in explain_artifact.explanations
        ],
        output_path=str(resolved_output_path),
        approval_status=ApprovalStatus.DRAFT,
    )

    updated_run = explain_artifact.run.model_copy(
        update={
            "stage_status": {
                **explain_artifact.run.stage_status,
                StageName.RENDER: StageExecutionState(
                    status=StageExecutionStatus.COMPLETED,
                    artifact_path=str(render_artifact_path),
                    updated_at=datetime.now(UTC),
                    message=(
                        f"{output_type} brief "
                        f"{len(bundle.included_document_ids)}건 문헌으로 생성 완료"
                    ),
                ),
            }
        }
    )

    artifact = RenderArtifact(run=updated_run, bundles=[bundle])
    write_model(render_artifact_path, artifact)
    return artifact, resolved_output_path
