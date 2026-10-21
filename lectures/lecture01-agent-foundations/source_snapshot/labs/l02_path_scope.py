"""计算四种路径是否属于项目目录，不读取这些目标文件。"""

from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    print(f"Project root: {root}")

    examples = [
        ("existing file inside project", "labs/fixtures/hello.txt"),
        ("missing file inside project", "labs/fixtures/missing.txt"),
        ("relative path outside project", "../outside-demo.txt"),
        ("absolute path outside project", str(root.parent / "outside-demo.txt")),
    ]

    for label, relative_path in examples:
        target = (root / relative_path).resolve()
        allowed = target.is_relative_to(root)
        print(f"\n{label}")
        print(f"  input: {relative_path}")
        print(f"  resolved: {target}")
        print(f"  allowed: {allowed}")


if __name__ == "__main__":
    main()
