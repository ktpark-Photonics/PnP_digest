"""Phase 5 release 통합 테스트."""

from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    ApprovalStatus,
    OutputBundle,
    OutputType,
    PipelineRun,
    ReleaseManifest,
    RenderArtifact,
    ReviewStage,
    ReviewStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase5-release-fixture"
runner = CliRunner()


def _build_render_artifact(*, all_approved: bool = False) -> RenderArtifact:
    """release 입력용 render artifact fixture를 생성한다."""

    second_status = ApprovalStatus.APPROVED if all_approved else ApprovalStatus.DRAFT
    return RenderArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 6),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase5-default",
        ),
        bundles=[
            OutputBundle(
                bundle_id=f"{RUN_ID}:markdown-brief",
                run_id=RUN_ID,
                output_type=OutputType.MARKDOWN,
                template_version="phase4-markdown-v1",
                included_document_ids=["patent:number:sample-us-partial-001-a1"],
                output_path="artifacts/runs/phase5-release-fixture/render/brief.md",
                approval_status=ApprovalStatus.APPROVED,
            ),
            OutputBundle(
                bundle_id=f"{RUN_ID}:pptx-brief",
                run_id=RUN_ID,
                output_type=OutputType.PPTX,
                template_version="phase4-pptx-v1",
                included_document_ids=["patent:number:sample-us-partial-001-a1"],
                output_path="artifacts/runs/phase5-release-fixture/render/brief.pptx",
                approval_status=second_status,
            ),
        ],
    )


def test_release_cli_creates_manifest_with_only_approved_bundles(tmp_path: Path) -> None:
    """release는 render artifact에서 승인된 bundle만 approved 목록에 반영해야 한다."""

    render_artifact_path = tmp_path / "render_artifact.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(render_artifact_path, _build_render_artifact())

    result = runner.invoke(
        app,
        [
            "release",
            "--run-id",
            RUN_ID,
            "--render-artifact",
            str(render_artifact_path),
            "--artifact-root",
            str(artifact_root),
            "--distribution-target",
            "internal",
            "--distribution-target",
            "archive",
            "--release-note",
            "markdown bundle ready",
            "--release-note",
            "pptx bundle approval pending",
        ],
    )
    assert result.exit_code == 0

    manifest_path = artifact_root / RUN_ID / "release" / "release_manifest.json"
    assert manifest_path.exists()

    manifest = read_model(manifest_path, ReleaseManifest)
    assert manifest.review_stage == ReviewStage.FINAL_RELEASE
    assert len(manifest.bundles) == 2
    assert manifest.approved_bundle_ids == [f"{RUN_ID}:markdown-brief"]
    assert manifest.approved_output_paths == [
        "artifacts/runs/phase5-release-fixture/render/brief.md"
    ]
    assert manifest.review_signoff == ReviewStatus.PENDING
    assert manifest.distribution_targets == ["internal", "archive"]
    assert manifest.release_notes == [
        "markdown bundle ready",
        "pptx bundle approval pending",
    ]
    assert manifest.published_at is None
    assert manifest.run.stage_status["release"].artifact_path.endswith("release_manifest.json")


def test_release_cli_marks_manifest_published_when_all_bundles_are_approved(tmp_path: Path) -> None:
    """모든 bundle이 승인 상태이면 mark-published로 published_at을 기록해야 한다."""

    render_artifact_path = tmp_path / "render_artifact.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(render_artifact_path, _build_render_artifact(all_approved=True))

    result = runner.invoke(
        app,
        [
            "release",
            "--run-id",
            RUN_ID,
            "--render-artifact",
            str(render_artifact_path),
            "--artifact-root",
            str(artifact_root),
            "--mark-published",
        ],
    )
    assert result.exit_code == 0

    manifest_path = artifact_root / RUN_ID / "release" / "release_manifest.json"
    manifest = read_model(manifest_path, ReleaseManifest)

    assert manifest.review_signoff == ReviewStatus.APPROVED
    assert len(manifest.approved_bundle_ids) == 2
    assert len(manifest.approved_output_paths) == 2
    assert manifest.published_at is not None
