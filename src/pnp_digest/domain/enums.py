"""도메인 전반에서 공유하는 enum 정의."""

from enum import StrEnum


class DocumentType(StrEnum):
    """문헌의 상위 유형."""

    PAPER = "paper"
    PATENT = "patent"


class StageName(StrEnum):
    """파이프라인 stage 이름."""

    INGEST = "ingest"
    NORMALIZE = "normalize"
    ASSESS_RELEVANCE = "assess_relevance"
    VERIFY = "verify"
    SUMMARIZE = "summarize"
    EXPLAIN = "explain"
    REVIEW = "review"
    RENDER = "render"
    RELEASE = "release"
    PUBLISH = "publish"


class StageExecutionStatus(StrEnum):
    """stage 실행 상태."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReviewStatus(StrEnum):
    """문헌 또는 자산의 검수 상태."""

    PENDING = "pending"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    APPROVED = "approved"
    REJECTED = "rejected"


class RelevanceDecision(StrEnum):
    """관련성 판단 결과."""

    RELEVANT = "relevant"
    BORDERLINE = "borderline"
    NOT_RELEVANT = "not_relevant"


class VerificationStatus(StrEnum):
    """필드 단위 검증 상태."""

    MATCHED = "matched"
    PARTIALLY_MATCHED = "partially_matched"
    MISMATCHED = "mismatched"
    MISSING = "missing"
    NOT_CHECKED = "not_checked"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class LicenseStatus(StrEnum):
    """figure 라이선스 상태."""

    UNKNOWN = "unknown"
    NOT_ALLOWED = "not_allowed"
    ALLOWED_WITH_ATTRIBUTION = "allowed_with_attribution"
    LICENSED = "licensed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class ReviewStage(StrEnum):
    """사람 검수가 개입하는 단계."""

    RELEVANCE = "relevance"
    VERIFICATION = "verification"
    SUMMARY = "summary"
    FIGURE = "figure"
    FINAL_RELEASE = "final_release"
    PUBLISH = "publish"


class ReviewTaskStatus(StrEnum):
    """검수 작업 상태."""

    OPEN = "open"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class OutputType(StrEnum):
    """최종 산출물 형식."""

    MARKDOWN = "markdown"
    DOCX = "docx"
    PPTX = "pptx"
    PDF = "pdf"


class ApprovalStatus(StrEnum):
    """배포 산출물 승인 상태."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PublishStatus(StrEnum):
    """publish stub 실행 상태."""

    SIMULATED = "simulated"
    PUBLISHED = "published"
    FAILED = "failed"
