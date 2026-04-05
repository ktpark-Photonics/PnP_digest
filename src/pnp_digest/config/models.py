"""도메인 설정 모델."""

from pydantic import Field

from pnp_digest.domain.models import DigestBaseModel


class ThresholdConfig(DigestBaseModel):
    """관련성 및 검수 threshold 설정."""

    relevant_min: float = Field(default=0.75, ge=0.0, le=1.0)
    borderline_min: float = Field(default=0.5, ge=0.0, le=1.0)


class DomainProfile(DigestBaseModel):
    """기술 분야별 사전 및 규칙 설정."""

    domain_name: str = Field(description="기술 분야 이름")
    synonyms: list[str] = Field(default_factory=list, description="동의어 목록")
    positive_terms: list[str] = Field(default_factory=list, description="허용 또는 가중 키워드")
    negative_terms: list[str] = Field(default_factory=list, description="배제 키워드")
    classification_allowlist: list[str] = Field(default_factory=list, description="허용 분류 코드")
    classification_denylist: list[str] = Field(default_factory=list, description="배제 분류 코드")
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig, description="점수 threshold")
