import math


def verify_metrics(metrics, max_mse=0.1):
    """检查 mse 是否为有限、非负数值，并满足可信调用方给定的阈值。

    max_mse 由可信 Python 调用方给定，本题假定它是有限非负数值。
    bool、数值字符串、NaN、正负无穷都不是有效的 mse。
    """
    if not isinstance(metrics, dict) or "mse" not in metrics:
        return {
            "status": "failed",
            "reason": "invalid_metrics",
        }

    mse = metrics["mse"]
    
    # 1. 检查类型：必须是 int 或 float，且不能是 bool（因为 bool 是 int 的子类）
    if isinstance(mse, bool) or not isinstance(mse, (int, float)):
        return {
            "status": "failed",
            "reason": "invalid_metrics",
        }
    
    # 2. 检查数值的有效性：必须是有限数（排除 NaN、正负无穷）且非负
    if not math.isfinite(mse) or mse < 0:
        return {
            "status": "failed",
            "reason": "invalid_metrics",
        }
    
    # 3. 阈值判断：mse 大于 max_mse 判为不通过
    if mse > max_mse:
        return {
            "status": "failed",
            "reason": "mse_above_threshold",
            "mse": mse,
            "max_mse": max_mse,
        }
    
    # 4. 合法且小于等于阈值，返回通过
    return {
        "status": "passed",
        "reason": "verified_metrics",
        "mse": mse,
    }