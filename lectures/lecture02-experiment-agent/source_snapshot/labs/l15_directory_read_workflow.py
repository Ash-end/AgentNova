"""列目录、选择唯一文本文件、读取正文：固定 Python 流程，不请求模型。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from exercises.select_text_file import select_unique_text_file
from experiment_agent.tools.registry import build_tool_registry, call_tool


def run_directory_read_workflow(tools: dict, relative_directory: str) -> dict:
    """复用学习者的选择函数；选择失败就返回，不执行读取。"""
    directory_result = call_tool(
        tools, "list_directory", {"relative_path": relative_directory},
    )
    trace = [{"step": "list_directory", "result": directory_result}]

    selection = select_unique_text_file(directory_result)
    trace.append({"step": "select_unique_text_file", "result": selection})
    if selection["status"] != "success":
        return {"status": "failed", "result": selection, "trace": trace}

    read_result = call_tool(
        tools, "read_text_file", {"relative_path": selection["relative_path"]},
    )
    trace.append({"step": "read_text_file", "result": read_result})
    return {"status": read_result["status"], "result": read_result, "trace": trace}


def run_case(label, tools, relative_directory):
    result = run_directory_read_workflow(tools, relative_directory)
    print(f"\nCase: {label}")
    for event in result["trace"]:
        print(f"Step: {event['step']}")
        print(json.dumps(event["result"], ensure_ascii=False, indent=2))
    print(f"Workflow status: {result['status']}")
    if result["status"] == "success":
        print(f"Actual file content:\n{result['result']['content']}")
    else:
        print(f"Stopped because: {result['result']['error_type']}")
    return {"case": label, **result}


def main():
    root = Path(__file__).resolve().parents[1]
    print("Fixed Python workflow; no model API called.")
    print("Case 1 reads the project fixture; other cases use temporary files.")
    reports = [run_case("unique_text_file", build_tool_registry(str(root)), "labs/fixtures")]

    with TemporaryDirectory(prefix="directory-read-lesson-") as directory:
        demo_root = Path(directory)
        multiple = demo_root / "multiple"
        multiple.mkdir()
        (multiple / "a.txt").write_text("first", encoding="utf-8")
        (multiple / "b.txt").write_text("second", encoding="utf-8")
        invalid = demo_root / "invalid_utf8"
        invalid.mkdir()
        (invalid / "bad.txt").write_bytes(b"\xff\xfe")
        tools = build_tool_registry(str(demo_root))
        reports.append(run_case("multiple_text_files", tools, "multiple"))
        reports.append(run_case("invalid_utf8_file", tools, "invalid_utf8"))

    report_path = root / "reports" / "l15_directory_read_workflow.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"\nSaved report: {report_path}")


if __name__ == "__main__":
    main()
