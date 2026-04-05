"""artifact 경로 관리 유틸리티."""

from __future__ import annotations

from pathlib import Path

from pnp_digest.domain.enums import StageName
from pnp_digest.services.io import ensure_directory


class ArtifactManager:
    """run_id 기준 artifact 디렉터리를 관리한다."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def run_dir(self, run_id: str) -> Path:
        """특정 run의 루트 디렉터리를 반환한다."""

        return ensure_directory(self.base_dir / run_id)

    def stage_dir(self, run_id: str, stage: StageName) -> Path:
        """특정 stage의 artifact 디렉터리를 반환한다."""

        return ensure_directory(self.run_dir(run_id) / stage.value)
