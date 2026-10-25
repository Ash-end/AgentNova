"""CPU 合成数据线性回归：固定配置、全批量梯度下降、独立验证集。"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter


LEARNING_RATES = {"linear_regression": 0.1, "linear_regression_slow": 0.01}


def make_data(samples, seed, *, weight=3.0, bias=2.0, noise_std=0.1):
    rng = random.Random(seed)
    data = []
    for _ in range(samples):
        x = rng.uniform(-1.0, 1.0)
        y = weight * x + bias + rng.gauss(0.0, noise_std)
        data.append({"x": x, "y": y})
    return data


def mse(data, weight, bias):
    return math.fsum((weight * row["x"] + bias - row["y"]) ** 2 for row in data) / len(data)


def fit_line(train_data, learning_rate, steps):
    """只接收训练集；验证数据不参与梯度、早停或训练步数选择。"""
    weight, bias = 0.0, 0.0
    for _ in range(steps):
        errors = [weight * row["x"] + bias - row["y"] for row in train_data]
        grad_weight = 2.0 * math.fsum(error * row["x"] for error, row in zip(errors, train_data)) / len(train_data)
        grad_bias = 2.0 * math.fsum(errors) / len(train_data)
        weight -= learning_rate * grad_weight
        bias -= learning_rate * grad_bias
    return {"weight": weight, "bias": bias}


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def data_digest(data):
    content = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case", choices=list(LEARNING_RATES), required=True)
    args = parser.parse_args()
    config = {
        "learning_rate": LEARNING_RATES[args.case], "steps": 100,
        "train_samples": 128, "validation_samples": 64,
        "train_seed": 20261025, "validation_seed": 20261026,
        "target_weight": 3.0, "target_bias": 2.0, "noise_std": 0.1,
        "initial_weight": 0.0, "initial_bias": 0.0,
    }
    settings = {"weight": config["target_weight"], "bias": config["target_bias"], "noise_std": config["noise_std"]}
    train_data = make_data(config["train_samples"], config["train_seed"], **settings)
    validation_data = make_data(config["validation_samples"], config["validation_seed"], **settings)
    initial_train_mse = mse(train_data, 0.0, 0.0)
    initial_validation_mse = mse(validation_data, 0.0, 0.0)
    train_mean = math.fsum(row["y"] for row in train_data) / len(train_data)
    baseline_validation_mse = mse(validation_data, 0.0, train_mean)

    started = perf_counter()
    model = fit_line(train_data, config["learning_rate"], config["steps"])
    training_seconds = perf_counter() - started
    train_mse = mse(train_data, model["weight"], model["bias"])
    validation_mse = mse(validation_data, model["weight"], model["bias"])
    predictions = [{
        "x": row["x"], "y_true": row["y"],
        "y_pred": model["weight"] * row["x"] + model["bias"],
    } for row in validation_data]
    data = {"train": train_data, "validation": validation_data}
    metrics = {
        "run_id": args.run_id, "case": args.case, "task": "synthetic_linear_regression",
        "mse": validation_mse, "validation_mse": validation_mse, "train_mse": train_mse,
        "initial_train_mse": initial_train_mse, "initial_validation_mse": initial_validation_mse,
        "baseline_validation_mse": baseline_validation_mse,
        "training_seconds": training_seconds, "model": model, "config": config,
        "data_split_id": data_digest(data),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python_version": sys.version.split()[0],
        "artifacts": {"config": "config.json", "data": "data.json", "model": "model.json",
                      "validation_predictions": "validation_predictions.json"},
    }
    write_json("config.json", config)
    write_json("data.json", data)
    write_json("model.json", model)
    write_json("validation_predictions.json", predictions)
    # 最后写 metrics；所有产物仍在父进程创建的本次 cwd 中。
    write_json("metrics.json", metrics)
    print(f"Run ID: {args.run_id}")
    print(f"Learning rate: {config['learning_rate']}; full-batch steps: {config['steps']}")
    print(f"Initial train MSE: {initial_train_mse:.8f}; final train MSE: {train_mse:.8f}")
    print(f"Initial validation MSE: {initial_validation_mse:.8f}; final validation MSE: {validation_mse:.8f}")
    print(f"Learned weight: {model['weight']:.8f}; bias: {model['bias']:.8f}")


if __name__ == "__main__":
    main()
