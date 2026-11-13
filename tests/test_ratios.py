"""检查比率计算是否符合手算结果，以及平均口径和期末口径是否被正确区分。"""

from dupont.ratios import check_roe_identity, choose_balance, compute_row_ratios


def _sample_row():
    # 这组数字可以心算：平均资产 850，平均权益 420。
    return {
        "year": 2020,
        "revenue": 1000,
        "net_profit": 80,
        "total_assets_begin": 800,
        "total_assets_end": 900,
        "equity_begin": 400,
        "equity_end": 440,
    }


def test_choose_balance_average_and_end():
    assert choose_balance(800, 900, "average") == 850
    assert choose_balance(800, 900, "end") == 900


def test_ratio_math_with_average_basis():
    result = compute_row_ratios(_sample_row(), basis="average")

    # 80 / 1000 = 0.08
    assert result["net_margin"] == 0.08
    # 1000 / 850
    assert abs(result["asset_turnover"] - (1000 / 850)) < 1e-12
    # 850 / 420
    assert abs(result["equity_multiplier"] - (850 / 420)) < 1e-12
    # 80 / 420
    assert abs(result["roe"] - (80 / 420)) < 1e-12


def test_product_of_three_factors_matches_direct_roe():
    result = compute_row_ratios(_sample_row(), basis="average")
    product, difference, matched = check_roe_identity(
        result["net_margin"],
        result["asset_turnover"],
        result["equity_multiplier"],
        result["roe"],
    )
    assert matched is True
    assert abs(difference) < 1e-12
    assert abs(product - result["roe"]) < 1e-12
    assert result["roe_identity_ok"] is True


def test_average_basis_differs_from_end_basis():
    average = compute_row_ratios(_sample_row(), basis="average")
    end = compute_row_ratios(_sample_row(), basis="end")

    # 期末资产 900、期末权益 440，和平均数不同，周转率、乘数、ROE 都应跟着变。
    assert end["assets"] == 900
    assert end["equity"] == 440
    assert average["assets"] != end["assets"]
    assert average["equity"] != end["equity"]
    assert average["asset_turnover"] != end["asset_turnover"]
    assert average["equity_multiplier"] != end["equity_multiplier"]
    assert abs(end["roe"] - (80 / 440)) < 1e-12
    assert end["roe_identity_ok"] is True
