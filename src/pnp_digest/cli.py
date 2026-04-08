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
        OutputBundle,
        PipelineRun,
        RawSourceRecord,
        RelevanceArtifact,
        RelevanceAssessment,
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


@app.command("render")
def render(
    run_id: str = typer.Option(..., help="주간 실행 ID"),
    explain_artifact: Path = typer.Option(..., exists=True, dir_okay=False, help="explain artifact 경로"),
    artifact_root: Path = typer.Option(Path("artifacts/runs"), help="artifact 루트 경로"),
    output_path: Path | None = typer.Option(None, help="생성할 Markdown brief 경로"),
    title: str = typer.Option("PnP Digest Brief", help="Markdown brief 제목"),
) -> None:
    """explain artifact를 Markdown brief와 render artifact로 변환한다."""

    from pnp_digest.pipelines.render import run_render

    artifact, written_path = run_render(
        run_id=run_id,
        explain_artifact_path=explain_artifact,
        artifact_root=artifact_root,
        output_path=output_path,
        brief_title=title,
    )
    typer.echo(f"render 완료: {len(artifact.bundles)}개 bundle -> {written_path}")


if __name__ == "__main__":
    app()
