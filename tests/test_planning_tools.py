"""
测试任务规划工具
"""
import pytest
from tools.planning_tools import PlanCodingTaskTool


@pytest.fixture
def tool():
    """创建工具实例"""
    return PlanCodingTaskTool()


class TestPlanCodingTaskTool:
    """测试任务规划工具"""
    
    def test_tool_name(self, tool):
        """测试工具名称"""
        assert tool.name == "plan_coding_task"
    
    def test_tool_description(self, tool):
        """测试工具描述"""
        assert "规划编程任务" in tool.description
        assert "生成详细的执行步骤" in tool.description
    
    def test_plan_add_feature(self, tool):
        """测试规划添加功能"""
        result = tool._run("添加一个翻译工具")
        
        assert "任务规划" in result
        assert "添加功能" in result
        assert "执行步骤" in result
        assert "预计时间" in result
    
    def test_plan_fix_bug(self, tool):
        """测试规划修复Bug"""
        result = tool._run("修复 butler.py 第 100 行的错误")
        
        assert "任务规划" in result
        assert "修复Bug" in result
        assert "butler.py" in result
        assert "100" in result
    
    def test_plan_refactor(self, tool):
        """测试规划重构"""
        result = tool._run("重构 code_analyzer.py")
        
        assert "任务规划" in result
        assert "重构代码" in result
        assert "code_analyzer.py" in result
    
    def test_plan_optimize(self, tool):
        """测试规划优化"""
        result = tool._run("优化测试工具的性能")
        
        assert "任务规划" in result
        assert "优化性能" in result
    
    def test_plan_add_test(self, tool):
        """测试规划添加测试"""
        result = tool._run("为 butler.py 添加单元测试")
        
        assert "任务规划" in result
        assert "添加测试" in result
    
    def test_plan_update_doc(self, tool):
        """测试规划更新文档"""
        result = tool._run("更新 README.md 文档")
        
        assert "任务规划" in result
        assert "更新文档" in result
    
    def test_output_format(self, tool):
        """测试输出格式"""
        result = tool._run("添加翻译工具")
        
        # 检查输出包含关键信息
        assert "📋" in result  # 任务规划标题
        assert "🎯" in result  # 任务类型
        assert "⏱️" in result  # 预计时间
        assert "📌" in result  # 执行步骤
        assert "💡" in result  # 建议
    
    def test_error_handling(self, tool):
        """测试错误处理"""
        # 空描述
        result = tool._run("")
        assert "任务规划" in result or "失败" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
