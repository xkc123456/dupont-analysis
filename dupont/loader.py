"""从 CSV 读入一家公司连续多年的财务报表关键数据，并做基本检查。

为什么要先检查再计算？
后面的除法会用到营业收入、总资产、所有者权益当分子或分母。
如果缺了一列，或分母是 0、负数，程序要么直接崩溃，要么算出没有意义的比率。
把检查集中在这里，错误可以提前用中文说清楚，也避免计算模块里到处写判断。
"""

from pathlib import Path

import pandas as pd


# 程序按这些英文列名取值。名称固定下来后，示例文件、README 和代码就都对得上了。
REQUIRED_COLUMNS = [
    "year",
    "revenue",
    "net_profit",
    "total_assets_begin",
    "total_assets_end",
    "equity_begin",
    "equity_end",
]

# 报错时改用中文列名，读消息的人不必先去记英文单词。
COLUMN_LABELS = {
    "year": "年份",
    "revenue": "营业收入",
    "net_profit": "净利润",
    "total_assets_begin": "总资产期初",
    "total_assets_end": "总资产期末",
    "equity_begin": "所有者权益期初",
    "equity_end": "所有者权益期末",
}

# 这些列要当除数，或要拿来算平均余额，因此必须大于 0。
# 净利润可以是负数（亏损），所以不放在这里。
POSITIVE_COLUMNS = [
    "revenue",
    "total_assets_begin",
    "total_assets_end",
    "equity_begin",
    "equity_end",
]


def load_company_csv(csv_path):
    """读入 CSV，返回按年份排好序的表格。

    以 # 开头的行会当作注释跳过，这样示例文件可以在表头上方写说明。
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"找不到数据文件：{path}。请确认路径是否写对，文件是否还在。"
        )

    # comment="#" 会忽略以 # 开头的行；encoding 写成 utf-8，避免中文注释读乱码。
    frame = pd.read_csv(path, comment="#", encoding="utf-8")
    frame = _normalize_column_names(frame)
    _check_required_columns(frame)
    _check_values(frame)

    # 后面按相邻年份做连环替代，必须先按年份从小到大排好。
    frame = frame.sort_values("year").reset_index(drop=True)
    return frame


def _normalize_column_names(frame):
    """去掉列名前后空格，避免 'revenue ' 这种不易发现的笔误导致“缺列”。"""
    renamed = {}
    for column in frame.columns:
        renamed[column] = str(column).strip()
    return frame.rename(columns=renamed)


def _check_required_columns(frame):
    missing = []
    for column in REQUIRED_COLUMNS:
        if column not in frame.columns:
            missing.append(column)

    if missing:
        labels = []
        for column in missing:
            labels.append(COLUMN_LABELS.get(column, column))
        # 用顿号把缺失列拼成一句人话，比直接打印英文列表更易读。
        joined = "、".join(labels)
        raise ValueError(
            "CSV 里缺少必需列："
            + joined
            + "。请对照 README 或示例文件 data/sample_company.csv，"
            "检查表头是否写错、是否漏列。"
        )


def _check_values(frame):
    if frame.empty:
        raise ValueError("CSV 里没有数据行。请至少提供一年的数据后再运行。")

    # 年份重复时，无法判断该用哪一行去和下一年比较，所以直接拒绝。
    duplicated_years = frame[frame["year"].duplicated(keep=False)]["year"]
    if len(duplicated_years) > 0:
        year_text = "、".join(str(int(year)) for year in sorted(set(duplicated_years)))
        raise ValueError(
            f"年份重复了：{year_text}。每个年份只能有一行，请删掉重复行后再运行。"
        )

    for row_number, row in frame.iterrows():
        year_text = _year_text(row["year"])
        for column in REQUIRED_COLUMNS:
            value = row[column]
            if pd.isna(value):
                label = COLUMN_LABELS[column]
                raise ValueError(
                    f"{year_text}的「{label}」是空值，缺少计算所需数据。"
                    "请补全后再运行。"
                )

        for column in POSITIVE_COLUMNS:
            value = row[column]
            if value <= 0:
                label = COLUMN_LABELS[column]
                raise ValueError(
                    f"{year_text}的「{label}」是 {value}，不能用来做分母。"
                    "净利率、总资产周转率、权益乘数和 ROE 的分母必须大于 0"
                    "（营业收入、总资产、所有者权益）。请检查是否填错或漏填。"
                )


def _year_text(year):
    """把年份格式化成报错里用的文字。年份缺失时不能强行转成整数。"""
    if pd.isna(year):
        return "有一行"
    try:
        return f"{int(year)} 年"
    except (TypeError, ValueError):
        return f"年份 {year} "
