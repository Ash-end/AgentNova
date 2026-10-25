import re

SPECIAL = {"≈": r"\ensuremath{\approx}", "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
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
        elif line.startswith("#### "):
            out += [r"\subsubsection{" + escape(line[5:].replace("`", "")) + "}"]
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

