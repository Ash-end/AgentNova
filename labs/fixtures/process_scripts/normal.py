"""正常执行：stderr 也可以承载诊断信息。"""

import sys


print("正常脚本：2 + 3 = 5", flush=True)
print("诊断信息：本次计算已完成。", file=sys.stderr, flush=True)
