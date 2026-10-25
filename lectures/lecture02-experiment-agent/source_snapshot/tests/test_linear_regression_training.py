"""真实 CPU 训练与独立产物复算；不固定断言某个恰好的测量小数。"""

import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiment_agent.experiment_workflow import TRAINING_SCRIPT, run_experiment_workflow
from experiments.linear_regression.train import fit_line, mse


class LinearRegressionTrainingTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="linear-regression-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "project"
        self.script = self.root / TRAINING_SCRIPT
        self.script.parent.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / TRAINING_SCRIPT
        shutil.copyfile(source, self.script)

    def train(self, case="linear_regression"):
        result = run_experiment_workflow(self.root, case)
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertFalse(result["execution"]["timed_out"])
        metrics = json.loads((self.root / result["metrics_path"]).read_text(encoding="utf-8"))
        self.assertEqual(metrics["run_id"], result["run_id"])
        self.assertEqual(result["trace"][-2]["result"]["reason"], "run_id_matched")
        return result, metrics

    def artifact(self, result, name):
        return json.loads((self.root / result["run_directory"] / name).read_text(encoding="utf-8"))

    def test_real_training_improves_and_fits_the_synthetic_relationship(self):
        result, metrics = self.train()
        self.assertEqual(result["status"], "passed")
        self.assertLess(metrics["train_mse"], metrics["initial_train_mse"])
        self.assertLess(metrics["mse"], metrics["initial_validation_mse"])
        self.assertLess(metrics["mse"], metrics["baseline_validation_mse"])
        self.assertAlmostEqual(metrics["model"]["weight"], 3.0, delta=0.1)
        self.assertAlmostEqual(metrics["model"]["bias"], 2.0, delta=0.1)
        self.assertGreaterEqual(metrics["training_seconds"], 0)
        self.assertTrue(math.isfinite(metrics["mse"]))

    def test_saved_data_and_model_independently_reproduce_reported_validation_mse(self):
        result, metrics = self.train()
        data = self.artifact(result, "data.json")
        model = self.artifact(result, "model.json")
        predictions = self.artifact(result, "validation_predictions.json")
        config = self.artifact(result, "config.json")
        squared_errors = []
        for row, prediction in zip(data["validation"], predictions):
            predicted = model["weight"] * row["x"] + model["bias"]
            squared_errors.append((predicted - row["y"]) ** 2)
            self.assertEqual(prediction, {"x": row["x"], "y_true": row["y"], "y_pred": predicted})
        self.assertEqual(len(predictions), config["validation_samples"])
        self.assertEqual(len(data["train"]), config["train_samples"])
        independent_mse = sum(squared_errors) / len(data["validation"])
        self.assertAlmostEqual(independent_mse, metrics["mse"], places=12)
        self.assertEqual(metrics["mse"], metrics["validation_mse"])
        self.assertEqual(config, metrics["config"])
        self.assertEqual(model, metrics["model"])
        self.assertEqual(hashlib.sha256(self.script.read_bytes()).hexdigest(), metrics["script_sha256"])

    def test_learning_rate_comparison_keeps_data_and_other_conditions_equal(self):
        fast_result, fast = self.train()
        slow_result, slow = self.train("linear_regression_slow")
        self.assertEqual(self.artifact(fast_result, "data.json"), self.artifact(slow_result, "data.json"))
        self.assertEqual(fast["data_split_id"], slow["data_split_id"])
        self.assertEqual(fast["script_sha256"], slow["script_sha256"])
        self.assertEqual(
            {k: v for k, v in fast["config"].items() if k != "learning_rate"},
            {k: v for k, v in slow["config"].items() if k != "learning_rate"},
        )
        self.assertEqual((fast["config"]["learning_rate"], slow["config"]["learning_rate"]), (0.1, 0.01))
        self.assertLess(fast["mse"], slow["mse"])

    def test_repeated_configuration_reproduces_results_in_a_new_run(self):
        first_result, first = self.train()
        first_path = self.root / first_result["metrics_path"]
        original = first_path.read_bytes()
        second_result, second = self.train()
        self.assertNotEqual(first_result["run_id"], second_result["run_id"])
        for field in ("mse", "train_mse", "model", "config", "data_split_id"):
            self.assertEqual(first[field], second[field])
        self.assertEqual(first_path.read_bytes(), original)

    def test_gradient_descent_fits_a_known_noiseless_line(self):
        train = [{"x": -1.0, "y": -1.0}, {"x": 0.0, "y": 1.0}, {"x": 1.0, "y": 3.0}]
        model = fit_line(train, learning_rate=0.1, steps=200)
        self.assertAlmostEqual(model["weight"], 2.0, places=9)
        self.assertAlmostEqual(model["bias"], 1.0, places=9)

    def test_mse_matches_an_independent_hand_calculated_example(self):
        # 预测为 [1, 2]，真值为 [1, 3]，均方误差为 (0 + 1) / 2。
        self.assertEqual(mse([{"x": 0, "y": 1}, {"x": 1, "y": 3}], weight=1, bias=1), 0.5)

    def test_underfit_execution_succeeds_but_threshold_fails_without_automatic_retry(self):
        with patch("experiment_agent.experiment_workflow.subprocess.run", wraps=subprocess.run) as launch:
            result, metrics = self.train("linear_regression_slow")
        launch.assert_called_once()
        self.assertGreater(metrics["mse"], 0.1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["reason"], "mse_above_threshold")
        self.assertEqual(result["result"]["mse"], metrics["mse"])


if __name__ == "__main__":
    unittest.main()
