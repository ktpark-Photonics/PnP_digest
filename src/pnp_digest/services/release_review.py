"""release manifest 최종 검토 CSV export/import 유틸리티."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from pnp_digest.domain import ReviewStatus
from pnp_digest.domain.models import ReleaseManifest, ReleaseReviewResolutionArtifact
from pnp_digest.services.io import ensure_directory

RELEASE_REVIEW_REQUIRED_COLUMNS = {
    "run_id",
    "review_stage",
    "source_render_artifact_path",
    "bundle_ids",
    "approved_bundle_ids",
    "approved_output_paths",
    "distribution_targets",
    "release_notes",
    "review_signoff",
    "reviewer",
    "review_notes",
    "mark_published",
}


def _join_pipe_separated_values(values: list[str]) -> str:
    """문자열 목록을 `a | b | c` 형식으로 변환한다."""

    return " | ".join(values)


def _split_pipe_separated_values(value: str | None) -> list[str]:
    """`a | b | c` 형식 문자열을 목록으로 변환한다."""

    if value is None:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def default_release_review_export_path(source_manifest_path: Path) -> Path:
    """입력 release manifest 경로 기준 기본 CSV 경로를 만든다."""

    return source_manifest_path.with_suffix(".csv")


def export_release_review_manifest(
    manifest: ReleaseManifest,
    *,
    source_manifest_path: Path,
    output_path: Path | None = None,
) -> Path:
    """release manifest를 사람이 수정할 CSV 파일로 저장한다."""

    resolved_output_path = output_path or default_release_review_export_path(source_manifest_path)
    ensure_directory(resolved_output_path.parent)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "run_id",
            "review_stage",
            "source_render_artifact_path",
            "bundle_ids",
            "approved_bundle_ids",
            "approved_output_paths",
            "distribution_targets",
            "release_notes",
            "review_signoff",
            "reviewer",
            "review_notes",
            "mark_published",
        ]
    )
    writer.writerow(
        [
            manifest.run.run_id,
            manifest.review_stage,
            manifest.source_render_artifact_path,
            _join_pipe_separated_values([bundle.bundle_id for bundle in manifest.bundles]),
            _join_pipe_separated_values(manifest.approved_bundle_ids),
            _join_pipe_separated_values(manifest.approved_output_paths),
            _join_pipe_separated_values(manifest.distribution_targets),
            _join_pipe_separated_values(manifest.release_notes),
            manifest.review_signoff,
            "",
            "",
            "false",
        ]
    )
    resolved_output_path.write_text(buffer.getvalue(), encoding="utf-8")
    return resolved_output_path


def _validate_columns(fieldnames: list[str] | None) -> None:
    """CSV header가 필요한 컬럼을 모두 포함하는지 확인한다."""

    actual_columns = set(fieldnames or [])
    missing_columns = sorted(RELEASE_REVIEW_REQUIRED_COLUMNS - actual_columns)
    if missing_columns:
        raise ValueError(
            "release review import CSV에 필요한 컬럼이 없습니다: " + ", ".join(missing_columns)
        )


def _parse_review_signoff(value: str | None) -> ReviewStatus:
    """CSV review_signoff 값을 enum으로 변환한다."""

    if value is None or not value.strip():
        return ReviewStatus.PENDING

    normalized = value.strip().lower()
    try:
        return ReviewStatus(normalized)
    except ValueError as error:
        raise ValueError(
            "review_signoff는 pending, manual_review_required, approved, rejected 중 하나여야 합니다."
        ) from error


def _parse_mark_published(value: str | None) -> bool:
    """CSV mark_published 값을 bool로 파싱한다."""

    normalized = (value or "").strip().lower()
    if normalized in {"", "0", "false", "no", "n"}:
        return False
    if normalized in {"1", "true", "yes", "y"}:
        return True
    raise ValueError("mark_published는 true/false로 입력해야 합니다.")


def _validate_readonly_columns(row: dict[str, str], manifest: ReleaseManifest) -> None:
    """CSV의 읽기 전용 요약 컬럼이 원본 manifest와 일치하는지 확인한다."""

    expected_values = {
        "run_id": manifest.run.run_id,
        "review_stage": str(manifest.review_stage),
        "source_render_artifact_path": manifest.source_render_artifact_path,
        "bundle_ids": _join_pipe_separated_values([bundle.bundle_id for bundle in manifest.bundles]),
        "approved_bundle_ids": _join_pipe_separated_values(manifest.approved_bundle_ids),
        "approved_output_paths": _join_pipe_separated_values(manifest.approved_output_paths),
        "distribution_targets": _join_pipe_separated_values(manifest.distribution_targets),
        "release_notes": _join_pipe_separated_values(manifest.release_notes),
    }
    mismatched_columns = [
        column_name
        for column_name, expected_value in expected_values.items()
        if (row.get(column_name) or "").strip() != expected_value
    ]
    if mismatched_columns:
        raise ValueError(
            "release review import CSV의 읽기 전용 컬럼이 원본 manifest와 다릅니다: "
            + ", ".join(mismatched_columns)
        )


def build_release_review_resolution_artifact(
    manifest: ReleaseManifest,
    *,
    source_manifest_path: Path,
    review_csv_path: Path,
) -> ReleaseReviewResolutionArtifact:
    """사람이 수정한 release review CSV를 JSON artifact로 변환한다."""

    with review_csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames)
        rows = list(reader)

    if len(rows) != 1:
        raise ValueError("release review import CSV에는 정확히 1개의 데이터 행이 있어야 합니다.")

    row = rows[0]
    _validate_readonly_columns(row, manifest)

    review_signoff = _parse_review_signoff(row.get("review_signoff"))
    mark_published = _parse_mark_published(row.get("mark_published"))

    if review_signoff == ReviewStatus.APPROVED and not manifest.approved_bundle_ids:
        raise ValueError("approved release signoff를 하려면 적어도 1개의 승인 bundle이 있어야 합니다.")
    if mark_published and review_signoff != ReviewStatus.APPROVED:
        raise ValueError("published 확정은 review_signoff=approved일 때만 가능합니다.")

    imported_at = datetime.now(UTC)
    published_at = imported_at if mark_published else None

    return ReleaseReviewResolutionArtifact(
        run=manifest.run,
        run_id=manifest.run.run_id,
        source_release_manifest_path=str(source_manifest_path),
        imported_csv_path=str(review_csv_path),
        imported_at=imported_at,
        bundles=manifest.bundles,
        approved_bundle_ids=manifest.approved_bundle_ids,
        approved_output_paths=manifest.approved_output_paths,
        distribution_targets=manifest.distribution_targets,
        release_notes=manifest.release_notes,
        review_signoff=review_signoff,
        reviewer=(row.get("reviewer") or "").strip() or None,
        review_notes=(row.get("review_notes") or "").strip() or None,
        published_at=published_at,
    )
