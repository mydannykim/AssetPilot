from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .ai_briefing import AIBriefing, HoldingBriefing, load_briefing
from .analysis.allocation import AllocationReport
from .analysis.models import Holding, PortfolioSummary
from .analysis.report import PortfolioReport

DEFAULT_OUTPUT_PATH = Path("data/dashboard.html")

# 검증된(색맹 접근성 체크 통과) 카테고리 색상. 종목이 2개를 넘어가면 중립색으로 폴백한다.
_CATEGORY_COLORS = ["var(--cat-1)", "var(--cat-2)"]
_NEUTRAL_COLOR = "var(--text-muted)"

_CURRENCY_SYMBOLS = {"KRW": "₩", "USD": "$"}

_STYLE = """
:root {
  --bg: #F3F4F7; --surface: #FFFFFF; --surface-2: #EDEFF4; --border: #DADFE7;
  --text: #161A24; --text-muted: #5B6478; --accent: #0E7C8C; --accent-dim: #D3ECEF;
  --gain: #1C8F5C; --gain-bg: #E4F3EB; --loss: #C43C42; --loss-bg: #FBE9E9;
  --warn: #A6690E; --warn-bg: #FBF0DD; --cat-1: #00899E; --cat-2: #7346A0;
  --shadow: 0 1px 2px rgba(20, 24, 34, 0.06), 0 8px 24px rgba(20, 24, 34, 0.05);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0A0E16; --surface: #131926; --surface-2: #1B2333; --border: #29334A;
    --text: #E7EAF2; --text-muted: #8892A8; --accent: #4FD1E0; --accent-dim: #163A40;
    --gain: #3FBE7B; --gain-bg: #123324; --loss: #E5636A; --loss-bg: #3A1618;
    --warn: #E8A33D; --warn-bg: #3A2A0C; --cat-1: #0EA5B8; --cat-2: #9868C4;
    --shadow: 0 1px 2px rgba(0,0,0,.4), 0 8px 28px rgba(0,0,0,.45);
  }
}
:root[data-theme="dark"] {
  --bg: #0A0E16; --surface: #131926; --surface-2: #1B2333; --border: #29334A;
  --text: #E7EAF2; --text-muted: #8892A8; --accent: #4FD1E0; --accent-dim: #163A40;
  --gain: #3FBE7B; --gain-bg: #123324; --loss: #E5636A; --loss-bg: #3A1618;
  --warn: #E8A33D; --warn-bg: #3A2A0C; --cat-1: #0EA5B8; --cat-2: #9868C4;
  --shadow: 0 1px 2px rgba(0,0,0,.4), 0 8px 28px rgba(0,0,0,.45);
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; padding: 32px 20px 64px; }
.page { max-width: 1080px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
.display { font-family: "Iowan Old Style", "Palatino Linotype", Georgia, "Times New Roman", serif; }
.mono { font-family: ui-monospace, "SF Mono", "Roboto Mono", "JetBrains Mono", Consolas, monospace; font-variant-numeric: tabular-nums; }
.label { font-size: 11px; font-weight: 600; letter-spacing: .09em; text-transform: uppercase; color: var(--text-muted); }
.topbar { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px 20px; padding-bottom: 4px; }
.brand { display: flex; align-items: baseline; gap: 10px; }
.brand-mark { font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif; font-size: 20px; font-weight: 600; letter-spacing: .02em; }
.brand-mark span { color: var(--accent); }
.subtitle { font-size: 13px; color: var(--text-muted); }
.status { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }
.dot { width: 7px; height: 7px; border-radius: 999px; background: var(--gain); box-shadow: 0 0 0 3px var(--gain-bg); animation: pulse 2.4s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) { .dot { animation: none; } }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .45; } }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; box-shadow: var(--shadow); }
.panel-head { padding: 16px 20px 0; }
.panel-body { padding: 16px 20px 20px; }
.hero { position: relative; overflow: hidden; padding: 4px; }
.hero::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--accent), transparent 70%); }
.hero-inner { padding: 22px 24px 24px; display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-end; justify-content: space-between; }
.hero-figure { display: flex; flex-direction: column; gap: 6px; }
.hero-value { font-size: 44px; font-weight: 600; line-height: 1; letter-spacing: -.01em; }
.hero-meta { display: flex; gap: 22px; flex-wrap: wrap; }
.meta-item { display: flex; flex-direction: column; gap: 4px; }
.pill { display: inline-flex; align-items: center; gap: 4px; padding: 2px 9px; border-radius: 999px; font-size: 13px; font-weight: 600; width: fit-content; }
.pill.gain { color: var(--gain); background: var(--gain-bg); }
.pill.loss { color: var(--loss); background: var(--loss-bg); }
.pill.neutral { color: var(--text-muted); background: var(--surface-2); }
.pill.sm { font-size: 11px; padding: 1px 7px; }
.briefing-summary { font-size: 14px; line-height: 1.6; margin: 0 0 14px; }
.briefing-holding { padding: 12px 0; border-bottom: 1px solid var(--border); }
.briefing-holding:last-child { border-bottom: none; padding-bottom: 0; }
.briefing-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.briefing-name { font-weight: 600; font-size: 13.5px; }
.briefing-text { font-size: 13px; color: var(--text); line-height: 1.55; margin: 0; }
.briefing-points { margin: 6px 0 0; padding-left: 18px; font-size: 12.5px; color: var(--text-muted); }
.briefing-points li { margin-bottom: 2px; }
.briefing-empty { color: var(--text-muted); font-size: 13px; }
.briefing-meta { font-size: 11.5px; color: var(--text-muted); margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border); }
.grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: 20px; align-items: start; }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }
h2.panel-title { margin: 0; font-size: 15px; font-weight: 600; }
.panel-sub { margin: 2px 0 0; font-size: 12.5px; color: var(--text-muted); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; min-width: 560px; }
thead th { text-align: right; font-size: 10.5px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: var(--text-muted); padding: 0 8px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
thead th:first-child, tbody td:first-child { text-align: left; }
tbody td { padding: 12px 8px; border-bottom: 1px solid var(--border); text-align: right; white-space: nowrap; }
tbody tr:last-child td { border-bottom: none; }
tbody tr { transition: background-color .12s ease; }
tbody tr:hover { background: var(--surface-2); }
.sym-cell { display: flex; align-items: center; gap: 9px; }
.swatch { width: 8px; height: 8px; border-radius: 2px; flex: none; }
.sym-name { font-weight: 600; }
.sym-code { display: block; font-size: 11px; color: var(--text-muted); font-weight: 400; }
.market-chip { font-size: 10.5px; font-weight: 600; color: var(--text-muted); border: 1px solid var(--border); border-radius: 4px; padding: 1px 5px; }
.alloc-row { display: flex; flex-direction: column; gap: 6px; padding: 10px 0; border-bottom: 1px solid var(--border); }
.alloc-row:last-of-type { border-bottom: none; padding-bottom: 2px; }
.alloc-top { display: flex; justify-content: space-between; align-items: baseline; font-size: 13px; gap: 8px; }
.alloc-name { font-weight: 600; }
.alloc-krw { color: var(--text-muted); font-size: 12px; }
.meter { height: 8px; border-radius: 999px; background: var(--surface-2); overflow: hidden; position: relative; }
.meter-fill { height: 100%; border-radius: 999px; }
.warn-item { display: flex; gap: 10px; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.warn-item:last-child { border-bottom: none; padding-bottom: 0; }
.warn-icon { width: 20px; height: 20px; flex: none; border-radius: 5px; background: var(--warn-bg); color: var(--warn); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
.warn-text b { font-weight: 600; }
.warn-sub { color: var(--text-muted); font-size: 12px; margin-top: 1px; }
.no-warn { color: var(--text-muted); font-size: 13px; }
.history-list { display: flex; flex-direction: column; }
.history-item { display: flex; justify-content: space-between; align-items: center; padding: 9px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.history-item:last-child { border-bottom: none; }
.history-empty { color: var(--text-muted); font-size: 12px; }
.history-note { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border); font-size: 12px; color: var(--text-muted); line-height: 1.5; }
footer { text-align: center; font-size: 12px; color: var(--text-muted); padding-top: 8px; line-height: 1.7; }
"""


