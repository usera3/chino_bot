"""工作流工具 - AI创建和管理工作流的接口"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uuid

from models.workflow_models import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
    ErrorStrategy
)
from core.workflow_scheduler import get_workflow_scheduler, WorkflowScheduler


class CreateWorkflowInput(BaseModel):
    """创建工作流输入"""
    name: str = Field(description="工作流名称，简短描述工作流的目的")
    trigger_time: str = Field(description="触发时间。支持：相对时间（'10秒后'、'5分钟后'）或绝对时间（'12:24'、'12:24:30'）")
    steps: List[Dict[str, Any]] = Field(description="""步骤列表，按执行顺序排列。每个步骤包含：
- tool_name: 工具名称（如 send_email, get_weather, web_search 等）
- parameters: 工具参数（可以使用 {{output_key}} 引用前面步骤的输出）
- output_key: 保存输出的键名（可选）
- depends_on: 依赖的步骤ID列表（可选）
- is_critical: 是否关键步骤（可选，默认false）""")
    on_error: str = Field(default="continue", description="错误处理策略：continue（继续执行）或 stop（停止执行）")
    max_retries: int = Field(default=3, description="最大重试次数")


class CreateWorkflowTool(BaseTool):
    """创建工作流工具"""
    name: str = "create_workflow"
    description: str = """创建工作流，在指定时间自动执行一系列工具调用。

工作流支持：
- 多个步骤按顺序执行
- 步骤间数据传递（使用 {{output_key}} 引用前面步骤的输出）
- 相对时间（"10秒后"、"5分钟后"）和绝对时间（"12:24"）
- 错误处理和重试

使用场景：
- "12:24的时候给我发邮件" → 单步骤工作流
- "10秒后搜索天气然后发邮件告诉我" → 多步骤工作流，第二步使用第一步的输出
- "明天8点提醒我，然后给我点赞" → 多步骤工作流

AI的职责：
- 解析用户意图，确定需要哪些工具
- 为每个工具生成完整的参数（包括邮件主题、内容等）
- 确定步骤间的依赖关系
- 使用模板变量传递数据

示例1（单步骤 - 定时发邮件）：
用户："12:24给我发邮件提醒吃饭"
{
    "name": "吃饭提醒",
    "trigger_time": "12:24",
    "steps": [
        {
            "tool_name": "send_email",
            "parameters": {
                "receiver_email": "123456@qq.com",
                "subject": "吃饭提醒",
                "content": "该吃饭啦！记得按时吃饭哦~"
            }
        }
    ]
}

