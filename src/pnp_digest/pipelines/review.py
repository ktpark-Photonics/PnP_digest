"""review stage import 구현."""

from __future__ import annotations

from pathlib import Path

from pnp_digest.domain.models import (
    OpsClosureReport,
    OpsClosureResolutionArtifact,
    OpsEscalationManifest,
    OpsEscalationResolutionArtifact,
    OpsFollowupManifest,
    OpsFollowupResolutionArtifact,
    OpsHandoffArtifact,
    OpsHandoffResolutionArtifact,
    PublishArtifact,
    PublishReviewResolutionArtifact,
    ReleaseManifest,
    ReleaseReviewResolutionArtifact,
    VerificationReviewManifest,
    VerificationReviewResolutionArtifact,
)
from pnp_digest.domain.enums import StageName
from pnp_digest.services.artifacts import ArtifactManager
from pnp_digest.services.closure_review import build_ops_closure_resolution_artifact
from pnp_digest.services.escalation_review import build_ops_escalation_resolution_artifact
from pnp_digest.services.followup_review import build_ops_followup_resolution_artifact
from pnp_digest.services.handoff_review import build_ops_handoff_resolution_artifact
from pnp_digest.services.io import read_model, write_model
from pnp_digest.services.publish_review import build_publish_review_resolution_artifact
from pnp_digest.services.release_review import build_release_review_resolution_artifact
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


def run_import_release_review(
    *,
    release_manifest_path: Path,
    review_csv_path: Path,
    artifact_root: Path,
    output_path: Path | None = None,
) -> tuple[ReleaseReviewResolutionArtifact, Path]:
    """release review CSV를 review stage artifact로 저장한다."""

    manifest = read_model(release_manifest_path, ReleaseManifest)
    artifact = build_release_review_resolution_artifact(
        manifest,
        source_manifest_path=release_manifest_path,
        review_csv_path=review_csv_path,
    )

    resolved_output_path = output_path
    if resolved_output_path is None:
        artifact_manager = ArtifactManager(artifact_root)
        resolved_output_path = (
            artifact_manager.stage_dir(manifest.run.run_id, StageName.REVIEW)
            / "release_review_resolution.json"
        )

    write_model(resolved_output_path, artifact)
    return artifact, resolved_output_path


def run_import_publish_review(
    *,
    publish_artifact_path: Path,
    review_csv_path: Path,
    artifact_root: Path,
    output_path: Path | None = None,
) -> tuple[PublishReviewResolutionArtifact, Path]:
    """publish review CSV를 review stage artifact로 저장한다."""

    publish_artifact = read_model(publish_artifact_path, PublishArtifact)
    artifact = build_publish_review_resolution_artifact(
        publish_artifact,
        source_publish_artifact_path=publish_artifact_path,
        review_csv_path=review_csv_path,
    )

    resolved_output_path = output_path
    if resolved_output_path is None:
        artifact_manager = ArtifactManager(artifact_root)
        resolved_output_path = (
            artifact_manager.stage_dir(publish_artifact.run.run_id, StageName.REVIEW)
            / "publish_review_resolution.json"
        )

    write_model(resolved_output_path, artifact)
    return artifact, resolved_output_path


def run_import_handoff_review(
    *,
    ops_handoff_path: Path,
    review_csv_path: Path,
    artifact_root: Path,
    output_path: Path | None = None,
) -> tuple[OpsHandoffResolutionArtifact, Path]:
    """handoff review CSV를 review stage artifact로 저장한다."""

    ops_handoff_artifact = read_model(ops_handoff_path, OpsHandoffArtifact)
    artifact = build_ops_handoff_resolution_artifact(
        ops_handoff_artifact,
        source_handoff_path=ops_handoff_path,
        review_csv_path=review_csv_path,
    )

    resolved_output_path = output_path
    if resolved_output_path is None:
        artifact_manager = ArtifactManager(artifact_root)
        resolved_output_path = (
            artifact_manager.stage_dir(ops_handoff_artifact.run.run_id, StageName.REVIEW)
            / "ops_handoff_resolution.json"
        )

    write_model(resolved_output_path, artifact)
    return artifact, resolved_output_path


def run_import_followup_review(
    *,
    followup_manifest_path: Path,
    review_csv_path: Path,
    artifact_root: Path,
    output_path: Path | None = None,
) -> tuple[OpsFollowupResolutionArtifact, Path]:
    """followup review CSV를 review stage artifact로 저장한다."""

    followup_manifest = read_model(followup_manifest_path, OpsFollowupManifest)
    artifact = build_ops_followup_resolution_artifact(
        followup_manifest,
        source_followup_manifest_path=followup_manifest_path,
        review_csv_path=review_csv_path,
    )

    resolved_output_path = output_path
    if resolved_output_path is None:
        artifact_manager = ArtifactManager(artifact_root)
        resolved_output_path = (
            artifact_manager.stage_dir(followup_manifest.run_id, StageName.REVIEW)
            / "followup_resolution.json"
        )

    write_model(resolved_output_path, artifact)
    return artifact, resolved_output_path


def run_import_escalation_review(
    *,
    escalation_manifest_path: Path,
    review_csv_path: Path,
    artifact_root: Path,
    output_path: Path | None = None,
) -> tuple[OpsEscalationResolutionArtifact, Path]:
    """escalation review CSV를 review stage artifact로 저장한다."""

    escalation_manifest = read_model(escalation_manifest_path, OpsEscalationManifest)
    artifact = build_ops_escalation_resolution_artifact(
        escalation_manifest,
        source_escalation_manifest_path=escalation_manifest_path,
        review_csv_path=review_csv_path,
    )

    resolved_output_path = output_path
    if resolved_output_path is None:
        artifact_manager = ArtifactManager(artifact_root)
        resolved_output_path = (
            artifact_manager.stage_dir(escalation_manifest.run_id, StageName.REVIEW)
            / "escalation_resolution.json"
        )

    write_model(resolved_output_path, artifact)
    return artifact, resolved_output_path


def run_import_closure_review(
    *,
    closure_report_path: Path,
    review_csv_path: Path,
    artifact_root: Path,
    output_path: Path | None = None,
) -> tuple[OpsClosureResolutionArtifact, Path]:
    """closure review CSV를 review stage artifact로 저장한다."""

    closure_report = read_model(closure_report_path, OpsClosureReport)
    artifact = build_ops_closure_resolution_artifact(
        closure_report,
        source_closure_report_path=closure_report_path,
        review_csv_path=review_csv_path,
    )

    resolved_output_path = output_path
    if resolved_output_path is None:
        artifact_manager = ArtifactManager(artifact_root)
        resolved_output_path = (
            artifact_manager.stage_dir(closure_report.run_id, StageName.REVIEW)
            / "closure_resolution.json"
        )

    write_model(resolved_output_path, artifact)
    return artifact, resolved_output_path
