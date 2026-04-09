# PnP Digest

CIS 분야 최신 논문 및 특허를 주간 단위로 수집하고, 구조화 요약과 검수 가능한 기술 브리프를 만들기 위한 내부 도구다.

현재 구현 범위는 `Phase 5.15`이며 다음을 포함한다.

- 핵심 canonical schema 패키지
- 로컬 fixture 기반 `ingest` / `normalize` 파이프라인
- 규칙 기반 `assess-relevance` 파이프라인(근거 snippet 및 수동 검토 manifest 생성)
- mock/manual provider 기반 `verify` 파이프라인(특허 존재 확인 + 핵심 필드 검증 + review manifest 생성)
- `verification_review_manifest.json`을 CSV/Markdown으로 내보내는 `review export` CLI
- 사람이 수정한 review CSV를 다시 JSON artifact로 반영하는 `review import` CLI
- `approved` 검토 결과만 읽어 placeholder `summary_artifact.json`을 생성하는 `summarize` 파이프라인
- `summary_artifact.json`에서 직급별 설명을 분리한 `explain_artifact.json`을 생성하는 `explain` 파이프라인
- `explain_artifact.json`에서 Markdown, DOCX, PDF 또는 PPTX brief와 `render_artifact.json`을 생성하는 `render` 파이프라인
- `render_artifact.json`을 읽어 release candidate와 승인 bundle 목록을 정리하는 `release` 파이프라인
- `release_manifest.json`을 reviewer용 CSV로 내보내고, 최종 signoff를 `release_review_resolution.json`으로 반영하는 final release review CLI
- `release_review_resolution.json`을 읽어 채널별 `publish_artifact.json` stub를 생성하는 `publish` 파이프라인
- `publish_artifact.json`을 reviewer용 CSV로 내보내고, 채널별 최종 상태를 `publish_review_resolution.json`으로 반영하는 publish review CLI
- `publish_review_resolution.json`에서 실패/미확인 채널만 추린 `retry_manifest.json`을 생성하는 `retry` 파이프라인
- `retry_manifest.json`을 운영 전달용 `ops_handoff.json` task 목록으로 정리하는 `handoff` 파이프라인
- `ops_handoff.json`을 reviewer용 CSV로 내보내고, task 상태를 `ops_handoff_resolution.json`으로 반영하는 handoff review CLI
- `ops_handoff_resolution.json`에서 아직 끝나지 않은 task만 추린 `followup_manifest.json`을 생성하는 `followup` 파이프라인
- `followup_manifest.json`을 사람이 바로 처리할 수 있는 `ops_daily_queue.csv`로 내보내는 followup export CLI
- `ops_daily_queue.csv`를 다시 `followup_resolution.json`으로 반영하는 followup review import CLI
- `followup_resolution.json`에서 아직 `in_review`인 task만 추린 `escalation_manifest.json`을 생성하는 escalation 파이프라인
- `escalation_manifest.json`을 reviewer용 CSV로 내보내고, task 상태를 `escalation_resolution.json`으로 반영하는 escalation review CLI
- `escalation_resolution.json`에서 종결 task와 남은 task를 분리한 `closure_report.json`을 생성하는 closure 파이프라인
- `closure_report.json`을 사람이 바로 볼 수 있는 `closure_report.csv`로 내보내는 closure export CLI
- `closure_report.csv`를 다시 `closure_resolution.json`으로 반영하는 closure review import CLI
- `closure_resolution.json`을 사람이 공유할 수 있는 `closure_resolution.md`로 내보내는 closure brief CLI
- JSON schema export CLI
- 샘플 입력/출력 데이터
- 기본 단위/통합 테스트

샘플 입력 데이터는 모두 `Synthetic fixture only`로 표시된 합성 테스트 데이터이며, 실제 특허/논문 사실을 주장하지 않는다.

## 빠른 개요

파이프라인은 아래 순서를 기준으로 확장된다.

1. `ingest`
2. `normalize`
3. `assess-relevance`
4. `verify`
5. `summarize`
6. `explain`
7. `review`
8. `render`
9. `release`
10. `publish`
11. `retry`
12. `handoff`
13. `followup`
14. `escalation`
15. `closure`

Phase 5.15 현재 범위에서는 `assess-relevance`, `verify`, `review import/export`, `summarize`, `explain`, `render`, `release`, `review release-export/import`, `publish`, `review publish-export/import`, `retry`, `handoff`, `review handoff-export/import`, `followup`, `review followup-export/import`, `escalation`, `review escalation-export/import`, `closure`, `review closure-export`, `review closure-import`, `review closure-brief`를 구현했으며, 현재 `render`는 Markdown, DOCX, PDF, PPTX를 지원한다.

