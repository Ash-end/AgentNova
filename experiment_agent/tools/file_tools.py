"""文件读取工具。"""

from pathlib import Path


def read_text_file(project_root: str, relative_path: str) -> dict:
    """仅尝试读取指定项目范围内的 UTF-8 文本。"""
    root = Path(project_root).resolve()
    path = (root / relative_path).resolve()

    if not path.is_relative_to(root):
        return {
            "status": "failed",
            "error_type": "path_outside_project",
            "path": str(path),
        }

    try:
        content = path.read_text(encoding="utf-8")
        return {
            "status": "success",
            "content": content,
        }
    except FileNotFoundError:
        return {
            "status": "failed",
            "error_type": "file_not_found",
            "path": str(path),
        }
