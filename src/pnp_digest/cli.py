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
        FigureAsset,
        IngestArtifact,
        NormalizedArtifact,
        OutputBundle,
        PipelineRun,
        RawSourceRecord,
        RelevanceAssessment,
        ReviewTask,
        SummaryPayload,
        VerificationResult,
    )
    from pnp_digest.services.io import write_json

    models = [
        PipelineRun,
        RawSourceRecord,
        DocumentRecord,
        RelevanceAssessment,
        VerificationResult,
        SummaryPayload,
        FigureAsset,
        ReviewTask,
        OutputBundle,
        IngestArtifact,
        NormalizedArtifact,
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
def assess_relevance() -> None:
    """관련성 판정 stage skeleton."""

    typer.echo("Phase 0에서는 assess-relevance가 아직 skeleton 상태입니다.")
    announce_phase_stub("assess-relevance")


@app.command("verify")
def verify() -> None:
    """검증 stage skeleton."""

    typer.echo("Phase 0에서는 verify가 아직 skeleton 상태입니다.")
    announce_phase_stub("verify")


@app.command("summarize")
def summarize() -> None:
    """요약 stage skeleton."""

    typer.echo("Phase 0에서는 summarize가 아직 skeleton 상태입니다.")
    announce_phase_stub("summarize")


@app.command("explain")
def explain() -> None:
    """직급별 설명 stage skeleton."""

    typer.echo("Phase 0에서는 explain이 아직 skeleton 상태입니다.")
    announce_phase_stub("explain")


review_app = typer.Typer(help="파일 기반 검수 보조 명령")
app.add_typer(review_app, name="review")


@review_app.command("export")
def review_export() -> None:
    """검수 export skeleton."""

    typer.echo("Phase 0에서는 review export가 아직 skeleton 상태입니다.")
    announce_phase_stub("review export")


@review_app.command("import")
def review_import() -> None:
    """검수 import skeleton."""

    typer.echo("Phase 0에서는 review import가 아직 skeleton 상태입니다.")
    announce_phase_stub("review import")


@app.command("render")
def render() -> None:
    """문서 렌더 stage skeleton."""

    typer.echo("Phase 0에서는 render가 아직 skeleton 상태입니다.")
    announce_phase_stub("render")


if __name__ == "__main__":
    app()