示例2（多步骤 - 先查天气再发邮件）：
用户："10秒后查深圳天气然后发邮件告诉我"
{
    "name": "天气查询并通知",
    "trigger_time": "10秒后",
    "steps": [
        {
            "tool_name": "get_weather",
            "parameters": {"city": "深圳"},
            "output_key": "weather_info"
        },
        {
            "tool_name": "send_email",
            "parameters": {
                "receiver_email": "123456@qq.com",
                "subject": "深圳天气",
                "content": "深圳天气情况：{{weather_info}}"
            },
            "depends_on": [1]
        }
    ]
}"""
    args_schema: type[BaseModel] = CreateWorkflowInput
    
    # 工具注册表（需要在初始化时设置）
    tool_registry: Dict[str, Any] = {}
    
    # 用户上下文（需要在每次调用时设置）
    current_user_id: Optional[str] = None
    current_group_id: Optional[str] = None
    
    def _run(
        self,
        name: str,
        trigger_time: str,
        steps: List[Dict[str, Any]],
        on_error: str = "continue",
        max_retries: int = 3
    ) -> str:
        """同步执行（不支持）"""
        return "❌ 工作流工具只支持异步调用"
    
    async def _arun(
        self,
        name: str,
        trigger_time: str,
        steps: List[Dict[str, Any]],
        on_error: str = "continue",
        max_retries: int = 3
    ) -> str:
        """
        创建工作流
        
        Args:
            name: 工作流名称
            trigger_time: 触发时间
            steps: 步骤列表
            on_error: 错误处理策略
            max_retries: 最大重试次数
        
        Returns:
            创建结果
        """
        try:
            # 获取用户上下文
            user_id = self.current_user_id
            group_id = self.current_group_id
            
            if not user_id:
                return "❌ 无法确定用户ID"
            
            print(f"📝 创建工作流: {name}")
            print(f"   用户: {user_id}, 触发时间: {trigger_time}")
            print(f"   步骤数: {len(steps)}")
            
            # 1. 验证步骤
            validation_result = self._validate_steps(steps)
            if not validation_result["valid"]:
                return f"❌ 工作流验证失败: {validation_result['error']}"
            
            # 2. 解析触发时间
            try:
                trigger_timestamp = WorkflowScheduler.parse_trigger_time(trigger_time)
            except ValueError as e:
                return f"❌ 无法解析触发时间: {str(e)}"
            
            # 3. 创建工作流定义
            workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
            
            workflow_steps = []
            for idx, step_data in enumerate(steps, 1):
                step = WorkflowStep(
                    step_id=idx,
                    tool_name=step_data["tool_name"],
                    parameters=step_data["parameters"],
                    output_key=step_data.get("output_key"),
                    depends_on=step_data.get("depends_on", []),
                    is_critical=step_data.get("is_critical", False)
                )
                workflow_steps.append(step)
            
            workflow = WorkflowDefinition(
                workflow_id=workflow_id,
                name=name,
                user_id=user_id,
                group_id=group_id,
                trigger_time=trigger_time,
                trigger_timestamp=trigger_timestamp,
                steps=workflow_steps,
                status=WorkflowStatus.PENDING,
                on_error=ErrorStrategy.CONTINUE if on_error == "continue" else ErrorStrategy.STOP,
                max_retries=max_retries
            )
            
            # 4. 注册到调度器
            scheduler = get_workflow_scheduler(self.tool_registry)
            success = await scheduler.schedule_workflow(workflow)
            
            if success:
                print(f"✅ 工作流创建成功: {workflow_id}")
                
                # 生成友好的确认消息
                steps_desc = []
                for step in workflow_steps:
                    desc = f"{step.step_id}. {step.tool_name}"
                    if step.output_key:
                        desc += f" → {step.output_key}"
                    steps_desc.append(desc)
                
                message = f"好的，我已创建工作流「{name}」\n"
                message += f"⏰ 触发时间：{trigger_time}\n"
                message += f"📋 步骤：\n" + "\n".join(steps_desc)
                
                return message
            else:
                return "❌ 工作流调度失败"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ 创建工作流失败: {str(e)}"
    
    def _validate_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证步骤定义
        
        Args:
            steps: 步骤列表
        
        Returns:
            验证结果 {"valid": bool, "error": str}
        """
        if not steps:
            return {"valid": False, "error": "步骤列表不能为空"}
        
        for idx, step in enumerate(steps, 1):
            # 检查必需字段
            if "tool_name" not in step:
                return {"valid": False, "error": f"步骤 {idx} 缺少 tool_name"}
            
            if "parameters" not in step:
                return {"valid": False, "error": f"步骤 {idx} 缺少 parameters"}
            
            # 验证工具是否存在
            tool_name = step["tool_name"]
            if tool_name not in self.tool_registry:
                return {"valid": False, "error": f"步骤 {idx}: 工具不存在 '{tool_name}'"}
            
            # 验证依赖关系
            depends_on = step.get("depends_on", [])
            for dep_id in depends_on:
                if dep_id < 1 or dep_id >= idx:
                    return {
                        "valid": False,
                        "error": f"步骤 {idx}: 无效的依赖 {dep_id}（必须是之前的步骤）"
                    }
        
        return {"valid": True, "error": None}


def get_workflow_tool(tool_registry: Dict[str, Any]) -> CreateWorkflowTool:
    """
    获取工作流工具实例
    
    Args:
        tool_registry: 工具注册表
    
    Returns:
        工作流工具实例
    """
    tool = CreateWorkflowTool()
    tool.tool_registry = tool_registry
    return tool
