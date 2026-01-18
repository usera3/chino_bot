"""
定时任务工具 - 基于 nonebot-plugin-apscheduler
"""
from langchain_core.tools import Tool
from datetime import datetime, timedelta
from typing import Optional
import re


class SchedulerToolWrapper:
    """定时任务工具包装器"""
    
    def __init__(self):
        """初始化"""
        self.scheduler = None
        self.bot = None
        self.tasks = {}  # 存储任务信息
    
    def set_scheduler(self, scheduler):
        """设置 scheduler 实例"""
        self.scheduler = scheduler
    
    def set_bot(self, bot):
        """设置 bot 实例"""
        self.bot = bot
    
    def parse_delay(self, time_str: str) -> Optional[int]:
        """
        解析时间延迟字符串，返回秒数
        
        支持格式：
        - "10秒后"、"10秒"
        - "5分钟后"、"5分钟"
        - "2小时后"、"2小时"
        - "HH:MM" (如 "14:30")
        
        Returns:
            秒数，如果解析失败返回 None
        """
        time_str = time_str.strip()
        
        # 匹配 "数字+单位" 格式
        patterns = [
            (r'(\d+)\s*秒', 1),
            (r'(\d+)\s*分钟?', 60),
            (r'(\d+)\s*小时', 3600),
            (r'(\d+)\s*天', 86400),
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, time_str)
            if match:
                number = int(match.group(1))
                return number * multiplier
        
        # 匹配 "HH:MM" 格式（今天的某个时间点）
        time_match = re.match(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            
            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 如果目标时间已过，设置为明天
            if target_time <= now:
                target_time += timedelta(days=1)
            
            delta = target_time - now
            return int(delta.total_seconds())
        
        return None
    
    async def create_task(
        self,
        delay: str,
        action: str,
        user_id: str,
        group_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        创建定时任务
        
        Args:
            delay: 延迟时间（如 "10秒后"、"5分钟"、"14:30"）
            action: 动作类型（"send_message"、"send_email"）
            user_id: 用户 QQ 号
            group_id: 群号（可选）
            **kwargs: 其他参数（如 message、email_subject、email_content 等）
        
        Returns:
            任务创建结果
        """
        if not self.scheduler:
            return "❌ 定时任务系统未初始化"
        
        if not self.bot:
            return "❌ Bot 实例未设置"
        
        # 解析延迟时间
        seconds = self.parse_delay(delay)
        if seconds is None:
            return f"❌ 无法解析时间：{delay}\n支持格式：10秒、5分钟、2小时、14:30"
        
        # 计算执行时间
        run_time = datetime.now() + timedelta(seconds=seconds)
        
        # 创建任务 ID
        task_id = f"task_{user_id}_{int(datetime.now().timestamp())}"
        
        # 根据动作类型定义任务函数
        if action == "send_message":
            message = kwargs.get("message", "时间到了！")
            
            async def task_func():
                """发送 QQ 消息"""
                try:
                    if group_id:
                        await self.bot.send_group_msg(
                            group_id=int(group_id),
                            message=message
                        )
                    else:
                        await self.bot.send_private_msg(
                            user_id=int(user_id),
                            message=message
                        )
                    
                    if task_id in self.tasks:
                        del self.tasks[task_id]
                
                except Exception as e:
                    print(f"❌ 定时任务执行失败: {e}")
        
        elif action == "send_email":
            email_address = kwargs.get("email_address", f"{user_id}@qq.com")
            subject = kwargs.get("subject", "定时提醒")
            content = kwargs.get("content", "时间到了！")
            
            async def task_func():
                """发送邮件"""
                try:
                    # 导入邮件工具
                    from tools.basic_tools import send_email_tool
                    
                    # 发送邮件
                    result = await send_email_tool(
                        receiver_email=email_address,
                        subject=subject,
                        content=content
                    )
                    
                    print(f"📧 定时邮件发送结果: {result}")
                    
                    if task_id in self.tasks:
                        del self.tasks[task_id]
                
                except Exception as e:
                    print(f"❌ 定时邮件发送失败: {e}")
        
        else:
            return f"❌ 不支持的动作类型: {action}\n支持：send_message、send_email"
        
        # 添加任务到调度器
        try:
            self.scheduler.add_job(
                task_func,
                'date',
                run_date=run_time,
                id=task_id,
                replace_existing=True
            )
            
            # 保存任务信息
            self.tasks[task_id] = {
                "delay": delay,
                "action": action,
                "user_id": user_id,
                "group_id": group_id,
                "run_time": run_time,
                "created_at": datetime.now(),
                **kwargs
            }
            
            # 格式化时间显示
            if seconds < 60:
                time_desc = f"{seconds}秒后"
            elif seconds < 3600:
                time_desc = f"{seconds // 60}分钟后"
            elif seconds < 86400:
                time_desc = f"{seconds // 3600}小时后"
            else:
                time_desc = run_time.strftime("%Y-%m-%d %H:%M")
            
            action_desc = {
                "send_message": "发送消息",
                "send_email": "发送邮件"
            }.get(action, action)
            
            return f"✅ 定时任务已创建\n⏰ 将在 {time_desc} {action_desc}"
        
        except Exception as e:
            return f"❌ 创建定时任务失败: {e}"
    
    def get_active_tasks(self, user_id: Optional[str] = None) -> list:
        """
        获取活跃的任务列表
        
        Args:
            user_id: 用户 QQ 号（可选，用于过滤）
        
        Returns:
            任务列表
        """
        if user_id:
            return [
                task for task_id, task in self.tasks.items()
                if task["user_id"] == user_id
            ]
        return list(self.tasks.values())


# 全局实例
_scheduler_wrapper = SchedulerToolWrapper()


def get_scheduler_tool() -> Optional[Tool]:
    """获取定时任务工具"""
    
    async def schedule_task(input_str: str) -> str:
        """
        创建定时任务
        
        输入格式：JSON 字符串，包含以下字段：
        - delay: 延迟时间（必需）
        - action: 动作类型（必需）："send_message" 或 "send_email"
        - user_id: 用户 QQ 号（必需）
        - group_id: 群号（可选）
        
        根据 action 类型，需要不同的参数：
        
        send_message:
        - message: 消息内容
        
        send_email:
        - email_address: 邮箱地址（默认为 user_id@qq.com）
        - subject: 邮件主题
        - content: 邮件内容
        
        示例1（发送消息）：
        {"delay": "10秒后", "action": "send_message", "message": "时间到了！", "user_id": "123456"}
        
        示例2（发送邮件）：
        {"delay": "2分钟", "action": "send_email", "email_address": "123456@qq.com", "subject": "吃饭提醒", "content": "该吃饭啦！", "user_id": "123456"}
        """
        import json
        
        try:
            # 解析输入
            params = json.loads(input_str)
            
            delay = params.get("delay")
            action = params.get("action")
            user_id = params.get("user_id")
            
            if not delay or not action or not user_id:
                return "❌ 缺少必需参数：delay、action、user_id"
            
            # 移除已处理的参数，剩余的作为 kwargs
            kwargs = {k: v for k, v in params.items() if k not in ["delay", "action", "user_id"]}
            
            # 创建任务
            result = await _scheduler_wrapper.create_task(
                delay=delay,
                action=action,
                user_id=user_id,
                **kwargs
            )
            
            return result
        
        except json.JSONDecodeError:
            return "❌ 输入格式错误，需要 JSON 格式"
        except Exception as e:
            return f"❌ 创建任务失败: {e}"
    
    tool = Tool(
        name="schedule_task",
        description="""创建定时任务，支持发送消息或邮件。

使用场景：
- 用户说"10秒后提醒我" → 创建定时消息
- 用户说"5分钟后给我发邮件" → 创建定时邮件
- 用户说"14:30提醒我开会" → 创建定时消息

支持的动作类型：
1. send_message - 发送 QQ 消息
2. send_email - 发送邮件

支持的时间格式：
- "10秒"、"10秒后"
- "5分钟"、"5分钟后"
- "2小时"、"2小时后"
- "14:30"（今天的某个时间点）

输入：JSON 字符串
{
    "delay": "10秒后",
    "action": "send_message" 或 "send_email",
    "user_id": "123456",
    "message": "消息内容" (send_message 时需要),
    "email_address": "123456@qq.com" (send_email 时需要),
    "subject": "邮件主题" (send_email 时需要),
    "content": "邮件内容" (send_email 时需要)
}

输出：任务创建结果""",
        func=schedule_task,
        coroutine=schedule_task
    )
    
    return tool


def init_scheduler(scheduler, bot):
    """
    初始化定时任务工具
    
    Args:
        scheduler: APScheduler 实例
        bot: NoneBot Bot 实例
    """
    _scheduler_wrapper.set_scheduler(scheduler)
    _scheduler_wrapper.set_bot(bot)


def get_scheduler_wrapper():
    """获取 scheduler wrapper 实例"""
    return _scheduler_wrapper
