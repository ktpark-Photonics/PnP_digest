# Phase 0 운영 메모

- 입력은 `data/sample_inputs/`의 로컬 fixture를 사용한다.
- 검수는 아직 사람이 JSON artifact를 직접 확인하는 파일 기반 방식만 지원한다.
- normalize 단계는 동일 DOI 또는 동일 patent number를 가진 문헌을 하나의 `DocumentRecord`로 병합한다.
- 중복 병합은 보수적으로 수행하며, 병합 근거는 `dedup_candidate_keys`와 `source_record_ids`에 남긴다.
