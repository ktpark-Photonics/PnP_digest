# PnP Digest

CIS 분야 최신 논문 및 특허를 주간 단위로 수집하고, 구조화 요약과 검수 가능한 기술 브리프를 만들기 위한 내부 도구다.

현재 구현 범위는 `Phase 4`이며 다음을 포함한다.

- 핵심 canonical schema 패키지
- 로컬 fixture 기반 `ingest` / `normalize` 파이프라인
- 규칙 기반 `assess-relevance` 파이프라인(근거 snippet 및 수동 검토 manifest 생성)
- mock/manual provider 기반 `verify` 파이프라인(특허 존재 확인 + 핵심 필드 검증 + review manifest 생성)
- `verification_review_manifest.json`을 CSV/Markdown으로 내보내는 `review export` CLI
- 사람이 수정한 review CSV를 다시 JSON artifact로 반영하는 `review import` CLI
- `approved` 검토 결과만 읽어 placeholder `summary_artifact.json`을 생성하는 `summarize` 파이프라인
- `summary_artifact.json`에서 직급별 설명을 분리한 `explain_artifact.json`을 생성하는 `explain` 파이프라인
- `explain_artifact.json`에서 Markdown brief와 `render_artifact.json`을 생성하는 `render` 파이프라인
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

Phase 4 현재 범위에서는 `assess-relevance`, `verify`, `review import/export`, `summarize`, `explain`, `render`를 구현했으며, DOCX/PPTX/PDF 렌더링은 아직 포함하지 않는다.

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
./.venv/bin/python -m pnp_digest.cli summarize --help
./.venv/bin/python -m pnp_digest.cli explain --help
./.venv/bin/python -m pnp_digest.cli render --help
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
Phase 4에서는 `explain_artifact.json`을 Markdown brief로 렌더링하고, 출력 메타데이터를 `render_artifact.json`으로 저장한다.

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
- `artifacts/runs/<run_id>/render/brief.md` (`render` 실행 시 생성되는 Markdown brief)
- `artifacts/runs/<run_id>/render/render_artifact.json` (`Markdown brief output metadata`)

규칙 사전 초안은 `data/dictionaries/` 아래 파일을 사용한다.

- `cis_allow_keywords.txt`
- `cis_deny_keywords.txt`
- `cis_classification_rules.toml`

## 현재 제한 사항

- 외부 API 연동은 아직 없다.
- 특허 검증은 아직 mock/manual provider 기반이며 실제 온라인 조회를 하지 않는다.
- LLM 기반 relevance/요약 생성은 아직 없다.
- 현재 `render`는 Markdown brief만 생성하며 DOCX/PPTX/PDF 렌더링은 아직 없다.

상세 구조는 [docs/architecture.md](/home/kyongtae/projects/PnP_digest/docs/architecture.md)에서 설명한다.
