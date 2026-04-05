"""PnP Digest canonical schema 정의."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pnp_digest.domain.enums import (
    ApprovalStatus,
    DocumentType,
    LicenseStatus,
    OutputType,
    RelevanceDecision,
    ReviewStage,
    ReviewStatus,
    ReviewTaskStatus,
    StageExecutionStatus,
    StageName,
    VerificationStatus,
)
from pnp_digest.domain.schema import SCHEMA_VERSION


class DigestBaseModel(BaseModel):
    """모든 canonical model의 공통 설정."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, use_enum_values=True)


def enum_or_string_value(value: str | object) -> str:
    """enum 또는 문자열 입력을 항상 문자열 값으로 정규화한다."""

    return str(value)


class StageExecutionState(DigestBaseModel):
    """개별 stage 실행 상태."""

    status: StageExecutionStatus = Field(description="현재 stage의 실행 상태")
    artifact_path: str | None = Field(default=None, description="해당 stage 산출물의 대표 경로")
    updated_at: datetime | None = Field(default=None, description="상태가 마지막으로 갱신된 시각")
    message: str | None = Field(default=None, description="상태 설명 또는 실패 메모")


class PipelineRun(DigestBaseModel):
    """주간 배치 실행 단위를 표현하는 모델."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    run_id: str = Field(description="주간 실행 식별자")
    domain: str = Field(description="대상 기술 분야")
    week_start: date = Field(description="주간 브리프 기준 시작일")
    stage_status: dict[StageName, StageExecutionState] = Field(
        default_factory=dict,
        description="stage별 진행 상태",
    )
    started_at: datetime = Field(description="실행 시작 시각")
    ended_at: datetime | None = Field(default=None, description="실행 종료 시각")
    operator: str = Field(description="실행한 운영자 또는 배치 주체")
    config_version: str = Field(description="사용된 설정 버전")


class EvidenceSnippet(DigestBaseModel):
    """판정 또는 요약 근거로 사용된 snippet."""

    source_url: str | None = Field(default=None, description="근거의 원문 URL")
    locator: str = Field(description="근거 위치 정보")
    snippet_text: str = Field(description="근거 본문")
    supports_fields: list[str] = Field(
        min_length=1,
        description="이 snippet이 뒷받침하는 필드 이름 목록",
    )


class PaperMetadata(DigestBaseModel):
    """논문 전용 메타데이터."""

    metadata_type: Literal["paper"] = "paper"
    doi: str | None = Field(default=None, description="DOI")
    authors: list[str] = Field(default_factory=list, description="저자 목록")
    venue: str | None = Field(default=None, description="게재 학회 또는 저널")
    publisher: str | None = Field(default=None, description="출판사")
    publication_type: str | None = Field(default=None, description="논문 유형")
    license: str | None = Field(default=None, description="라이선스 정보")
    pdf_url: str | None = Field(default=None, description="PDF URL")


class PatentMetadata(DigestBaseModel):
    """특허 전용 메타데이터."""

    metadata_type: Literal["patent"] = "patent"
    patent_number: str | None = Field(default=None, description="공개 또는 등록 특허번호")
    application_number: str | None = Field(default=None, description="출원번호")
    jurisdiction: str | None = Field(default=None, description="관할 국가 또는 기관")
    applicants: list[str] = Field(default_factory=list, description="출원인 목록")
    assignees: list[str] = Field(default_factory=list, description="권리자 목록")
    inventors: list[str] = Field(default_factory=list, description="발명자 목록")
    filing_date: date | None = Field(default=None, description="출원일")
    publication_date: date | None = Field(default=None, description="공개일")
    grant_date: date | None = Field(default=None, description="등록일")
    cpc_codes: list[str] = Field(default_factory=list, description="CPC 분류 코드")
    ipc_codes: list[str] = Field(default_factory=list, description="IPC 분류 코드")
    family_id: str | None = Field(default=None, description="패밀리 식별자")


DocumentMetadata = Annotated[PaperMetadata | PatentMetadata, Field(discriminator="metadata_type")]


class RawSourceRecord(DigestBaseModel):
    """수집 단계에서 원문 payload를 추적하는 레코드."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    raw_id: str = Field(description="원시 레코드 식별자")
    document_type: DocumentType = Field(description="원문이 가리키는 문헌 유형")
    source_type: str = Field(description="source adapter가 사용하는 원문 분류")
    source_name: str = Field(description="원문 소스 이름")
    query: str | None = Field(default=None, description="수집 시 사용한 검색어")
    source_url: str | None = Field(default=None, description="원문 항목 URL")
    fetched_at: datetime = Field(description="수집 시각")
    raw_payload_path: str = Field(description="저장된 payload 파일 경로")
    checksum: str = Field(description="payload checksum")


