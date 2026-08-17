from __future__ import annotations

import click

from .config import load_settings
from .storage.db import init_db
from .storage.portfolio import save_holdings_snapshot
from .toss_client.client import TossClient


def _resolve_account_seq(client: TossClient, account_seq: str | None) -> str:
    if account_seq is not None:
        return account_seq
    accounts = client.get_accounts()["result"]
    return str(accounts[0]["accountSeq"])


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
    """토스증권 계좌 목록을 조회해 출력한다."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        accounts = client.get_accounts()
        click.echo(accounts)


@main.command("holdings")
@click.option("--account-seq", default=None, help="계좌 시퀀스 번호 (생략 시 첫 번째 계좌 사용)")
def holdings_cmd(account_seq: str | None) -> None:
    """보유 종목을 조회해 출력한다."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        client.set_account(_resolve_account_seq(client, account_seq))
        click.echo(client.get_holdings())


@main.command("snapshot")
@click.option("--account-seq", default=None, help="계좌 시퀀스 번호 (생략 시 첫 번째 계좌 사용)")
def snapshot_cmd(account_seq: str | None) -> None:
    """보유 종목을 조회해 로컬 SQLite DB에 스냅샷으로 기록한다."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        resolved_seq = _resolve_account_seq(client, account_seq)
        client.set_account(resolved_seq)
        holdings = client.get_holdings()
        saved = save_holdings_snapshot(settings.db_path, resolved_seq, holdings)
        click.echo(f"스냅샷 저장 완료: {saved}건 (계좌 {resolved_seq})")


@main.command("price")
@click.argument("symbol")
def price_cmd(symbol: str) -> None:
    """종목 현재가를 조회해 출력한다."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        click.echo(client.get_price(symbol))


if __name__ == "__main__":
    main()
