"""使用已安装的 ReportLab 离线排版同一份 Markdown，作为 TeX 首次初始化的备用导出。"""

import html
import json
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, LongTable, PageBreak, PageTemplate, Paragraph, Spacer, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents


HERE = Path(__file__).resolve().parent
FONT = "LectureChinese"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/simhei.ttf"))
pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT, italic=FONT, boldItalic=FONT)
INK, ACCENT = colors.HexColor("#17324D"), colors.HexColor("#007F83")
WIDTH, HEIGHT = A4
MARGIN = 56
TEXT_WIDTH = WIDTH - 2 * MARGIN
STYLES = {
    "body": ParagraphStyle("Body", fontName=FONT, fontSize=10.2, leading=16.5, wordWrap="CJK", spaceAfter=6, textColor=INK),
    "h1": ParagraphStyle("H1", fontName=FONT, fontSize=16, leading=23, spaceBefore=15, spaceAfter=9, textColor=INK, keepWithNext=True),
    "h2": ParagraphStyle("H2", fontName=FONT, fontSize=12.5, leading=19, spaceBefore=11, spaceAfter=6, textColor=ACCENT, keepWithNext=True),
    "table": ParagraphStyle("Cell", fontName=FONT, fontSize=8.8, leading=13.5, wordWrap="CJK", textColor=INK),
    "tablehead": ParagraphStyle("CellHead", fontName=FONT, fontSize=9, leading=13.5, wordWrap="CJK", textColor=colors.white),
    "code": ParagraphStyle("Code", fontName=FONT, fontSize=8.1, leading=11.6, wordWrap="CJK", spaceBefore=5, spaceAfter=9,
                           backColor=colors.HexColor("#F2F5F7"), borderColor=colors.HexColor("#D6E3E8"), borderWidth=.4, borderPadding=7),
    "bullet": ParagraphStyle("Bullet", fontName=FONT, fontSize=10.2, leading=16.5, wordWrap="CJK", leftIndent=15, firstLineIndent=-12, spaceAfter=4, textColor=INK),
}


def inline(text):
    result = []
    for part in re.split(r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^\)]+\))", text):
        if part.startswith("`") and part.endswith("`"):
            result.append('<font color="#006C73">' + html.escape(part[1:-1]) + "</font>")
        elif part.startswith("**"):
            result.append("<b>" + html.escape(part[2:-2]) + "</b>")
        elif part.startswith("["):
            match = re.fullmatch(r"\[([^\]]+)\]\(([^\)]+)\)", part)
            label, target = match.groups()
            if target.startswith("http"):
                result.append('<a href="' + html.escape(target, quote=True) + '" color="#007F83">' + html.escape(label) + "</a>")
            else:
                result.append(html.escape(label))
        else:
            result.append(html.escape(part))
    return "".join(result)


def code_wrap(line):
    chunks, current = [], ""
    for char in line.expandtabs(4):
        if current and pdfmetrics.stringWidth(current + char, FONT, 8.1) > TEXT_WIDTH - 25:
            chunks.append(current)
            current = "    "
        current += char
    chunks.append(current)
    return chunks