class DocumentRecord(DigestBaseModel):
    """정규화된 공통 문헌 엔터티."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    document_id: str = Field(description="정규화된 문헌 식별자")
    document_type: DocumentType = Field(description="문헌 유형")
    canonical_title: str = Field(description="정규화된 제목")
    abstract_text: str | None = Field(default=None, description="정규화된 초록 또는 요약")
    publication_date: date | None = Field(default=None, description="대표 공개일")
    language: str | None = Field(default=None, description="문헌 언어")
    canonical_url: str | None = Field(default=None, description="대표 URL")
    source_record_ids: list[str] = Field(default_factory=list, description="병합된 원시 레코드 목록")
    fingerprint: str = Field(description="중복 판단에 사용하는 fingerprint")
    review_status: ReviewStatus = Field(default=ReviewStatus.PENDING, description="현재 검수 상태")
    dedup_candidate_keys: list[str] = Field(
        default_factory=list,
        description="중복 후보 비교를 위한 canonical key 목록",
    )
    metadata: DocumentMetadata = Field(description="문헌 유형별 세부 메타데이터")

    @model_validator(mode="after")
    def validate_document_type_matches_metadata(self) -> "DocumentRecord":
        """문헌 유형과 metadata discriminator의 일치 여부를 확인한다."""

        expected_type = enum_or_string_value(self.metadata.metadata_type)
        actual_type = enum_or_string_value(self.document_type)
        if actual_type != expected_type:
            raise ValueError("document_type과 metadata.metadata_type이 일치해야 합니다.")
        return self


class RelevanceAssessment(DigestBaseModel):
    """관련성 판정 결과와 근거."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    document_id: str = Field(description="대상 문헌 ID")
    rule_score: float = Field(ge=0.0, le=1.0, description="규칙 기반 점수")
    metadata_score: float = Field(ge=0.0, le=1.0, description="메타데이터 점수")
    llm_score: float | None = Field(default=None, ge=0.0, le=1.0, description="LLM 점수")
    final_decision: RelevanceDecision = Field(description="최종 관련성 판정")
    matched_terms: list[str] = Field(default_factory=list, description="매칭된 용어")
    matched_classifications: list[str] = Field(default_factory=list, description="매칭된 분류 코드")
    decision_reason: str = Field(description="판정 사유 요약")
    evidence_links_or_snippets: list[EvidenceSnippet] = Field(
        default_factory=list,
        description="관련성 근거",
    )
    review_required: bool = Field(default=False, description="사람 검수 필요 여부")


class VerificationResult(DigestBaseModel):
    """필드 단위 검증 결과."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    verification_field: str = Field(description="검증 대상 필드")
    status: VerificationStatus = Field(description="검증 상태")
    evidence_source: str | None = Field(default=None, description="근거 출처")
    evidence_text: str | None = Field(default=None, description="근거 텍스트")
    confidence: float = Field(ge=0.0, le=1.0, description="검증 신뢰도")
    notes: str | None = Field(default=None, description="검토 메모")
    expected_value: str | None = Field(default=None, description="내부 기록값")
    observed_value: str | None = Field(default=None, description="외부 근거값")
    checked_at: datetime | None = Field(default=None, description="검증 시각")


class VerificationReport(DigestBaseModel):
    """문헌별 검증 결과 묶음."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    document_id: str = Field(description="대상 문헌 ID")
    overall_pass: bool = Field(description="전체 검증 통과 여부")
    review_required: bool = Field(description="사람 검수 필요 여부")
    results: list[VerificationResult] = Field(default_factory=list, description="필드별 결과")


