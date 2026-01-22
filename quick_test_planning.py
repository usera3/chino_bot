"""
快速测试任务规划工具
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.task_planner import TaskPlanner, TaskType
from tools.planning_tools import PlanCodingTaskTool


def test_task_planner():
    """测试任务规划器"""
    print("=" * 60)
    print("测试任务规划器")
    print("=" * 60)
    
    planner = TaskPlanner()
    
    # 测试 1：分类任务
    print("\n【测试 1】任务分类")
    test_cases = [
        ("添加一个翻译工具", TaskType.ADD_FEATURE),
        ("修复 butler.py 第 100 行的错误", TaskType.FIX_BUG),
        ("重构 code_analyzer.py", TaskType.REFACTOR),
        ("优化测试工具的性能", TaskType.OPTIMIZE),
        ("为 butler.py 添加单元测试", TaskType.ADD_TEST),
        ("更新 README.md 文档", TaskType.UPDATE_DOC),
    ]
    
    passed = 0
    for description, expected_type in test_cases:
        task_type = planner.classify_task(description)
        status = "✅" if task_type == expected_type else "❌"
        print(f"{status} {description} → {task_type.value}")
        if task_type == expected_type:
            passed += 1
    
    print(f"\n分类测试: {passed}/{len(test_cases)} 通过")
    
    # 测试 2：信息提取
    print("\n【测试 2】信息提取")
    test_cases = [
        ("修复 butler.py 的错误", "target_file", "butler.py"),
        ("修复 process 函数的错误", "target_function", "process"),
        ("重构 Butler 类", "target_class", "Butler"),
        ("修复第 100 行的错误", "error_line", 100),
        ("添加翻译工具", "feature_name", "翻译工具"),
    ]
    
    passed = 0
    for description, key, expected_value in test_cases:
        info = planner.extract_info(description)
        actual_value = info.get(key)
        status = "✅" if actual_value == expected_value else "❌"
        print(f"{status} {description} → {key}={actual_value}")
        if actual_value == expected_value:
            passed += 1
    
    print(f"\n提取测试: {passed}/{len(test_cases)} 通过")
    
    # 测试 3：完整规划
    print("\n【测试 3】完整规划")
    test_cases = [
        "添加一个翻译工具",
        "修复 butler.py 第 100 行的错误",
        "重构 code_analyzer.py",
    ]
    
    passed = 0
    for description in test_cases:
        try:
            plan = planner.plan_task(description)
            
            # 检查必要字段
            required_fields = ["task_type", "description", "steps", "time_estimate", "dependencies"]
            has_all_fields = all(field in plan for field in required_fields)
            has_steps = len(plan["steps"]) > 0
            
            if has_all_fields and has_steps:
                print(f"✅ {description}")
                print(f"   - 任务类型: {plan['task_type']}")
                print(f"   - 步骤数: {plan['total_steps']}")
                print(f"   - 预计时间: {plan['time_estimate']['formatted']}")
                passed += 1
            else:
                print(f"❌ {description} - 缺少必要字段")
        except Exception as e:
            print(f"❌ {description} - 错误: {e}")
    
    print(f"\n规划测试: {passed}/{len(test_cases)} 通过")
    
    return passed == len(test_cases)


def test_planning_tool():
    """测试任务规划工具"""
    print("\n" + "=" * 60)
    print("测试任务规划工具")
    print("=" * 60)
    
    tool = PlanCodingTaskTool()
    
    # 测试工具属性
    print("\n【测试 1】工具属性")
    print(f"✅ 工具名称: {tool.name}")
    print(f"✅ 工具描述: {tool.description[:50]}...")
    
    # 测试工具执行
    print("\n【测试 2】工具执行")
    test_cases = [
        "添加一个翻译工具",
        "修复 butler.py 第 100 行的错误",
        "重构 code_analyzer.py",
    ]
    
    passed = 0
    for description in test_cases:
        try:
            result = tool._run(description)
            
            # 检查输出格式
            required_markers = ["📋", "🎯", "⏱️", "📌", "💡"]
            has_all_markers = all(marker in result for marker in required_markers)
            
            if has_all_markers:
                print(f"✅ {description}")
                # 显示部分输出
                lines = result.split('\n')
                for line in lines[:5]:
                    print(f"   {line}")
                print(f"   ... (共 {len(lines)} 行)")
                passed += 1
            else:
                print(f"❌ {description} - 输出格式不完整")
        except Exception as e:
            print(f"❌ {description} - 错误: {e}")
    
    print(f"\n工具测试: {passed}/{len(test_cases)} 通过")
    
    return passed == len(test_cases)


def main():
    """主函数"""
    print("\n🧪 开始测试任务规划功能...\n")
    
    # 测试任务规划器
    planner_ok = test_task_planner()
    
    # 测试任务规划工具
    tool_ok = test_planning_tool()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if planner_ok and tool_ok:
        print("✅ 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        if not planner_ok:
            print("   - 任务规划器测试失败")
        if not tool_ok:
            print("   - 任务规划工具测试失败")
        return 1


if __name__ == '__main__':
    exit(main())
