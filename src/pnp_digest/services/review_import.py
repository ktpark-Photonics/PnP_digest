"""verification review CSV import 유틸리티."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from pnp_digest.domain import ReviewStatus
from pnp_digest.domain.models import (
    VerificationReviewManifest,
    VerificationReviewResolutionArtifact,
    VerificationReviewResolutionItem,
)

REVIEW_IMPORT_REQUIRED_COLUMNS = {
    "document_id",
    "provider_name",
    "review_reason",
    "existence_status",
    "flagged_fields",
    "overall_pass",
    "source_artifact_path",
    "recommended_action",
    "review_status",
    "reviewer",
    "review_notes",
    "resolved_fields",
}


def _split_pipe_separated_values(value: str | None) -> list[str]:
    """`a | b | c` 형식 문자열을 목록으로 변환한다."""

    if value is None:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def _parse_review_status(value: str | None) -> ReviewStatus:
    """CSV review_status 값을 enum으로 변환한다."""

    if value is None or not value.strip():
        return ReviewStatus.PENDING

    normalized = value.strip().lower()
    try:
        return ReviewStatus(normalized)
    except ValueError as error:
        raise ValueError(
            "review_status는 pending, manual_review_required, approved, rejected 중 하나여야 합니다."
        ) from error


def _validate_columns(fieldnames: list[str] | None) -> None:
    """CSV header가 필요한 컬럼을 모두 포함하는지 확인한다."""

    actual_columns = set(fieldnames or [])
    missing_columns = sorted(REVIEW_IMPORT_REQUIRED_COLUMNS - actual_columns)
    if missing_columns:
        raise ValueError(
            "review import CSV에 필요한 컬럼이 없습니다: " + ", ".join(missing_columns)
        )


def build_verification_review_resolution_artifact(
    manifest: VerificationReviewManifest,
    *,
    source_manifest_path: Path,
    review_csv_path: Path,
) -> VerificationReviewResolutionArtifact:
    """reviewer가 수정한 CSV를 검증 결과 artifact로 변환한다."""

    with review_csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames)
        rows = list(reader)

    rows_by_document_id = {row["document_id"]: row for row in rows}
    expected_document_ids = {item.document_id for item in manifest.items}
    actual_document_ids = set(rows_by_document_id)

    missing_document_ids = sorted(expected_document_ids - actual_document_ids)
    unexpected_document_ids = sorted(actual_document_ids - expected_document_ids)
    if missing_document_ids or unexpected_document_ids:
        message_parts: list[str] = []
        if missing_document_ids:
            message_parts.append("누락 문헌: " + ", ".join(missing_document_ids))
        if unexpected_document_ids:
            message_parts.append("예상 외 문헌: " + ", ".join(unexpected_document_ids))
        raise ValueError("review import CSV 문헌 집합이 manifest와 일치하지 않습니다. " + " / ".join(message_parts))

    items: list[VerificationReviewResolutionItem] = []
    for manifest_item in manifest.items:
        row = rows_by_document_id[manifest_item.document_id]
        resolved_fields = _split_pipe_separated_values(row.get("resolved_fields"))
        invalid_fields = [field for field in resolved_fields if field not in manifest_item.flagged_fields]
        if invalid_fields:
            raise ValueError(
                f"{manifest_item.document_id}의 resolved_fields에는 flagged_fields에 없는 값이 있습니다: "
                + ", ".join(invalid_fields)
            )

        items.append(
            VerificationReviewResolutionItem(
                document_id=manifest_item.document_id,
                provider_name=manifest_item.provider_name,
                existence_status=manifest_item.existence_status,
                flagged_fields=manifest_item.flagged_fields,
                review_status=_parse_review_status(row.get("review_status")),
                reviewer=(row.get("reviewer") or "").strip() or None,
                review_notes=(row.get("review_notes") or "").strip() or None,
                resolved_fields=resolved_fields,
                review_reason=manifest_item.review_reason,
                source_artifact_path=manifest_item.source_artifact_path,
            )
        )

    return VerificationReviewResolutionArtifact(
        run_id=manifest.run_id,
        source_manifest_path=str(source_manifest_path),
        imported_csv_path=str(review_csv_path),
        imported_at=datetime.now(UTC),
        items=items,
    )
