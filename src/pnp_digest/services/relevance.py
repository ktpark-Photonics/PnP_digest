"""규칙 기반 관련성 판정 서비스."""

from __future__ import annotations

from dataclasses import dataclass

from pnp_digest.config import RelevanceRuleSet
from pnp_digest.domain.enums import RelevanceDecision
from pnp_digest.domain.models import (
    DocumentRecord,
    EvidenceSnippet,
    PatentMetadata,
    RelevanceAssessment,
)


@dataclass(slots=True)
class MatchResult:
    """본문/분류 매칭 결과."""

    allow_terms: list[str]
    deny_terms: list[str]
    synonym_terms: list[str]
    allow_classifications: list[str]
    deny_classifications: list[str]


def _collect_classification_codes(document: DocumentRecord) -> list[str]:
    """문헌에서 분류 코드를 추출한다."""

    if not isinstance(document.metadata, PatentMetadata):
        return []
    codes = [*document.metadata.cpc_codes, *document.metadata.ipc_codes]
    return sorted({code.strip().upper() for code in codes if code and code.strip()})


def _find_matches(document: DocumentRecord, rules: RelevanceRuleSet) -> MatchResult:
    """문헌 본문과 분류 코드에서 규칙 매칭을 찾는다."""

    normalized_text = " ".join(
        part.strip().lower()
        for part in [document.canonical_title, document.abstract_text or ""]
        if part and part.strip()
    )

    allow_terms = sorted({term for term in rules.allow_terms if term.lower() in normalized_text})
    deny_terms = sorted({term for term in rules.deny_terms if term.lower() in normalized_text})
    synonym_terms = sorted({term for term in rules.synonym_terms if term.lower() in normalized_text})

    classifications = _collect_classification_codes(document)
    allow_classifications = sorted(
        {code for code in classifications if code in {item.upper() for item in rules.classification.allowlist}}
    )
    deny_classifications = sorted(
        {code for code in classifications if code in {item.upper() for item in rules.classification.denylist}}
    )

    return MatchResult(
        allow_terms=allow_terms,
        deny_terms=deny_terms,
        synonym_terms=synonym_terms,
        allow_classifications=allow_classifications,
        deny_classifications=deny_classifications,
    )


def _clamp_score(score: float) -> float:
    """점수를 0.0~1.0으로 제한한다."""

    return max(0.0, min(1.0, score))


def _build_evidence(document: DocumentRecord, matches: MatchResult) -> list[EvidenceSnippet]:
    """판정 근거 snippet을 생성한다."""

    evidence_items: list[EvidenceSnippet] = []

    if matches.allow_terms or matches.deny_terms or matches.synonym_terms:
        term_summary = ", ".join(matches.allow_terms + matches.synonym_terms + matches.deny_terms)
        evidence_items.append(
            EvidenceSnippet(
                source_url=document.canonical_url,
                locator="title+abstract",
                snippet_text=f"용어 매칭: {term_summary}",
                supports_fields=["matched_terms", "rule_score", "final_decision"],
            )
        )

    if matches.allow_classifications or matches.deny_classifications:
        class_summary = ", ".join(matches.allow_classifications + matches.deny_classifications)
        evidence_items.append(
            EvidenceSnippet(
                source_url=document.canonical_url,
                locator="metadata.classification_codes",
                snippet_text=f"분류 매칭: {class_summary}",
                supports_fields=["matched_classifications", "rule_score", "final_decision"],
            )
        )

    if not evidence_items:
        evidence_items.append(
            EvidenceSnippet(
                source_url=document.canonical_url,
                locator="title",
                snippet_text=f"명시적 키워드/분류 매칭 없음: {document.canonical_title}",
                supports_fields=["rule_score", "final_decision"],
            )
        )

    return evidence_items


def assess_document_relevance(document: DocumentRecord, rules: RelevanceRuleSet) -> RelevanceAssessment:
    """단일 문헌의 관련성을 규칙 기반으로 판정한다."""

    matches = _find_matches(document, rules)

    score = rules.base_score
    score += len(matches.allow_terms) * rules.allow_term_weight
    score += len(matches.synonym_terms) * rules.synonym_weight
    score += len(matches.deny_terms) * rules.deny_term_weight
    score += len(matches.allow_classifications) * rules.classification.allow_weight
    score += len(matches.deny_classifications) * rules.classification.deny_weight

    rule_score = round(_clamp_score(score), 4)

    if rule_score >= rules.classification.relevant_min:
        final_decision = RelevanceDecision.RELEVANT
    elif rule_score >= rules.classification.borderline_min:
        final_decision = RelevanceDecision.BORDERLINE
    else:
        final_decision = RelevanceDecision.NOT_RELEVANT

    matched_terms = [
        *[f"allow:{term}" for term in matches.allow_terms],
        *[f"synonym:{term}" for term in matches.synonym_terms],
        *[f"deny:{term}" for term in matches.deny_terms],
    ]
    matched_classifications = [
        *[f"allow:{code}" for code in matches.allow_classifications],
        *[f"deny:{code}" for code in matches.deny_classifications],
    ]

    reason = (
        f"allow_terms={len(matches.allow_terms)}, synonym_terms={len(matches.synonym_terms)}, "
        f"deny_terms={len(matches.deny_terms)}, allow_classes={len(matches.allow_classifications)}, "
        f"deny_classes={len(matches.deny_classifications)}"
    )

    evidence = _build_evidence(document, matches)

    return RelevanceAssessment(
        document_id=document.document_id,
        rule_score=rule_score,
        metadata_score=rule_score,
        final_decision=final_decision,
        matched_terms=matched_terms,
        matched_classifications=matched_classifications,
        decision_reason=reason,
        evidence_links_or_snippets=evidence,
        review_required=final_decision == RelevanceDecision.BORDERLINE,
    )
