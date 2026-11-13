"""用连环替代法，把相邻两年的 ROE 变动拆到三个因子上。

连环替代法的想法很简单：一次只换一个因子，看 ROE 因此变了多少，
就把这一段变化记在刚刚被换掉的那个因子头上。

本工具固定按下面的顺序替代（基期用下标 0，本期用下标 1）：

    1. 先把净利率从 A0 换成 A1，周转率和权益乘数仍用基期
    2. 再把周转率从 B0 换成 B1，权益乘数仍用基期
    3. 最后把权益乘数从 C0 换成 C1

于是：

    净利率贡献         = A1*B0*C0 - A0*B0*C0
    总资产周转率贡献   = A1*B1*C0 - A1*B0*C0
    权益乘数贡献       = A1*B1*C1 - A1*B1*C0

三项加起来一定等于 A1*B1*C1 - A0*B0*C0，也就是按三因素计算的 ROE 总变动。

为什么顺序会影响“分摊”，却不影响“合计”？
后被替代的因子，会乘上已经换成“本期”的前面因子。
换一种顺序，交叉影响会被算进不同的因子，所以每个因子的贡献数字会变；
但三段变化首尾相接，加总仍然等于总变动。详见 README。
"""

from dupont.ratios import DEFAULT_TOLERANCE


def decompose_roe_change(base, current, tolerance=DEFAULT_TOLERANCE):
    """对相邻的两期比率做一次连环替代，返回各因子贡献。"""
    a0 = base["net_margin"]
    b0 = base["asset_turnover"]
    c0 = base["equity_multiplier"]
    a1 = current["net_margin"]
    b1 = current["asset_turnover"]
    c1 = current["equity_multiplier"]

    # 下面四个 ROE 是逐步替换后的“中间结果”。
    # 相邻两项相减，就是刚被替换的那个因子的贡献。
    roe_base_factors = a0 * b0 * c0
    roe_after_margin = a1 * b0 * c0
    roe_after_turnover = a1 * b1 * c0
    roe_after_multiplier = a1 * b1 * c1

    contrib_net_margin = roe_after_margin - roe_base_factors
    contrib_asset_turnover = roe_after_turnover - roe_after_margin
    contrib_equity_multiplier = roe_after_multiplier - roe_after_turnover
    contribution_sum = (
        contrib_net_margin + contrib_asset_turnover + contrib_equity_multiplier
    )

    # 对外报告的“ROE 变动”用直接计算的 ROE（净利润 / 权益），
    # 与比率表里的口径保持一致。只要三因素恒等式成立，
    # 它应和贡献合计、以及三因素 ROE 的差相同。
    roe_change = current["roe"] - base["roe"]
    sum_matches = abs(contribution_sum - roe_change) <= tolerance

    return {
        "base_year": base["year"],
        "current_year": current["year"],
        "base_roe": base["roe"],
        "current_roe": current["roe"],
        "roe_change": roe_change,
        "contrib_net_margin": contrib_net_margin,
        "contrib_asset_turnover": contrib_asset_turnover,
        "contrib_equity_multiplier": contrib_equity_multiplier,
        "contribution_sum": contribution_sum,
        "sum_matches_change": sum_matches,
    }


def decompose_all(ratio_rows, tolerance=DEFAULT_TOLERANCE):
    """对按年份排好的比率结果，逐对相邻年份做连环替代。

    有 n 年数据时，会得到 n-1 段变动。只有一年时列表为空，并不是出错。
    """
    results = []
    index = 0
    while index < len(ratio_rows) - 1:
        base = ratio_rows[index]
        current = ratio_rows[index + 1]
        results.append(decompose_roe_change(base, current, tolerance=tolerance))
        index = index + 1
    return results
