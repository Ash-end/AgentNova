"""从固定资料快照生成 Markdown、LaTeX 正文与索引；不执行 Agent 或模型请求。"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOT = HERE / "source_snapshot"
SOURCE_GROUPS = ["docs", "lessons", "notes", "labs", "reports", "experiment_agent", "tests", "exercises", "templates"]
TOP_FILES = ["README.md", "PROGRESS.md", "environment.yml", ".gitignore"]
EVIDENCE = {
    name: HERE / "learner_evidence_inbox" / name
    for name in ("learner_l11_output.txt", "learner_l12_output.txt", "learner_l14_output.txt")
}


def create_snapshot():
    manifest_path = HERE / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = []
    for folder in SOURCE_GROUPS:
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                candidates.append((path.relative_to(ROOT).as_posix(), path))
    candidates += [(name, ROOT / name) for name in TOP_FILES if (ROOT / name).is_file()]
    candidates += [("learner_evidence/" + name, Path(path)) for name, path in EVIDENCE.items() if Path(path).is_file()]
    records = []
    for relative, original in sorted(candidates):
        raw = original.read_bytes()
        destination = SNAPSHOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        records.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    data = {"snapshot_created_local": datetime.now().isoformat(timespec="seconds"),
            "source_root": "<project-root>", "files": records}
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def first_heading(path):
    if path.suffix == ".md":
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return ""


def appendices(manifest):
    out = ["\n## 附录 A. 全部学习资料索引与快照\n"]
    out += [f"本次固定保存 {len(manifest['files'])} 个原始文件。下列链接指向讲义目录内 source_snapshot，不随原项目后续编辑而变化。manifest.json 记录字节数和 SHA-256；它保证归档内容可核对，不证明课程已全部掌握。\n"]
    labels = {"docs": "学习规划与资料", "lessons": "逐次讲义", "notes": "运行与反馈记录", "labs": "运行实验与夹具",
              "reports": "完整 JSON 运行报告", "experiment_agent": "Agent 实现与参数 Schema", "tests": "项目测试", "exercises": "独立练习验收",
              "templates": "学习与实验记录模板", "learner_evidence": "学习者原始终端附件", "top": "项目入口与环境"}
    groups = {group: [] for group in ["top", *SOURCE_GROUPS, "learner_evidence"]}
    for record in manifest["files"]:
        group = record["path"].split("/")[0] if "/" in record["path"] else "top"
        groups[group].append(record)
    for group, records in groups.items():
        out += [f"\n### {labels[group]}\n"]
        for record in records:
            relative = record["path"]
            title = first_heading(SNAPSHOT / relative)
            suffix = f"：{title}" if title else ""
            out += [f"- [{relative}](source_snapshot/{relative}){suffix}\n"]

    out += ["\n## 附录 B. 关键源码：按调用链复习\n",
            "以下摘录是本次归档时的真实源码，不是额外实现的新版本。完整实验与测试见附录 A。\n"]
    sources = [
        ("文件读取工具", "experiment_agent/tools/file_tools.py"),
        ("目录工具", "experiment_agent/tools/directory_tools.py"),
        ("注册、参数校验与异常转换", "experiment_agent/tools/registry.py"),
        ("策略函数", "experiment_agent/tool_policy.py"),
        ("原生消息自动循环", "experiment_agent/ollama_loop.py"),
        ("内部 mock 协议循环，作为对照", "experiment_agent/loop.py"),
        ("读取工具 Schema", "experiment_agent/tools/read_text_file.schema.json"),
        ("目录工具 Schema", "experiment_agent/tools/list_directory.schema.json"),
    ]
    for title, relative in sources:
        language = "json" if relative.endswith(".json") else "python"
        out += [f"\n### {title}\n\n来源：`{relative}`。\n\n```{language}\n",
                (SNAPSHOT / relative).read_text(encoding="utf-8").rstrip() + "\n```\n"]

    out += ["\n## 附录 C. 当前报告快照清单\n",
            "同名报告代表快照时的最近保存结果，不一定是首次运行。上文已将关键结果的学习者/AI 来源分别注明。原始 JSON 保留模型响应、消息历史或实验案例；需要精确核对时打开原文件。\n",
            "\n| 报告 | 结构与用途 | 时长或案例数 |\n| --- | --- | --- |\n"]
    for path in sorted((SNAPSHOT / "reports").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            description, metric = "预设请求/异常演示的逐案例结果", f"{len(data)} 个案例"
        else:
            status = data.get("result", {}).get("status")
            response = data.get("response", {})
            description = f"循环终态 {status}" if status else f"模型响应 done={response.get('done', '未记录')}"
            elapsed = data.get("elapsed_seconds")
            metric = f"{elapsed:.3f} 秒" if isinstance(elapsed, (int, float)) else "见原始字段"
        out += [f"| `{path.name}` | {description} | {metric} |\n"]

    out += ["\n## 附录 D. K01–K27 知识域定位\n",
            "此处只标记本阶段覆盖程度；详细内容和未来验收标准见源文件 docs/02-knowledge-map.md。局部接触不代表整域完成。\n",
            "\n| 编号 | 知识域 | 本阶段定位 |\n| --- | --- | --- |\n"]
    touched = {"K01": "基础闭环已学习，独立完整实现待验收", "K02": "接触生成参数与接口，模型原理未系统复习",
               "K03": "本地聊天、原生工具消息已独立运行", "K04": "工具说明与消息历史局部接触",
               "K05": "工具契约已运行，超时分支独立修改", "K06": "循环、停止、修正预算已实践；恢复/幂等未做",
               "K14": "已有单元测试与简单轨迹核对；独立任务评测未做", "K15": "已区分冷/热观测；尚无受控优化实验",
               "K16": "保存 JSON 报告与错误；完整追踪系统未做", "K17": "已有路径边界；更完整权限和注入实验未做",
               "K20": "专用环境与模块运行已完成；产品化未做", "K21": "接触调用次数与时间，经济性实验未做",
               "K23": "观察加载与缓存指标；系统服务实验未做", "K27": "选定代码实验 Agent，尚未执行训练任务"}
    matrix = (SNAPSHOT / "docs/02-knowledge-map.md").read_text(encoding="utf-8")
    for line in matrix.splitlines():
        if re.match(r"\| K\d+ \|", line):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            out += [f"| {cells[0]} | {cells[1]} | {touched.get(cells[0], '后续学习，尚未验收')} |\n"]
    return "".join(out)


SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
           "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def escape(text):
    return "".join(SPECIAL.get(char, char) for char in text)


def inline(text):
    pattern = r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^\)]+\))"
    parts = re.split(pattern, text)
    output = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            value = part[1:-1]
            if ("/" in value or "_" in value) and "{" not in value and "}" not in value:
                output.append(r"\nolinkurl{" + value + "}")
            else:
                output.append(r"\code{" + value + "}")
        elif part.startswith("**"):
            output.append(r"\textbf{" + escape(part[2:-2]) + "}")
        elif part.startswith("["):
            match = re.fullmatch(r"\[([^\]]+)\]\(([^\)]+)\)", part)
            label, target = match.groups()
            if target.startswith("https://") or target.startswith("http://"):
                output.append(r"\href{" + escape(target) + "}{" + escape(label) + "}")
            else:
                output.append(r"\nolinkurl{" + label + "}")
        else:
            # 普通正文与表格里的工具/实验名也允许在下划线处换行。
            for chunk in re.split(r"([A-Za-z_][A-Za-z0-9_]*_[A-Za-z0-9_]+)", part):
                if "_" in chunk and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]+", chunk):
                    output.append(r"\nolinkurl{" + chunk + "}")
                else:
                    output.append(escape(chunk))
    return "".join(output)


def md_to_tex(markdown):
    lines = markdown.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            i += 1
            continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            if i == len(lines):
                raise ValueError("Unclosed code block")
            out += [r"\begin{Code}", *code, r"\end{Code}"]
        elif line.startswith("## "):
            title = line[3:]
            title = re.sub(r"^\d+\.\s*", "", title)
            out += [r"\section{" + escape(title.replace("`", "")) + "}"]
        elif line.startswith("### "):
            title = re.sub(r"^\d+\.\d+\s*", "", line[4:])
            out += [r"\subsection{" + escape(title.replace("`", "")) + "}"]
        elif line.startswith("| "):
            rows = []
            while i < len(lines) and lines[i].startswith("| "):
                cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+", cell) for cell in cells):
                    rows.append(cells)
                i += 1
            count = len(rows[0])
            widths = {2: [.28, .63], 3: [.23, .33, .33], 4: [.18, .29, .16, .22]}.get(count, [.85/count] * count)
            columns = "".join(r">{\raggedright\arraybackslash}p{" + str(width) + r"\linewidth}" for width in widths)
            out += [r"{\small\setlength{\tabcolsep}{4pt}", r"\renewcommand{\arraystretch}{1.25}", r"\begin{longtable}{" + columns + "}", r"\toprule"]
            header = " & ".join(r"\textbf{" + inline(cell) + "}" for cell in rows[0]) + r" \\"
            out += [header, r"\midrule\endfirsthead", r"\toprule", header, r"\midrule\endhead",
                    r"\bottomrule\endfoot"]
            for row in rows[1:]:
                out += [" & ".join(inline(cell) for cell in row) + r" \\"]
            out += [r"\end{longtable}}"]
            continue
        elif re.match(r"^(\d+\. |- )", line):
            ordered = bool(re.match(r"^\d+\. ", line))
            env = "enumerate" if ordered else "itemize"
            out += [r"\begin{" + env + "}"]
            while i < len(lines) and (bool(re.match(r"^\d+\. ", lines[i])) if ordered else lines[i].startswith("- ")):
                text = re.sub(r"^\d+\. ", "", lines[i]) if ordered else lines[i][2:]
                out += [r"\item " + inline(text)]
                i += 1
            out += [r"\end{" + env + "}"]
            continue
        elif not line.strip():
            out += [""]
        else:
            out += [inline(line)]
        i += 1
    return "\n".join(out) + "\n"


def main():
    manifest = create_snapshot()
    markdown = (HERE / "lecture_body.md").read_text(encoding="utf-8") + appendices(manifest)
    (HERE / "lecture.md").write_text(markdown, encoding="utf-8")
    (HERE / "content.tex").write_text(md_to_tex(markdown), encoding="utf-8")
    main_source = (HERE / "main.tex").read_text(encoding="utf-8")
    (HERE / "lecture.tex").write_text(
        main_source.replace(r"\input{content.tex}", md_to_tex(markdown)), encoding="utf-8"
    )
    print(f"Snapshot files: {len(manifest['files'])}")
    print(f"Markdown characters: {len(markdown)}")
    print("Generated lecture.md, content.tex and standalone lecture.tex; main.tex is the project entry.")


if __name__ == "__main__":
    main()
