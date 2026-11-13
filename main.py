"""杜邦分析自动化工具的入口。

从这里开始运行：读取 CSV，计算比率，做连环替代分解，再写出表格和趋势图。
具体计算分别放在 dupont 包的几个模块里，本文件只负责把步骤串起来，
并处理命令行参数（比如用平均余额还是期末余额）。
"""

import argparse
import sys
from pathlib import Path

from dupont.decompose import decompose_all
from dupont.loader import load_company_csv
from dupont.ratios import DEFAULT_TOLERANCE, compute_all_ratios
from dupont.report import plot_trends, write_decomposition_csv, write_ratios_csv


def build_parser():
    """准备命令行参数说明。把这段单独写成函数，是为了让测试也可以拿到同一套参数定义。"""
    parser = argparse.ArgumentParser(
        description=(
            "杜邦分析自动化工具：从 CSV 计算净利率、总资产周转率、"
            "权益乘数和 ROE，并用连环替代法分解相邻年份的 ROE 变动。"
        )
    )
    parser.add_argument(
        "--input",
        default="data/sample_company.csv",
        help="输入 CSV 路径。默认使用附带的示例数据。",
    )
    parser.add_argument(
        "--basis",
        choices=["average", "end"],
        default="average",
        help="资产和权益的余额口径：average 为平均余额（默认），end 为期末余额。",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录。将写入比率表、分解表和趋势图。",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help="核对三因素乘积、以及贡献合计时允许的误差，默认 1e-8。",
    )
    return parser


def run(input_path, basis, output_dir, tolerance=DEFAULT_TOLERANCE):
    """执行完整流程，并返回写出的文件路径，方便测试或调用方检查。"""
    frame = load_company_csv(input_path)
    ratio_rows = compute_all_ratios(frame, basis=basis)
    decomp_rows = decompose_all(ratio_rows, tolerance=tolerance)

    output_dir = Path(output_dir)
    ratios_path = output_dir / "dupont_ratios.csv"
    decomp_path = output_dir / "dupont_decomposition.csv"
    chart_path = output_dir / "dupont_trends.png"

    write_ratios_csv(ratio_rows, ratios_path)
    write_decomposition_csv(decomp_rows, decomp_path)
    plot_trends(ratio_rows, chart_path, basis=basis)

    return {
        "ratio_rows": ratio_rows,
        "decomp_rows": decomp_rows,
        "ratios_path": ratios_path,
        "decomp_path": decomp_path,
        "chart_path": chart_path,
    }


def print_summary(result, basis):
    """在终端用中文简要汇报结果，不必再打开文件也能知道有没有算对。"""
    if basis == "average":
        basis_text = "平均余额"
    else:
        basis_text = "期末余额"

    print(f"余额口径：{basis_text}")
    print("各年比率：")
    for row in result["ratio_rows"]:
        year = int(row["year"])
        identity = "通过" if row["roe_identity_ok"] else "未通过"
        print(
            f"  {year} 年  净利率={row['net_margin']:.4f}  "
            f"周转率={row['asset_turnover']:.4f}  "
            f"权益乘数={row['equity_multiplier']:.4f}  "
            f"ROE={row['roe']:.4f}  三因素恒等式：{identity}"
        )

    if not result["decomp_rows"]:
        print("只有一年数据，没有相邻年度可以做连环替代分解。")
    else:
        print("连环替代分解（替代顺序：净利率 → 总资产周转率 → 权益乘数）：")
        for row in result["decomp_rows"]:
            match = "通过" if row["sum_matches_change"] else "未通过"
            print(
                f"  {int(row['base_year'])} → {int(row['current_year'])}  "
                f"ROE变动={row['roe_change']:.4f}  "
                f"净利率贡献={row['contrib_net_margin']:.4f}  "
                f"周转率贡献={row['contrib_asset_turnover']:.4f}  "
                f"权益乘数贡献={row['contrib_equity_multiplier']:.4f}  "
                f"贡献合计核对：{match}"
            )

    print("已写出：")
    print(f"  {result['ratios_path']}")
    print(f"  {result['decomp_path']}")
    print(f"  {result['chart_path']}")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(
            input_path=args.input,
            basis=args.basis,
            output_dir=args.output_dir,
            tolerance=args.tolerance,
        )
    except (FileNotFoundError, ValueError) as error:
        # 数据问题用友好中文提示后结束，不必再打印一长串英文报错栈。
        print("运行失败：" + str(error), file=sys.stderr)
        return 1

    print_summary(result, args.basis)
    return 0


if __name__ == "__main__":
    # 只有直接运行 python main.py 时才会走进这里；
    # 被测试 import 时不会自动执行，避免测试时误写出文件。
    sys.exit(main())
