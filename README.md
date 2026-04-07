# PnP Digest

CIS 분야 최신 논문 및 특허를 주간 단위로 수집하고, 구조화 요약과 검수 가능한 기술 브리프를 만들기 위한 내부 도구다.

현재 구현 범위는 `Phase 1`이며 다음을 포함한다.

- 핵심 canonical schema 패키지
- 로컬 fixture 기반 `ingest` / `normalize` 파이프라인
- 규칙 기반 `assess-relevance` 파이프라인(근거 snippet 및 수동 검토 manifest 생성)
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

Phase 1에서는 `assess-relevance`를 추가 구현했으며, `verify` 이후 단계는 동일 CLI 인터페이스를 가진 skeleton으로 제공한다.

## WSL 로컬 검증

Python 3.12와 `.venv` 기준으로 아래 순서를 권장한다.

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/python -m pytest -q
./.venv/bin/python -m pnp_digest.cli assess-relevance --help
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

## 예시 명령

```bash
pnp-digest export-schemas
pnp-digest ingest --run-id 2026w14 --input-path data/sample_inputs/cis_weekly_fixture.json
pnp-digest normalize --run-id 2026w14 --ingest-artifact artifacts/runs/2026w14/ingest/ingest_artifact.json
pnp-digest assess-relevance --run-id 2026w14 --normalized-artifact artifacts/runs/2026w14/normalize/normalized_artifact.json
```

`assess-relevance` 실행 시 아래 파일이 저장된다.

- `artifacts/runs/<run_id>/assess_relevance/relevance_report.json`
- `artifacts/runs/<run_id>/assess_relevance/manual_review_manifest.json` (`borderline` 문헌만 포함)

규칙 사전 초안은 `data/dictionaries/` 아래 파일을 사용한다.

- `cis_allow_keywords.txt`
- `cis_deny_keywords.txt`
- `cis_classification_rules.toml`

## 현재 제한 사항

- 외부 API 연동은 아직 없다.
- 특허 실재 검증 로직은 아직 없다.
- LLM 기반 relevance/요약 생성은 아직 없다.
- DOCX/PPTX/PDF 렌더링은 아직 없다.

상세 구조는 [docs/architecture.md](/home/kyongtae/projects/PnP_digest/docs/architecture.md)에서 설명한다.