class LectureDoc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=52, bottomMargin=48, title="Agent 学习讲义 01：从文件工具到双工具真实循环", author="Agent Study")
        frame = Frame(MARGIN, 48, TEXT_WIDTH, HEIGHT - 100, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="lecture", frames=[frame], onPage=self.decorate))
        self.heading_serial = 0

    def beforeDocument(self):
        self.heading_serial = 0

    def decorate(self, canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(INK)
        if doc.page > 1:
            canvas.drawString(MARGIN, HEIGHT - 29, "ExperimentAgent / Lecture 01")
            canvas.drawRightString(WIDTH - MARGIN, HEIGHT - 29, "2026-10-21")
            canvas.setStrokeColor(colors.HexColor("#D6E3E8"))
            canvas.line(MARGIN, HEIGHT - 36, WIDTH - MARGIN, HEIGHT - 36)
        canvas.drawCentredString(WIDTH / 2, 27, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in {"H1", "H2"}:
            text = flowable.getPlainText()
            level = 0 if flowable.style.name == "H1" else 1
            self.heading_serial += 1
            key = f"heading-{self.heading_serial}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))


def main():
    story = []
    cover_label = ParagraphStyle("CoverLabel", fontName=FONT, fontSize=12, leading=19, textColor=ACCENT)
    cover_title = ParagraphStyle("CoverTitle", fontName=FONT, fontSize=30, leading=41, textColor=INK, spaceAfter=12)
    cover_sub = ParagraphStyle("CoverSub", fontName=FONT, fontSize=18, leading=28, textColor=INK)
    story += [Spacer(1, 45), Paragraph("实验驱动学习 / 第一阶段复盘", cover_label), Spacer(1, 30),
              Paragraph("Agent 学习讲义 01", cover_title), Paragraph("从文件工具到双工具真实循环", cover_sub), Spacer(1, 25),
              Paragraph("概念、代码、实验、错题与复习路线", cover_label), Spacer(1, 28)]
    for text in ["学习日期：2026 年 10 月 21 日", "项目：ExperimentAgent（代码实验助手）", "环境：Windows / Anaconda / Python 3.11 / Ollama",
                 "范围：16 次小课、14 个实验、1 次独立功能修改", "归档：95 个原始学习文件及终端证据", "当前阶段：已跑通最小模型与工具闭环，G1 尚未整体验收"]:
        story.append(Paragraph(text, STYLES["body"]))
    story += [Spacer(1, 45), Paragraph("本讲是本项目阶段性复盘，不是 CS2680 官方讲义。实际运行、教学模拟、独立修改和后续规划分别标记。", STYLES["body"]), PageBreak()]
    toc_title = ParagraphStyle("TOCTitle", parent=STYLES["h1"])
    story.append(Paragraph("目录", toc_title))
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("TOC0", fontName=FONT, fontSize=10.2, leading=17, leftIndent=0, firstLineIndent=0, spaceBefore=5, textColor=INK),
                       ParagraphStyle("TOC1", fontName=FONT, fontSize=9, leading=14, leftIndent=16, firstLineIndent=0, textColor=INK)]
    story += [toc, PageBreak()]
    lines = (HERE / "lecture.md").read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("# "):
            i += 1
            continue
        if line.startswith("```"):
            chunks = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                chunks += code_wrap(lines[i])
                i += 1
            value = "<br/>".join(html.escape(x).replace(" ", "&#160;") if x else "&#160;" for x in chunks)
            story.append(Paragraph(value or "&#160;", STYLES["code"]))
        elif line.startswith("## "):
            if line.startswith("## 附录"):
                story.append(PageBreak())
            story.append(Paragraph(inline(line[3:]), STYLES["h1"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), STYLES["h2"]))
        elif line.startswith("| "):
            rows = []
            while i < len(lines) and lines[i].startswith("| "):
                cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+", x) for x in cells):
                    rows.append(cells)
                i += 1
            n = len(rows[0])
            ratios = {2: [.31, .69], 3: [.25, .36, .39], 4: [.19, .35, .17, .29]}.get(n, [1/n] * n)
            data = [[Paragraph(inline(x), STYLES["tablehead"] if r == 0 else STYLES["table"]) for x in row] for r, row in enumerate(rows)]
            table = LongTable(data, colWidths=[TEXT_WIDTH * x for x in ratios], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), INK), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F7")]),
                ("LINEBELOW", (0, 0), (-1, -1), .35, colors.HexColor("#D6E3E8")),
            ]))
            story += [table, Spacer(1, 9)]
            continue
        elif re.match(r"^(\d+\. |- )", line):
            story.append(Paragraph(inline(line), STYLES["bullet"]))
        else:
            story.append(Paragraph(inline(line), STYLES["body"]))
        i += 1

    destination = HERE / "lecture01-agent-foundations.pdf"
    doc = LectureDoc(destination)
    doc.multiBuild(story)
    (HERE / "pdf-build.json").write_text(json.dumps({
        "renderer": "ReportLab", "source": "lecture.md", "output": destination.name,
        "reason": "Offline fallback while the first TeX resource initialization is pending.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
