"""scoring.py 单元测试（unittest 风格，可直接 `py tests/test_scoring.py` 运行）。"""

import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring import (  # noqa: E402
    normalize_value,
    column_signature,
    score_task,
    _read_csv,
    score_batch,
    aggregate,
)


class TestNormalize(unittest.TestCase):
    """归一化黄金向量（对齐社区对官方规则的复现）。"""

    def test_nulls(self):
        for v in [None, float("nan"), "", "   ", "nan", "null", "None", "n/a"]:
            self.assertEqual(normalize_value(v), "", f"{v!r} 应为空串")

    def test_floats(self):
        self.assertEqual(normalize_value(1.0), "1")
        self.assertEqual(normalize_value(1.50), "1.5")
        self.assertEqual(normalize_value(0.0), "0")
        self.assertEqual(normalize_value(2.675), "2.67")  # Python round(2.675,2) 语义，官方实现同样带入
        self.assertEqual(normalize_value(1000.0), "1000")

    def test_bool_int(self):
        self.assertEqual(normalize_value(True), "1")
        self.assertEqual(normalize_value(False), "0")
        self.assertEqual(normalize_value(42), "42")
        self.assertEqual(normalize_value(-7), "-7")

    def test_numeric_strings(self):
        self.assertEqual(normalize_value("42"), "42")
        self.assertEqual(normalize_value("1.0"), "1")
        self.assertEqual(normalize_value("1.50"), "1.5")
        self.assertEqual(normalize_value("0.000"), "0")
        self.assertEqual(normalize_value("1e3"), "1000")

    def test_dates(self):
        self.assertEqual(normalize_value("2024-01-05"), "2024-01-05")
        self.assertEqual(normalize_value("2024/1/5"), "2024-01-05")
        self.assertEqual(normalize_value("2024.12.31"), "2024-12-31")
        self.assertEqual(normalize_value("2024-1-5T23:59:59"), "2024-01-05")

    def test_text(self):
        self.assertEqual(normalize_value("  hello   world  "), "hello world")
        # 字符串形态的 True/False 不识别为 bool（仅 strip+折叠空白）
        self.assertEqual(normalize_value("True"), "True")