## WSL 로컬 검증

Python 3.12와 `.venv` 기준으로 아래 순서를 권장한다.

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/python -m pytest -q
./.venv/bin/python -m pnp_digest.cli assess-relevance --help
./.venv/bin/python -m pnp_digest.cli verify --help
./.venv/bin/python -m pnp_digest.cli review export --help
./.venv/bin/python -m pnp_digest.cli review import --help
./.venv/bin/python -m pnp_digest.cli review release-export --help
./.venv/bin/python -m pnp_digest.cli review release-import --help
./.venv/bin/python -m pnp_digest.cli review publish-export --help
./.venv/bin/python -m pnp_digest.cli review publish-import --help
./.venv/bin/python -m pnp_digest.cli review handoff-export --help
./.venv/bin/python -m pnp_digest.cli review handoff-import --help
./.venv/bin/python -m pnp_digest.cli review followup-export --help
./.venv/bin/python -m pnp_digest.cli review followup-import --help
./.venv/bin/python -m pnp_digest.cli review escalation-export --help
./.venv/bin/python -m pnp_digest.cli review escalation-import --help
./.venv/bin/python -m pnp_digest.cli review closure-export --help
./.venv/bin/python -m pnp_digest.cli review closure-import --help
./.venv/bin/python -m pnp_digest.cli review closure-brief --help
./.venv/bin/python -m pnp_digest.cli summarize --help
./.venv/bin/python -m pnp_digest.cli explain --help
./.venv/bin/python -m pnp_digest.cli render --help
./.venv/bin/python -m pnp_digest.cli release --help
./.venv/bin/python -m pnp_digest.cli publish --help
./.venv/bin/python -m pnp_digest.cli retry --help
./.venv/bin/python -m pnp_digest.cli handoff --help
./.venv/bin/python -m pnp_digest.cli followup --help
./.venv/bin/python -m pnp_digest.cli escalation --help
./.venv/bin/python -m pnp_digest.cli closure --help
```

기본 샘플 fixture로 `ingest -> normalize -> assess-relevance`까지 확인하려면:

```bash
./.venv/bin/python -m pnp_digest.cli ingest \
  --run-id local-phase1-sample \
  --input-path data/sample_inputs/cis_weekly_fixture.json

./.venv/bin/python -m pnp_digest.cli normalize \
  --run-id local-phase1-sample \
  --ingest-artifact artifacts/runs/local-phase1-sample/ingest/ingest_artifact.json

./.venv/bin/python -m pnp_digest.cli assess-relevance \
  --run-id local-phase1-sample \
  --normalized-artifact artifacts/runs/local-phase1-sample/normalize/normalized_artifact.json
```

`relevant / borderline / not_relevant` 3단계가 모두 실제로 나오는지 바로 확인하려면, `normalized_artifact` 샘플을 직접 입력으로 사용할 수 있다.

```bash
./.venv/bin/python -m pnp_digest.cli assess-relevance \
  --run-id phase1-threeway-fixture \
  --normalized-artifact data/sample_inputs/phase1_relevance_normalized_fixture.json
```

결과는 아래 경로에 저장된다.

- `artifacts/runs/<run_id>/assess_relevance/relevance_report.json`
- `artifacts/runs/<run_id>/assess_relevance/manual_review_manifest.json`

특허 검증은 `normalized_artifact`와 provider fixture를 입력으로 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli verify \
  --run-id phase2-patent-verify \
  --normalized-artifact data/sample_inputs/phase2_patent_verify_normalized_fixture.json \
  --provider mock \
  --provider-data data/sample_inputs/phase2_patent_verification_mock_fixture.json
```

수동 검증 결과를 그대로 반영하려면 `manual` provider를 사용한다.

```bash
./.venv/bin/python -m pnp_digest.cli verify \
  --run-id phase2-patent-verify \
  --normalized-artifact data/sample_inputs/phase2_patent_verify_normalized_fixture.json \
  --provider manual \
  --provider-data data/sample_inputs/phase2_patent_verification_manual_fixture.json
```

`verify` 실행 시 아래 파일이 저장된다.

- `artifacts/runs/<run_id>/verify/verification_report.json`
- `artifacts/runs/<run_id>/verify/verification_review_manifest.json` (`review_required=true` 문헌이 있을 때만 생성)

