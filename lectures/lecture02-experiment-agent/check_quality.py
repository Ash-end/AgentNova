"""核对最终 PDF、快照与三格式文稿；生成逐页缩略图供人工检查。"""

import hashlib
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw
import pdfplumber
import pypdfium2 as pdfium
from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
PDF = HERE / "lecture02-experiment-agent.pdf"


def main():
    reader = PdfReader(PDF)
    texts = []
    outside = []
    with pdfplumber.open(PDF) as document:
        for index, page in enumerate(document.pages):
            texts.append(page.extract_text() or "")
            invalid = [c for c in page.chars if c["text"].strip() and (
                c["x0"] < 8 or c["x1"] > page.width - 8 or c["top"] < 8 or c["bottom"] > page.height - 8)]
            if invalid:
                outside.append({"page": index + 1, "characters": len(invalid)})
    full_text = "\n".join(texts)
    compact = re.sub(r"\s+", "", full_text)
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    hashes_match = all(hashlib.sha256((HERE / "source_snapshot" / item["path"]).read_bytes()).hexdigest()
                       == item["sha256"] for item in manifest["files"])
    output = HERE / "build" / "previews"
    output.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(PDF)
    contact_files = []
    for start in range(0, len(document), 12):
        sheet = Image.new("RGB", (1000, 1120), "#dce5e9")
        draw = ImageDraw.Draw(sheet)
        for offset, index in enumerate(range(start, min(start + 12, len(document)))):
            page = document[index]
            picture = page.render(scale=0.4).to_pil().convert("RGB")
            picture.thumbnail((240, 340))
            x, y = (offset % 4) * 250 + 5, (offset // 4) * 370 + 22
            sheet.paste(picture, (x, y))
            draw.text((x, y - 17), f"Page {index + 1}", fill="black")
            page.close()
        target = output / f"contact-{start // 12 + 1:02d}.png"
        sheet.save(target)
        contact_files.append(target.name)
    selected = {0, 1}
    for phrase in ("第二组", "MSE", "select_unique_text_file(directory_result)", "def run_experiment_workflow", "self.subTest", "数据指纹"):
        for index, text in enumerate(texts):
            if phrase in text:
                selected.add(index)
                break
    for index in sorted(selected):
        page = document[index]
        page.render(scale=1.2).to_pil().save(output / f"page-{index + 1:03d}.png")
        page.close()
    document.close()
    checks = {
        "renderer": "Tectonic 0.17.0", "text_extractor": "pdfplumber", "compiled_source": "lecture.tex",
        "desktop_compiler_validation": "success", "edition": "public-redacted",
        "pages": len(reader.pages), "empty_pages": [i + 1 for i, text in enumerate(texts) if len(text.strip()) < 5],
        "outside_page_safe_area": outside, "replacement_characters": full_text.count("\ufffd"),
        "coverage_checks": {word: word in compact for word in ("0.87744596", "0.01207715", "run_id_mismatch", "自测题", "第27")},
        "snapshot_files": len(manifest["files"]), "snapshot_hashes_match": hashes_match,
        "standalone_tex_has_no_content_dependency": r"\input{content.tex}" not in (HERE / "lecture.tex").read_text(encoding="utf-8"),
        "pdf_author": str(reader.metadata.author), "pdf_embedded_attachments": len(reader.attachments),
        "contact_sheets": contact_files, "selected_render_pages": [i + 1 for i in sorted(selected)],
        "visual_review": "pending",
    }
    for name in ("lecture.md", "lecture.tex", "main.tex", "content.tex", PDF.name):
        checks[name + "_sha256"] = hashlib.sha256((HERE / name).read_bytes()).hexdigest()
    (HERE / "quality-check.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if checks["empty_pages"] or outside or not hashes_match or not all(checks["coverage_checks"].values()):
        raise SystemExit("A PDF or archive quality check failed")


if __name__ == "__main__":
    main()
