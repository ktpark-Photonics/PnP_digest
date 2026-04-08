"""수동 검토 manifest export 유틸리티."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from pnp_digest.domain.models import VerificationReviewItem, VerificationReviewManifest
from pnp_digest.services.io import ensure_directory

SUPPORTED_REVIEW_EXPORT_FORMATS = {"csv", "markdown"}


def normalize_review_export_format(value: str) -> str:
    """지원하는 review export 형식을 정규화한다."""

    normalized = value.strip().lower()
    if normalized not in SUPPORTED_REVIEW_EXPORT_FORMATS:
        raise ValueError("review export 형식은 csv 또는 markdown 이어야 합니다.")
    return normalized


def default_review_export_path(source_manifest_path: Path, export_format: str) -> Path:
    """입력 manifest 경로를 기준으로 기본 출력 경로를 만든다."""

    normalized_format = normalize_review_export_format(export_format)
    suffix = ".csv" if normalized_format == "csv" else ".md"
    return source_manifest_path.with_suffix(suffix)


def _serialize_flagged_fields(item: VerificationReviewItem) -> str:
    """flagged field 목록을 사람이 읽기 쉬운 문자열로 변환한다."""

    return " | ".join(item.flagged_fields)


def _build_csv_content(manifest: VerificationReviewManifest) -> str:
    """verification review manifest를 CSV 문자열로 직렬화한다."""

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
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
        ]
    )
    for item in manifest.items:
        writer.writerow(
            [
                item.document_id,
                item.provider_name,
                item.review_reason,
                item.existence_status,
                _serialize_flagged_fields(item),
                str(item.overall_pass).lower(),
                item.source_artifact_path,
                item.recommended_action,
                "",
                "",
                "",
                "",
            ]
        )
    return buffer.getvalue()


def _escape_markdown_cell(value: str) -> str:
    """Markdown table cell에서 깨질 수 있는 문자를 이스케이프한다."""

    return value.replace("|", r"\|").replace("\n", "<br>")


def _build_markdown_row(cells: list[str]) -> str:
    """Markdown table row를 생성한다."""

    escaped_cells = [_escape_markdown_cell(cell) for cell in cells]
    return f"| {' | '.join(escaped_cells)} |"


def _build_markdown_content(manifest: VerificationReviewManifest) -> str:
    """verification review manifest를 Markdown 문자열로 직렬화한다."""

    lines = [
        "# Verification Review Manifest",
        "",
        f"- run_id: {manifest.run_id}",
        f"- review_stage: {manifest.review_stage}",
        f"- item_count: {len(manifest.items)}",
        "",
        _build_markdown_row(
            [
                "document_id",
                "provider_name",
                "existence_status",
                "flagged_fields",
                "overall_pass",
                "review_reason",
                "recommended_action",
                "source_artifact_path",
            ]
        ),
        _build_markdown_row(["---"] * 8),
    ]
    for item in manifest.items:
        lines.append(
            _build_markdown_row(
                [
                    item.document_id,
                    item.provider_name,
                    item.existence_status,
                    _serialize_flagged_fields(item),
                    str(item.overall_pass).lower(),
                    item.review_reason,
                    item.recommended_action,
                    item.source_artifact_path,
                ]
            )
        )
    return "\n".join(lines) + "\n"


def build_verification_review_export(
    manifest: VerificationReviewManifest,
    *,
    export_format: str,
) -> str:
    """verification review manifest를 지정 형식의 문자열로 변환한다."""

    normalized_format = normalize_review_export_format(export_format)
    if normalized_format == "csv":
        return _build_csv_content(manifest)
    return _build_markdown_content(manifest)


def export_verification_review_manifest(
    manifest: VerificationReviewManifest,
    *,
    source_manifest_path: Path,
    export_format: str,
    output_path: Path | None = None,
) -> Path:
    """verification review manifest를 CSV 또는 Markdown 파일로 저장한다."""

    resolved_output_path = output_path or default_review_export_path(source_manifest_path, export_format)
    ensure_directory(resolved_output_path.parent)
    content = build_verification_review_export(manifest, export_format=export_format)
    resolved_output_path.write_text(content, encoding="utf-8")
    return resolved_output_path