def _currency_symbol(currency: str) -> str:
    return _CURRENCY_SYMBOLS.get(currency, currency + " ")


def _fmt_qty(qty: float) -> str:
    if qty == int(qty):
        return f"{int(qty):,}"
    return f"{qty:,.4f}"


def _fmt_amount(amount: float, currency: str) -> str:
    symbol = _currency_symbol(currency)
    decimals = 0 if currency == "KRW" else 2
    return f"{symbol}{amount:,.{decimals}f}"


def _fmt_signed_amount(amount: float, currency: str) -> str:
    symbol = _currency_symbol(currency)
    decimals = 0 if currency == "KRW" else 2
    sign = "+" if amount >= 0 else "−"
    return f"{sign}{symbol}{abs(amount):,.{decimals}f}"


def _fmt_pct(ratio: float) -> str:
    sign = "+" if ratio >= 0 else ""
    return f"{sign}{ratio * 100:.2f}%"


def _pl_class(amount: float) -> str:
    return "gain" if amount >= 0 else "loss"


def _pl_arrow(amount: float) -> str:
    return "▲" if amount >= 0 else "▼"


_SENTIMENT_CLASS = {"positive": "gain", "neutral": "neutral", "negative": "loss"}
_SENTIMENT_LABEL = {"positive": "긍정", "neutral": "중립", "negative": "부정"}
_SENTIMENT_ARROW = {"positive": "▲", "neutral": "―", "negative": "▼"}