class AudienceExplanation(DigestBaseModel):
    """직급별 설명 정책을 구조화한 블록."""

    purpose: str = Field(description="이 설명이 필요한 목적")
    audience_focus: list[str] = Field(default_factory=list, description="강조할 관점")
    explanation_text: str = Field(description="설명 본문")
    key_points: list[str] = Field(default_factory=list, description="핵심 포인트")
    cautions: list[str] = Field(default_factory=list, description="오해 방지 또는 제한 사항")
    action_prompt: str | None = Field(default=None, description="후속 검토 또는 액션 제안")


class SummaryPayload(DigestBaseModel):
    """근거 연결형 구조화 요약."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    background_context: str = Field(description="문헌이 등장한 배경")
    problem_statement: str = Field(description="기존 기술의 한계 또는 문제 정의")
    purpose: str = Field(description="연구 또는 발명의 목적")
    core_idea: str = Field(description="핵심 아이디어")
    expected_effect: str = Field(description="예상 효과")
    limitations_or_unknowns: list[str] = Field(default_factory=list, description="한계 또는 미확인 사항")
    evidence_links_or_snippets: list[EvidenceSnippet] = Field(
        min_length=1,
        description="요약 필드와 연결된 근거",
    )
    entry_level_explanation: AudienceExplanation = Field(description="신입사원용 설명")
    manager_level_explanation: AudienceExplanation = Field(description="과장급 설명")
    director_level_explanation: AudienceExplanation = Field(description="부장급 설명")
    summary_confidence: float = Field(ge=0.0, le=1.0, description="요약 신뢰도")
    human_review_notes: str | None = Field(default=None, description="사람 검수 메모")


class FigureAsset(DigestBaseModel):
    """문헌 figure 자산과 라이선스 상태."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    figure_id: str = Field(description="figure 식별자")
    document_id: str = Field(description="연결된 문헌 ID")
    figure_label: str | None = Field(default=None, description="문헌 내부 label")
    caption: str | None = Field(default=None, description="figure caption")
    source_locator: str | None = Field(default=None, description="원문 내 위치")
    asset_path: str | None = Field(default=None, description="저장된 이미지 경로")
    license_status: LicenseStatus = Field(description="라이선스 상태")
    license_source: str | None = Field(default=None, description="라이선스 근거")
    manual_review_status: ReviewStatus = Field(description="수동 검토 상태")
    approved_for_output: bool = Field(default=False, description="최종 산출물 삽입 가능 여부")


class ReviewChecklistItem(DigestBaseModel):
    """검수 체크리스트 항목."""

    item_id: str = Field(description="체크 항목 식별자")
    prompt: str = Field(description="검토 질문")
    required: bool = Field(default=True, description="필수 여부")
    response: str | None = Field(default=None, description="검토 결과 또는 메모")


class ReviewTask(DigestBaseModel):
    """사람 검수 워크플로 엔터티."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    review_task_id: str = Field(description="검수 작업 식별자")
    target_type: str = Field(description="검토 대상 유형")
    target_id: str = Field(description="검토 대상 식별자")
    review_stage: ReviewStage = Field(description="검수 단계")
    assignee: str | None = Field(default=None, description="담당자")
    status: ReviewTaskStatus = Field(description="검수 상태")
    checklist: list[ReviewChecklistItem] = Field(default_factory=list, description="검수 체크리스트")
    notes: str | None = Field(default=None, description="검토 메모")
    reviewed_at: datetime | None = Field(default=None, description="검토 완료 시각")


class OutputBundle(DigestBaseModel):
    """배포용 문서 산출물 메타데이터."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    bundle_id: str = Field(description="산출물 묶음 ID")
    run_id: str = Field(description="연결된 run ID")
    output_type: OutputType = Field(description="산출물 형식")
    template_version: str = Field(description="템플릿 버전")
    included_document_ids: list[str] = Field(default_factory=list, description="포함된 문헌 ID")
    output_path: str = Field(description="산출물 경로")
    approval_status: ApprovalStatus = Field(description="배포 승인 상태")


