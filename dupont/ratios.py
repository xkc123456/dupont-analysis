"""计算杜邦分析用到的四个比率，并核对“三因素相乘是否等于直接计算的 ROE”。

杜邦分析把净资产收益率（ROE）拆成三项：

    ROE = 净利率 × 总资产周转率 × 权益乘数

写出来就是：

    净利润 / 所有者权益
        = (净利润 / 营业收入)
        × (营业收入 / 总资产)
        × (总资产 / 所有者权益)

中间的营业收入、总资产可以约掉，所以在理想情况下两边应该完全相等。
实际计算会有一点点浮点误差，所以用容差来判断“是否足够接近”，而不是要求分毫不差。
"""

# 允许的最大误差。普通的四则运算差会远小于这个数；
# 如果超过它，多半是公式写错了，而不是正常的四舍五入。
DEFAULT_TOLERANCE = 1e-8

VALID_BASIS = ("average", "end")


def choose_balance(begin, end, basis):
    """按口径选出这一年要用的资产或权益余额。

    为什么要单独写成函数？
    资产和权益都要用同一套规则。写成函数后，改口径时只改一处，
    也不会出现“资产用了平均、权益却用了期末”这种不一致。
    """
    if basis == "average":
        # 年内资产、权益会变动。用期初和期末的平均数，
        # 更接近这一年真正占用的资源，计算周转率和权益乘数时更稳妥。
        return (begin + end) / 2.0
    if basis == "end":
        # 有些教材或快报只用期末数：计算更简单，但忽略了年内变化。
        return end
    raise ValueError(
        f"不支持的余额口径：{basis}。请使用 average（平均余额）或 end（期末余额）。"
    )


def compute_row_ratios(row, basis="average"):
    """根据一行原始数据，算出四个比率，并核对着乘积。

    这里返回一个普通字典，而不是再包一层类。
    对刚学会函数的读者来说，用名字取值（ratios["roe"]）比先理解对象更直观。
    """
    _check_basis(basis)

    assets = choose_balance(
        row["total_assets_begin"],
        row["total_assets_end"],
        basis,
    )
    equity = choose_balance(
        row["equity_begin"],
        row["equity_end"],
        basis,
    )

    # 分母在 loader 里已经要求大于 0。这里再防一层，
    # 是因为这个函数也可能被测试或其他代码单独调用。
    revenue = row["revenue"]
    net_profit = row["net_profit"]
    if revenue <= 0:
        raise ValueError("营业收入必须大于 0，才能计算净利率。")
    if assets <= 0:
        raise ValueError("总资产余额必须大于 0，才能计算总资产周转率。")
    if equity <= 0:
        raise ValueError("所有者权益余额必须大于 0，才能计算权益乘数和 ROE。")

    net_margin = net_profit / revenue
    asset_turnover = revenue / assets
    equity_multiplier = assets / equity
    # 直接用“净利润 / 权益”计算 ROE，不经过三个因子。
    # 后面会拿它和三因素乘积对照，用来发现公式是否写错。
    roe = net_profit / equity

    product, difference, matched = check_roe_identity(
        net_margin,
        asset_turnover,
        equity_multiplier,
        roe,
    )

    return {
        "year": row["year"],
        "revenue": revenue,
        "net_profit": net_profit,
        "assets": assets,
        "equity": equity,
        "basis": basis,
        "net_margin": net_margin,
        "asset_turnover": asset_turnover,
        "equity_multiplier": equity_multiplier,
        "roe": roe,
        "roe_from_factors": product,
        "roe_difference": difference,
        "roe_identity_ok": matched,
    }


def compute_all_ratios(frame, basis="average"):
    """对表格里的每一年分别计算比率，返回一个新的列表（每项是一行结果字典）。

    不用复杂的 pandas 链式写法，是为了让计算步骤可以一行一行跟下来。
    """
    _check_basis(basis)
    results = []
    for _, row in frame.iterrows():
        results.append(compute_row_ratios(row, basis=basis))
    return results


def check_roe_identity(
    net_margin,
    asset_turnover,
    equity_multiplier,
    roe,
    tolerance=DEFAULT_TOLERANCE,
):
    """检查 净利率 × 周转率 × 权益乘数 是否等于直接计算的 ROE。

    返回三个值：三因素乘积、乘积与直接 ROE 的差、是否在容差内。
    用绝对值判断差距，因为我们只关心“差了多少”，不关心谁比谁大。
    """
    product = net_margin * asset_turnover * equity_multiplier
    difference = product - roe
    matched = abs(difference) <= tolerance
    return product, difference, matched


def _check_basis(basis):
    if basis not in VALID_BASIS:
        raise ValueError(
            f"不支持的余额口径：{basis}。请使用 average（平均余额）或 end（期末余额）。"
        )
