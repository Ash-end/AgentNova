"""指标验收契约测试：全部为人工构造数据，不含训练、文件读取或模型请求。"""

from copy import deepcopy
import math
import unittest

from exercises.verify_metrics import verify_metrics


class MetricsVerifierTests(unittest.TestCase):
    def assert_invalid(self, metrics):
        self.assertEqual(verify_metrics(metrics), {
            "status": "failed", "reason": "invalid_metrics",
        })

    def test_valid_numbers_include_zero_and_threshold_boundary_without_mutation(self):
        for value in (0, 0.04, 0.1):
            with self.subTest(value=value):
                metrics = {"mse": value, "note": "保留其他字段"}
                original = deepcopy(metrics)
                self.assertEqual(verify_metrics(metrics), {
                    "status": "passed", "reason": "verified_metrics", "mse": value,
                })
                self.assertEqual(metrics, original)

    def test_non_object_json_values_are_rejected(self):
        for value in (None, [], "metrics", 0):
            with self.subTest(value=value):
                self.assert_invalid(value)

    def test_missing_mse_is_rejected(self):
        self.assert_invalid({"accuracy": 0.99})

    def test_numeric_strings_and_null_are_rejected_without_coercion(self):
        for value in ("0.04", "", None):
            with self.subTest(value=value):
                self.assert_invalid({"mse": value})

    def test_booleans_are_rejected_even_though_bool_is_a_subclass_of_int(self):
        for value in (True, False):
            with self.subTest(value=value):
                self.assert_invalid({"mse": value})

    def test_nan_and_infinities_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                self.assert_invalid({"mse": value})

    def test_negative_mse_is_rejected(self):
        self.assert_invalid({"mse": -0.01})

    def test_valid_but_excessive_mse_fails_the_task_threshold(self):
        self.assertEqual(verify_metrics({"mse": 1.2}), {
            "status": "failed", "reason": "mse_above_threshold",
            "mse": 1.2, "max_mse": 0.1,
        })
        self.assertEqual(verify_metrics({"mse": 0.15}, max_mse=0.2), {
            "status": "passed", "reason": "verified_metrics", "mse": 0.15,
        })
        self.assertEqual(verify_metrics({"mse": 0.15}, max_mse=0.12), {
            "status": "failed", "reason": "mse_above_threshold",
            "mse": 0.15, "max_mse": 0.12,
        })


if __name__ == "__main__":
    unittest.main()