수동 검토용 파일을 사람이 읽기 쉬운 형식으로 내보내려면 `review export`를 사용한다.

```bash
./.venv/bin/python -m pnp_digest.cli review export \
  --verification-review-manifest artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.json
```

기본 형식은 CSV이며, 입력 manifest와 같은 디렉터리에 `verification_review_manifest.csv`를 생성한다.

Markdown으로 내보내려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review export \
  --verification-review-manifest artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.json \
  --format markdown \
  --output-path artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.md
```

CSV를 사람이 수정한 뒤 review stage artifact로 반영하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review import \
  --verification-review-manifest artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.json \
  --review-csv artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.csv
```

`review import`는 기본적으로 아래 파일을 생성한다.

- `artifacts/runs/<run_id>/review/verification_review_resolution.json`

승인된 검토 결과만 placeholder summary artifact로 넘기려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli summarize \
  --run-id phase2-patent-verify \
  --normalized-artifact data/sample_inputs/phase2_patent_verify_normalized_fixture.json \
  --verification-review-resolution artifacts/runs/phase2-patent-verify/review/verification_review_resolution.json
```

`summarize`는 기본적으로 아래 파일을 생성한다.

- `artifacts/runs/<run_id>/summarize/summary_artifact.json`

직급별 설명 artifact를 생성하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli explain \
  --run-id phase2-patent-verify \
  --summary-artifact artifacts/runs/phase2-patent-verify/summarize/summary_artifact.json
```

`explain`은 기본적으로 아래 파일을 생성한다.

- `artifacts/runs/<run_id>/explain/explain_artifact.json`

Markdown brief를 생성하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli render \
  --run-id phase2-patent-verify \
  --explain-artifact artifacts/runs/phase2-patent-verify/explain/explain_artifact.json
```

`render`는 기본적으로 아래 파일을 생성한다.

- `artifacts/runs/<run_id>/render/brief.md`
- `artifacts/runs/<run_id>/render/render_artifact.json`

DOCX로 생성하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli render \
  --run-id phase2-patent-verify \
  --explain-artifact artifacts/runs/phase2-patent-verify/explain/explain_artifact.json \
  --output-type docx
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/render/brief.docx`

PDF로 생성하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli render \
  --run-id phase2-patent-verify \
  --explain-artifact artifacts/runs/phase2-patent-verify/explain/explain_artifact.json \
  --output-type pdf
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/render/brief.pdf`

PPTX로 생성하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli render \
  --run-id phase2-patent-verify \
  --explain-artifact artifacts/runs/phase2-patent-verify/explain/explain_artifact.json \
  --output-type pptx
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/render/brief.pptx`

release manifest를 생성하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli release \
  --run-id phase2-patent-verify \
  --render-artifact artifacts/runs/phase2-patent-verify/render/render_artifact.json \
  --distribution-target internal \
  --distribution-target archive \
  --release-note "최종 배포 검토 전 candidate 정리"
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/release/release_manifest.json`

release manifest를 reviewer용 CSV로 내보내려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review release-export \
  --release-manifest artifacts/runs/phase2-patent-verify/release/release_manifest.json
```

기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/release/release_manifest.csv`

CSV를 사람이 수정한 뒤 final release review 결과를 JSON artifact로 반영하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review release-import \
  --release-manifest artifacts/runs/phase2-patent-verify/release/release_manifest.json \
  --review-csv artifacts/runs/phase2-patent-verify/release/release_manifest.csv
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/review/release_review_resolution.json`

release review resolution을 publish stub artifact로 변환하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli publish \
  --run-id phase2-patent-verify \
  --release-review-resolution artifacts/runs/phase2-patent-verify/review/release_review_resolution.json
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/publish/publish_artifact.json`

publish 결과를 사람이 채널별로 확인하려면 아래처럼 CSV로 export한다.

```bash
./.venv/bin/python -m pnp_digest.cli review publish-export \
  --publish-artifact artifacts/runs/phase2-patent-verify/publish/publish_artifact.json
```

기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/publish/publish_artifact.csv`

CSV를 사람이 수정한 뒤 채널별 최종 상태를 JSON artifact로 반영하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review publish-import \
  --publish-artifact artifacts/runs/phase2-patent-verify/publish/publish_artifact.json \
  --review-csv artifacts/runs/phase2-patent-verify/publish/publish_artifact.csv
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/review/publish_review_resolution.json`

publish review resolution에서 실패 또는 미확인 채널만 retry 대상으로 정리하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli retry \
  --run-id phase2-patent-verify \
  --publish-review-resolution artifacts/runs/phase2-patent-verify/review/publish_review_resolution.json
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/retry/retry_manifest.json`

