"""独立练习：根据目录观察选择唯一的普通 .txt 文件；不访问文件或模型。"""


def select_unique_text_file(directory_result: dict) -> dict:
    """返回可读取的 relative_path，或返回说明无法选择的结构化失败。

    本题假设输入符合现有 list_directory 的返回结构。
    具体契约见 lessons/17-directory-observation-exercise.md。
    """
    if directory_result["status"] != "success":
        return directory_result

    if directory_result["truncated"]:
        return {
        "status": "failed",
        "error_type": "incomplete_directory_listing",
    }

    candidates = []

    for entry in directory_result["entries"]:
    # 同时检查：
    # entry["type"] 是否等于 "file"
        if entry["type"] == "file" and entry["name"].lower().endswith(".txt"):
            candidates.append(entry)
    # entry["name"].lower().endswith(".txt") 是否成立
    if len(candidates) == 0:
        return {
        "status": "failed",
        "error_type": "no_text_file",
    }
    if len(candidates) > 1:
        return{
                "status": "failed", 
                "error_type": "multiple_text_files",
            }
    # 返回 failed，error_type 为 multiple_text_files
    # 满足时，用 candidates.append(entry) 保存整个条目
    return {
    "status": "success",
    "relative_path": candidates[0]["relative_path"],
}



  