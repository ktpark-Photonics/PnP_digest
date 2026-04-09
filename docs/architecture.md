# Phase 0 아키텍처

## 목표

Phase 0의 목표는 이후 단계가 모두 공유할 수 있는 구조화 데이터 계약과 배치형 실행 골격을 먼저 고정하는 것이다.

## 현재 포함 범위

- `Pydantic v2` 기반 canonical schema
- 배치형 CLI
- 로컬 fixture 기반 ingest
- 정규화 및 중복 후보 병합
- JSON artifact 저장 규칙
- JSON schema export

## 계층 구조

### `domain`
- 파이프라인 전 단계가 공유하는 enum, Pydantic 모델, schema version 정의를 둔다.

### `adapters`
- 외부 소스 대신 로컬 JSON fixture를 읽는 adapter를 둔다.

### `services`
- artifact 저장, JSON 입출력, 정규화 유틸리티를 둔다.

### `pipelines`
- stage별 orchestration을 둔다.

### `config`
- 향후 relevance/verification 단계에서 사용할 도메인 설정 모델과 CIS 기본 용어 사전을 둔다.

## Artifact 규칙

- 실행 산출물은 `artifacts/runs/<run_id>/<stage>/` 아래에 저장한다.
- ingest 단계는 원시 payload와 `ingest_artifact.json`을 저장한다.
- normalize 단계는 `normalized_artifact.json`을 저장한다.
- 각 artifact는 `schema_version`과 `run` 정보를 포함한다.

## 향후 확장 포인트

- `assess-relevance`: 규칙 기반 필터와 classification 근거 저장
- `verify`: 필드 단위 특허 검증 및 reviewer import/export
- `summarize` / `explain`: evidence-linked summary payload 생성
- `review`: verification 검수와 final release signoff를 파일로 주고받는 단계
- `render`: 현재는 Markdown/DOCX/PDF/PPTX brief 렌더러
- `release`: render 결과를 배포용 manifest로 정리하는 최종 후보 단계
- `publish`: release review 승인 결과를 채널별 publish stub artifact로 정리하는 단계
- `publish review`: publish 결과를 사람이 다시 확인해 채널별 최종 상태를 artifact로 남기는 단계
