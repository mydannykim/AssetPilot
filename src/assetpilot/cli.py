from __future__ import annotations

import webbrowser

import click

from .analysis.allocation import compute_allocation
from .analysis.fx import fetch_fx_rates_to_krw
from .analysis.market_flow import summarize_market_flow
from .analysis.models import parse_holdings
from .analysis.report import generate_report
from .config import load_settings
from .dashboard import write_dashboard
from .news.collector import collect_news_for_holdings
from .storage.db import init_db
from .storage.news import list_news
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


@main.command("dashboard")
@click.option("--account-seq", default=None, help="계좌 시퀀스 번호 (생략 시 첫 번째 계좌 사용)")
@click.option("--threshold", default=0.3, help="집중도 경고 임계치 (기본 0.3 = 30%)")
@click.option("--open/--no-open", "open_browser", default=True, help="생성 후 기본 브라우저로 열기 (기본값: 열기)")
def dashboard_cmd(account_seq: str | None, threshold: float, open_browser: bool) -> None:
    """최신 데이터로 로컬 대시보드 HTML을 생성하고 브라우저로 연다."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        resolved_seq, holdings, fx_rates = _fetch_holdings_and_fx(client, account_seq)
        portfolio = parse_holdings(holdings, fx_rates)
        allocation = compute_allocation(portfolio, threshold)

    history = generate_report(settings.db_path, resolved_seq)
    output_path = write_dashboard(portfolio, allocation, history, settings.db_path.parent / "dashboard.html")
    click.echo(f"대시보드 생성 완료: {output_path.resolve()}")

    if open_browser:
        webbrowser.open(output_path.resolve().as_uri())


@main.command("trends")
@click.argument("symbol")
@click.option("--days", default=5, help="집계할 최근 영업일 수 (기본 5일)")
def trends_cmd(symbol: str, days: int) -> None:
    """국내 종목의 투자자별 매매동향/공매도/매수유의 정보를 요약해 출력한다 (국내 종목 전용)."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        investor = client.get_investor_trading(symbol)
        short = client.get_short_selling(symbol)
        warnings = client.get_stock_warnings(symbol)

    summary = summarize_market_flow(symbol, investor, short, warnings, days=days)
    click.echo(f"[{symbol}] 최근 {len(summary.days)}영업일 매매동향")
    click.echo(f"  외국인: {summary.foreigner_net_sum:+,.0f}주 ({summary.foreigner_streak})")
    click.echo(f"  기관:   {summary.institution_net_sum:+,.0f}주 ({summary.institution_streak})")
    click.echo(f"  개인:   {summary.individual_net_sum:+,.0f}주")
    if summary.short_selling_volume_rate is not None:
        click.echo(f"  공매도 비중: {summary.short_selling_volume_rate:.2%} (최근 거래일)")
    if summary.warnings:
        click.echo(f"  ⚠ 매수 유의사항 {summary.warning_count}건: {summary.warnings}")


@main.command("news")
@click.option("--account-seq", default=None, help="계좌 시퀀스 번호 (생략 시 첫 번째 계좌 사용)")
@click.option("--max-items", default=8, help="종목당 최대 수집 기사 수 (기본 8)")
def news_cmd(account_seq: str | None, max_items: int) -> None:
    """보유 종목 관련 뉴스를 구글 뉴스에서 수집해 로컬 DB에 저장한다 (감성분석 없이 원문만 저장)."""
    settings = load_settings()
    with TossClient(
        client_id=settings.toss_client_id,
        client_secret=settings.toss_client_secret,
        base_url=settings.toss_api_base_url,
    ) as client:
        _, holdings, fx_rates = _fetch_holdings_and_fx(client, account_seq)
        portfolio = parse_holdings(holdings, fx_rates)
        saved_counts = collect_news_for_holdings(client, settings.db_path, portfolio.holdings, max_items)

    for symbol, count in saved_counts.items():
        click.echo(f"  {symbol}: 신규 {count}건 저장")


@main.command("news-list")
@click.option("--symbol", default=None, help="특정 종목 코드로 필터링 (생략 시 전체)")
@click.option("--limit", default=20, help="최대 출력 건수 (기본 20)")
def news_list_cmd(symbol: str | None, limit: int) -> None:
    """저장된 뉴스 목록을 출력한다."""
    settings = load_settings()
    items = list_news(settings.db_path, symbol, limit)
    if not items:
        click.echo("저장된 뉴스가 없습니다. `assetpilot news`를 먼저 실행하세요.")
        return
    for item in items:
        click.echo(f"[{item['related_symbols']}] {item['title']}")
        click.echo(f"    {item['source']} · {item['published_at'] or '날짜 미상'}")
        click.echo(f"    {item['url']}")


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
