"""三个稳定案例：确定性模型替身、真实临时文件工具、独立读取证据验收。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from experiment_agent.ollama_loop import run_ollama_loop
from experiment_agent.tools.registry import build_tool_registry
from experiment_agent.verification import verify_unique_text_read


def tool_reply(name, path):
    return {"done": True, "done_reason": "stop", "message": {
        "role": "assistant", "content": "", "tool_calls": [{"function": {
            "name": name, "arguments": {"relative_path": path},
        }}],
    }}


def final_reply(content):
    return {"done": True, "done_reason": "stop", "message": {
        "role": "assistant", "content": content,
    }}


def run_cases(root):
    """root 是已准备 data/hello.txt 与 other/other.txt 的临时项目。"""
    cases = {
        "correct_completion": [
            tool_reply("list_directory", "data"),
            tool_reply("read_text_file", "data/hello.txt"),
            final_reply("文件内容：\n你好，验收器！\n"),
        ],
        "claimed_without_reading": [
            tool_reply("list_directory", "data"),
            final_reply("我已成功读取 data/hello.txt。"),
        ],
        "wrong_file_read": [
            tool_reply("list_directory", "data"),
            tool_reply("read_text_file", "other/other.txt"),
            final_reply("已读取文件，任务完成。"),
        ],
    }
    results = []
    for label, replies in cases.items():
        responses = iter(replies)

        def chat(messages, descriptions):
            return next(responses)

        run = run_ollama_loop(
            "先查看 data 目录，找到唯一的普通 .txt 文件并读取其正文。",
            chat, build_tool_registry(str(root)), [], max_steps=4,
        )
        verification = verify_unique_text_read(run, "data")
        results.append({"case": label, "source": "deterministic_chat_real_file_tools",
                        "run": run, "verification": verification})
    return results


def main():
    project_root = Path(__file__).resolve().parents[1]
    print("Deterministic assistant responses; real temporary file tools; no model API called.")
    print("Verifier reads recorded evidence only; it does not rerun tools.")
    with TemporaryDirectory(prefix="task-verifier-lesson-") as directory:
        root = Path(directory)
        (root / "data").mkdir()
        (root / "other").mkdir()
        (root / "data/hello.txt").write_text("你好，验收器！\n", encoding="utf-8")
        (root / "other/other.txt").write_text("这是另一个文件。\n", encoding="utf-8")
        results = run_cases(root)
    for case in results:
        run = case["run"]
        print(f"\nCase: {case['case']}")
        print(f"Loop status: {run['status']}")
        print(f"Executed tools: {[m['tool_name'] for m in run['messages'] if m['role'] == 'tool']}")
        print(f"Model claim: {run.get('answer', '')}")
        print("Verification:")
        print(json.dumps(case["verification"], ensure_ascii=False, indent=2))
    path = project_root / "reports/l16_agent_task_verifier.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved report: {path}")


if __name__ == "__main__":
    main()
