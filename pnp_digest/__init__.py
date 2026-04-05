"""로컬 개발에서 `src` 레이아웃 패키지를 찾기 위한 얇은 shim."""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path
from typing import Any

__path__ = extend_path(__path__, __name__)

SRC_PACKAGE_PATH = Path(__file__).resolve().parent.parent / "src" / "pnp_digest"
if SRC_PACKAGE_PATH.exists():
    __path__.append(str(SRC_PACKAGE_PATH))

__all__ = ["SCHEMA_VERSION"]


def __getattr__(name: str) -> Any:
    """필요할 때만 실제 패키지 속성을 지연 로드한다."""

    if name == "SCHEMA_VERSION":
        from pnp_digest.domain.schema import SCHEMA_VERSION

        return SCHEMA_VERSION
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