class SamplePaperPayload(DigestBaseModel):
    """로컬 fixture에서 사용하는 논문 payload."""

    document_type: Literal["paper"] = "paper"
    title: str = Field(description="원문 제목")
    abstract_text: str | None = Field(default=None, description="원문 초록")
    publication_date: date | None = Field(default=None, description="발행일")
    language: str | None = Field(default=None, description="언어")
    canonical_url: str | None = Field(default=None, description="대표 URL")
    doi: str | None = Field(default=None, description="DOI")
    authors: list[str] = Field(default_factory=list, description="저자 목록")
    venue: str | None = Field(default=None, description="게재처")
    publisher: str | None = Field(default=None, description="출판사")
    publication_type: str | None = Field(default=None, description="논문 유형")
    license: str | None = Field(default=None, description="라이선스")
    pdf_url: str | None = Field(default=None, description="PDF URL")


class SamplePatentPayload(DigestBaseModel):
    """로컬 fixture에서 사용하는 특허 payload."""

    document_type: Literal["patent"] = "patent"
    title: str = Field(description="원문 제목")
    abstract_text: str | None = Field(default=None, description="원문 요약")
    publication_date: date | None = Field(default=None, description="공개일")
    filing_date: date | None = Field(default=None, description="출원일")
    grant_date: date | None = Field(default=None, description="등록일")
    language: str | None = Field(default=None, description="언어")
    canonical_url: str | None = Field(default=None, description="대표 URL")
    patent_number: str | None = Field(default=None, description="특허번호")
    application_number: str | None = Field(default=None, description="출원번호")
    jurisdiction: str | None = Field(default=None, description="관할")
    applicants: list[str] = Field(default_factory=list, description="출원인")
    assignees: list[str] = Field(default_factory=list, description="권리자")
    inventors: list[str] = Field(default_factory=list, description="발명자")
    cpc_codes: list[str] = Field(default_factory=list, description="CPC 코드")
    ipc_codes: list[str] = Field(default_factory=list, description="IPC 코드")
    family_id: str | None = Field(default=None, description="패밀리 ID")


SamplePayload = Annotated[SamplePaperPayload | SamplePatentPayload, Field(discriminator="document_type")]


class SampleSourceRecord(DigestBaseModel):
    """Phase 0 로컬 fixture 입력 레코드."""

    fixture_id: str = Field(description="샘플 fixture 식별자")
    source_type: str = Field(description="source adapter 분류")
    source_name: str = Field(description="source 이름")
    query: str | None = Field(default=None, description="검색어")
    source_url: str | None = Field(default=None, description="source URL")
    fetched_at: datetime = Field(description="수집 시각")
    payload: SamplePayload = Field(description="문헌 유형별 payload")


class IngestArtifact(DigestBaseModel):
    """ingest 단계 산출물."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    run: PipelineRun = Field(description="연결된 실행 정보")
    raw_records: list[RawSourceRecord] = Field(default_factory=list, description="저장된 원시 레코드 목록")


class NormalizedArtifact(DigestBaseModel):
    """normalize 단계 산출물."""

    schema_version: str = Field(default=SCHEMA_VERSION, description="적용된 canonical schema 버전")
    run: PipelineRun = Field(description="연결된 실행 정보")
    documents: list[DocumentRecord] = Field(default_factory=list, description="정규화된 문헌 목록")
