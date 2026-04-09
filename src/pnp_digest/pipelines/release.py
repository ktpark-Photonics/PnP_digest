"""release stage 구현."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain.enums import ApprovalStatus, ReviewStatus, StageExecutionStatus, StageName
from pnp_digest.domain.models import ReleaseManifest, RenderArtifact, StageExecutionState
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model


def run_release(
    *,
    run_id: str,
    render_artifact_path: Path,
    artifact_root: Path,
    distribution_targets: list[str] | None = None,
    release_notes: list[str] | None = None,
    mark_published: bool = False,
) -> ReleaseManifest:
    """render artifact를 읽어 release manifest를 생성한다."""

    render_artifact = read_model(render_artifact_path, RenderArtifact)
    if render_artifact.run.run_id != run_id:
        raise ValueError("run_id와 render artifact의 run_id가 일치해야 합니다.")

    approved_bundles = [
        bundle for bundle in render_artifact.bundles if bundle.approval_status == ApprovalStatus.APPROVED
    ]
    review_signoff = (
        ReviewStatus.APPROVED
        if render_artifact.bundles and len(approved_bundles) == len(render_artifact.bundles)
        else ReviewStatus.PENDING
    )
    generated_at = datetime.now(UTC)
    published_at = generated_at if mark_published and review_signoff == ReviewStatus.APPROVED else None

    artifact_manager = ArtifactManager(artifact_root)
    stage_dir = artifact_manager.stage_dir(run_id, StageName.RELEASE)
    release_manifest_path = stage_dir / "release_manifest.json"

    updated_run = render_artifact.run.model_copy(
        update={
            "stage_status": {
                **render_artifact.run.stage_status,
                StageName.RELEASE: StageExecutionState(
                    status=StageExecutionStatus.COMPLETED,
                    artifact_path=str(release_manifest_path),
                    updated_at=generated_at,
                    message=(
                        f"release candidate {len(render_artifact.bundles)}개 정리, "
                        f"승인 bundle {len(approved_bundles)}개"
                    ),
                ),
            }
        }
    )

    manifest = ReleaseManifest(
        run=updated_run,
        source_render_artifact_path=str(render_artifact_path),
        bundles=render_artifact.bundles,
        approved_bundle_ids=[bundle.bundle_id for bundle in approved_bundles],
        approved_output_paths=[bundle.output_path for bundle in approved_bundles],
        release_notes=list(release_notes or []),
        review_signoff=review_signoff,
        distribution_targets=list(distribution_targets or ["internal"]),
        generated_at=generated_at,
        published_at=published_at,
    )
    write_model(release_manifest_path, manifest)
    return manifest