def _holding_briefing_card(item: HoldingBriefing) -> str:
    cls = _SENTIMENT_CLASS.get(item.sentiment, "neutral")
    label = _SENTIMENT_LABEL.get(item.sentiment, item.sentiment)
    arrow = _SENTIMENT_ARROW.get(item.sentiment, "―")
    points_html = ""
    if item.key_points:
        points = "".join(f"<li>{p}</li>" for p in item.key_points)
        points_html = f'<ul class="briefing-points">{points}</ul>'
    return f"""
    <div class="briefing-holding">
      <div class="briefing-head">
        <span class="briefing-name">{item.name}</span>
        <span class="pill {cls} sm">{arrow} {label}</span>
      </div>
      <p class="briefing-text">{item.summary}</p>
      {points_html}
    </div>"""


def _briefing_section(briefing: AIBriefing | None) -> str:
    if briefing is None:
        body = (
            '<div class="briefing-empty">아직 AI 브리핑이 없습니다. '
            "Claude Code에서 뉴스/동향을 분석해 저장하면 여기에 표시됩니다.</div>"
        )
    else:
        cards = "\n".join(_holding_briefing_card(h) for h in briefing.holdings)
        body = f"""<p class="briefing-summary">{briefing.overall_summary}</p>
        {cards}
        <div class="briefing-meta">생성 시각: {briefing.generated_at}</div>"""

    return f"""
  <section class="panel">
    <div class="panel-head">
      <h2 class="panel-title">AI 브리핑</h2>
      <p class="panel-sub">뉴스 · 매매동향 기반 (Claude 분석)</p>
    </div>
    <div class="panel-body">{body}
    </div>
  </section>"""


