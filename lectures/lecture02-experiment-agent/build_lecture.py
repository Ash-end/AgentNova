"""从公开脱敏固定快照生成讲义，不请求模型、不执行训练。"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from markdown_to_tex import md_to_tex


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOT = HERE / "source_snapshot"
GROUPS = ("docs", "lessons", "notes", "labs", "reports", "experiment_agent", "tests", "exercises", "experiments", "templates")
TOP = ("README.md", "PROGRESS.md", "SECURITY.md", "environment.yml", ".gitignore", ".gitattributes")


def redact(text):
    text = re.sub(r"(?i)([A-Z]:[\\/]+Users[\\/]+)[^\\/\s\"']+", r"\1USER", text)
    text = re.sub(r"(?i)[A-Z]:[\\/]+Users[\\/]+USER[\\/]+\.codex[\\/]+attachments[\\/]+[0-9a-f-]{36}[^\s\"<>]*", "<private-attachment>", text)
    return text


def snapshot(refresh=False):
    manifest_path = HERE / "manifest.json"
    if manifest_path.exists() and not refresh:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = []
    for group in GROUPS:
        candidates.extend((p.relative_to(ROOT).as_posix(), p) for p in (ROOT / group).rglob("*")
                          if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    candidates.extend(("gitattributes.snapshot.txt" if name == ".gitattributes" else name, ROOT / name)
                      for name in TOP if (ROOT / name).is_file())
    candidates.extend(("learner_evidence/" + p.name, p) for p in (HERE / "learner_evidence").glob("*") if p.is_file())
    # 只选汇总报告明确关联的 JSON 产物，不递归归档本机全部 runs。
    report = json.loads((ROOT / "reports/l21_real_linear_regression.json").read_text(encoding="utf-8"))
    for run in report["runs"]:
        folder = (ROOT / run["run_directory"]).resolve()
        if not folder.is_relative_to((ROOT / "runs").resolve()):
            raise ValueError("Run path outside expected runs directory")
        for name in ("config.json", "data.json", "model.json", "validation_predictions.json", "metrics.json"):
            path = folder / name
            if path.is_file():
                candidates.append((f"selected_runs/{run['run_id']}/{name}", path))
    records = []
    for relative, original in sorted(candidates):
        # 保留原换行字节，只对需公开脱敏的内容做替换。
        raw = redact(original.read_bytes().decode("utf-8-sig")).encode("utf-8")
        target = SNAPSHOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        records.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    data = {"snapshot_date": "2026-10-25", "source_root": "<project-root>",
            "edition": "public-redacted", "files": records}
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def appendices(manifest):
    out = ["\n## 附录 A. 第 17–27 课完整任务与原始教学细节\n",
           "以下保留归档时逐课全文，包括最初待办、失败过程及后续验收。正文已汇总最终状态；历史文字不应单独当成当前状态。\n"]
    for path in sorted((SNAPSHOT / "lessons").glob("*.md")):
        match = re.match(r"(\d+)-", path.name)
        if not match or not 17 <= int(match[1]) <= 27:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        out.append("\n### " + lines[0].removeprefix("# ") + "\n")
        for line in lines[1:]:
            out.append(("##" + line if line.startswith("## ") else line) + "\n")
    out.extend(["\n## 附录 B. 当前核心源码全文\n",
                "这些是固定快照中的真实实现；局部片段不能脱离函数层级直接粘贴。全部测试和其他实现见资料索引。\n"])
    sources = [
        "exercises/select_text_file.py", "labs/l15_directory_read_workflow.py",
        "experiment_agent/verification.py", "experiment_agent/tools/script_tools.py",
        "experiment_agent/tool_policy.py", "labs/l18_real_script_agent.py",
        "exercises/g1_agent_loop.py", "exercises/verify_metrics.py",
        "experiment_agent/metrics_workflow.py", "experiment_agent/experiment_workflow.py",
        "experiments/linear_regression/train.py", "labs/l21_real_linear_regression.py",
    ]
    for relative in sources:
        out.extend([f"\n### {relative}\n\n```python\n",
                    (SNAPSHOT / relative).read_text(encoding="utf-8").rstrip() + "\n```\n"])
    out.extend(["\n## 附录 C. 固定学习资料、证据和训练产物索引\n",
                f"本次固定保存 {len(manifest['files'])} 个文件。路径指向 source_snapshot；manifest.json 记录公开脱敏字节的 SHA-256，不随原项目后续变化。\n"])
    grouped = {}
    for item in manifest["files"]:
        group = item["path"].split("/")[0] if "/" in item["path"] else "项目入口与环境"
        grouped.setdefault(group, []).append(item)
    for group, items in sorted(grouped.items()):
        out.append(f"\n### {group}\n")
        for item in items:
            relative = item["path"]
            out.append(f"- [{relative}](source_snapshot/{relative})\n")
    out.extend(["\n## 附录 D. 学习者对话与终端证据摘录\n",
                "对话摘录由本次会话整理，不伪装成完整原始聊天导出。原始终端附件另列在资料索引；私人附件位置已移除。\n",
                (SNAPSHOT / "learner_evidence/study-dialogue.md").read_text(encoding="utf-8")])
    return "".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-snapshot", action="store_true")
    args = parser.parse_args()
    manifest = snapshot(args.refresh_snapshot)
    markdown = (HERE / "lecture_body.md").read_text(encoding="utf-8") + appendices(manifest)
    content = md_to_tex(markdown)
    (HERE / "lecture.md").write_text(markdown, encoding="utf-8")
    (HERE / "content.tex").write_text(content, encoding="utf-8")
    main_tex = (HERE / "main.tex").read_text(encoding="utf-8")
    (HERE / "lecture.tex").write_text(main_tex.replace(r"\input{content.tex}", content), encoding="utf-8")
    print(f"Snapshot files: {len(manifest['files'])}; Markdown characters: {len(markdown)}")


if __name__ == "__main__":
    main()
