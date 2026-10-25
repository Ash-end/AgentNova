"""固定可信教学脚本：演示产物来源关联，指标为常量，不执行训练。"""

import argparse
import json
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case", required=True, choices=[
        "normal", "missing_metrics", "wrong_run_id", "error", "timeout",
    ])
    args = parser.parse_args()
    if args.case == "missing_metrics":
        print("本次正常退出，但故意不生成 metrics.json；旧目录不应被读取。")
        return

    metrics = {
        "run_id": "previous_run" if args.case == "wrong_run_id" else args.run_id,
        "mse": 0.04,
    }
    Path("metrics.json").write_text(json.dumps(metrics, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"教学指标已写入本次目录，run_id={metrics['run_id']}", flush=True)
    if args.case == "error":
        raise RuntimeError("演示：虽有指标文件，但进程执行失败，不能验收通过。")
    if args.case == "timeout":
        time.sleep(10)


if __name__ == "__main__":
    main()
