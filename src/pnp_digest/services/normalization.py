"""정규화 및 dedup 유틸리티."""

from __future__ import annotations

import hashlib
import re
from datetime import date

from pnp_digest.domain.enums import DocumentType, ReviewStatus
from pnp_digest.domain.models import (
    DocumentRecord,
    PaperMetadata,
    PatentMetadata,
    RawSourceRecord,
    SamplePaperPayload,
    SamplePatentPayload,
    enum_or_string_value,
)


def normalize_whitespace(value: str | None) -> str | None:
    """연속 공백을 정규화한다."""

    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized or None


def normalize_identifier(value: str | None) -> str | None:
    """식별자 비교용 canonical form을 만든다."""

    if value is None:
        return None
    compact = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return compact or None


def normalize_url(value: str | None) -> str | None:
    """URL의 불필요한 공백만 제거한다."""

    return normalize_whitespace(value)


def build_fingerprint(
    document_type: DocumentType,
    canonical_title: str,
    publication_date: date | None,
    primary_identifier: str | None,
) -> str:
    """중복 판단에 사용할 fingerprint를 생성한다."""

    material = "|".join(
        [
            enum_or_string_value(document_type),
            canonical_title.lower(),
            publication_date.isoformat() if publication_date else "",
            primary_identifier or "",
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_document_id(
    document_type: DocumentType,
    canonical_title: str,
    publication_date: date | None,
    doi: str | None = None,
    patent_number: str | None = None,
) -> str:
    """문헌 유형별 canonical ID를 생성한다."""

    document_type_value = enum_or_string_value(document_type)

    if document_type_value == DocumentType.PAPER and doi:
        return f"paper:doi:{normalize_identifier(doi)}"

    if document_type_value == DocumentType.PATENT and patent_number:
        return f"patent:number:{normalize_identifier(patent_number)}"

    title_key = normalize_identifier(canonical_title) or "untitled"
    date_key = publication_date.isoformat() if publication_date else "unknown-date"
    return f"{document_type_value}:title:{title_key}:{date_key}"


def build_dedup_candidate_keys(
    document_type: DocumentType,
    canonical_title: str,
    publication_date: date | None,
    doi: str | None = None,
    patent_number: str | None = None,
) -> list[str]:
    """중복 후보 비교용 key 목록을 생성한다."""

    keys: list[str] = []
    if doi:
        keys.append(f"doi:{normalize_identifier(doi)}")
    if patent_number:
        keys.append(f"patent_number:{normalize_identifier(patent_number)}")
    title_hash_source = "|".join(
        [enum_or_string_value(document_type), canonical_title.lower(), publication_date.isoformat() if publication_date else ""]
    )
    title_hash = hashlib.sha256(title_hash_source.encode("utf-8")).hexdigest()[:16]
    keys.append(f"title_hash:{title_hash}")
    return keys


def normalize_document(raw_record: RawSourceRecord, payload: SamplePaperPayload | SamplePatentPayload) -> DocumentRecord:
    """원시 payload를 canonical `DocumentRecord`로 변환한다."""

    canonical_title = normalize_whitespace(payload.title)
    if canonical_title is None:
        raise ValueError("title은 비어 있을 수 없습니다.")

    abstract_text = normalize_whitespace(payload.abstract_text)
    language = normalize_whitespace(payload.language)
    canonical_url = normalize_url(payload.canonical_url)

    if raw_record.document_type == DocumentType.PAPER:
        paper_payload = payload
        metadata = PaperMetadata(
            doi=normalize_whitespace(paper_payload.doi),
            authors=[item for item in (normalize_whitespace(author) for author in paper_payload.authors) if item],
            venue=normalize_whitespace(paper_payload.venue),
            publisher=normalize_whitespace(paper_payload.publisher),
            publication_type=normalize_whitespace(paper_payload.publication_type),
            license=normalize_whitespace(paper_payload.license),
            pdf_url=normalize_url(paper_payload.pdf_url),
        )
        document_id = build_document_id(
            document_type=DocumentType.PAPER,
            canonical_title=canonical_title,
            publication_date=paper_payload.publication_date,
            doi=paper_payload.doi,
        )
        dedup_candidate_keys = build_dedup_candidate_keys(
            document_type=DocumentType.PAPER,
            canonical_title=canonical_title,
            publication_date=paper_payload.publication_date,
            doi=paper_payload.doi,
        )
        fingerprint = build_fingerprint(
            document_type=DocumentType.PAPER,
            canonical_title=canonical_title,
            publication_date=paper_payload.publication_date,
            primary_identifier=paper_payload.doi,
        )
        publication_date = paper_payload.publication_date
    else:
        patent_payload = payload
        metadata = PatentMetadata(
            patent_number=normalize_whitespace(patent_payload.patent_number),
            application_number=normalize_whitespace(patent_payload.application_number),
            jurisdiction=normalize_whitespace(patent_payload.jurisdiction),
            applicants=[item for item in (normalize_whitespace(applicant) for applicant in patent_payload.applicants) if item],
            assignees=[item for item in (normalize_whitespace(assignee) for assignee in patent_payload.assignees) if item],
            inventors=[item for item in (normalize_whitespace(inventor) for inventor in patent_payload.inventors) if item],
            filing_date=patent_payload.filing_date,
            publication_date=patent_payload.publication_date,
            grant_date=patent_payload.grant_date,
            cpc_codes=[item for item in (normalize_whitespace(code) for code in patent_payload.cpc_codes) if item],
            ipc_codes=[item for item in (normalize_whitespace(code) for code in patent_payload.ipc_codes) if item],
            family_id=normalize_whitespace(patent_payload.family_id),
        )
        document_id = build_document_id(
            document_type=DocumentType.PATENT,
            canonical_title=canonical_title,
            publication_date=patent_payload.publication_date,
            patent_number=patent_payload.patent_number,
        )
        dedup_candidate_keys = build_dedup_candidate_keys(
            document_type=DocumentType.PATENT,
            canonical_title=canonical_title,
            publication_date=patent_payload.publication_date,
            patent_number=patent_payload.patent_number,
        )
        fingerprint = build_fingerprint(
            document_type=DocumentType.PATENT,
            canonical_title=canonical_title,
            publication_date=patent_payload.publication_date,
            primary_identifier=patent_payload.patent_number,
        )
        publication_date = patent_payload.publication_date

    return DocumentRecord(
        document_id=document_id,
        document_type=raw_record.document_type,
        canonical_title=canonical_title,
        abstract_text=abstract_text,
        publication_date=publication_date,
        language=language,
        canonical_url=canonical_url,
        source_record_ids=[raw_record.raw_id],
        fingerprint=fingerprint,
        review_status=ReviewStatus.PENDING,
        dedup_candidate_keys=dedup_candidate_keys,
        metadata=metadata,
    )


def merge_documents(existing: DocumentRecord, candidate: DocumentRecord) -> DocumentRecord:
    """동일 canonical ID를 가진 문헌을 보수적으로 병합한다."""

    merged_source_ids = sorted(set(existing.source_record_ids + candidate.source_record_ids))
    merged_dedup_keys = sorted(set(existing.dedup_candidate_keys + candidate.dedup_candidate_keys))

    return existing.model_copy(
        update={
            "source_record_ids": merged_source_ids,
            "dedup_candidate_keys": merged_dedup_keys,
            "canonical_url": existing.canonical_url or candidate.canonical_url,
            "abstract_text": existing.abstract_text or candidate.abstract_text,
            "language": existing.language or candidate.language,
        }
    )
