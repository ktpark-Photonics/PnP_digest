"""publish artifact 수동 확인 CSV export/import 유틸리티."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from pnp_digest.domain import PublishStatus
from pnp_digest.domain.models import (
    PublishArtifact,
    PublishReviewResolutionArtifact,
    PublishReviewResolutionRecord,
)
from pnp_digest.services.io import ensure_directory

PUBLISH_REVIEW_REQUIRED_COLUMNS = {
    "run_id",
    "source_release_review_resolution_path",
    "simulation_mode",
    "blocked_reason",
    "bundle_id",
    "output_type",
    "output_path",
    "distribution_target",
    "initial_status",
    "initial_external_reference",
    "initial_notes",
    "reviewed_status",
    "external_reference",
    "record_notes",
    "reviewer",
    "review_notes",
}


def default_publish_review_export_path(source_publish_artifact_path: Path) -> Path:
    """입력 publish artifact 경로 기준 기본 CSV 경로를 만든다."""

    return source_publish_artifact_path.with_suffix(".csv")


def export_publish_review_manifest(
    artifact: PublishArtifact,
    *,
    source_publish_artifact_path: Path,
    output_path: Path | None = None,
) -> Path:
    """publish artifact를 사람이 확인할 CSV 파일로 저장한다."""

    resolved_output_path = output_path or default_publish_review_export_path(source_publish_artifact_path)
    ensure_directory(resolved_output_path.parent)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "run_id",
            "source_release_review_resolution_path",
            "simulation_mode",
            "blocked_reason",
            "bundle_id",
            "output_type",
            "output_path",
            "distribution_target",
            "initial_status",
            "initial_external_reference",
            "initial_notes",
            "reviewed_status",
            "external_reference",
            "record_notes",
            "reviewer",
            "review_notes",
        ]
    )

    for record in artifact.publish_records:
        writer.writerow(
            [
                artifact.run.run_id,
                artifact.source_release_review_resolution_path,
                "true" if artifact.simulation_mode else "false",
                artifact.blocked_reason or "",
                record.bundle_id,
                record.output_type,
                record.output_path,
                record.distribution_target,
                record.status,
                record.external_reference or "",
                record.notes or "",
                record.status,
                record.external_reference or "",
                "",
                "",
                "",
            ]
        )

    resolved_output_path.write_text(buffer.getvalue(), encoding="utf-8")
    return resolved_output_path


def _validate_columns(fieldnames: list[str] | None) -> None:
    """CSV header가 필요한 컬럼을 모두 포함하는지 확인한다."""

    actual_columns = set(fieldnames or [])
    missing_columns = sorted(PUBLISH_REVIEW_REQUIRED_COLUMNS - actual_columns)
    if missing_columns:
        raise ValueError(
            "publish review import CSV에 필요한 컬럼이 없습니다: " + ", ".join(missing_columns)
        )


def _parse_publish_status(value: str | None, *, default: PublishStatus) -> PublishStatus:
    """CSV publish status 값을 enum으로 변환한다."""

    normalized = (value or "").strip().lower()
    if not normalized:
        return default

    try:
        return PublishStatus(normalized)
    except ValueError as error:
        raise ValueError("reviewed_status는 simulated, published, failed 중 하나여야 합니다.") from error


def _readonly_value_map(artifact: PublishArtifact, row: dict[str, str]) -> dict[str, str]:
    """CSV row와 비교할 읽기 전용 기대값을 반환한다."""

    record_key = ((row.get("bundle_id") or "").strip(), (row.get("distribution_target") or "").strip())
    record_map = {
        (record.bundle_id, record.distribution_target): record for record in artifact.publish_records
    }
    if record_key not in record_map:
        raise ValueError(
            "publish review import CSV에 원본 publish artifact에 없는 record가 있습니다: "
            f"{record_key[0]} / {record_key[1]}"
        )

    record = record_map[record_key]
    return {
        "run_id": artifact.run.run_id,
        "source_release_review_resolution_path": artifact.source_release_review_resolution_path,
        "simulation_mode": "true" if artifact.simulation_mode else "false",
        "blocked_reason": artifact.blocked_reason or "",
        "bundle_id": record.bundle_id,
        "output_type": str(record.output_type),
        "output_path": record.output_path,
        "distribution_target": record.distribution_target,
        "initial_status": str(record.status),
        "initial_external_reference": record.external_reference or "",
        "initial_notes": record.notes or "",
    }


def _validate_readonly_columns(artifact: PublishArtifact, rows: list[dict[str, str]]) -> None:
    """CSV의 읽기 전용 컬럼이 원본 publish artifact와 일치하는지 확인한다."""

    seen_keys: set[tuple[str, str]] = set()
    for row in rows:
        record_key = ((row.get("bundle_id") or "").strip(), (row.get("distribution_target") or "").strip())
        if record_key in seen_keys:
            raise ValueError(
                "publish review import CSV에 중복 record가 있습니다: "
                f"{record_key[0]} / {record_key[1]}"
            )
        seen_keys.add(record_key)

        expected_values = _readonly_value_map(artifact, row)
        mismatched_columns = [
            column_name
            for column_name, expected_value in expected_values.items()
            if (row.get(column_name) or "").strip() != expected_value
        ]
        if mismatched_columns:
            raise ValueError(
                "publish review import CSV의 읽기 전용 컬럼이 원본 artifact와 다릅니다: "
                + ", ".join(mismatched_columns)
            )


def _extract_shared_optional_value(rows: list[dict[str, str]], column_name: str) -> str | None:
    """여러 row에 반복되는 선택값이 있으면 일관성을 확인한 뒤 반환한다."""

    non_empty_values = {
        (row.get(column_name) or "").strip() for row in rows if (row.get(column_name) or "").strip()
    }
    if len(non_empty_values) > 1:
        raise ValueError(f"{column_name} 값은 모든 row에서 동일해야 합니다.")
    return next(iter(non_empty_values)) if non_empty_values else None


def build_publish_review_resolution_artifact(
    artifact: PublishArtifact,
    *,
    source_publish_artifact_path: Path,
    review_csv_path: Path,
) -> PublishReviewResolutionArtifact:
    """사람이 수정한 publish review CSV를 JSON artifact로 변환한다."""

    with review_csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames)
        rows = list(reader)

    if artifact.publish_records and len(rows) != len(artifact.publish_records):
        raise ValueError("publish review import CSV row 수가 원본 publish record 수와 다릅니다.")
    if not artifact.publish_records and rows:
        raise ValueError("원본 publish artifact에 record가 없으므로 CSV에도 데이터 행이 있으면 안 됩니다.")

    _validate_readonly_columns(artifact, rows)

    row_map = {
        ((row.get("bundle_id") or "").strip(), (row.get("distribution_target") or "").strip()): row
        for row in rows
    }

    resolved_records: list[PublishReviewResolutionRecord] = []
    for publish_record in artifact.publish_records:
        row = row_map[(publish_record.bundle_id, publish_record.distribution_target)]
        resolved_records.append(
            PublishReviewResolutionRecord(
                bundle_id=publish_record.bundle_id,
                output_type=publish_record.output_type,
                output_path=publish_record.output_path,
                distribution_target=publish_record.distribution_target,
                initial_status=publish_record.status,
                reviewed_status=_parse_publish_status(
                    row.get("reviewed_status"),
                    default=publish_record.status,
                ),
                external_reference=(row.get("external_reference") or "").strip() or None,
                record_notes=(row.get("record_notes") or "").strip() or None,
            )
        )

    return PublishReviewResolutionArtifact(
        run=artifact.run,
        run_id=artifact.run.run_id,
        source_publish_artifact_path=str(source_publish_artifact_path),
        imported_csv_path=str(review_csv_path),
        imported_at=datetime.now(UTC),
        simulation_mode=artifact.simulation_mode,
        review_signoff=artifact.review_signoff,
        reviewer=_extract_shared_optional_value(rows, "reviewer"),
        review_notes=_extract_shared_optional_value(rows, "review_notes"),
        blocked_reason=artifact.blocked_reason,
        published_record_count=sum(
            1 for record in resolved_records if record.reviewed_status == PublishStatus.PUBLISHED
        ),
        failed_record_count=sum(
            1 for record in resolved_records if record.reviewed_status == PublishStatus.FAILED
        ),
        unresolved_record_count=sum(
            1 for record in resolved_records if record.reviewed_status == PublishStatus.SIMULATED
        ),
        records=resolved_records,
    )
