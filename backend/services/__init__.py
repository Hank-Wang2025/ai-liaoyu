"""服务包。

避免在包导入时级联加载所有子模块，否则单个可选组件失败会阻断整站启动。
需要具体服务时，请直接导入对应子模块，例如 `from services.plan_manager import PlanManager`。
"""

__all__ = []
