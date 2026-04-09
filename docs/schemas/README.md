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
- `ReleaseManifest`
- `ReleaseReviewResolutionArtifact`
- `PublishReviewResolutionArtifact`
- `PublishArtifact`
- `PublishRetryManifest`
- `OpsHandoffArtifact`
- `OpsHandoffResolutionArtifact`
- `OpsFollowupManifest`
- `OpsFollowupResolutionArtifact`
- `OpsEscalationManifest`
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
- `ReleaseManifest`: render 결과와 승인 bundle 집합, 배포 메모를 정리한 release 단계 artifact
- `ReleaseReviewResolutionArtifact`: 사람이 release manifest를 검토한 최종 signoff와 published 여부를 기록한 review 단계 artifact
- `PublishReviewResolutionArtifact`: 사람이 publish 결과를 검토해 채널별 최종 상태와 메모를 기록한 review 단계 artifact
- `PublishArtifact`: 승인된 release review 결과를 채널별 simulated publish 기록으로 정리한 publish 단계 artifact
- `PublishRetryManifest`: publish review 결과 중 failed 또는 simulated 채널만 추린 retry 단계 artifact
- `OpsHandoffArtifact`: retry 결과를 운영팀 전달용 `ReviewTask` 목록으로 정리한 handoff 단계 artifact
- `OpsHandoffResolutionArtifact`: 사람이 handoff task 상태와 체크리스트 응답을 갱신해 다시 JSON으로 반영한 review 단계 artifact
- `OpsFollowupManifest`: handoff resolution 이후에도 남아 있는 `open`/`in_review` task만 다시 모은 followup 단계 artifact
- `OpsFollowupResolutionArtifact`: 사람이 `ops_daily_queue.csv`를 수정한 뒤 followup task 상태를 다시 JSON으로 반영한 review 단계 artifact
- `OpsEscalationManifest`: followup resolution 이후에도 `in_review`로 남아 있는 task만 다시 모은 escalation 단계 artifact
- `OpsEscalationResolutionArtifact`: 사람이 `ops_escalation_queue.csv`를 수정한 뒤 escalation task 상태를 다시 JSON으로 반영한 review 단계 artifact
- `OpsClosureReport`: escalation resolution 기준으로 종결 task와 남은 task를 함께 정리한 closure 단계 artifact
- `OpsClosureResolutionArtifact`: 사람이 `closure_report.csv`를 수정한 뒤 closure 상태를 다시 JSON으로 반영한 review 단계 artifact

이 디렉터리의 JSON schema 파일은 코드 변경 후 수동으로 다시 생성해 최신 상태를 유지한다.
