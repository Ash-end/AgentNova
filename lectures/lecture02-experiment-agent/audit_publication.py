"""补充扫描将发布的文本、PDF 正文/元数据和 ZIP 内部文件；不读取被忽略的本机文件。"""

import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

import pdfplumber
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PATTERNS = {
    "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "github_token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b",
    "api_secret": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b",
    "aws_key": r"\bAKIA[A-Z0-9]{16}\b",
    "device_sid": r"\bS-1-5-21-\d+-\d+-\d+(?:-\d+)?\b",
    "mac_address": r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
    "windows_product_key": r"\b[A-Z0-9]{5}(?:-[A-Z0-9]{5}){4}\b",
}


def main():
    names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    names = sorted(set(name for name in names if name))
    findings = []
    inspected = {"public_files": len(names), "text_items": 0, "pdfs": 0, "zip_entries": 0}

    def check_text(label, text):
        inspected["text_items"] += 1
        for kind, pattern in PATTERNS.items():
            if re.search(pattern, text):
                findings.append({"path": label, "kind": kind})
        for match in re.finditer(r"(?i)[A-Z]:[\\/]+Users[\\/]+([^\\/\s\"']+)", text):
            if match[1].upper() != "USER":
                findings.append({"path": label, "kind": "non_redacted_user_directory"})
                break
        if re.search(r"(?i)\.codex[\\/]+attachments[\\/]+[0-9a-f]{8}-[0-9a-f-]{27,}", text):
            findings.append({"path": label, "kind": "private_attachment_location"})

    def inspect(label, raw):
        suffix = Path(label).suffix.lower()
        if suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for item in archive.infolist():
                    if not item.is_dir():
                        inspected["zip_entries"] += 1
                        inspect(label + "!" + item.filename, archive.read(item))
        elif suffix == ".pdf":
            inspected["pdfs"] += 1
            reader = PdfReader(io.BytesIO(raw))
            check_text(label + ":metadata", str(reader.metadata))
            with pdfplumber.open(io.BytesIO(raw)) as document:
                check_text(label + ":text", "\n".join(page.extract_text() or "" for page in document.pages))
            for page in reader.pages:
                for annotation in page.get("/Annots", []):
                    target = annotation.get_object().get("/A", {}).get("/URI")
                    if target:
                        check_text(label + ":link", str(target))
            if reader.attachments:
                findings.append({"path": label, "kind": "embedded_attachments_require_review"})
        else:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                return
            check_text(label, text)

    for name in names:
        path = ROOT / name
        if path.is_file():
            inspect(name, path.read_bytes())
    findings = [dict(item) for item in {tuple(sorted(item.items())) for item in findings}]
    result = {"date": "2026-10-25", "scope": "Git-tracked and non-ignored publication files, PDF content/metadata/links and ZIP contents",
              "inspected": inspected, "findings": findings, "passed": not findings,
              "notes": "Pattern screening supplements Gitleaks; software run IDs and generic hardware/model metadata remain public. Not a whole-computer security assessment."}
    (HERE / "security-review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
