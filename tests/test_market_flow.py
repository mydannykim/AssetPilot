from __future__ import annotations

from assetpilot.analysis.market_flow import summarize_market_flow


def _flow_day(date: str, net: float) -> dict:
    return {
        "date": date,
        "individual": {"netBuyVolume": net},
        "foreigner": {"netBuyVolume": net},
        "institution": {"netBuyVolume": net},
    }


def test_skips_incomplete_intraday_record_instead_of_crashing():
    """장중(당일)에는 individual/foreigner/institution이 null로 오는 경우가 있다 — 08-18 실전 장애 재현."""
    investor_trading_response = {
        "result": {
            "records": [
                {"date": "2026-08-18", "individual": None, "foreigner": None, "institution": None},
                _flow_day("2026-08-17", 100.0),
                _flow_day("2026-08-14", 200.0),
            ]
        }
    }

    summary = summarize_market_flow(
        symbol="005935",
        investor_trading_response=investor_trading_response,
        short_selling_response={"result": {"records": []}},
        warnings_response={"result": []},
        days=5,
    )

    assert [d.date for d in summary.days] == ["2026-08-17", "2026-08-14"]
    assert summary.individual_net_sum == 300.0


def test_all_complete_records_are_kept():
    investor_trading_response = {
        "result": {
            "records": [_flow_day("2026-08-18", 50.0), _flow_day("2026-08-17", -20.0)],
        }
    }

    summary = summarize_market_flow(
        symbol="005935",
        investor_trading_response=investor_trading_response,
        short_selling_response={"result": {"records": []}},
        warnings_response={"result": []},
        days=5,
    )

    assert len(summary.days) == 2
    assert summary.foreigner_streak == "1일 연속 순매수"
