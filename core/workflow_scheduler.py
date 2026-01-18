"""工作流调度器 - 负责在指定时间触发工作流执行"""
from typing import Dict, Optional, List
import asyncio
import time
from datetime import datetime, timedelta
import re

from models.workflow_models import WorkflowDefinition, WorkflowStatus
from core.workflow_executor import WorkflowExecutor


class WorkflowScheduler:
    """工作流调度器"""
    
    def __init__(self, tools: Dict):
        """
        初始化调度器
        
        Args:
            tools: 工具字典
        """
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.executor = WorkflowExecutor(tools)
        self.tasks: Dict[str, asyncio.Task] = {}  # 存储异步任务
        print("[WorkflowScheduler] 初始化完成")
    
    async def schedule_workflow(self, workflow: WorkflowDefinition) -> bool:
        """
        注册工作流到调度器
        
        Args:
            workflow: 工作流定义
        
        Returns:
            是否成功
        """
        try:
            workflow_id = workflow.workflow_id
            
            # 保存工作流
            self.workflows[workflow_id] = workflow
            
            # 计算延迟时间
            delay = workflow.trigger_timestamp - time.time()
            
            if delay < 0:
                print(f"⚠️  工作流 {workflow_id} 的触发时间已过，立即执行")
                delay = 0
            
            print(f"⏰ 调度工作流: {workflow_id} - {workflow.name}")
            print(f"   触发时间: {workflow.trigger_time} (延迟 {delay:.1f}秒)")
            
            # 创建异步任务
            task = asyncio.create_task(self._wait_and_execute(workflow, delay))
            self.tasks[workflow_id] = task
            
            return True
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ 调度工作流失败: {e}")
            return False
    
    async def _wait_and_execute(self, workflow: WorkflowDefinition, delay: float):
        """
        等待并执行工作流
        
        Args:
            workflow: 工作流定义
            delay: 延迟秒数
        """
        try:
            workflow_id = workflow.workflow_id
            
            # 等待指定时间
            if delay > 0:
                print(f"⏳ 工作流 {workflow_id} 将在 {delay:.1f}秒后执行")
                await asyncio.sleep(delay)
            
            # 检查是否已取消
            if workflow.status == WorkflowStatus.CANCELLED:
                print(f"🚫 工作流 {workflow_id} 已取消，不执行")
                return
            
            # 执行工作流
            print(f"🚀 触发工作流执行: {workflow_id}")
            success = await self.executor.execute_workflow(workflow)
            
            if success:
                print(f"✅ 工作流 {workflow_id} 执行成功")
            else:
                print(f"❌ 工作流 {workflow_id} 执行失败")
        
        except asyncio.CancelledError:
            print(f"🚫 工作流 {workflow_id} 被取消")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"💥 工作流 {workflow_id} 执行异常: {e}")
        
        finally:
            # 清理
            if workflow_id in self.workflows:
                del self.workflows[workflow_id]
            if workflow_id in self.tasks:
                del self.tasks[workflow_id]
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        取消工作流
        
        Args:
            workflow_id: 工作流ID
        
        Returns:
            是否成功
        """
        try:
            if workflow_id not in self.workflows:
                print(f"⚠️  工作流不存在: {workflow_id}")
                return False
            
            workflow = self.workflows[workflow_id]
            
            # 检查状态
            if workflow.status == WorkflowStatus.RUNNING:
                print(f"⚠️  工作流 {workflow_id} 正在执行，无法取消")
                return False
            
            # 标记为已取消
            workflow.status = WorkflowStatus.CANCELLED
            
            # 取消异步任务
            if workflow_id in self.tasks:
                task = self.tasks[workflow_id]
                task.cancel()
            
            print(f"🚫 工作流 {workflow_id} 已取消")
            return True
        
        except Exception as e:
            print(f"❌ 取消工作流失败: {e}")
            return False
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """
        获取工作流
        
        Args:
            workflow_id: 工作流ID
        
        Returns:
            工作流定义，如果不存在则返回None
        """
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, user_id: Optional[str] = None) -> List[WorkflowDefinition]:
        """
        列出工作流
        
        Args:
            user_id: 用户ID（可选，用于筛选）
        
        Returns:
            工作流列表
        """
        if user_id:
            return [wf for wf in self.workflows.values() if wf.user_id == user_id]
        return list(self.workflows.values())
    
    @staticmethod
    def parse_trigger_time(trigger_time: str) -> float:
        """
        解析触发时间，返回时间戳
        
        支持格式：
        1. 相对时间：10秒后、5分钟后、1小时后
        2. 绝对时间：12:24、12:24:30
        
        Args:
            trigger_time: 触发时间字符串
        
        Returns:
            时间戳
        """
        trigger_time = trigger_time.strip().replace("后", "").replace("之后", "")
        
        # 尝试解析绝对时间（HH:MM 或 HH:MM:SS）
        time_pattern = r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$'
        time_match = re.match(time_pattern, trigger_time)
        
        if time_match:
            from datetime import timezone
            
            target_hour = int(time_match.group(1))
            target_minute = int(time_match.group(2))
            target_second = int(time_match.group(3)) if time_match.group(3) else 0
            
            # 验证时间有效性
            if target_hour > 23 or target_minute > 59 or target_second > 59:
                raise ValueError(f"无效的时间: {trigger_time}")
            
            # 获取当前时间（东八区）
            tz = timezone(timedelta(hours=8))
            now = datetime.now(tz)
            
            # 构建目标时间（今天）
            target_time = now.replace(
                hour=target_hour,
                minute=target_minute,
                second=target_second,
                microsecond=0
            )
            
            # 如果目标时间已经过了，设置为明天
            if target_time <= now:
                target_time += timedelta(days=1)
            
            return target_time.timestamp()
        
        # 解析相对时间
        patterns = [
            (r'(\d+)\s*秒', 1),
            (r'(\d+)\s*分钟?', 60),
            (r'(\d+)\s*小时', 3600),
            (r'(\d+)\s*天', 86400),
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, trigger_time)
            if match:
                value = int(match.group(1))
                delay_seconds = value * multiplier
                return time.time() + delay_seconds
        
        raise ValueError(f"无法解析时间格式: {trigger_time}")


# 全局单例
_scheduler: Optional[WorkflowScheduler] = None


def get_workflow_scheduler(tools: Dict = None) -> WorkflowScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        if tools is None:
            raise ValueError("首次创建调度器需要提供 tools")
        _scheduler = WorkflowScheduler(tools)
    return _scheduler
