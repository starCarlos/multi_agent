"""辅助函数模块，提供各种通用工具函数"""

import uuid

# 生成唯一ID
def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id