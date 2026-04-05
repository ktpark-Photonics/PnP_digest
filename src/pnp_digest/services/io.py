"""JSON artifact 입출력 유틸리티."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


def ensure_directory(path: Path) -> Path:
    """디렉터리가 없으면 생성하고 경로를 반환한다."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    """dict payload를 보기 쉬운 JSON으로 저장한다."""

    ensure_directory(path.parent)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def write_model(path: Path, model: BaseModel) -> Path:
    """Pydantic model을 JSON 파일로 저장한다."""

    return write_json(path, model.model_dump(mode="json"))


def read_json(path: Path) -> dict[str, Any]:
    """JSON 파일을 읽어 dict로 반환한다."""

    return json.loads(path.read_text(encoding="utf-8"))


def read_model(path: Path, model_class: type[ModelType]) -> ModelType:
    """JSON 파일을 읽어 지정한 Pydantic model로 검증한다."""

    payload = read_json(path)
    return model_class.model_validate(payload)
