"""특허 검증 provider 및 비교 로직."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Protocol

from pydantic import Field, model_validator

from pnp_digest.domain.enums import VerificationStatus
from pnp_digest.domain.models import (
    DigestBaseModel,
    DocumentRecord,
    PatentMetadata,
    VerificationResult,
)
from pnp_digest.services.io import read_json
from pnp_digest.services.normalization import normalize_identifier, normalize_whitespace

PATENT_EXISTENCE_FIELD = "patent_existence"
PATENT_VERIFICATION_FIELDS = (
    "patent_number",
    "title",
    "applicant_or_assignee",
    "filing_date",
    "publication_date",
    "summary",
)
EXACT_MATCH_FIELDS = {"patent_number", "filing_date", "publication_date"}


class PatentVerificationOutcome(DigestBaseModel):
    """provider가 반환하는 단일 특허 검증 결과."""

    provider_name: str = Field(description="사용한 provider 이름")
    existence_check: VerificationResult = Field(description="특허 실재 여부 확인 결과")
    field_results: list[VerificationResult] = Field(default_factory=list, description="필드별 비교 결과")


class PatentVerificationProvider(Protocol):
    """특허 검증 provider 인터페이스."""

    provider_name: str

    def verify_patent(self, document: DocumentRecord) -> PatentVerificationOutcome:
        """단일 특허 문헌을 검증한다."""


class MockPatentObservationRecord(DigestBaseModel):
    """mock provider가 읽는 특허 관측값."""

    patent_number: str = Field(description="조회한 특허번호")
    exists: bool = Field(default=True, description="mock registry 상 존재 여부")
    evidence_source: str = Field(description="근거 출처 식별자")
    evidence_text: str = Field(description="근거 텍스트")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="관측값 기본 신뢰도")
    notes: str | None = Field(default=None, description="추가 메모")
    title: str | None = Field(default=None, description="관측 제목")
    applicant_or_assignee: str | None = Field(default=None, description="관측 출원인 또는 권리자")
    filing_date: date | None = Field(default=None, description="관측 출원일")
    publication_date: date | None = Field(default=None, description="관측 공개일")
    summary: str | None = Field(default=None, description="관측 요약")


class MockPatentVerificationFixture(DigestBaseModel):
    """mock provider 입력 fixture."""

    records: list[MockPatentObservationRecord] = Field(default_factory=list, description="특허 관측값 목록")


class ManualPatentVerificationRecord(DigestBaseModel):
    """manual provider가 읽는 수동 검증 결과."""

    patent_number: str = Field(description="대상 특허번호")
    existence_check: VerificationResult = Field(description="존재 확인 결과")
    field_results: list[VerificationResult] = Field(default_factory=list, description="필드별 수동 검증 결과")

    @model_validator(mode="after")
    def validate_required_fields(self) -> "ManualPatentVerificationRecord":
        """수동 검증 결과가 고정 필드를 모두 포함하는지 확인한다."""

        if self.existence_check.verification_field != PATENT_EXISTENCE_FIELD:
            raise ValueError("existence_check.verification_field는 patent_existence여야 합니다.")

        field_names = [result.verification_field for result in self.field_results]
        if sorted(field_names) != sorted(PATENT_VERIFICATION_FIELDS):
            raise ValueError("field_results는 고정된 특허 검증 필드를 모두 포함해야 합니다.")
        return self


class ManualPatentVerificationFixture(DigestBaseModel):
    """manual provider 입력 fixture."""

    records: list[ManualPatentVerificationRecord] = Field(default_factory=list, description="수동 검증 결과 목록")


def _serialize_value(value: str | date | None) -> str | None:
    """비교/기록에 사용할 문자열 값을 만든다."""

    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return normalize_whitespace(value)


def _text_tokens(value: str | None) -> set[str]:
    """텍스트 비교용 token 집합을 만든다."""

    if value is None:
        return set()
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return {token for token in normalized.split() if token}


def _build_result(
    *,
    verification_field: str,
    status: VerificationStatus,
    evidence_source: str | None,
    evidence_text: str | None,
    confidence: float,
    notes: str | None,
    expected_value: str | None,
    observed_value: str | None,
) -> VerificationResult:
    """`VerificationResult`를 일관된 형식으로 생성한다."""

    return VerificationResult(
        verification_field=verification_field,
        status=status,
        evidence_source=evidence_source,
        evidence_text=evidence_text,
        confidence=confidence,
        notes=notes,
        expected_value=expected_value,
        observed_value=observed_value,
        checked_at=None,
    )


def _extract_expected_fields(document: DocumentRecord) -> dict[str, str | None]:
    """정규화된 특허 문헌에서 기대값을 추출한다."""

    if not isinstance(document.metadata, PatentMetadata):
        raise ValueError("특허 검증은 patent 문헌에 대해서만 수행할 수 있습니다.")

    names: list[str] = []
    for candidate in [*document.metadata.assignees, *document.metadata.applicants]:
        normalized = normalize_whitespace(candidate)
        if normalized and normalized not in names:
            names.append(normalized)

    return {
        "patent_number": _serialize_value(document.metadata.patent_number),
        "title": _serialize_value(document.canonical_title),
        "applicant_or_assignee": " | ".join(names) if names else None,
        "filing_date": _serialize_value(document.metadata.filing_date),
        "publication_date": _serialize_value(document.metadata.publication_date),
        "summary": _serialize_value(document.abstract_text),
    }


def _compare_text_field(expected_value: str, observed_value: str) -> VerificationStatus:
    """텍스트 필드의 match 상태를 계산한다."""

    expected_normalized = normalize_whitespace(expected_value) or ""
    observed_normalized = normalize_whitespace(observed_value) or ""
    if expected_normalized.lower() == observed_normalized.lower():
        return VerificationStatus.MATCHED

    expected_tokens = _text_tokens(expected_normalized)
    observed_tokens = _text_tokens(observed_normalized)
    overlap = expected_tokens & observed_tokens
    if expected_tokens and overlap and len(overlap) / len(expected_tokens) >= 0.5:
        return VerificationStatus.PARTIALLY_MATCHED

    if expected_normalized.lower() in observed_normalized.lower() or observed_normalized.lower() in expected_normalized.lower():
        return VerificationStatus.PARTIALLY_MATCHED

    return VerificationStatus.MISMATCHED


def _compare_field(
    *,
    field_name: str,
    expected_value: str | None,
    observed_value: str | None,
    evidence_source: str,
    evidence_text: str,
    notes: str | None,
    base_confidence: float,
) -> VerificationResult:
    """단일 필드의 비교 결과를 생성한다."""

    field_evidence_text = f"{evidence_text} | observed_{field_name}={observed_value or 'N/A'}"
    if expected_value is None:
        return _build_result(
            verification_field=field_name,
            status=VerificationStatus.NOT_CHECKED,
            evidence_source=evidence_source,
            evidence_text=field_evidence_text,
            confidence=0.0,
            notes="normalized artifact에 기대값이 없어 비교를 건너뜀",
            expected_value=None,
            observed_value=observed_value,
        )

    if observed_value is None:
        return _build_result(
            verification_field=field_name,
            status=VerificationStatus.MISSING,
            evidence_source=evidence_source,
            evidence_text=field_evidence_text,
            confidence=0.1,
            notes=notes or "provider 관측값에 해당 필드가 없음",
            expected_value=expected_value,
            observed_value=None,
        )

    if field_name in EXACT_MATCH_FIELDS:
        status = (
            VerificationStatus.MATCHED
            if normalize_identifier(expected_value) == normalize_identifier(observed_value)
            else VerificationStatus.MISMATCHED
        )
    else:
        status = _compare_text_field(expected_value, observed_value)

    confidence_by_status = {
        VerificationStatus.MATCHED: min(base_confidence, 1.0),
        VerificationStatus.PARTIALLY_MATCHED: min(base_confidence, 0.75),
        VerificationStatus.MISMATCHED: min(base_confidence, 0.25),
    }
    return _build_result(
        verification_field=field_name,
        status=status,
        evidence_source=evidence_source,
        evidence_text=field_evidence_text,
        confidence=confidence_by_status[status],
        notes=notes,
        expected_value=expected_value,
        observed_value=observed_value,
    )


def _not_checked_field_results(
    *,
    expected_fields: dict[str, str | None],
    evidence_source: str,
    evidence_text: str,
    notes: str,
    status: VerificationStatus = VerificationStatus.NOT_CHECKED,
) -> list[VerificationResult]:
    """필드 비교를 수행하지 못한 경우 기본 결과를 만든다."""

    return [
        _build_result(
            verification_field=field_name,
            status=status,
            evidence_source=evidence_source,
            evidence_text=evidence_text,
            confidence=0.0,
            notes=notes,
            expected_value=expected_fields[field_name],
            observed_value=None,
        )
        for field_name in PATENT_VERIFICATION_FIELDS
    ]


class MockPatentVerificationProvider:
    """로컬 fixture 관측값으로 자동 비교하는 mock provider."""

    provider_name = "mock"

    def __init__(self, fixture_path: Path) -> None:
        fixture = MockPatentVerificationFixture.model_validate(read_json(fixture_path))
        self.fixture_path = fixture_path
        self.records = {
            normalize_identifier(record.patent_number): record for record in fixture.records
        }

    def verify_patent(self, document: DocumentRecord) -> PatentVerificationOutcome:
        """정규화된 특허 문헌을 mock 관측값과 비교한다."""

        expected_fields = _extract_expected_fields(document)
        patent_number = expected_fields["patent_number"]
        record = self.records.get(normalize_identifier(patent_number))
        default_source = f"mock:{self.fixture_path.name}"

        if record is None:
            existence_check = _build_result(
                verification_field=PATENT_EXISTENCE_FIELD,
                status=VerificationStatus.MISSING,
                evidence_source=default_source,
                evidence_text="mock fixture에 해당 특허 레코드가 없음",
                confidence=0.0,
                notes="존재 확인 실패",
                expected_value=patent_number,
                observed_value=None,
            )
            return PatentVerificationOutcome(
                provider_name=self.provider_name,
                existence_check=existence_check,
                field_results=_not_checked_field_results(
                    expected_fields=expected_fields,
                    evidence_source=default_source,
                    evidence_text="존재 확인 실패로 필드 비교를 수행하지 않음",
                    notes="mock fixture record 없음",
                ),
            )

        if not record.exists:
            existence_check = _build_result(
                verification_field=PATENT_EXISTENCE_FIELD,
                status=VerificationStatus.MISSING,
                evidence_source=record.evidence_source,
                evidence_text=record.evidence_text,
                confidence=min(record.confidence, 0.2),
                notes=record.notes or "mock registry에서 특허를 찾지 못함",
                expected_value=patent_number,
                observed_value=None,
            )
            return PatentVerificationOutcome(
                provider_name=self.provider_name,
                existence_check=existence_check,
                field_results=_not_checked_field_results(
                    expected_fields=expected_fields,
                    evidence_source=record.evidence_source,
                    evidence_text=record.evidence_text,
                    notes="존재 확인 실패로 필드 비교를 수행하지 않음",
                ),
            )

        existence_check = _build_result(
            verification_field=PATENT_EXISTENCE_FIELD,
            status=VerificationStatus.MATCHED,
            evidence_source=record.evidence_source,
            evidence_text=record.evidence_text,
            confidence=record.confidence,
            notes=record.notes,
            expected_value=patent_number,
            observed_value=_serialize_value(record.patent_number),
        )

        observed_fields = {
            "patent_number": _serialize_value(record.patent_number),
            "title": _serialize_value(record.title),
            "applicant_or_assignee": _serialize_value(record.applicant_or_assignee),
            "filing_date": _serialize_value(record.filing_date),
            "publication_date": _serialize_value(record.publication_date),
            "summary": _serialize_value(record.summary),
        }
        field_results = [
            _compare_field(
                field_name=field_name,
                expected_value=expected_fields[field_name],
                observed_value=observed_fields[field_name],
                evidence_source=record.evidence_source,
                evidence_text=record.evidence_text,
                notes=record.notes,
                base_confidence=record.confidence,
            )
            for field_name in PATENT_VERIFICATION_FIELDS
        ]
        return PatentVerificationOutcome(
            provider_name=self.provider_name,
            existence_check=existence_check,
            field_results=field_results,
        )


class ManualPatentVerificationProvider:
    """수동으로 작성된 필드별 결과를 반환하는 provider."""

    provider_name = "manual"

    def __init__(self, fixture_path: Path) -> None:
        fixture = ManualPatentVerificationFixture.model_validate(read_json(fixture_path))
        self.fixture_path = fixture_path
        self.records = {
            normalize_identifier(record.patent_number): record for record in fixture.records
        }

    def verify_patent(self, document: DocumentRecord) -> PatentVerificationOutcome:
        """수동 검증 fixture의 결과를 반환한다."""

        expected_fields = _extract_expected_fields(document)
        patent_number = expected_fields["patent_number"]
        record = self.records.get(normalize_identifier(patent_number))
        default_source = f"manual:{self.fixture_path.name}"

        if record is None:
            return PatentVerificationOutcome(
                provider_name=self.provider_name,
                existence_check=_build_result(
                    verification_field=PATENT_EXISTENCE_FIELD,
                    status=VerificationStatus.MANUAL_REVIEW_REQUIRED,
                    evidence_source=default_source,
                    evidence_text="manual fixture에 해당 특허 결과가 없음",
                    confidence=0.0,
                    notes="수동 검증 결과 누락",
                    expected_value=patent_number,
                    observed_value=None,
                ),
                field_results=_not_checked_field_results(
                    expected_fields=expected_fields,
                    evidence_source=default_source,
                    evidence_text="manual fixture에 해당 특허 결과가 없어 필드 검증을 수행하지 않음",
                    notes="수동 검증 결과 누락",
                    status=VerificationStatus.MANUAL_REVIEW_REQUIRED,
                ),
            )

        results_by_field = {result.verification_field: result for result in record.field_results}
        field_results = [results_by_field[field_name] for field_name in PATENT_VERIFICATION_FIELDS]
        return PatentVerificationOutcome(
            provider_name=self.provider_name,
            existence_check=record.existence_check,
            field_results=field_results,
        )


def load_patent_verification_provider(
    provider_name: str,
    fixture_path: Path,
) -> PatentVerificationProvider:
    """provider 이름과 fixture 경로로 특허 검증 provider를 생성한다."""

    normalized_name = provider_name.strip().lower()
    if normalized_name == "mock":
        return MockPatentVerificationProvider(fixture_path)
    if normalized_name == "manual":
        return ManualPatentVerificationProvider(fixture_path)
    raise ValueError("provider는 mock 또는 manual 이어야 합니다.")
