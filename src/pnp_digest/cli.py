"""PnP Digest CLI."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import typer

app = typer.Typer(help="CIS 주간 기술 브리프 배치 파이프라인 CLI")


def build_run(run_id: str, operator: str, week_start: date | None = None):
    """CLI 실행에 사용할 기본 `PipelineRun`을 생성한다."""

    from pnp_digest.domain import PipelineRun

    return PipelineRun(
        run_id=run_id,
        domain="cmos_image_sensor",
        week_start=week_start or date.today(),
        started_at=datetime.now(UTC),
        operator=operator,
        config_version="phase0-default",
    )


def parse_iso_date(value: str | None, option_name: str = "--week-start") -> date | None:
    """CLI 문자열 입력을 ISO 날짜로 파싱한다."""

    if value is None:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise typer.BadParameter(
            f"{option_name}는 YYYY-MM-DD 형식의 날짜여야 합니다. 예: 2026-04-05"
        ) from error


@app.command("export-schemas")
def export_schemas(output_dir: Path = Path("docs/schemas")) -> None:
    """핵심 canonical schema를 JSON schema 파일로 내보낸다."""

    from pnp_digest.domain import (
        DocumentRecord,
        ExplainArtifact,
        FigureAsset,
        IngestArtifact,
        ManualReviewManifest,
        NormalizedArtifact,
        OpsClosureReport,
        OpsClosureResolutionArtifact,
        OpsEscalationManifest,
        OpsEscalationResolutionArtifact,
        OpsFollowupManifest,
        OpsFollowupResolutionArtifact,
        OpsHandoffArtifact,
        OpsHandoffResolutionArtifact,
        OutputBundle,
        PipelineRun,
        PublishArtifact,
        PublishRetryManifest,
        PublishReviewResolutionArtifact,
        RawSourceRecord,
        RelevanceArtifact,
        RelevanceAssessment,
        ReleaseManifest,
        ReleaseReviewResolutionArtifact,
        RenderArtifact,
        ReviewTask,
        SummaryArtifact,
        SummaryPayload,
        VerificationArtifact,
        VerificationReviewManifest,
        VerificationReviewResolutionArtifact,
        VerificationReport,
        VerificationResult,
    )
    from pnp_digest.services.io import write_json

    models = [
        PipelineRun,
        RawSourceRecord,
        DocumentRecord,
        RelevanceAssessment,
        RelevanceArtifact,
        VerificationResult,
        VerificationReport,
        VerificationArtifact,
        VerificationReviewManifest,
        VerificationReviewResolutionArtifact,
        SummaryArtifact,
        ExplainArtifact,
        RenderArtifact,
        ReleaseManifest,
        ReleaseReviewResolutionArtifact,
        PublishReviewResolutionArtifact,
        PublishArtifact,
        PublishRetryManifest,
        OpsClosureReport,
        OpsClosureResolutionArtifact,
        OpsEscalationManifest,
        OpsEscalationResolutionArtifact,
        OpsFollowupManifest,
        OpsFollowupResolutionArtifact,
        OpsHandoffArtifact,
        OpsHandoffResolutionArtifact,
        SummaryPayload,
        FigureAsset,
        ReviewTask,
        OutputBundle,
        IngestArtifact,
        NormalizedArtifact,
        ManualReviewManifest,
    ]
    for model in models:
        file_path = output_dir / f"{model.__name__}.schema.json"
        write_json(file_path, model.model_json_schema())
    typer.echo(f"{len(models)}개 schema를 {output_dir}에 저장했습니다.")


@app.command("ingest")
def ingest(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    input_path: Path = typer.Option(..., exists=True, dir_okay=False, help="로컬 fixture JSON 경로"),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    operator: str = typer.Option("manual", help="실행 주체"),
    week_start: str | None = typer.Option(None, help="브리프 기준 시작일 (YYYY-MM-DD)"),
) -> None:
    """로컬 fixture를 ingest artifact로 저장한다."""

    from pnp_digest.pipelines.ingest import run_ingest

    run = build_run(
        run_id=run_id,
        operator=operator,
        week_start=parse_iso_date(week_start),
    )
    artifact = run_ingest(run=run, input_path=input_path, artifact_root=artifact_root)
    typer.echo(f"ingest 완료: {len(artifact.raw_records)}건")


@app.command("normalize")
def normalize(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    ingest_artifact: Path = typer.Option(..., exists=True, dir_okay=False, help="ingest artifact 경로"),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
) -> None:
    """ingest artifact를 정규화된 문헌 목록으로 변환한다."""

    from pnp_digest.pipelines.normalize import run_normalize

    artifact = run_normalize(
        run_id=run_id,
        ingest_artifact_path=ingest_artifact,
        artifact_root=artifact_root,
    )
    typer.echo(f"normalize 완료: {len(artifact.documents)}건")


def announce_phase_stub(stage_name: str) -> None:
    """Phase 0에서 미구현 stage임을 명확히 알린다."""

    raise typer.Exit(
        code=2,
    )


@app.command("assess-relevance")
def assess_relevance(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    normalized_artifact: Path = typer.Option(..., exists=True, dir_okay=False, help="normalized artifact 경로"),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    dictionary_dir: Path = typer.Option(Path("data/dictionaries"), exists=True, file_okay=False, help="규칙 사전 디렉터리"),
) -> None:
    """규칙 기반 관련성 판정을 수행하고 결과 artifact를 저장한다."""

    from pnp_digest.pipelines.assess_relevance import run_assess_relevance

    relevance_artifact, review_manifest = run_assess_relevance(
        run_id=run_id,
        normalized_artifact_path=normalized_artifact,
        artifact_root=artifact_root,
        dictionary_dir=dictionary_dir,
    )
    typer.echo(
        "assess-relevance 완료: "
        f"{len(relevance_artifact.assessments)}건 판정, "
        f"{len(review_manifest.items)}건 수동 검토"
    )


@app.command("verify")
def verify(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    normalized_artifact: Path = typer.Option(..., exists=True, dir_okay=False, help="normalized artifact 경로"),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    provider: str = typer.Option("mock", help="특허 검증 provider 이름 (mock/manual)"),
    provider_data: Path = typer.Option(..., exists=True, dir_okay=False, help="provider 입력 JSON 경로"),
) -> None:
    """특허 검증 provider를 사용해 verify artifact를 생성한다."""

    from pnp_digest.pipelines.verify import run_verify

    artifact, review_manifest = run_verify(
        run_id=run_id,
        normalized_artifact_path=normalized_artifact,
        artifact_root=artifact_root,
        provider_name=provider,
        provider_data_path=provider_data,
    )
    review_count = len(review_manifest.items) if review_manifest is not None else 0
    typer.echo(f"verify 완료: {len(artifact.reports)}건 특허 검증, {review_count}건 수동 검토")


@app.command("summarize")
def summarize(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    normalized_artifact: Path = typer.Option(..., exists=True, dir_okay=False, help="normalized artifact 경로"),
    verification_review_resolution: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="review import로 생성된 verification review resolution artifact 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
) -> None:
    """승인된 verification review 결과만 summary artifact로 변환한다."""

    from pnp_digest.pipelines.summarize import run_summarize

    artifact = run_summarize(
        run_id=run_id,
        normalized_artifact_path=normalized_artifact,
        verification_review_resolution_path=verification_review_resolution,
        artifact_root=artifact_root,
    )
    typer.echo(f"summarize 완료: {len(artifact.summaries)}건 요약")


@app.command("explain")
def explain(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    summary_artifact: Path = typer.Option(..., exists=True, dir_okay=False, help="summary artifact 경로"),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
) -> None:
    """summary artifact를 직급별 설명 artifact로 변환한다."""

    from pnp_digest.pipelines.explain import run_explain

    artifact = run_explain(
        run_id=run_id,
        summary_artifact_path=summary_artifact,
        artifact_root=artifact_root,
    )
    typer.echo(f"explain 완료: {len(artifact.explanations)}건 설명")


review_app = typer.Typer(help="파일 기반 검수 보조 명령")
app.add_typer(review_app, name="review")


@review_app.command("export")
def review_export(
    verification_review_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="verification review manifest JSON 경로",
    ),
    export_format: str = typer.Option("csv", "--format", help="export 형식 (csv/markdown)"),
    output_path: Path | None = typer.Option(None, help="출력 파일 경로"),
) -> None:
    """수동 검토용 verification manifest를 CSV 또는 Markdown으로 내보낸다."""

    from pnp_digest.domain import VerificationReviewManifest
    from pnp_digest.services.io import read_model
    from pnp_digest.services.review_export import (
        export_verification_review_manifest,
        normalize_review_export_format,
    )

    try:
        normalized_format = normalize_review_export_format(export_format)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--format") from error

    manifest = read_model(verification_review_manifest, VerificationReviewManifest)
    written_path = export_verification_review_manifest(
        manifest,
        source_manifest_path=verification_review_manifest,
        export_format=normalized_format,
        output_path=output_path,
    )
    typer.echo(f"review export 완료: {len(manifest.items)}건 -> {written_path}")


@review_app.command("import")
def review_import(
    verification_review_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="verification review manifest JSON 경로",
    ),
    review_csv: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="review export 후 사람이 수정한 CSV 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_path: Path | None = typer.Option(None, help="출력 artifact 경로"),
) -> None:
    """수정된 verification review CSV를 JSON artifact로 가져온다."""

    from pnp_digest.pipelines.review import run_import_verification_review

    artifact, written_path = run_import_verification_review(
        verification_review_manifest_path=verification_review_manifest,
        review_csv_path=review_csv,
        artifact_root=artifact_root,
        output_path=output_path,
    )
    typer.echo(f"review import 완료: {len(artifact.items)}건 -> {written_path}")


@review_app.command("release-export")
def review_release_export(
    release_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="release manifest JSON 경로",
    ),
    output_path: Path | None = typer.Option(None, help="출력 CSV 경로"),
) -> None:
    """최종 배포 검토용 release manifest를 CSV로 내보낸다."""

    from pnp_digest.domain import ReleaseManifest
    from pnp_digest.services.io import read_model
    from pnp_digest.services.release_review import export_release_review_manifest

    manifest = read_model(release_manifest, ReleaseManifest)
    written_path = export_release_review_manifest(
        manifest,
        source_manifest_path=release_manifest,
        output_path=output_path,
    )
    typer.echo(f"review release export 완료: {len(manifest.bundles)}개 bundle -> {written_path}")


@review_app.command("release-import")
def review_release_import(
    release_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="release manifest JSON 경로",
    ),
    review_csv: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="release-export 후 사람이 수정한 CSV 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_path: Path | None = typer.Option(None, help="출력 artifact 경로"),
) -> None:
    """수정된 release review CSV를 JSON artifact로 가져온다."""

    from pnp_digest.pipelines.review import run_import_release_review

    artifact, written_path = run_import_release_review(
        release_manifest_path=release_manifest,
        review_csv_path=review_csv,
        artifact_root=artifact_root,
        output_path=output_path,
    )
    typer.echo(
        "review release import 완료: "
        f"signoff={artifact.review_signoff} -> {written_path}"
    )


@review_app.command("publish-export")
def review_publish_export(
    publish_artifact: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="publish artifact JSON 경로",
    ),
    output_path: Path | None = typer.Option(None, help="출력 CSV 경로"),
) -> None:
    """publish artifact를 사람이 확인할 CSV로 내보낸다."""

    from pnp_digest.domain import PublishArtifact
    from pnp_digest.services.io import read_model
    from pnp_digest.services.publish_review import export_publish_review_manifest

    artifact = read_model(publish_artifact, PublishArtifact)
    written_path = export_publish_review_manifest(
        artifact,
        source_publish_artifact_path=publish_artifact,
        output_path=output_path,
    )
    typer.echo(
        "review publish export 완료: "
        f"{len(artifact.publish_records)}개 record -> {written_path}"
    )


@review_app.command("publish-import")
def review_publish_import(
    publish_artifact: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="publish artifact JSON 경로",
    ),
    review_csv: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="publish-export 후 사람이 수정한 CSV 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_path: Path | None = typer.Option(None, help="출력 artifact 경로"),
) -> None:
    """수정된 publish review CSV를 JSON artifact로 가져온다."""

    from pnp_digest.pipelines.review import run_import_publish_review

    artifact, written_path = run_import_publish_review(
        publish_artifact_path=publish_artifact,
        review_csv_path=review_csv,
        artifact_root=artifact_root,
        output_path=output_path,
    )
    typer.echo(
        "review publish import 완료: "
        f"published={artifact.published_record_count}, failed={artifact.failed_record_count} -> {written_path}"
    )


@review_app.command("handoff-export")
def review_handoff_export(
    ops_handoff: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="ops handoff artifact JSON 경로",
    ),
    output_path: Path | None = typer.Option(None, help="출력 CSV 경로"),
) -> None:
    """ops handoff artifact를 사람이 수정할 CSV로 내보낸다."""

    from pnp_digest.domain import OpsHandoffArtifact
    from pnp_digest.services.handoff_review import export_ops_handoff_manifest
    from pnp_digest.services.io import read_model

    artifact = read_model(ops_handoff, OpsHandoffArtifact)
    written_path = export_ops_handoff_manifest(
        artifact,
        source_handoff_path=ops_handoff,
        output_path=output_path,
    )
    typer.echo(f"review handoff export 완료: {len(artifact.tasks)}개 task -> {written_path}")


@review_app.command("handoff-import")
def review_handoff_import(
    ops_handoff: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="ops handoff artifact JSON 경로",
    ),
    review_csv: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="handoff-export 후 사람이 수정한 CSV 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_path: Path | None = typer.Option(None, help="출력 artifact 경로"),
) -> None:
    """수정된 handoff review CSV를 JSON artifact로 가져온다."""

    from pnp_digest.pipelines.review import run_import_handoff_review

    artifact, written_path = run_import_handoff_review(
        ops_handoff_path=ops_handoff,
        review_csv_path=review_csv,
        artifact_root=artifact_root,
        output_path=output_path,
    )
    typer.echo(
        "review handoff import 완료: "
        f"open={artifact.open_task_count}, closed={artifact.closed_task_count} -> {written_path}"
    )


@review_app.command("followup-export")
def review_followup_export(
    followup_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="followup manifest JSON 경로",
    ),
    output_path: Path | None = typer.Option(None, help="출력 CSV 경로"),
) -> None:
    """followup manifest를 운영용 CSV 큐로 내보낸다."""

    from pnp_digest.domain import OpsFollowupManifest
    from pnp_digest.services.followup_queue import export_ops_daily_queue
    from pnp_digest.services.io import read_model

    artifact = read_model(followup_manifest, OpsFollowupManifest)
    written_path = export_ops_daily_queue(
        artifact,
        source_followup_manifest_path=followup_manifest,
        output_path=output_path,
    )
    typer.echo(f"review followup export 완료: {len(artifact.tasks)}개 task -> {written_path}")


@review_app.command("escalation-export")
def review_escalation_export(
    escalation_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="escalation manifest JSON 경로",
    ),
    output_path: Path | None = typer.Option(None, help="출력 CSV 경로"),
) -> None:
    """escalation manifest를 사람이 수정할 CSV로 내보낸다."""

    from pnp_digest.domain import OpsEscalationManifest
    from pnp_digest.services.escalation_review import export_escalation_review_manifest
    from pnp_digest.services.io import read_model

    artifact = read_model(escalation_manifest, OpsEscalationManifest)
    written_path = export_escalation_review_manifest(
        artifact,
        source_escalation_manifest_path=escalation_manifest,
        output_path=output_path,
    )
    typer.echo(f"review escalation export 완료: {len(artifact.tasks)}개 task -> {written_path}")


@review_app.command("closure-export")
def review_closure_export(
    closure_report: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="closure report JSON 경로",
    ),
    output_path: Path | None = typer.Option(None, help="출력 CSV 경로"),
) -> None:
    """closure report를 사람이 확인할 CSV로 내보낸다."""

    from pnp_digest.domain import OpsClosureReport
    from pnp_digest.services.closure_review import export_closure_report
    from pnp_digest.services.io import read_model

    artifact = read_model(closure_report, OpsClosureReport)
    written_path = export_closure_report(
        artifact,
        source_closure_report_path=closure_report,
        output_path=output_path,
    )
    total_tasks = artifact.closed_task_count + artifact.remaining_task_count
    typer.echo(f"review closure export 완료: {total_tasks}개 task -> {written_path}")


@review_app.command("closure-import")
def review_closure_import(
    closure_report: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="closure report JSON 경로",
    ),
    review_csv: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="closure-export 후 사람이 수정한 CSV 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_path: Path | None = typer.Option(None, help="출력 artifact 경로"),
) -> None:
    """수정된 closure review CSV를 JSON artifact로 가져온다."""

    from pnp_digest.pipelines.review import run_import_closure_review

    artifact, written_path = run_import_closure_review(
        closure_report_path=closure_report,
        review_csv_path=review_csv,
        artifact_root=artifact_root,
        output_path=output_path,
    )
    typer.echo(
        "review closure import 완료: "
        f"closed={artifact.closed_task_count}, remaining={artifact.remaining_task_count} -> {written_path}"
    )


@review_app.command("closure-brief")
def review_closure_brief(
    closure_resolution: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="closure resolution JSON 경로",
    ),
    output_path: Path | None = typer.Option(None, help="출력 Markdown 경로"),
    title: str = typer.Option("Ops Closure Resolution Brief", help="보고서 제목"),
) -> None:
    """closure resolution을 사람이 공유할 Markdown 보고서로 내보낸다."""

    from pnp_digest.domain import OpsClosureResolutionArtifact
    from pnp_digest.services.closure_brief import export_closure_brief_markdown
    from pnp_digest.services.io import read_model

    artifact = read_model(closure_resolution, OpsClosureResolutionArtifact)
    written_path = export_closure_brief_markdown(
        artifact,
        source_closure_resolution_path=closure_resolution,
        output_path=output_path,
        title=title,
    )
    total_tasks = artifact.closed_task_count + artifact.remaining_task_count
    typer.echo(f"review closure brief 완료: {total_tasks}개 task -> {written_path}")


@review_app.command("followup-import")
def review_followup_import(
    followup_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="followup manifest JSON 경로",
    ),
    review_csv: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="followup-export 후 사람이 수정한 CSV 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_path: Path | None = typer.Option(None, help="출력 artifact 경로"),
) -> None:
    """수정된 followup review CSV를 JSON artifact로 가져온다."""

    from pnp_digest.pipelines.review import run_import_followup_review

    artifact, written_path = run_import_followup_review(
        followup_manifest_path=followup_manifest,
        review_csv_path=review_csv,
        artifact_root=artifact_root,
        output_path=output_path,
    )
    typer.echo(
        "review followup import 완료: "
        f"open={artifact.open_task_count}, in_review={artifact.in_review_task_count}, closed={artifact.closed_task_count} -> {written_path}"
    )


@review_app.command("escalation-import")
def review_escalation_import(
    escalation_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="escalation manifest JSON 경로",
    ),
    review_csv: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="escalation-export 후 사람이 수정한 CSV 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_path: Path | None = typer.Option(None, help="출력 artifact 경로"),
) -> None:
    """수정된 escalation review CSV를 JSON artifact로 가져온다."""

    from pnp_digest.pipelines.review import run_import_escalation_review

    artifact, written_path = run_import_escalation_review(
        escalation_manifest_path=escalation_manifest,
        review_csv_path=review_csv,
        artifact_root=artifact_root,
        output_path=output_path,
    )
    typer.echo(
        "review escalation import 완료: "
        f"open={artifact.open_task_count}, in_review={artifact.in_review_task_count}, closed={artifact.closed_task_count} -> {written_path}"
    )


@app.command("render")
def render(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    explain_artifact: Path = typer.Option(..., exists=True, dir_okay=False, help="explain artifact 경로"),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_type: str = typer.Option("markdown", help="render 출력 형식 (markdown/docx/pdf/pptx)"),
    output_path: Path | None = typer.Option(None, help="생성할 brief 파일 경로"),
    title: str = typer.Option("PnP Digest Brief", help="brief 제목"),
) -> None:
    """explain artifact를 Markdown, DOCX, PDF 또는 PPTX brief와 render artifact로 변환한다."""

    from pnp_digest.domain import OutputType
    from pnp_digest.pipelines.render import run_render

    try:
        normalized_output_type = OutputType(output_type.strip().lower())
    except ValueError as error:
        raise typer.BadParameter(
            "render 출력 형식은 markdown, docx, pdf 또는 pptx 이어야 합니다.",
            param_hint="--output-type",
        ) from error

    artifact, written_path = run_render(
        run_id=run_id,
        explain_artifact_path=explain_artifact,
        artifact_root=artifact_root,
        output_type=normalized_output_type,
        output_path=output_path,
        brief_title=title,
    )
    typer.echo(f"render 완료: {len(artifact.bundles)}개 bundle -> {written_path}")


@app.command("release")
def release(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    render_artifact: Path = typer.Option(..., exists=True, dir_okay=False, help="render artifact 경로"),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    distribution_targets: list[str] = typer.Option(
        ["internal"],
        "--distribution-target",
        help="배포 대상 채널",
    ),
    release_notes: list[str] = typer.Option(
        [],
        "--release-note",
        help="release manifest에 남길 메모",
    ),
    mark_published: bool = typer.Option(
        False,
        "--mark-published",
        help="모든 bundle이 승인 상태일 때 published_at을 함께 기록한다.",
    ),
) -> None:
    """render artifact를 release manifest로 정리한다."""

    from pnp_digest.pipelines.release import run_release

    manifest = run_release(
        run_id=run_id,
        render_artifact_path=render_artifact,
        artifact_root=artifact_root,
        distribution_targets=distribution_targets,
        release_notes=release_notes,
        mark_published=mark_published,
    )
    typer.echo(
        "release 완료: "
        f"{len(manifest.bundles)}개 bundle 정리, "
        f"{len(manifest.approved_bundle_ids)}개 승인 bundle"
    )


@app.command("publish")
def publish(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    release_review_resolution: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="review release-import로 생성된 release review resolution artifact 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
) -> None:
    """release review resolution을 publish stub artifact로 변환한다."""

    from pnp_digest.pipelines.publish import run_publish

    artifact = run_publish(
        run_id=run_id,
        release_review_resolution_path=release_review_resolution,
        artifact_root=artifact_root,
    )
    if artifact.blocked_reason:
        typer.echo(
            "publish 완료: "
            f"{len(artifact.publish_records)}건 simulated publish, blocked={artifact.blocked_reason}"
        )
        return
    typer.echo(f"publish 완료: {len(artifact.publish_records)}건 simulated publish")


@app.command("retry")
def retry(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    publish_review_resolution: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="review publish-import로 생성된 publish review resolution artifact 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
) -> None:
    """publish review resolution을 retry manifest로 정리한다."""

    from pnp_digest.pipelines.retry import run_retry

    artifact = run_retry(
        run_id=run_id,
        publish_review_resolution_path=publish_review_resolution,
        artifact_root=artifact_root,
    )
    if artifact.retry_count == 0:
        typer.echo(f"retry 완료: {artifact.retry_count}건, blocked={artifact.blocked_reason or 'none'}")
        return
    typer.echo(f"retry 완료: {artifact.retry_count}건")


@app.command("handoff")
def handoff(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    retry_manifest: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="retry로 생성된 retry manifest artifact 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    handoff_team: str = typer.Option("ops", help="전달 대상 팀"),
) -> None:
    """retry manifest를 운영 handoff artifact로 정리한다."""

    from pnp_digest.pipelines.handoff import run_handoff

    artifact = run_handoff(
        run_id=run_id,
        retry_manifest_path=retry_manifest,
        artifact_root=artifact_root,
        handoff_team=handoff_team,
    )
    if artifact.open_task_count == 0:
        typer.echo(f"handoff 완료: {artifact.open_task_count}건, blocked={artifact.blocked_reason or 'none'}")
        return
    typer.echo(f"handoff 완료: {artifact.open_task_count}건 -> team={artifact.handoff_team}")


@app.command("followup")
def followup(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    ops_handoff_resolution: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="review handoff-import로 생성된 ops handoff resolution artifact 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    followup_team: str = typer.Option("ops", help="후속 대응 대상 팀"),
) -> None:
    """ops handoff resolution을 followup manifest로 정리한다."""

    from pnp_digest.pipelines.followup import run_followup

    artifact = run_followup(
        run_id=run_id,
        ops_handoff_resolution_path=ops_handoff_resolution,
        artifact_root=artifact_root,
        followup_team=followup_team,
    )
    if not artifact.tasks:
        typer.echo(f"followup 완료: 0건, blocked={artifact.blocked_reason or 'none'}")
        return
    typer.echo(f"followup 완료: {len(artifact.tasks)}건 -> team={artifact.followup_team}")


@app.command("escalation")
def escalation(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    followup_resolution: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="review followup-import로 생성된 followup resolution artifact 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    escalation_team: str = typer.Option("ops-lead", help="에스컬레이션 대상 팀"),
) -> None:
    """followup resolution을 escalation manifest로 정리한다."""

    from pnp_digest.pipelines.escalation import run_escalation

    artifact = run_escalation(
        run_id=run_id,
        followup_resolution_path=followup_resolution,
        artifact_root=artifact_root,
        escalation_team=escalation_team,
    )
    if not artifact.tasks:
        typer.echo(f"escalation 완료: 0건, blocked={artifact.blocked_reason or 'none'}")
        return
    typer.echo(f"escalation 완료: {len(artifact.tasks)}건 -> team={artifact.escalation_team}")


@app.command("closure")
def closure(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    escalation_resolution: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="review escalation-import로 생성된 escalation resolution artifact 경로",
    ),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    closure_team: str = typer.Option("ops-lead", help="최종 종료 보고를 정리할 팀"),
) -> None:
    """escalation resolution을 closure report로 정리한다."""

    from pnp_digest.pipelines.closure import run_closure

    artifact = run_closure(
        run_id=run_id,
        escalation_resolution_path=escalation_resolution,
        artifact_root=artifact_root,
        closure_team=closure_team,
    )
    if not artifact.closed_tasks and not artifact.remaining_tasks:
        typer.echo(f"closure 완료: 0건, blocked={artifact.blocked_reason or 'none'}")
        return
    typer.echo(
        "closure 완료: "
        f"closed={artifact.closed_task_count}, remaining={artifact.remaining_task_count} -> team={artifact.closure_team}"
    )


if __name__ == "__main__":
    app()
