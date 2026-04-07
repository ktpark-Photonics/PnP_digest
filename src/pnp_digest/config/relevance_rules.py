"""관련성 규칙 사전 로딩 유틸리티."""

from __future__ import annotations

from pathlib import Path
import tomllib

from pydantic import Field

from pnp_digest.domain.models import DigestBaseModel


class ClassificationRuleConfig(DigestBaseModel):
    """분류 코드 기반 규칙 설정."""

    allowlist: list[str] = Field(default_factory=list, description="허용 분류 코드")
    denylist: list[str] = Field(default_factory=list, description="배제 분류 코드")
    allow_weight: float = Field(default=0.2, description="허용 분류 코드 가중치")
    deny_weight: float = Field(default=-0.35, description="배제 분류 코드 가중치")
    relevant_min: float = Field(default=0.7, ge=0.0, le=1.0, description="relevant 최소 점수")
    borderline_min: float = Field(default=0.45, ge=0.0, le=1.0, description="borderline 최소 점수")


class RelevanceRuleSet(DigestBaseModel):
    """규칙 기반 관련성 판정 설정 묶음."""

    allow_terms: list[str] = Field(default_factory=list, description="허용 키워드")
    deny_terms: list[str] = Field(default_factory=list, description="배제 키워드")
    synonym_terms: list[str] = Field(default_factory=list, description="도메인 동의어")
    allow_term_weight: float = Field(default=0.2, description="허용 키워드 가중치")
    deny_term_weight: float = Field(default=-0.4, description="배제 키워드 가중치")
    synonym_weight: float = Field(default=0.1, description="도메인 동의어 가중치")
    base_score: float = Field(default=0.3, ge=0.0, le=1.0, description="기본 점수")
    classification: ClassificationRuleConfig = Field(default_factory=ClassificationRuleConfig)


def _read_keyword_lines(path: Path) -> list[str]:
    """키워드 파일에서 주석과 빈 줄을 제거해 읽는다."""

    keywords: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        keywords.append(line)
    return keywords


def load_relevance_rules(dictionary_dir: Path) -> RelevanceRuleSet:
    """사전/규칙 파일을 읽어 관련성 규칙을 구성한다."""

    allow_terms = _read_keyword_lines(dictionary_dir / "cis_allow_keywords.txt")
    deny_terms = _read_keyword_lines(dictionary_dir / "cis_deny_keywords.txt")

    classification_payload = tomllib.loads(
        (dictionary_dir / "cis_classification_rules.toml").read_text(encoding="utf-8")
    )
    synonym_terms = classification_payload.get("synonym_terms", [])

    return RelevanceRuleSet(
        allow_terms=allow_terms,
        deny_terms=deny_terms,
        synonym_terms=synonym_terms,
        allow_term_weight=classification_payload.get("allow_term_weight", 0.2),
        deny_term_weight=classification_payload.get("deny_term_weight", -0.4),
        synonym_weight=classification_payload.get("synonym_weight", 0.1),
        base_score=classification_payload.get("base_score", 0.3),
        classification=ClassificationRuleConfig.model_validate(classification_payload.get("classification", {})),
    )
