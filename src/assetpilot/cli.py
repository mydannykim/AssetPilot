from __future__ import annotations

import click

from .config import load_settings
from .storage.db import init_db
from .toss_client.client import TossClient


@click.group()
def main() -> None:
    """AssetPilot: 토스증권 + Claude 연동 자산관리 CLI"""


@main.command("init-db")
def init_db_cmd() -> None:
    """로컬 SQLite DB 스키마를 생성한다."""
    settings = load_settings()
    init_db(settings.db_path)
    click.echo(f"DB 초기화 완료: {settings.db_path}")


@main.command("status")
def status_cmd() -> None:
    """토스증권 계좌 잔고/보유종목을 조회해 출력한다."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        accounts = client.get_accounts()
        click.echo(accounts)


if __name__ == "__main__":
    main()