class TestScoreTask(unittest.TestCase):
    def _sig_row(self):
        return [["1"], ["2"]]

    def test_perfect(self):
        h, r = ["ID", "SEX"], [["1", "M"], ["2", "F"]]
        out = score_task(h, r, h, [list(x) for x in r])
        self.assertEqual(out["score"], 1.0)
        self.assertEqual(out["matched"], 2)

    def test_row_order_and_header_ignored(self):
        # 列名不同、行序打乱、列序打乱 → 仍满分
        pred_h = ["a", "b"]
        pred_r = [["F", "2"], ["M", "1"]]
        gold_h = ["sex", "id"]
        gold_r = [["1", "M"], ["2", "F"]]
        out = score_task(pred_h, pred_r, gold_h, gold_r)
        self.assertEqual(out["score"], 1.0)

    def test_extra_column_penalty(self):
        # pred A,B,C；gold B,C → recall=1，extra=1/3，score=1-0.5*1/3
        pred_h = ["A", "B", "C"]
        pred_r = [["x", "1", "a"], ["y", "2", "b"]]
        gold_h = ["B", "C"]
        gold_r = [["1", "a"], ["2", "b"]]
        out = score_task(pred_h, pred_r, gold_h, gold_r, lam=0.5)
        self.assertEqual(out["recall"], 1.0)
        self.assertEqual(out["extra"], 1)
        self.assertAlmostEqual(out["score"], 1 - 0.5 / 3, places=6)

    def test_missing_column_reduces_recall(self):
        pred_h = ["A"]
        pred_r = [["1"], ["2"]]
        gold_h = ["A", "B"]
        gold_r = [["1", "M"], ["2", "F"]]
        out = score_task(pred_h, pred_r, gold_h, gold_r)
        self.assertEqual(out["recall"], 0.5)
        self.assertEqual(out["score"], 0.5)

    def test_no_match_score_zero(self):
        pred_h = ["A"]
        pred_r = [["zzz"]]
        gold_h = ["B"]
        gold_r = [["yyy"]]
        self.assertEqual(score_task(pred_h, pred_r, gold_h, gold_r)["score"], 0.0)

    def test_negative_floor_at_zero(self):
        # 全错 + 一堆多余列 → recall=0 → max(0, …)=0
        pred_h = ["A", "B", "C"]
        pred_r = [["q", "r", "s"]]
        gold_h = ["G"]
        gold_r = [["gold"]]
        out = score_task(pred_h, pred_r, gold_h, gold_r)
        self.assertEqual(out["recall"], 0.0)
        self.assertEqual(out["score"], 0.0)

    def test_empty_pred(self):
        self.assertEqual(score_task(None, None, ["B"], [["1"]])["note"], "no prediction.csv")
        # 有表头无数据行
        out = score_task(["A"], [], ["B"], [["1"]])
        self.assertEqual(out["predicted_columns"], 1)
        self.assertEqual(out["recall"], 0.0)

    def test_empty_gold_rows(self):
        out = score_task(["A"], [["1"]], ["B"], [])
        self.assertEqual(out["note"], "empty gold rows")
        self.assertEqual(out["score"], 0.0)

    def test_value_format_equivalence(self):
        # "1.0" 与 "1"、日期不同写法都应匹配
        pred_h = ["X"]
        pred_r = [["1.0"], ["2024/1/5"]]
        gold_h = ["Y"]
        gold_r = [["1"], ["2024-01-05"]]
        self.assertEqual(score_task(pred_h, pred_r, gold_h, gold_r)["score"], 1.0)

    def test_duplicate_similar_columns_one_to_one(self):
        # 一对一匹配：pred 只有 1 个 (1,2) 签名列，gold 有 2 个同签名列 → matched=1
        # （若实现错误地按计数一抵多，会得到 matched=2 而误判满分）
        pred_h = ["A"]
        pred_r = [["1"], ["2"]]
        gold_h = ["X", "Y"]
        gold_r = [["1", "1"], ["2", "2"]]
        out = score_task(pred_h, pred_r, gold_h, gold_r)
        self.assertEqual(out["matched"], 1)
        self.assertEqual(out["recall"], 0.5)
        self.assertEqual(out["extra"], 0)
        self.assertEqual(out["score"], 0.5)


class TestCsvAndBatch(unittest.TestCase):
    def test_read_csv_padding(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.csv")
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write("a,b\n1\n")  # 第二行缺列
            header, rows = _read_csv(pathlib.Path(p))
            self.assertEqual(header, ["a", "b"])
            self.assertEqual(rows, [["1", ""]])

    def test_score_batch_and_aggregate(self):
        with tempfile.TemporaryDirectory() as td:
            gold_root = pathlib.Path(td) / "gold"
            pred_root = pathlib.Path(td) / "pred"
            for tid in ["task_11", "task_22"]:
                (gold_root / tid).mkdir(parents=True)
                (pred_root / tid).mkdir(parents=True)
            (gold_root / "task_11" / "gold.csv").write_text(
                "id,name\n1,a\n2,b\n", encoding="utf-8")
            (gold_root / "task_22" / "gold.csv").write_text(
                "v\nx\n", encoding="utf-8")
            (pred_root / "task_11" / "prediction.csv").write_text(
                "id,name\n1,a\n2,b\n", encoding="utf-8")  # 满分
            # task_22 未提交 → no prediction.csv
            tasks = score_batch(pred_root, gold_root)
            by = {t["task_id"]: t for t in tasks}
            self.assertEqual(by["task_11"]["score"], 1.0)
            self.assertEqual(by["task_22"]["note"], "no prediction.csv")
            agg = aggregate(tasks)
            self.assertEqual(agg["total"], 2)
            self.assertEqual(agg["submitted"], 1)
            self.assertAlmostEqual(agg["submitted_mean"], 1.0)
            self.assertAlmostEqual(agg["overall"]["mean"], 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