retry manifest를 운영 전달용 task 목록으로 정리하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli handoff \
  --run-id phase2-patent-verify \
  --retry-manifest artifacts/runs/phase2-patent-verify/retry/retry_manifest.json
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/handoff/ops_handoff.json`

ops handoff를 사람이 수정할 CSV로 내보내려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review handoff-export \
  --ops-handoff artifacts/runs/phase2-patent-verify/handoff/ops_handoff.json
```

기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/handoff/ops_handoff.csv`

CSV를 사람이 수정한 뒤 handoff task 상태를 JSON artifact로 반영하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review handoff-import \
  --ops-handoff artifacts/runs/phase2-patent-verify/handoff/ops_handoff.json \
  --review-csv artifacts/runs/phase2-patent-verify/handoff/ops_handoff.csv
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/review/ops_handoff_resolution.json`

ops handoff resolution에서 아직 남아 있는 task만 followup 대상으로 정리하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli followup \
  --run-id phase2-patent-verify \
  --ops-handoff-resolution artifacts/runs/phase2-patent-verify/review/ops_handoff_resolution.json
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/followup/followup_manifest.json`

followup manifest를 사람이 바로 쓸 수 있는 운영 CSV로 내보내려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review followup-export \
  --followup-manifest artifacts/runs/phase2-patent-verify/followup/followup_manifest.json
```

기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/followup/ops_daily_queue.csv`

CSV를 사람이 수정한 뒤 followup task 상태를 다시 JSON artifact로 반영하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review followup-import \
  --followup-manifest artifacts/runs/phase2-patent-verify/followup/followup_manifest.json \
  --review-csv artifacts/runs/phase2-patent-verify/followup/ops_daily_queue.csv
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/review/followup_resolution.json`

followup resolution에서 아직 `in_review`인 task만 escalation 대상으로 정리하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli escalation \
  --run-id phase2-patent-verify \
  --followup-resolution artifacts/runs/phase2-patent-verify/review/followup_resolution.json
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/escalation/escalation_manifest.json`

escalation manifest를 reviewer용 CSV로 내보내려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review escalation-export \
  --escalation-manifest artifacts/runs/phase2-patent-verify/escalation/escalation_manifest.json
```

기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/escalation/ops_escalation_queue.csv`

CSV를 사람이 수정한 뒤 escalation task 상태를 다시 JSON artifact로 반영하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review escalation-import \
  --escalation-manifest artifacts/runs/phase2-patent-verify/escalation/escalation_manifest.json \
  --review-csv artifacts/runs/phase2-patent-verify/escalation/ops_escalation_queue.csv
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/review/escalation_resolution.json`

escalation resolution에서 종결 task와 남은 task를 한 번에 정리하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli closure \
  --run-id phase2-patent-verify \
  --escalation-resolution artifacts/runs/phase2-patent-verify/review/escalation_resolution.json
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/closure/closure_report.json`

closure report를 사람이 바로 볼 수 있는 CSV로 내보내려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review closure-export \
  --closure-report artifacts/runs/phase2-patent-verify/closure/closure_report.json
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/closure/closure_report.csv`

CSV를 사람이 수정한 뒤 closure 상태를 다시 JSON artifact로 반영하려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review closure-import \
  --closure-report artifacts/runs/phase2-patent-verify/closure/closure_report.json \
  --review-csv artifacts/runs/phase2-patent-verify/closure/closure_report.csv
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/review/closure_resolution.json`

closure resolution을 사람이 바로 공유할 Markdown 보고서로 내보내려면 아래처럼 실행한다.

```bash
./.venv/bin/python -m pnp_digest.cli review closure-brief \
  --closure-resolution artifacts/runs/phase2-patent-verify/review/closure_resolution.json
