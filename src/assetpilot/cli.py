from __future__ import annotations

import click

from .analysis.allocation import compute_allocation
from .analysis.fx import fetch_fx_rates_to_krw
from .analysis.models import parse_holdings
from .analysis.report import generate_report
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


def _fetch_holdings_and_fx(client: TossClient, account_seq: str | None) -> tuple[str, dict, dict[str, float]]:
    resolved_seq = _resolve_account_seq(client, account_seq)
    client.set_account(resolved_seq)
    holdings = client.get_holdings()
    currencies = {item.get("currency", "KRW") for item in holdings.get("result", {}).get("items", [])}
    fx_rates = fetch_fx_rates_to_krw(client, currencies)
    return resolved_seq, holdings, fx_rates


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
        resolved_seq, holdings, fx_rates = _fetch_holdings_and_fx(client, account_seq)
        saved = save_holdings_snapshot(settings.db_path, resolved_seq, holdings, fx_rates)
        click.echo(f"스냅샷 저장 완료: {saved}건 (계좌 {resolved_seq})")


@main.command("allocation")
@click.option("--account-seq", default=None, help="계좌 시퀀스 번호 (생략 시 첫 번째 계좌 사용)")
@click.option("--threshold", default=0.3, help="집중도 경고 임계치 (기본 0.3 = 30%)")
def allocation_cmd(account_seq: str | None, threshold: float) -> None:
    """보유 종목의 원화 환산 비중과 집중도 경고를 출력한다."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        _, holdings, fx_rates = _fetch_holdings_and_fx(client, account_seq)
        portfolio = parse_holdings(holdings, fx_rates)
        report = compute_allocation(portfolio, threshold)

        click.echo(f"총 평가금액: {report.total_eval_amount_krw:,.0f} KRW")
        for item in report.breakdown:
            click.echo(f"  {item.name:12s} {item.weight:6.1%}  ({item.eval_amount_krw:,.0f} KRW)")
        for warning in report.warnings:
            click.echo(f"⚠ {warning}")


@main.command("report")
@click.option("--account-seq", default=None, help="계좌 시퀀스 번호 (생략 시 첫 번째 계좌 사용)")
def report_cmd(account_seq: str | None) -> None:
    """저장된 스냅샷 히스토리를 바탕으로 기간별 평가금액 변화 리포트를 출력한다."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        resolved_seq = _resolve_account_seq(client, account_seq)

    report = generate_report(settings.db_path, resolved_seq)
    if report is None:
        click.echo("저장된 스냅샷이 없습니다. `assetpilot snapshot`을 먼저 실행하세요.")
        return

    click.echo(f"기준 시각: {report.as_of}")
    click.echo(f"현재 평가금액: {report.total_eval_amount_krw:,.0f} KRW")
    for label, comparison in report.comparisons.items():
        if comparison is None:
            click.echo(f"  {label}: 비교할 스냅샷 없음")
            continue
        sign = "+" if comparison.diff_amount_krw >= 0 else ""
        pct = f" ({sign}{comparison.diff_pct:.2f}%)" if comparison.diff_pct is not None else ""
        click.echo(f"  {label}: {sign}{comparison.diff_amount_krw:,.0f} KRW{pct}")


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
