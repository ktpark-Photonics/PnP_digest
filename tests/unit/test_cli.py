"""CLI 입력 파싱 테스트."""

from datetime import date

import pytest
import typer

from pnp_digest.cli import parse_iso_date


def test_parse_iso_date_accepts_iso_date_string() -> None:
    """ISO 형식 문자열은 date 객체로 변환되어야 한다."""

    assert parse_iso_date("2026-04-05") == date(2026, 4, 5)


def test_parse_iso_date_rejects_invalid_format() -> None:
    """잘못된 날짜 형식은 이해하기 쉬운 에러로 안내해야 한다."""

    with pytest.raises(typer.BadParameter, match="YYYY-MM-DD"):
        parse_iso_date("2026/04/05")
