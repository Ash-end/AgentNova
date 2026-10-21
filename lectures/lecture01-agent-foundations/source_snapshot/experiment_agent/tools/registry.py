"""工具名称与可调用函数的映射。"""

from pathlib import Path

from experiment_agent.tools.directory_tools import list_directory
from experiment_agent.tools.file_tools import read_text_file


def build_tool_registry(project_root: str) -> dict:
    """创建绑定到指定项目根目录的工具表。"""
    root = str(Path(project_root).resolve())

    def read_project_file(relative_path: str) -> dict:
        return read_text_file(root, relative_path)

    def list_project_directory(relative_path: str) -> dict:
        return list_directory(root, relative_path)

    return {
        "read_text_file": read_project_file,
        "list_directory": list_project_directory,
    }


def validate_relative_path_arguments(arguments: object) -> str | None:
    """参数合法时返回 None，否则返回错误说明。"""
    if not isinstance(arguments, dict):
        return "arguments must be a dictionary"

    if "relative_path" not in arguments:
        return "relative_path is required"

    if set(arguments) != {"relative_path"}:
        return "only relative_path is allowed"

    value = arguments["relative_path"]
    if not isinstance(value, str) or not value.strip():
        return "relative_path must be a non-empty string"

    return None


def _exception_result(name: str, error_type: str, error: Exception) -> dict:
    """把已知执行异常转换成可记录、可交给策略判断的结果。"""
    return {
        "status": "failed",
        "error_type": error_type,
        "tool_name": name,
        "exception_type": type(error).__name__,
        "message": str(error),
    }


def call_tool(tools: dict, name: str, arguments: object) -> dict:
    """按名称查找并校验参数，在实际执行边界转换已知文件异常。"""
    tool = tools.get(name)

    if tool is None:
        return {
            "status": "failed",
            "error_type": "unknown_tool",
            "tool_name": name,
        }

    if name in {"read_text_file", "list_directory"}:
        message = validate_relative_path_arguments(arguments)
        if message is not None:
            return {
                "status": "failed",
                "error_type": "invalid_arguments",
                "message": message,
            }

    try:
        return tool(**arguments)
    except FileNotFoundError as error:
        return _exception_result(name, "file_not_found", error)
    except PermissionError as error:
        return _exception_result(name, "permission_denied", error)
    except IsADirectoryError as error:
        return _exception_result(name, "is_a_directory", error)
    except NotADirectoryError as error:
        return _exception_result(name, "not_a_directory", error)
    except UnicodeDecodeError as error:
        return _exception_result(name, "invalid_encoding", error)
    except TimeoutError as error:
        return _exception_result(name, "tool_timeout", error)
    except OSError as error:
        return _exception_result(name, "io_error", error)
