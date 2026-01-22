"""
任务规划工具
提供编程任务规划和步骤生成功能
"""
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field
import json
import sys
from pathlib import Path

# 导入任务规划器
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.task_planner import task_planner


# ==================== 输入模型 ====================

class PlanTaskInput(BaseModel):
    """规划任务的输入"""
    description: str = Field(description="任务描述，例如：'添加翻译工具'、'修复 butler.py 第 100 行的错误'")


# ==================== 工具类 ====================

class PlanCodingTaskTool(BaseTool):
    """规划编程任务工具"""
    name: str = "plan_coding_task"
    description: str = """规划编程任务，生成详细的执行步骤。
    
    功能：
    - 自动分类任务类型（添加功能、修复Bug、重构等）
    - 生成详细的执行步骤
    - 估算每个步骤的时间
    - 分析步骤之间的依赖关系
    
    使用场景：
    - 用户说"帮我添加一个翻译工具"
    - 用户说"修复 butler.py 的错误"
    - 用户说"重构 code_analyzer.py"
    - 用户说"优化测试性能"
    
    参数：
    - description: 任务描述
    
    示例：
    - plan_coding_task("添加翻译工具")
    - plan_coding_task("修复 butler.py 第 100 行的错误")
    - plan_coding_task("重构 code_analyzer.py")
    
    返回：
    - 任务类型
    - 详细步骤列表
    - 时间估算
    - 依赖关系
    """
    args_schema: Type[BaseModel] = PlanTaskInput
    
    def _run(self, description: str) -> str:
        """执行任务规划"""
        try:
            # 调用任务规划器
            plan = task_planner.plan_task(description)
            
            # 格式化输出
            output = []
            output.append(f"📋 任务规划: {description}")
            output.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 任务类型
            task_type_names = {
                "add_feature": "添加功能",
                "fix_bug": "修复Bug",
                "refactor": "重构代码",
                "optimize": "优化性能",
                "add_test": "添加测试",
                "update_doc": "更新文档",
                "unknown": "未知类型"
            }
            task_type_name = task_type_names.get(plan["task_type"], plan["task_type"])
            
            output.append(f"\n🎯 任务类型: {task_type_name}")
            
            # 提取的信息
            info = plan.get("extracted_info", {})
            if any(info.values()):
                output.append(f"\n📝 提取信息:")
                if info.get("target_file"):
                    output.append(f"  - 目标文件: {info['target_file']}")
                if info.get("target_function"):
                    output.append(f"  - 目标函数: {info['target_function']}")
                if info.get("target_class"):
                    output.append(f"  - 目标类: {info['target_class']}")
                if info.get("feature_name"):
                    output.append(f"  - 功能名称: {info['feature_name']}")
                if info.get("error_line"):
                    output.append(f"  - 错误行号: {info['error_line']}")
            
            # 时间估算
            time_est = plan.get("time_estimate", {})
            output.append(f"\n⏱️ 预计时间: {time_est.get('formatted', '未知')}")
            output.append(f"  - 总步骤数: {plan['total_steps']}")
            
            # 执行步骤
            steps = plan.get("steps", [])
            if steps:
                output.append(f"\n📌 执行步骤:")
                for step in steps:
                    step_id = step.get("id", "?")
                    action = step.get("action", "未知")
                    desc = step.get("description", "")
                    target = step.get("target", "")
                    tool = step.get("tool", "")
                    est_min = step.get("estimated_minutes", 0)
                    
                    output.append(f"\n  {step_id}. {desc}")
                    if target:
                        output.append(f"     目标: {target}")
                    if tool:
                        output.append(f"     工具: {tool}")
                    output.append(f"     预计: {est_min}分钟")
            
            # 依赖关系
            deps = plan.get("dependencies", {})
            if deps:
                output.append(f"\n🔗 依赖关系:")
                for step_id, dep_ids in deps.items():
                    output.append(f"  - 步骤 {step_id} 依赖: {', '.join(map(str, dep_ids))}")
            
            # 建议
            output.append(f"\n💡 建议:")
            output.append(f"  - 按照步骤顺序执行")
            output.append(f"  - 每完成一步进行测试")
            output.append(f"  - 遇到问题及时调整计划")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 任务规划失败: {str(e)}"


# ==================== 工具列表 ====================

def get_planning_tools():
    """获取所有任务规划工具"""
    return [
        PlanCodingTaskTool(),
    ]


if __name__ == '__main__':
    # 测试工具
    print("🧪 测试任务规划工具...\n")
    
    tools = get_planning_tools()
    print(f"✅ 加载了 {len(tools)} 个工具:")
    for tool in tools:
        print(f"  - {tool.name}")
    
    # 测试规划任务
    print("\n" + "="*50)
    print("测试 1: 规划添加功能")
    print("="*50)
    tool = PlanCodingTaskTool()
    result = tool._run("添加一个翻译工具")
    print(result)
    
    print("\n" + "="*50)
    print("测试 2: 规划修复Bug")
    print("="*50)
    result = tool._run("修复 butler.py 第 100 行的错误")
    print(result)
    
    print("\n" + "="*50)
    print("测试 3: 规划重构")
    print("="*50)
    result = tool._run("重构 code_analyzer.py")
    print(result)
    
    print("\n✅ 所有测试完成！")