def _holding_row(holding: Holding, color: str) -> str:
    krw_note = "" if holding.currency == "KRW" else f'<br><span style="font-size:11px;opacity:.7">≈ {_fmt_amount(holding.eval_amount_krw, "KRW")}</span>'
    pl_cls = _pl_class(holding.profit_loss)
    daily_cls = _pl_class(holding.daily_profit_loss)
    return f"""
    <tr>
      <td>
        <div class="sym-cell">
          <span class="swatch" style="background:{color}"></span>
          <span>
            <span class="sym-name">{holding.name}</span>
            <span class="sym-code">{holding.symbol} <span class="market-chip">{holding.market_country}</span></span>
          </span>
        </div>
      </td>
      <td class="mono">{_fmt_qty(holding.quantity)}</td>
      <td class="mono">{_fmt_amount(holding.current_price, holding.currency)}</td>
      <td class="mono">{_fmt_amount(holding.avg_price, holding.currency)}</td>
      <td class="mono">{_fmt_amount(holding.eval_amount, holding.currency)}{krw_note}</td>
      <td class="mono" style="color:var(--{pl_cls})">{_fmt_signed_amount(holding.profit_loss, holding.currency)}<br><span style="font-size:11px;opacity:.8">{_fmt_pct(holding.profit_loss_pct)}</span></td>
      <td class="mono" style="color:var(--{daily_cls})">{_fmt_signed_amount(holding.daily_profit_loss, holding.currency)}<br><span style="font-size:11px;opacity:.8">{_fmt_pct(holding.daily_profit_loss_pct)}</span></td>
    </tr>"""


def _allocation_row(symbol: str, name: str, eval_amount_krw: float, weight: float, color: str) -> str:
    return f"""
    <div class="alloc-row">
      <div class="alloc-top">
        <span class="alloc-name">{name}</span>
        <span class="mono">{weight * 100:.1f}% <span class="alloc-krw">· {_fmt_amount(eval_amount_krw, "KRW")}</span></span>
      </div>
      <div class="meter"><div class="meter-fill" style="width:{weight * 100:.1f}%; background:{color}"></div></div>
    </div>"""


def _warning_item(message: str) -> str:
    # "삼성전자우 비중이 57.5%로 임계치(30%)를 초과했습니다." 형태의 문장을 그대로 표시
    return f"""
    <div class="warn-item">
      <span class="warn-icon">!</span>
      <div class="warn-text"><div>{message}</div></div>
    </div>"""


def _history_item(label: str, comparison) -> str:
    if comparison is None:
        return f'<div class="history-item"><span>{label}</span><span class="history-empty">비교 데이터 없음</span></div>'
    cls = _pl_class(comparison.diff_amount_krw)
    pct = f" ({_fmt_pct(comparison.diff_pct / 100)})" if comparison.diff_pct is not None else ""
    return f'<div class="history-item"><span>{label}</span><span class="mono" style="color:var(--{cls})">{_fmt_signed_amount(comparison.diff_amount_krw, "KRW")}{pct}</span></div>'


