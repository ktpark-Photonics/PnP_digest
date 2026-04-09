"""Phase 5.3 publish review 통합 테스트."""

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from pnp_digest.cli import app
from pnp_digest.domain import (
    OutputType,
    PipelineRun,
    PublishArtifact,
    PublishRecord,
    PublishReviewResolutionArtifact,
    PublishStatus,
    ReviewStage,
    ReviewStatus,
)
from pnp_digest.services.io import read_model, write_model


RUN_ID = "phase53-publish-review-fixture"
runner = CliRunner()


def _build_publish_artifact(*, blocked: bool = False) -> PublishArtifact:
    """publish review 테스트용 publish artifact fixture를 만든다."""

    records = []
    blocked_reason = None
    if not blocked:
        records = [
            PublishRecord(
                bundle_id=f"{RUN_ID}:markdown-brief",
                output_type=OutputType.MARKDOWN,
                output_path=f"artifacts/runs/{RUN_ID}/render/brief.md",
                distribution_target="internal",
                status=PublishStatus.SIMULATED,
                published_at=datetime(2026, 4, 9, 13, 0, tzinfo=UTC),
                external_reference=None,
                notes="stub publish",
            ),
            PublishRecord(
                bundle_id=f"{RUN_ID}:markdown-brief",
                output_type=OutputType.MARKDOWN,
                output_path=f"artifacts/runs/{RUN_ID}/render/brief.md",
                distribution_target="archive",
                status=PublishStatus.SIMULATED,
                published_at=datetime(2026, 4, 9, 13, 0, tzinfo=UTC),
                external_reference=None,
                notes="stub publish",
            ),
        ]
    else:
        blocked_reason = "approved bundle이 없어 publish를 진행하지 않았다."

    return PublishArtifact(
        run=PipelineRun(
            run_id=RUN_ID,
            domain="cmos_image_sensor",
            week_start=date(2026, 4, 9),
            started_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
            operator="tester",
            config_version="phase53-default",
        ),
        source_release_review_resolution_path=f"artifacts/runs/{RUN_ID}/review/release_review_resolution.json",
        review_signoff=ReviewStatus.APPROVED if not blocked else ReviewStatus.PENDING,
        reviewer="ops-user" if not blocked else None,
        distribution_targets=["internal", "archive"],
        simulation_mode=True,
        blocked_reason=blocked_reason,
        publish_records=records,
    )


def test_review_publish_export_creates_one_row_per_publish_record(tmp_path: Path) -> None:
    """publish-export는 publish record 수만큼 CSV row를 만들어야 한다."""

    publish_artifact_path = tmp_path / "publish_artifact.json"
    write_model(publish_artifact_path, _build_publish_artifact())

    result = runner.invoke(
        app,
        [
            "review",
            "publish-export",
            "--publish-artifact",
            str(publish_artifact_path),
        ],
    )
    assert result.exit_code == 0

    csv_path = publish_artifact_path.with_suffix(".csv")
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2
    assert {row["distribution_target"] for row in rows} == {"internal", "archive"}
    assert all(row["reviewed_status"] == PublishStatus.SIMULATED for row in rows)


def test_review_publish_import_creates_resolution_artifact(tmp_path: Path) -> None:
    """publish-import는 채널별 확정 상태를 resolution artifact로 저장해야 한다."""

    publish_artifact_path = tmp_path / "publish_artifact.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(publish_artifact_path, _build_publish_artifact())

    export_result = runner.invoke(
        app,
        [
            "review",
            "publish-export",
            "--publish-artifact",
            str(publish_artifact_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = publish_artifact_path.with_suffix(".csv")
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        fieldnames = rows[0].keys()

    for row in rows:
        row["reviewer"] = "ops-confirmed"
        row["review_notes"] = "archive 채널 재시도 필요"
        if row["distribution_target"] == "internal":
            row["reviewed_status"] = PublishStatus.PUBLISHED
            row["external_reference"] = "internal://brief/2026-04-09"
            row["record_notes"] = "사내 채널 게시 완료"
        else:
            row["reviewed_status"] = PublishStatus.FAILED
            row["record_notes"] = "archive 권한 오류"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    import_result = runner.invoke(
        app,
        [
            "review",
            "publish-import",
            "--publish-artifact",
            str(publish_artifact_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "publish_review_resolution.json"
    artifact = read_model(resolution_path, PublishReviewResolutionArtifact)

    assert artifact.review_stage == ReviewStage.PUBLISH
    assert artifact.reviewer == "ops-confirmed"
    assert artifact.review_notes == "archive 채널 재시도 필요"
    assert artifact.published_record_count == 1
    assert artifact.failed_record_count == 1
    assert artifact.unresolved_record_count == 0
    assert {record.distribution_target for record in artifact.records} == {"internal", "archive"}
    assert {record.reviewed_status for record in artifact.records} == {
        PublishStatus.PUBLISHED,
        PublishStatus.FAILED,
    }


def test_review_publish_import_accepts_blocked_publish_artifact_without_rows(tmp_path: Path) -> None:
    """blocked publish artifact는 header-only CSV로도 import되어야 한다."""

    publish_artifact_path = tmp_path / "blocked_publish_artifact.json"
    artifact_root = tmp_path / "artifacts" / "runs"
    write_model(publish_artifact_path, _build_publish_artifact(blocked=True))

    export_result = runner.invoke(
        app,
        [
            "review",
            "publish-export",
            "--publish-artifact",
            str(publish_artifact_path),
        ],
    )
    assert export_result.exit_code == 0

    csv_path = publish_artifact_path.with_suffix(".csv")
    import_result = runner.invoke(
        app,
        [
            "review",
            "publish-import",
            "--publish-artifact",
            str(publish_artifact_path),
            "--review-csv",
            str(csv_path),
            "--artifact-root",
            str(artifact_root),
        ],
    )
    assert import_result.exit_code == 0

    resolution_path = artifact_root / RUN_ID / "review" / "publish_review_resolution.json"
    artifact = read_model(resolution_path, PublishReviewResolutionArtifact)

    assert artifact.records == []
    assert artifact.blocked_reason == "approved bundle이 없어 publish를 진행하지 않았다."
    assert artifact.published_record_count == 0
    assert artifact.failed_record_count == 0
    assert artifact.unresolved_record_count == 0
