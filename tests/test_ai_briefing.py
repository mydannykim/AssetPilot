from __future__ import annotations

from assetpilot.ai_briefing import AIBriefing, HoldingBriefing, KeyPoint


def test_key_point_impact_defaults_to_medium():
    kp = KeyPoint(point="테스트 이슈")
    assert kp.impact == "medium"


def test_holding_briefing_round_trips_key_points_with_impact():
    briefing = AIBriefing(
        generated_at="2026-08-18T12:00:00+09:00",
        overall_summary="테스트 총평",
        holdings=[
            HoldingBriefing(
                symbol="005935",
                name="삼성전자우",
                sentiment="positive",
                summary="테스트 요약",
                key_points=[
                    KeyPoint(point="실적 호조", impact="high"),
                    KeyPoint(point="일반 시황 언급", impact="low"),
                ],
            )
        ],
    )

    parsed = AIBriefing.model_validate_json(briefing.model_dump_json())

    assert parsed.holdings[0].key_points[0].impact == "high"
    assert parsed.holdings[0].key_points[1].point == "일반 시황 언급"
