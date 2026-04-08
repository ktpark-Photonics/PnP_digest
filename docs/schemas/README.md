# Schemas

이 디렉터리는 `pnp-digest export-schemas` 명령으로 생성된 JSON schema snapshot을 저장하는 위치다.

현재 기준으로 아래 명령으로 스키마를 다시 생성할 수 있다.

```bash
./.venv/bin/python -m pnp_digest.cli export-schemas
```

현재 기준으로 아래 모델 스키마를 내보내도록 구성되어 있다.

- `PipelineRun`
- `RawSourceRecord`
- `DocumentRecord`
- `RelevanceAssessment`
- `RelevanceArtifact`
- `ManualReviewManifest`
- `VerificationResult`
- `VerificationReport`
- `VerificationArtifact`
- `VerificationReviewManifest`
- `VerificationReviewResolutionArtifact`
- `SummaryArtifact`
- `ExplainArtifact`
- `RenderArtifact`
- `SummaryPayload`
- `FigureAsset`
- `ReviewTask`
- `OutputBundle`
- `IngestArtifact`
- `NormalizedArtifact`

특히 Phase 2 이후에는 아래 스키마가 새로 중요해진다.

- `RelevanceArtifact`: 관련성 판정 결과 전체 artifact
- `ManualReviewManifest`: `assess-relevance` 단계 수동 검토 입력
- `VerificationReport`: 단일 특허 검증 결과
- `VerificationArtifact`: `verify` 단계 전체 결과 artifact
- `VerificationReviewManifest`: `verify` 단계 수동 검토 입력 artifact
- `VerificationReviewResolutionArtifact`: 사람이 수정한 review CSV를 다시 JSON으로 가져온 결과 artifact
- `SummaryArtifact`: `approved` 검토 결과만 모은 summarize 단계 artifact
- `ExplainArtifact`: `summary_artifact`에서 직급별 설명 블록만 분리한 explain 단계 artifact
- `RenderArtifact`: Markdown, DOCX, PDF 또는 PPTX brief 출력 경로와 bundle 메타데이터를 담는 render 단계 artifact

이 디렉터리의 JSON schema 파일은 코드 변경 후 수동으로 다시 생성해 최신 상태를 유지한다.