```

이 경우 기본 출력 파일은 아래 경로다.

- `artifacts/runs/<run_id>/review/closure_resolution.md`

간단한 결과 확인 예시는 아래와 같다.

```bash
./.venv/bin/python -c 'import json, pathlib; p = pathlib.Path("artifacts/runs/phase1-threeway-fixture/assess_relevance/relevance_report.json"); data = json.loads(p.read_text()); print([(a["document_id"], a["final_decision"], len(a["evidence_links_or_snippets"])) for a in data["assessments"]])'
```

위 샘플에서는 아래를 기대할 수 있다.

- `paper:doi:relevant` -> `relevant`
- `paper:doi:borderline` -> `borderline`
- `paper:doi:not-relevant` -> `not_relevant`
- 모든 문헌의 `evidence_links_or_snippets` 길이 >= 1
- `manual_review_manifest.json`에는 `borderline` 문헌만 포함

## Phase 1.1 계약 테스트

Phase 1.1에서는 `assess-relevance` 산출물 계약과 회귀를 테스트로 고정한다.

- `tests/unit/test_schema_exports.py`: `RelevanceArtifact`, `ManualReviewManifest`를 포함한 상위 schema shape snapshot 검증
- `tests/integration/test_phase1_relevance.py`: 고정 `normalized_artifact` 입력에 대한 `relevance_report.json`, `manual_review_manifest.json` snapshot 검증

스냅샷 실패는 보통 아래 둘 중 하나를 의미한다.

- 산출물 JSON 포맷이 바뀌었다.
- 규칙 파일 변경으로 점수, 판정, 근거, 수동 검토 결과가 달라졌다.

빠른 실행 명령:

```bash
./.venv/bin/python -m pytest -q tests/unit/test_schema_exports.py tests/integration/test_phase1_relevance.py
```

전체 테스트 실행:

```bash
./.venv/bin/python -m pytest -q
```

Phase 2 특허 검증만 빠르게 확인하려면:

```bash
./.venv/bin/python -m pytest -q tests/integration/test_phase2_verify.py
```

Phase 2.1에서는 `verification_review_manifest.json`을 수동 검토 워크플로의 입력 artifact로 사용한다.
Phase 2.2에서는 이 manifest를 CSV 또는 Markdown으로 export해 사람이 바로 확인할 수 있게 한다.
Phase 2.3에서는 사람이 수정한 CSV를 다시 `verification_review_resolution.json`으로 import해 후속 단계가 읽을 수 있게 한다.
Phase 3 첫 구현에서는 `approved` 상태 문헌만 `summary_artifact.json`으로 넘겨 summarize 단계 입력 계약을 고정한다.
Phase 3.1에서는 `summary_artifact.json` 안의 직급별 설명 블록을 `explain_artifact.json`으로 분리해 explain 단계 계약을 고정한다.
Phase 3/3.1 snapshot 테스트에서는 고정 fixture 입력에 대한 `summary_artifact.json`과 `explain_artifact.json` 전체 구조를 snapshot으로 비교해 후반부 JSON 출력 회귀를 감지한다.
Phase 4에서는 `explain_artifact.json`을 Markdown brief로 렌더링하고, 출력 메타데이터를 `render_artifact.json`으로 저장한다.
Phase 4.1에서는 같은 입력으로 DOCX brief도 생성할 수 있게 해 output bundle을 확장한다.
Phase 4.2에서는 같은 입력으로 PDF brief도 생성할 수 있게 해 render output 선택 폭을 넓힌다.
Phase 4.3에서는 같은 입력으로 PPTX brief도 생성할 수 있게 해 발표 자료 초안을 파일 기반으로 검토할 수 있게 한다.

Phase 4.3 snapshot 테스트에서는 `render_artifact.json`과 각 출력 형식의 핵심 구조를 고정 fixture와 비교해 render 포맷 회귀를 감지한다.
Phase 5 첫 구현에서는 `release_manifest.json`으로 release candidate와 승인 bundle 집합을 구조화해 최종 배포 전 상태를 JSON으로 고정한다.
Phase 5.1에서는 release manifest를 사람이 검토할 CSV로 export하고, 최종 signoff와 published 여부를 `release_review_resolution.json`으로 import할 수 있게 한다.
Phase 5.2에서는 승인된 release review resolution을 입력으로 채널별 `simulated publish` 기록을 `publish_artifact.json`에 남긴다.
Phase 5.3에서는 publish artifact를 다시 reviewer CSV로 주고받아 채널별 최종 상태를 `publish_review_resolution.json`으로 고정한다.
Phase 5.4에서는 publish review resolution에서 `failed` 또는 아직 `simulated`인 채널만 추린 `retry_manifest.json`을 생성한다.
Phase 5.5에서는 retry manifest를 운영팀이 바로 받을 수 있는 `ops_handoff.json` task 목록으로 정리한다.
Phase 5.6에서는 ops handoff를 CSV로 주고받아 `ops_handoff_resolution.json`으로 task 상태를 다시 고정한다.
Phase 5.7에서는 ops handoff resolution에서 `open` 또는 `in_review` 상태만 남긴 `followup_manifest.json`을 생성한다.
Phase 5.8에서는 followup manifest를 사람이 바로 처리할 수 있도록 `ops_daily_queue.csv`로 export한다.
Phase 5.9에서는 사람이 수정한 `ops_daily_queue.csv`를 `followup_resolution.json`으로 다시 import할 수 있게 한다.
Phase 5.10에서는 followup resolution에서 `in_review` 상태만 남긴 `escalation_manifest.json`을 생성한다.
Phase 5.11에서는 escalation manifest를 CSV로 주고받아 `escalation_resolution.json`으로 task 상태를 다시 고정한다.
Phase 5.12에서는 escalation resolution에서 종결 task와 남은 task를 함께 정리한 `closure_report.json`을 생성한다.
Phase 5.13에서는 closure report를 사람이 바로 검토할 수 있게 `closure_report.csv`로 export한다.
Phase 5.14에서는 사람이 수정한 `closure_report.csv`를 `closure_resolution.json`으로 다시 import할 수 있게 한다.
Phase 5.15에서는 closure resolution을 사람이 공유할 수 있게 `closure_resolution.md`로 export한다.

- `tests/integration/test_phase4_render.py`: Markdown/DOCX/PDF/PPTX 산출물 생성 + snapshot 회귀 검증
- `tests/fixtures/phase4_render_snapshots.json`: render artifact 및 출력물 요약 snapshot

빠른 실행 명령:

```bash
./.venv/bin/python -m pytest -q tests/integration/test_phase3_summarize.py tests/integration/test_phase3_explain.py
./.venv/bin/python -m pytest -q tests/integration/test_phase4_render.py
```

## 예시 명령

```bash
pnp-digest export-schemas
pnp-digest ingest --run-id 2026w14 --input-path data/sample_inputs/cis_weekly_fixture.json
pnp-digest normalize --run-id 2026w14 --ingest-artifact artifacts/runs/2026w14/ingest/ingest_artifact.json
pnp-digest assess-relevance --run-id 2026w14 --normalized-artifact artifacts/runs/2026w14/normalize/normalized_artifact.json
pnp-digest verify --run-id phase2-patent-verify --normalized-artifact data/sample_inputs/phase2_patent_verify_normalized_fixture.json --provider mock --provider-data data/sample_inputs/phase2_patent_verification_mock_fixture.json
pnp-digest review export --verification-review-manifest artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.json
pnp-digest review import --verification-review-manifest artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.json --review-csv artifacts/runs/phase2-patent-verify/verify/verification_review_manifest.csv
pnp-digest summarize --run-id phase2-patent-verify --normalized-artifact data/sample_inputs/phase2_patent_verify_normalized_fixture.json --verification-review-resolution artifacts/runs/phase2-patent-verify/review/verification_review_resolution.json
pnp-digest explain --run-id phase2-patent-verify --summary-artifact artifacts/runs/phase2-patent-verify/summarize/summary_artifact.json
pnp-digest render --run-id phase2-patent-verify --explain-artifact artifacts/runs/phase2-patent-verify/explain/explain_artifact.json
pnp-digest render --run-id phase2-patent-verify --explain-artifact artifacts/runs/phase2-patent-verify/explain/explain_artifact.json --output-type docx
pnp-digest render --run-id phase2-patent-verify --explain-artifact artifacts/runs/phase2-patent-verify/explain/explain_artifact.json --output-type pdf
pnp-digest render --run-id phase2-patent-verify --explain-artifact artifacts/runs/phase2-patent-verify/explain/explain_artifact.json --output-type pptx
pnp-digest release --run-id phase2-patent-verify --render-artifact artifacts/runs/phase2-patent-verify/render/render_artifact.json --distribution-target internal
pnp-digest review release-export --release-manifest artifacts/runs/phase2-patent-verify/release/release_manifest.json
pnp-digest review release-import --release-manifest artifacts/runs/phase2-patent-verify/release/release_manifest.json --review-csv artifacts/runs/phase2-patent-verify/release/release_manifest.csv
pnp-digest publish --run-id phase2-patent-verify --release-review-resolution artifacts/runs/phase2-patent-verify/review/release_review_resolution.json
pnp-digest review publish-export --publish-artifact artifacts/runs/phase2-patent-verify/publish/publish_artifact.json
pnp-digest review publish-import --publish-artifact artifacts/runs/phase2-patent-verify/publish/publish_artifact.json --review-csv artifacts/runs/phase2-patent-verify/publish/publish_artifact.csv
pnp-digest retry --run-id phase2-patent-verify --publish-review-resolution artifacts/runs/phase2-patent-verify/review/publish_review_resolution.json
pnp-digest handoff --run-id phase2-patent-verify --retry-manifest artifacts/runs/phase2-patent-verify/retry/retry_manifest.json
pnp-digest review handoff-export --ops-handoff artifacts/runs/phase2-patent-verify/handoff/ops_handoff.json
pnp-digest review handoff-import --ops-handoff artifacts/runs/phase2-patent-verify/handoff/ops_handoff.json --review-csv artifacts/runs/phase2-patent-verify/handoff/ops_handoff.csv
pnp-digest followup --run-id phase2-patent-verify --ops-handoff-resolution artifacts/runs/phase2-patent-verify/review/ops_handoff_resolution.json
pnp-digest review followup-export --followup-manifest artifacts/runs/phase2-patent-verify/followup/followup_manifest.json
pnp-digest review followup-import --followup-manifest artifacts/runs/phase2-patent-verify/followup/followup_manifest.json --review-csv artifacts/runs/phase2-patent-verify/followup/ops_daily_queue.csv
pnp-digest escalation --run-id phase2-patent-verify --followup-resolution artifacts/runs/phase2-patent-verify/review/followup_resolution.json
pnp-digest review escalation-export --escalation-manifest artifacts/runs/phase2-patent-verify/escalation/escalation_manifest.json
pnp-digest review escalation-import --escalation-manifest artifacts/runs/phase2-patent-verify/escalation/escalation_manifest.json --review-csv artifacts/runs/phase2-patent-verify/escalation/ops_escalation_queue.csv
pnp-digest closure --run-id phase2-patent-verify --escalation-resolution artifacts/runs/phase2-patent-verify/review/escalation_resolution.json
pnp-digest review closure-export --closure-report artifacts/runs/phase2-patent-verify/closure/closure_report.json
pnp-digest review closure-import --closure-report artifacts/runs/phase2-patent-verify/closure/closure_report.json --review-csv artifacts/runs/phase2-patent-verify/closure/closure_report.csv
pnp-digest review closure-brief --closure-resolution artifacts/runs/phase2-patent-verify/review/closure_resolution.json
```

`assess-relevance` 실행 시 아래 파일이 저장된다.

- `artifacts/runs/<run_id>/assess_relevance/relevance_report.json`
- `artifacts/runs/<run_id>/assess_relevance/manual_review_manifest.json` (`borderline` 문헌만 포함)
- `artifacts/runs/<run_id>/verify/verification_report.json`
- `artifacts/runs/<run_id>/verify/verification_review_manifest.json` (`review_required=true` 검증 항목만 포함)
- `artifacts/runs/<run_id>/verify/verification_review_manifest.csv` 또는 `.md` (`review export` 실행 시 생성)
- `artifacts/runs/<run_id>/review/verification_review_resolution.json` (`review import` 실행 시 생성)
- `artifacts/runs/<run_id>/summarize/summary_artifact.json` (`approved` 검토 결과만 포함)
- `artifacts/runs/<run_id>/explain/explain_artifact.json` (`summary_artifact`의 직급별 설명 블록을 분리한 결과)
- `artifacts/runs/<run_id>/render/brief.md` (`render` 기본 실행 시 생성되는 Markdown brief)
- `artifacts/runs/<run_id>/render/brief.docx` (`render --output-type docx` 실행 시 생성)
- `artifacts/runs/<run_id>/render/brief.pdf` (`render --output-type pdf` 실행 시 생성)
- `artifacts/runs/<run_id>/render/brief.pptx` (`render --output-type pptx` 실행 시 생성)
- `artifacts/runs/<run_id>/render/render_artifact.json` (`render output metadata`)
- `artifacts/runs/<run_id>/release/release_manifest.json` (`release candidate 및 승인 bundle 목록`)
- `artifacts/runs/<run_id>/release/release_manifest.csv` (`review release-export` 실행 시 생성)
- `artifacts/runs/<run_id>/review/release_review_resolution.json` (`review release-import` 실행 시 생성)
- `artifacts/runs/<run_id>/publish/publish_artifact.json` (`publish stub 결과`)
- `artifacts/runs/<run_id>/publish/publish_artifact.csv` (`review publish-export` 실행 시 생성)
- `artifacts/runs/<run_id>/review/publish_review_resolution.json` (`review publish-import` 실행 시 생성)
- `artifacts/runs/<run_id>/retry/retry_manifest.json` (`retry 대상 채널 목록`)
- `artifacts/runs/<run_id>/handoff/ops_handoff.json` (`운영 전달용 task 목록`)
- `artifacts/runs/<run_id>/handoff/ops_handoff.csv` (`review handoff-export` 실행 시 생성)
- `artifacts/runs/<run_id>/review/ops_handoff_resolution.json` (`review handoff-import` 실행 시 생성)
- `artifacts/runs/<run_id>/followup/followup_manifest.json` (`아직 남아 있는 후속 task 목록`)
- `artifacts/runs/<run_id>/followup/ops_daily_queue.csv` (`review followup-export` 실행 시 생성)
- `artifacts/runs/<run_id>/review/followup_resolution.json` (`review followup-import` 실행 시 생성)
- `artifacts/runs/<run_id>/escalation/escalation_manifest.json` (`아직 `in_review`인 escalation 대상 task 목록`)
- `artifacts/runs/<run_id>/escalation/ops_escalation_queue.csv` (`review escalation-export` 실행 시 생성)
- `artifacts/runs/<run_id>/review/escalation_resolution.json` (`review escalation-import` 실행 시 생성)
- `artifacts/runs/<run_id>/closure/closure_report.json` (`종결 task와 남은 task를 함께 정리한 최종 운영 상태 보고서`)
- `artifacts/runs/<run_id>/closure/closure_report.csv` (`review closure-export` 실행 시 생성)
- `artifacts/runs/<run_id>/review/closure_resolution.json` (`review closure-import` 실행 시 생성)
- `artifacts/runs/<run_id>/review/closure_resolution.md` (`review closure-brief` 실행 시 생성)

규칙 사전 초안은 `data/dictionaries/` 아래 파일을 사용한다.

- `cis_allow_keywords.txt`
- `cis_deny_keywords.txt`
- `cis_classification_rules.toml`

## 현재 제한 사항

- 외부 API 연동은 아직 없다.
- 특허 검증은 아직 mock/manual provider 기반이며 실제 온라인 조회를 하지 않는다.
- LLM 기반 relevance/요약 생성은 아직 없다.
- 외부 프레젠테이션 템플릿 연동은 아직 없다.
- 실제 배포 채널 연동은 아직 없고 `publish`는 채널별 stub artifact만 생성한다.
- `review publish-import`는 사람이 채널별 상태를 확정하는 구조만 제공하며 외부 시스템 상태를 자동 조회하지 않는다.
- `retry`는 실제 재배포를 수행하지 않고 후속 운영에 필요한 재시도 대상만 정리한다.
- `handoff`는 실제 티켓 시스템 연동 없이 운영 전달용 JSON task 목록만 생성한다.
- `review handoff-import`는 사람이 task 상태와 체크리스트 응답을 고정하는 구조만 제공하며 외부 티켓 시스템 상태를 자동 조회하지 않는다.
- `followup`은 실제 자동 재배포나 자동 종료를 수행하지 않고 아직 남아 있는 task만 다시 정리한다.
- `review followup-import`는 사람이 CSV로 task 상태를 반영하는 구조만 제공하며 외부 운영 시스템 상태를 자동 조회하지 않는다.
- `escalation`은 실제 알림이나 티켓 에스컬레이션을 수행하지 않고 `in_review` task만 다시 정리한다.
- `review escalation-import`는 사람이 CSV로 escalation task 상태를 반영하는 구조만 제공하며 외부 알림/티켓 시스템과 연동하지 않는다.
- `closure`는 실제 운영 종료를 수행하지 않고 `escalation_resolution.json` 기준 상태를 요약한 보고서만 생성한다.
- `review closure-export`는 closure report를 CSV로 평탄화해 보여줄 뿐, 상태를 다시 import하거나 외부 시스템에 반영하지 않는다.
- `review closure-import`는 사람이 CSV로 closure 상태를 다시 고정하는 구조만 제공하며 외부 운영 시스템을 자동 갱신하지 않는다.
- `review closure-brief`는 최신 closure resolution 상태를 Markdown으로 정리해 보여줄 뿐, 외부 시스템에 전송하지 않는다.

상세 구조는 [docs/architecture.md](/home/kyongtae/projects/PnP_digest/docs/architecture.md)에서 설명한다.
