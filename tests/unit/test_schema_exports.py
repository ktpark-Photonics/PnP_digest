"""schema export 계약 테스트."""

import json
from pathlib import Path

from pnp_digest.domain import (
    DocumentRecord,
    ExplainArtifact,
    ManualReviewManifest,
    OpsClosureReport,
    OpsClosureResolutionArtifact,
    OpsEscalationManifest,
    OpsEscalationResolutionArtifact,
    OpsFollowupManifest,
    OpsFollowupResolutionArtifact,
    OpsHandoffArtifact,
    OpsHandoffResolutionArtifact,
    PublishArtifact,
    PublishRetryManifest,
    PublishReviewResolutionArtifact,
    RelevanceArtifact,
    ReleaseManifest,
    ReleaseReviewResolutionArtifact,
    RenderArtifact,
    SummaryArtifact,
    SummaryPayload,
    VerificationArtifact,
    VerificationReviewManifest,
    VerificationReviewResolutionArtifact,
    VerificationReport,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _schema_summary(model: type) -> dict[str, list[str]]:
    """모델의 상위 schema shape를 요약한다."""

    schema = model.model_json_schema()
    return {
        "required": schema.get("required", []),
        "properties": list(schema.get("properties", {}).keys()),
    }


def test_schema_summary_snapshot_matches_models() -> None:
    """핵심 모델의 상위 schema shape가 snapshot과 일치해야 한다."""

    snapshot_path = PROJECT_ROOT / "tests/fixtures/schema_summary_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    current = {
        "DocumentRecord": _schema_summary(DocumentRecord),
        "SummaryPayload": _schema_summary(SummaryPayload),
        "RelevanceArtifact": _schema_summary(RelevanceArtifact),
        "SummaryArtifact": _schema_summary(SummaryArtifact),
        "ExplainArtifact": _schema_summary(ExplainArtifact),
        "RenderArtifact": _schema_summary(RenderArtifact),
        "ReleaseManifest": _schema_summary(ReleaseManifest),
        "ReleaseReviewResolutionArtifact": _schema_summary(ReleaseReviewResolutionArtifact),
        "PublishReviewResolutionArtifact": _schema_summary(PublishReviewResolutionArtifact),
        "PublishArtifact": _schema_summary(PublishArtifact),
        "PublishRetryManifest": _schema_summary(PublishRetryManifest),
        "OpsClosureReport": _schema_summary(OpsClosureReport),
        "OpsClosureResolutionArtifact": _schema_summary(OpsClosureResolutionArtifact),
        "OpsEscalationManifest": _schema_summary(OpsEscalationManifest),
        "OpsEscalationResolutionArtifact": _schema_summary(OpsEscalationResolutionArtifact),
        "OpsFollowupManifest": _schema_summary(OpsFollowupManifest),
        "OpsFollowupResolutionArtifact": _schema_summary(OpsFollowupResolutionArtifact),
        "OpsHandoffArtifact": _schema_summary(OpsHandoffArtifact),
        "OpsHandoffResolutionArtifact": _schema_summary(OpsHandoffResolutionArtifact),
        "ManualReviewManifest": _schema_summary(ManualReviewManifest),
        "VerificationReport": _schema_summary(VerificationReport),
        "VerificationArtifact": _schema_summary(VerificationArtifact),
        "VerificationReviewManifest": _schema_summary(VerificationReviewManifest),
        "VerificationReviewResolutionArtifact": _schema_summary(VerificationReviewResolutionArtifact),
    }

    assert current == snapshot
