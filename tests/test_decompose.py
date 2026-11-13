"""检查连环替代法：各因子贡献加起来应等于 ROE 的总变动。"""

from dupont.decompose import decompose_all, decompose_roe_change
from dupont.ratios import compute_row_ratios


def _row(year, revenue, net_profit, assets_begin, assets_end, equity_begin, equity_end):
    return {
        "year": year,
        "revenue": revenue,
        "net_profit": net_profit,
        "total_assets_begin": assets_begin,
        "total_assets_end": assets_end,
        "equity_begin": equity_begin,
        "equity_end": equity_end,
    }


def test_chain_substitution_sum_equals_total_roe_change():
    base = compute_row_ratios(
        _row(2020, 1000, 80, 800, 900, 400, 440),
        basis="average",
    )
    current = compute_row_ratios(
        _row(2021, 1200, 108, 900, 1100, 440, 500),
        basis="average",
    )

    result = decompose_roe_change(base, current)

    expected_change = current["roe"] - base["roe"]
    assert abs(result["roe_change"] - expected_change) < 1e-12
    assert abs(result["contribution_sum"] - result["roe_change"]) < 1e-12
    assert result["sum_matches_change"] is True

    # 再按定义手算一遍三段贡献，避免“合计碰巧对了、每一段却写错”。
    a0, b0, c0 = base["net_margin"], base["asset_turnover"], base["equity_multiplier"]
    a1, b1, c1 = current["net_margin"], current["asset_turnover"], current["equity_multiplier"]
    assert abs(result["contrib_net_margin"] - (a1 * b0 * c0 - a0 * b0 * c0)) < 1e-12
    assert abs(result["contrib_asset_turnover"] - (a1 * b1 * c0 - a1 * b0 * c0)) < 1e-12
    assert abs(result["contrib_equity_multiplier"] - (a1 * b1 * c1 - a1 * b1 * c0)) < 1e-12


def test_decompose_all_walks_adjacent_years():
    rows = [
        compute_row_ratios(_row(2020, 1000, 80, 800, 900, 400, 440), basis="end"),
        compute_row_ratios(_row(2021, 1200, 108, 900, 1100, 440, 500), basis="end"),
        compute_row_ratios(_row(2022, 1350, 108, 1100, 1300, 500, 560), basis="end"),
    ]
    results = decompose_all(rows)
    assert len(results) == 2
    assert results[0]["base_year"] == 2020
    assert results[0]["current_year"] == 2021
    assert results[1]["base_year"] == 2021
    assert results[1]["current_year"] == 2022
    for item in results:
        assert item["sum_matches_change"] is True