def render_dashboard_html(
    portfolio: PortfolioSummary,
    allocation: AllocationReport,
    history: PortfolioReport | None,
    briefing: AIBriefing | None = None,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    generated_at_kst = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    color_by_symbol = {
        h.symbol: (_CATEGORY_COLORS[i] if i < len(_CATEGORY_COLORS) else _NEUTRAL_COLOR)
        for i, h in enumerate(portfolio.holdings)
    }

    holdings_rows = "\n".join(_holding_row(h, color_by_symbol[h.symbol]) for h in portfolio.holdings)
    allocation_rows = "\n".join(
        _allocation_row(item.symbol, item.name, item.eval_amount_krw, item.weight, color_by_symbol.get(item.symbol, _NEUTRAL_COLOR))
        for item in allocation.breakdown
    )
    warnings_html = (
        "\n".join(_warning_item(w) for w in allocation.warnings)
        if allocation.warnings
        else '<div class="no-warn">현재 집중도 경고가 없습니다.</div>'
    )

    if history is None:
        history_items = "".join(_history_item(label, None) for label in ("1일 전", "7일 전", "30일 전"))
        history_note = "아직 저장된 스냅샷이 없어요. `assetpilot snapshot`(또는 자동화된 launchd 작업)이 실행되면 이 패널에 기간별 변화가 표시됩니다."
    else:
        history_items = "".join(_history_item(label, comp) for label, comp in history.comparisons.items())
        history_note = f"기준 시각: {history.as_of}"

    daily_cls = _pl_class(portfolio.total_daily_profit_loss_krw)
    total_cls = _pl_class(portfolio.total_profit_loss_krw)

    return f"""<title>포트폴리오 계기판</title>
<style>{_STYLE}</style>
<div class="page">
  <div class="topbar">
    <div class="brand">
      <span class="brand-mark">Asset<span>Pilot</span></span>
      <span class="subtitle">포트폴리오 계기판</span>
    </div>
    <div class="status">
      <span class="dot"></span>
      조회 시각 {generated_at_kst} · 토스증권 실계좌 연동
    </div>
  </div>

  <section class="panel hero">
    <div class="hero-inner">
      <div class="hero-figure">
        <span class="label">총 평가금액</span>
        <span class="hero-value mono display">{_fmt_amount(portfolio.total_eval_amount_krw, "KRW")}</span>
      </div>
      <div class="hero-meta">
        <div class="meta-item">
          <span class="label">일간 손익</span>
          <span class="pill {daily_cls} mono">{_pl_arrow(portfolio.total_daily_profit_loss_krw)} {_fmt_signed_amount(portfolio.total_daily_profit_loss_krw, "KRW")} <span style="opacity:.75">({_fmt_pct(portfolio.total_daily_profit_loss_pct)})</span></span>
        </div>
        <div class="meta-item">
          <span class="label">누적 손익 (매입가 대비)</span>
          <span class="pill {total_cls} mono">{_pl_arrow(portfolio.total_profit_loss_krw)} {_fmt_signed_amount(portfolio.total_profit_loss_krw, "KRW")} <span style="opacity:.75">({_fmt_pct(portfolio.total_profit_loss_pct)})</span></span>
        </div>
      </div>
    </div>
  </section>
{_briefing_section(briefing)}
  <div class="grid">
    <section class="panel">
      <div class="panel-head">
        <h2 class="panel-title">보유 종목</h2>
        <p class="panel-sub">{len(portfolio.holdings)}개 종목</p>
      </div>
      <div class="panel-body table-wrap">
        <table>
          <thead>
            <tr><th>종목</th><th>수량</th><th>현재가</th><th>평단가</th><th>평가금액</th><th>누적 손익</th><th>일간</th></tr>
          </thead>
          <tbody>{holdings_rows}
          </tbody>
        </table>
      </div>
    </section>

    <div style="display:flex; flex-direction:column; gap:20px;">
      <section class="panel">
        <div class="panel-head">
          <h2 class="panel-title">자산 비중</h2>
          <p class="panel-sub">원화 환산 기준</p>
        </div>
        <div class="panel-body">{allocation_rows}
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2 class="panel-title">집중도 경고</h2>
          <p class="panel-sub">임계치 초과 종목</p>
        </div>
        <div class="panel-body">{warnings_html}
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2 class="panel-title">기간별 변화</h2>
          <p class="panel-sub">스냅샷 히스토리 기준</p>
        </div>
        <div class="panel-body">
          <div class="history-list">{history_items}</div>
          <div class="history-note">{history_note}</div>
        </div>
      </section>
    </div>
  </div>

  <footer>
    AssetPilot · 토스증권 Open API + 로컬 MCP 서버로 조회한 실계좌 데이터 (조회 전용, 매매 기능 없음)<br>
    이 파일은 <code>assetpilot dashboard</code> 실행 시마다 최신 데이터로 다시 생성됩니다.
  </footer>
</div>
"""


def write_dashboard(
    portfolio: PortfolioSummary,
    allocation: AllocationReport,
    history: PortfolioReport | None,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    briefing = load_briefing(output_path.parent / "ai_briefing.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_dashboard_html(portfolio, allocation, history, briefing), encoding="utf-8")
    return output_path
