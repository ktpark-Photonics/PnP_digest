"""review stage import 구현."""

from __future__ import annotations

from pathlib import Path

from pnp_digest.domain.models import VerificationReviewManifest, VerificationReviewResolutionArtifact
from pnp_digest.domain.enums import StageName
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.review_import import build_verification_review_resolution_artifact


def run_import_verification_review(
    *,
    verification_review_manifest_path: Path,
    review_csv_path: Path,
    artifact_root: Path,
    output_path: Path | None = None,
) -> tuple[VerificationReviewResolutionArtifact, Path]:
    """verification review CSV를 review stage artifact로 저장한다."""

    manifest = read_model(verification_review_manifest_path, VerificationReviewManifest)
    artifact = build_verification_review_resolution_artifact(
        manifest,
        source_manifest_path=verification_review_manifest_path,
        review_csv_path=review_csv_path,
    )

    resolved_output_path = output_path
    if resolved_output_path is None:
        artifact_manager = ArtifactManager(artifact_root)
        resolved_output_path = (
            artifact_manager.stage_dir(manifest.run_id, StageName.REVIEW)
            / "verification_review_resolution.json"
        )

    write_model(resolved_output_path, artifact)
    return artifact, resolved_output_path
