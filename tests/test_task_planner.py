"""
测试任务规划器
"""
import pytest
from core.task_planner import TaskPlanner, TaskType


@pytest.fixture
def planner():
    """创建任务规划器实例"""
    return TaskPlanner()


class TestTaskClassification:
    """测试任务分类"""
    
    def test_classify_add_feature(self, planner):
        """测试识别添加功能任务"""
        description = "添加一个翻译工具"
        task_type = planner.classify_task(description)
        assert task_type == TaskType.ADD_FEATURE
    
    def test_classify_fix_bug(self, planner):
        """测试识别修复Bug任务"""
        description = "修复 butler.py 第 100 行的错误"
        task_type = planner.classify_task(description)
        assert task_type == TaskType.FIX_BUG
    
    def test_classify_refactor(self, planner):
        """测试识别重构任务"""
        description = "重构 code_analyzer.py"
        task_type = planner.classify_task(description)
        assert task_type == TaskType.REFACTOR
    
    def test_classify_optimize(self, planner):
        """测试识别优化任务"""
        description = "优化测试工具的性能"
        task_type = planner.classify_task(description)
        assert task_type == TaskType.OPTIMIZE
    
    def test_classify_add_test(self, planner):
        """测试识别添加测试任务"""
        description = "为 butler.py 添加单元测试"
        task_type = planner.classify_task(description)
        assert task_type == TaskType.ADD_TEST
    
    def test_classify_update_doc(self, planner):
        """测试识别更新文档任务"""
        description = "更新 README.md 文档"
        task_type = planner.classify_task(description)
        assert task_type == TaskType.UPDATE_DOC


class TestInfoExtraction:
    """测试信息提取"""
    
    def test_extract_file_name(self, planner):
        """测试提取文件名"""
        description = "修复 butler.py 的错误"
        info = planner.extract_info(description)
        assert info["target_file"] == "butler.py"
    
    def test_extract_function_name(self, planner):
        """测试提取函数名"""
        description = "修复 process 函数的错误"
        info = planner.extract_info(description)
        assert info["target_function"] == "process"
    
    def test_extract_class_name(self, planner):
        """测试提取类名"""
        description = "重构 Butler 类"
        info = planner.extract_info(description)
        assert info["target_class"] == "Butler"
    
    def test_extract_line_number(self, planner):
        """测试提取行号"""
        description = "修复第 100 行的错误"
        info = planner.extract_info(description)
        assert info["error_line"] == 100
    
    def test_extract_feature_name(self, planner):
        """测试提取功能名称"""
        description = "添加翻译工具"
        info = planner.extract_info(description)
        assert info["feature_name"] == "翻译工具"


class TestStepGeneration:
    """测试步骤生成"""
    
    def test_generate_add_feature_steps(self, planner):
        """测试生成添加功能步骤"""
        description = "添加翻译工具"
        info = planner.extract_info(description)
        task_type = TaskType.ADD_FEATURE
        
        steps = planner.generate_steps(task_type, description, info, None)
        
        assert len(steps) > 0
        assert steps[0]["action"] == "analyze_requirements"
        assert any(step["action"] == "create_file" for step in steps)
        assert any(step["action"] == "implement_feature" for step in steps)
        assert any(step["action"] == "write_test" for step in steps)
    
    def test_generate_fix_bug_steps(self, planner):
        """测试生成修复Bug步骤"""
        description = "修复 butler.py 第 100 行的错误"
        info = planner.extract_info(description)
        task_type = TaskType.FIX_BUG
        
        steps = planner.generate_steps(task_type, description, info, None)
        
        assert len(steps) > 0
        assert steps[0]["action"] == "locate_error"
        assert any(step["action"] == "analyze_code" for step in steps)
        assert any(step["action"] == "fix_code" for step in steps)
    
    def test_generate_refactor_steps(self, planner):
        """测试生成重构步骤"""
        description = "重构 code_analyzer.py"
        info = planner.extract_info(description)
        task_type = TaskType.REFACTOR
        
        steps = planner.generate_steps(task_type, description, info, None)
        
        assert len(steps) > 0
        assert steps[0]["action"] == "analyze_current"
        assert any(step["action"] == "refactor_code" for step in steps)


class TestTimeEstimation:
    """测试时间估算"""
    
    def test_estimate_time(self, planner):
        """测试时间估算"""
        steps = [
            {"id": 1, "estimated_minutes": 10},
            {"id": 2, "estimated_minutes": 20},
            {"id": 3, "estimated_minutes": 5}
        ]
        
        time_est = planner.estimate_time(steps)
        
        assert time_est["total_minutes"] == 35
        assert time_est["total_hours"] == 0.6
        assert "分钟" in time_est["formatted"] or "小时" in time_est["formatted"]


class TestDependencyAnalysis:
    """测试依赖分析"""
    
    def test_analyze_dependencies(self, planner):
        """测试依赖分析"""
        steps = [
            {"id": 1, "action": "step1"},
            {"id": 2, "action": "step2"},
            {"id": 3, "action": "step3"}
        ]
        
        deps = planner.analyze_dependencies(steps)
        
        # 步骤 2 依赖步骤 1
        assert 2 in deps
        assert 1 in deps[2]
        
        # 步骤 3 依赖步骤 2
        assert 3 in deps
        assert 2 in deps[3]


class TestFullPlan:
    """测试完整规划"""
    
    def test_plan_add_feature(self, planner):
        """测试规划添加功能"""
        description = "添加翻译工具"
        
        plan = planner.plan_task(description)
        
        assert plan["task_type"] == "add_feature"
        assert plan["description"] == description
        assert "steps" in plan
        assert len(plan["steps"]) > 0
        assert "time_estimate" in plan
        assert "dependencies" in plan
        assert plan["total_steps"] == len(plan["steps"])
    
    def test_plan_fix_bug(self, planner):
        """测试规划修复Bug"""
        description = "修复 butler.py 第 100 行的错误"
        
        plan = planner.plan_task(description)
        
        assert plan["task_type"] == "fix_bug"
        assert plan["extracted_info"]["target_file"] == "butler.py"
        assert plan["extracted_info"]["error_line"] == 100
        assert len(plan["steps"]) > 0
    
    def test_plan_refactor(self, planner):
        """测试规划重构"""
        description = "重构 code_analyzer.py"
        
        plan = planner.plan_task(description)
        
        assert plan["task_type"] == "refactor"
        assert plan["extracted_info"]["target_file"] == "code_analyzer.py"
        assert len(plan["steps"]) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
