"""项目范围内的一层目录查看工具。"""

from pathlib import Path


def list_directory(project_root: str, relative_path: str) -> dict:
    """列出直接子项，最多返回 50 项；文件正文由读取工具获取。"""
    root = Path(project_root).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        return {"status": "failed", "error_type": "path_outside_project", "path": str(path)}

    children = sorted(path.iterdir(), key=lambda child: child.name.casefold())
    entries = []
    for child in children[:50]:
        if child.is_symlink():
            entry_type = "symlink"
        elif child.is_dir():
            entry_type = "directory"
        elif child.is_file():
            entry_type = "file"
        else:
            entry_type = "other"
        entries.append({
            "name": child.name,
            "type": entry_type,
            "relative_path": child.relative_to(root).as_posix(),
        })
    return {"status": "success", "entries": entries, "truncated": len(children) > 50}
