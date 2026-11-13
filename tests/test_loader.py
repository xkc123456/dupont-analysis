"""检查输入不合法时，会给出清楚的中文错误，而不是算到一半再崩溃。"""

import pytest

from dupont.loader import load_company_csv


HEADER = (
    "year,revenue,net_profit,total_assets_begin,total_assets_end,"
    "equity_begin,equity_end\n"
)


def _write_csv(path, body, with_header=True):
    text = body
    if with_header:
        text = HEADER + body
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_column_raises_chinese_error(tmp_path):
    csv_path = tmp_path / "missing.csv"
    csv_path.write_text(
        "year,revenue,net_profit,total_assets_begin,total_assets_end,equity_begin\n"
        "2020,1000,80,800,900,400\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as info:
        load_company_csv(csv_path)

    message = str(info.value)
    assert "缺少必需列" in message
    assert "所有者权益期末" in message


def test_non_positive_denominator_raises_chinese_error(tmp_path):
    csv_path = _write_csv(tmp_path / "zero_revenue.csv", "2020,0,80,800,900,400,440\n")

    with pytest.raises(ValueError) as info:
        load_company_csv(csv_path)

    message = str(info.value)
    assert "2020 年" in message
    assert "营业收入" in message
    assert "不能用来做分母" in message


def test_negative_equity_raises_chinese_error(tmp_path):
    csv_path = _write_csv(tmp_path / "bad_equity.csv", "2020,1000,80,800,900,400,-10\n")

    with pytest.raises(ValueError) as info:
        load_company_csv(csv_path)

    message = str(info.value)
    assert "所有者权益期末" in message
    assert "不能用来做分母" in message


def test_valid_sample_like_csv_loads_and_sorts(tmp_path):
    csv_path = _write_csv(
        tmp_path / "ok.csv",
        "2021,1200,108,900,1100,440,500\n"
        "2020,1000,80,800,900,400,440\n",
    )
    frame = load_company_csv(csv_path)
    assert list(frame["year"]) == [2020, 2021]
    assert len(frame) == 2
