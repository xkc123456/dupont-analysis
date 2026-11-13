"""把计算结果写成 CSV，并画出 ROE 与三个因子的趋势图。

CSV 使用 utf-8-sig（带 BOM 的 UTF-8）。
Excel 在 Windows 上打开普通 utf-8 时，有时会把中文列名显示成乱码；
加上 BOM 后，Excel 更容易识别编码。

画图时先指定 Agg 后端。Agg 不需要弹出窗口，适合在服务器或脚本里直接保存 PNG。
"""

from pathlib import Path

# 必须在 import pyplot 之前指定后端，否则可能已经选了需要屏幕的后端。
import matplotlib

matplotlib.use("Agg")

from matplotlib import font_manager
from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd


# 系统里常见的中文字体路径。找到第一个存在的即可。
CJK_FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]

CJK_FONT_NAME_KEYWORDS = [
    "Noto Sans CJK SC",
    "Noto Serif CJK SC",
    "Noto Sans CJK",
    "Source Han Sans",
    "WenQuanYi",
    "SimHei",
    "Microsoft YaHei",
    "PingFang",
    "Droid Sans Fallback",
]

BASIS_LABELS_ZH = {
    "average": "平均余额",
    "end": "期末余额",
}

BASIS_LABELS_EN = {
    "average": "average balance",
    "end": "end-of-period balance",
}


def write_ratios_csv(ratio_rows, output_path):
    """把比率结果写成便于用 Excel 打开的中文表。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for row in ratio_rows:
        records.append(
            {
                "年份": _as_year(row["year"]),
                "营业收入": row["revenue"],
                "净利润": row["net_profit"],
                "资产余额": row["assets"],
                "权益余额": row["equity"],
                "余额口径": BASIS_LABELS_ZH.get(row["basis"], row["basis"]),
                "净利率": row["net_margin"],
                "总资产周转率": row["asset_turnover"],
                "权益乘数": row["equity_multiplier"],
                "直接计算ROE": row["roe"],
                "三因素乘积ROE": row["roe_from_factors"],
                "乘积与直接ROE的差": row["roe_difference"],
                "差异是否在容差内": _bool_text(row["roe_identity_ok"]),
            }
        )

    frame = pd.DataFrame(records)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def write_decomposition_csv(decomp_rows, output_path):
    """把连环替代结果写成中文表。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for row in decomp_rows:
        records.append(
            {
                "基期年份": _as_year(row["base_year"]),
                "本期年份": _as_year(row["current_year"]),
                "基期ROE": row["base_roe"],
                "本期ROE": row["current_roe"],
                "ROE变动": row["roe_change"],
                "净利率贡献": row["contrib_net_margin"],
                "总资产周转率贡献": row["contrib_asset_turnover"],
                "权益乘数贡献": row["contrib_equity_multiplier"],
                "贡献合计": row["contribution_sum"],
                "合计是否等于变动": _bool_text(row["sum_matches_change"]),
            }
        )

    frame = pd.DataFrame(records)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def find_cjk_font():
    """寻找本机可用的中文字体，找不到就返回 None，由画图函数改用英文标签。

    为什么要自己找，而不是假定系统一定有中文字体？
    matplotlib 默认字体通常不含汉字。如果强行写中文，图上会变成方框，
    有些环境甚至会在缺字体时报错。先探测、再决定用中文还是英文，图才画得出来。
    """
    for font_path in CJK_FONT_PATHS:
        if Path(font_path).is_file():
            return font_path

    # 再在 matplotlib 已经扫描到的字体里按名字找一遍，覆盖用户自己安装的字体。
    for font in font_manager.fontManager.ttflist:
        name = font.name
        for keyword in CJK_FONT_NAME_KEYWORDS:
            if keyword.lower() in name.lower():
                return font.fname
    return None


def plot_trends(ratio_rows, output_path, basis="average"):
    """画出 ROE 和三个因子的趋势图，保存为 PNG。

    四个指标数量级不同（净利率、ROE 多在 0 到 1 之间，周转率和乘数通常更大），
    所以分成四个小图，各自用自己的纵轴，避免挤在一张图里看不清。
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    years = []
    net_margins = []
    turnovers = []
    multipliers = []
    roes = []
    for row in ratio_rows:
        years.append(_as_year(row["year"]))
        net_margins.append(row["net_margin"])
        turnovers.append(row["asset_turnover"])
        multipliers.append(row["equity_multiplier"])
        roes.append(row["roe"])

    font_path = find_cjk_font()
    use_chinese = font_path is not None
    font_prop = None
    if use_chinese:
        font_prop = FontProperties(fname=font_path)
        # 负号默认可能显示成方块，关掉这个替换，坐标轴的减号才能正常显示。
        plt.rcParams["axes.unicode_minus"] = False

    if use_chinese:
        title = "示例公司杜邦分析趋势图（示例数据，非真实公司）"
        footnote = (
            "数据为虚构教学示例，不代表任何真实公司。"
            "余额口径：" + BASIS_LABELS_ZH.get(basis, basis) + "。"
        )
        labels = {
            "roe": "净资产收益率（ROE）",
            "net_margin": "净利率",
            "asset_turnover": "总资产周转率",
            "equity_multiplier": "权益乘数",
            "year": "年份",
        }
    else:
        # 找不到中文字体时改用英文，避免程序崩溃或汉字变成方框。
        title = "DuPont trend chart (sample / fabricated data, not a real company)"
        footnote = (
            "Figures are fabricated for teaching. Balance basis: "
            + BASIS_LABELS_EN.get(basis, basis)
            + "."
        )
        labels = {
            "roe": "ROE",
            "net_margin": "Net profit margin",
            "asset_turnover": "Asset turnover",
            "equity_multiplier": "Equity multiplier",
            "year": "Year",
        }

    figure, axes = plt.subplots(2, 2, figsize=(10, 8))
    series_list = [
        (axes[0, 0], roes, labels["roe"], "#1f4e79"),
        (axes[0, 1], net_margins, labels["net_margin"], "#2e7d32"),
        (axes[1, 0], turnovers, labels["asset_turnover"], "#ef6c00"),
        (axes[1, 1], multipliers, labels["equity_multiplier"], "#6a1b9a"),
    ]

    for axis, values, ylabel, color in series_list:
        axis.plot(years, values, marker="o", color=color, linewidth=2)
        axis.set_xlabel(labels["year"], fontproperties=font_prop)
        axis.set_ylabel(ylabel, fontproperties=font_prop)
        axis.set_title(ylabel, fontproperties=font_prop)
        axis.grid(True, linestyle="--", alpha=0.4)
        axis.set_xticks(years)

    figure.suptitle(title, fontsize=14, fontproperties=font_prop)
    # 给底部脚注留一点空间，避免和横轴标签挤在一起。
    figure.tight_layout(rect=[0, 0.06, 1, 0.95])
    figure.text(0.5, 0.02, footnote, ha="center", va="bottom", fontsize=9, fontproperties=font_prop)
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def _as_year(value):
    """年份在 CSV 里常被读成 2020.0，写成整数更易读。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _bool_text(flag):
    if flag:
        return "是"
    return "否"
