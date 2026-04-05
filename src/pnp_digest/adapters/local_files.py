"""로컬 fixture 기반 source adapter."""

from __future__ import annotations

from pathlib import Path

from pnp_digest.domain.models import SampleSourceRecord
from pnp_digest.services.io import read_json


class LocalFixtureAdapter:
    """Phase 0에서 로컬 JSON fixture를 source처럼 읽는다."""

    def load_records(self, input_path: Path) -> list[SampleSourceRecord]:
        """입력 JSON을 `SampleSourceRecord` 목록으로 검증한다."""

        payload = read_json(input_path)
        if not isinstance(payload, list):
            raise ValueError("입력 fixture는 JSON 배열이어야 합니다.")
        return [SampleSourceRecord.model_validate(item) for item in payload]
