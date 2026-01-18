"""工作流数据模型"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorStrategy(Enum):
    """错误处理策略"""
    CONTINUE = "continue"  # 继续执行后续步骤
    STOP = "stop"          # 停止执行


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: int                          # 步骤ID
    tool_name: str                        # 工具名称
    parameters: Dict[str, Any]            # 参数（可包含模板变量）
    output_key: Optional[str] = None      # 输出保存的键名
    depends_on: List[int] = field(default_factory=list)  # 依赖的步骤ID列表
    is_critical: bool = False             # 是否关键步骤
    retry_count: int = 0                  # 当前重试次数
    status: StepStatus = StepStatus.PENDING  # 状态
    result: Optional[Any] = None          # 执行结果
    error: Optional[str] = None           # 错误信息


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    workflow_id: str                      # 唯一ID
    name: str                             # 工作流名称
    user_id: str                          # 创建者QQ号
    trigger_time: str                     # 触发时间（原始字符串）
    trigger_timestamp: float              # 触发时间戳
    steps: List[WorkflowStep]             # 步骤列表
    group_id: Optional[str] = None        # 群号（可选）
    status: WorkflowStatus = WorkflowStatus.PENDING  # 状态
    on_error: ErrorStrategy = ErrorStrategy.CONTINUE  # 错误处理策略
    max_retries: int = 3                  # 最大重试次数
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    executed_at: Optional[datetime] = None  # 执行时间
    completed_at: Optional[datetime] = None  # 完成时间
    error_message: Optional[str] = None   # 错误信息


@dataclass
class StepResult:
    """步骤执行结果"""
    success: bool                         # 是否成功
    data: Optional[Any] = None            # 返回数据
    error: Optional[str] = None           # 错误信息
