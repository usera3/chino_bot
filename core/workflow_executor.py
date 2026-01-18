"""工作流执行器 - 负责执行工作流中的所有步骤"""
from typing import Dict, Any, List
from datetime import datetime
import asyncio
import re

from models.workflow_models import (
    WorkflowDefinition,
    WorkflowStep,
    StepResult,
    WorkflowStatus,
    StepStatus,
    ErrorStrategy
)


class WorkflowExecutor:
    """工作流执行器"""
    
    def __init__(self, tools: Dict[str, Any]):
        """
        初始化执行器
        
        Args:
            tools: 工具字典 {tool_name: tool_instance}
        """
        self.tools = tools
        print("[WorkflowExecutor] 初始化完成")
    
    async def execute_workflow(self, workflow: WorkflowDefinition) -> bool:
        """
        执行整个工作流
        
        Args:
            workflow: 工作流定义
        
        Returns:
            是否成功
        """
        print(f"⚙️ 开始执行工作流: {workflow.workflow_id} - {workflow.name}")
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.executed_at = datetime.now()
        context = {}  # 存储步骤输出 {output_key: value}
        
        try:
            # 按依赖关系排序步骤
            sorted_steps = self._topological_sort(workflow.steps)
            print(f"📋 工作流包含 {len(sorted_steps)} 个步骤")
            
            for step in sorted_steps:
                print(f"▶️  执行步骤 {step.step_id}: {step.tool_name}")
                
                result = await self._execute_step(step, context, workflow)
                
                if not result.success:
                    print(f"❌ 步骤 {step.step_id} 执行失败: {result.error}")
                    
                    # 根据错误策略决定是否继续
                    if step.is_critical or workflow.on_error == ErrorStrategy.STOP:
                        print(f"⚠️  关键步骤失败或错误策略为STOP，停止工作流")
                        workflow.status = WorkflowStatus.FAILED
                        workflow.error_message = f"步骤 {step.step_id} 失败: {result.error}"
                        break
                    else:
                        print(f"ℹ️  非关键步骤失败，继续执行")
                else:
                    print(f"✅ 步骤 {step.step_id} 执行成功")
                    
                    # 保存输出到上下文
                    if step.output_key and result.data is not None:
                        context[step.output_key] = result.data
                        print(f"💾 保存输出: {step.output_key} = {str(result.data)[:100]}")
            
            # 如果没有被标记为失败，则标记为完成
            if workflow.status == WorkflowStatus.RUNNING:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
                print(f"🎉 工作流执行完成: {workflow.workflow_id}")
                return True
            else:
                workflow.completed_at = datetime.now()
                print(f"💥 工作流执行失败: {workflow.workflow_id}")
                return False
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"💥 工作流执行异常: {e}")
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = f"执行异常: {str(e)}"
            workflow.completed_at = datetime.now()
            return False
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
        workflow: WorkflowDefinition
    ) -> StepResult:
        """
        执行单个步骤
        
        Args:
            step: 步骤定义
            context: 上下文数据（包含前面步骤的输出）
            workflow: 工作流定义
        
        Returns:
            步骤执行结果
        """
        step.status = StepStatus.RUNNING
        
        try:
            # 1. 替换参数中的模板变量
            resolved_params = self._resolve_parameters(step.parameters, context)
            print(f"📝 解析后的参数: {resolved_params}")
            
            # 2. 获取工具
            tool = self.tools.get(step.tool_name)
            if not tool:
                error_msg = f"工具不存在: {step.tool_name}"
                print(f"❌ {error_msg}")
                step.status = StepStatus.FAILED
                step.error = error_msg
                return StepResult(success=False, error=error_msg)
            
            # 3. 准备上下文信息
            context_params = {
                "current_user_id": workflow.user_id,
                "current_group_id": workflow.group_id
            }
            
            # 4. 合并参数
            all_params = resolved_params.copy()
            all_params.update(context_params)
            
            # 5. 执行工具（带重试）
            for attempt in range(workflow.max_retries + 1):
                try:
                    print(f"🔧 调用工具: {step.tool_name} (尝试 {attempt + 1}/{workflow.max_retries + 1})")
                    
                    # 检查工具是否是 LangChain Tool
                    if hasattr(tool, 'ainvoke'):
                        # LangChain Tool - 使用 ainvoke
                        result = await tool.ainvoke(resolved_params)
                    elif hasattr(tool, 'arun'):
                        # LangChain Tool - 使用 arun
                        result = await tool.arun(**resolved_params)
                    elif asyncio.iscoroutinefunction(tool):
                        # 异步函数
                        result = await tool(**all_params)
                    else:
                        # 同步函数
                        result = tool(**all_params)
                    
                    # 成功
                    step.status = StepStatus.COMPLETED
                    step.result = result
                    return StepResult(success=True, data=result)
                
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ 工具执行异常: {error_msg}")
                    
                    if attempt < workflow.max_retries:
                        wait_time = 2 ** attempt
                        print(f"⚠️  {wait_time}秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        step.status = StepStatus.FAILED
                        step.error = error_msg
                        return StepResult(success=False, error=error_msg)
        
        except Exception as e:
            error_msg = f"步骤执行异常: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            step.status = StepStatus.FAILED
            step.error = error_msg
            return StepResult(success=False, error=error_msg)
    
    def _resolve_parameters(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        解析参数中的模板变量
        
        Args:
            parameters: 原始参数
            context: 上下文数据
        
        Returns:
            解析后的参数
        """
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str):
                # 替换字符串中的模板变量
                resolved[key] = self._replace_template(value, context)
            elif isinstance(value, dict):
                # 递归处理字典
                resolved[key] = self._resolve_parameters(value, context)
            elif isinstance(value, list):
                # 处理列表
                resolved[key] = [
                    self._replace_template(item, context) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                # 其他类型直接复制
                resolved[key] = value
        
        return resolved
    
    def _replace_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        替换模板字符串中的变量
        
        支持格式: {{variable_name}}
        
        Args:
            template: 模板字符串
            context: 上下文数据
        
        Returns:
            替换后的字符串
        """
        if "{{" not in template or "}}" not in template:
            return template
        
        pattern = r'\{\{(\w+)\}\}'
        
        def replacer(match):
            var_name = match.group(1)
            value = context.get(var_name)
            
            if value is None:
                print(f"⚠️  模板变量未找到: {var_name}")
                return f"{{{{MISSING:{var_name}}}}}"
            
            return str(value)
        
        result = re.sub(pattern, replacer, template)
        return result
    
    def _topological_sort(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """
        拓扑排序，确保依赖关系正确
        
        Args:
            steps: 步骤列表
        
        Returns:
            排序后的步骤列表
        """
        # 简单实现：按 step_id 排序
        sorted_steps = sorted(steps, key=lambda s: s.step_id)
        
        # 验证依赖关系
        executed_ids = set()
        for step in sorted_steps:
            for dep_id in step.depends_on:
                if dep_id not in executed_ids:
                    print(
                        f"⚠️  步骤 {step.step_id} 依赖步骤 {dep_id}，但 {dep_id} 尚未执行"
                    )
            executed_ids.add(step.step_id)
        
        return sorted_steps
