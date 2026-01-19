"""
任务规划器
分解编程任务为可执行的步骤
"""
import re
from typing import Dict, List, Optional
from enum import Enum


class TaskType(Enum):
    """任务类型"""
    ADD_FEATURE = "add_feature"  # 添加新功能
    FIX_BUG = "fix_bug"  # 修复 Bug
    REFACTOR = "refactor"  # 重构代码
    OPTIMIZE = "optimize"  # 优化性能
    ADD_TEST = "add_test"  # 添加测试
    UPDATE_DOC = "update_doc"  # 更新文档
    UNKNOWN = "unknown"  # 未知类型


class TaskPlanner:
    """任务规划器"""
    
    def __init__(self):
        """初始化任务规划器"""
        # 任务类型关键词
        self.task_keywords = {
            TaskType.ADD_FEATURE: [
                "添加", "新增", "创建", "实现", "开发", "add", "create", "implement", "new"
            ],
            TaskType.FIX_BUG: [
                "修复", "解决", "修改", "fix", "solve", "bug", "error", "问题"
            ],
            TaskType.REFACTOR: [
                "重构", "优化结构", "改进", "refactor", "restructure", "improve"
            ],
            TaskType.OPTIMIZE: [
                "优化", "提升性能", "加速", "optimize", "performance", "speed up"
            ],
            TaskType.ADD_TEST: [
                "测试", "test", "单元测试", "集成测试"
            ],
            TaskType.UPDATE_DOC: [
                "文档", "注释", "说明", "doc", "documentation", "comment"
            ]
        }
        
        # 步骤模板
        self.step_templates = {
            TaskType.ADD_FEATURE: self._template_add_feature,
            TaskType.FIX_BUG: self._template_fix_bug,
            TaskType.REFACTOR: self._template_refactor,
            TaskType.OPTIMIZE: self._template_optimize,
            TaskType.ADD_TEST: self._template_add_test,
            TaskType.UPDATE_DOC: self._template_update_doc,
        }
    
    def plan_task(self, description: str, context: Optional[Dict] = None) -> Dict:
        """
        规划任务
        
        Args:
            description: 任务描述
            context: 上下文信息（可选）
            
        Returns:
            任务规划结果
        """
        # 1. 分类任务
        task_type = self.classify_task(description)
        
        # 2. 提取关键信息
        info = self.extract_info(description)
        
        # 3. 生成步骤
        steps = self.generate_steps(task_type, description, info, context)
        
        # 4. 估算时间
        time_estimate = self.estimate_time(steps)
        
        # 5. 分析依赖
        dependencies = self.analyze_dependencies(steps)
        
        return {
            "task_type": task_type.value,
            "description": description,
            "extracted_info": info,
            "steps": steps,
            "time_estimate": time_estimate,
            "dependencies": dependencies,
            "total_steps": len(steps)
        }
    
    def classify_task(self, description: str) -> TaskType:
        """
        分类任务类型
        
        Args:
            description: 任务描述
            
        Returns:
            任务类型
        """
        description_lower = description.lower()
        
        # 计算每种类型的匹配分数
        scores = {}
        for task_type, keywords in self.task_keywords.items():
            score = sum(1 for keyword in keywords if keyword in description_lower)
            scores[task_type] = score
        
        # 返回得分最高的类型
        max_score = max(scores.values())
        if max_score == 0:
            return TaskType.UNKNOWN
        
        for task_type, score in scores.items():
            if score == max_score:
                return task_type
        
        return TaskType.UNKNOWN
    
    def extract_info(self, description: str) -> Dict:
        """
        提取关键信息
        
        Args:
            description: 任务描述
            
        Returns:
            提取的信息
        """
        info = {
            "target_file": None,
            "target_function": None,
            "target_class": None,
            "feature_name": None,
            "error_line": None,
        }
        
        # 提取文件名
        file_pattern = r'([a-zA-Z0-9_]+\.py)'
        file_match = re.search(file_pattern, description)
        if file_match:
            info["target_file"] = file_match.group(1)
        
        # 提取函数名
        func_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*函数|函数\s*([a-zA-Z_][a-zA-Z0-9_]*)'
        func_match = re.search(func_pattern, description)
        if func_match:
            info["target_function"] = func_match.group(1) or func_match.group(2)
        
        # 提取类名
        class_pattern = r'([A-Z][a-zA-Z0-9_]*)\s*类|类\s*([A-Z][a-zA-Z0-9_]*)'
        class_match = re.search(class_pattern, description)
        if class_match:
            info["target_class"] = class_match.group(1) or class_match.group(2)
        
        # 提取行号
        line_pattern = r'第?\s*(\d+)\s*行'
        line_match = re.search(line_pattern, description)
        if line_match:
            info["error_line"] = int(line_match.group(1))
        
        # 提取功能名称（简单提取）
        feature_patterns = [
            r'添加\s*([^，。！？\s]+)',
            r'创建\s*([^，。！？\s]+)',
            r'实现\s*([^，。！？\s]+)',
        ]
        for pattern in feature_patterns:
            match = re.search(pattern, description)
            if match:
                info["feature_name"] = match.group(1)
                break
        
        return info
    
    def generate_steps(
        self, 
        task_type: TaskType, 
        description: str, 
        info: Dict,
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        生成执行步骤
        
        Args:
            task_type: 任务类型
            description: 任务描述
            info: 提取的信息
            context: 上下文信息
            
        Returns:
            步骤列表
        """
        # 使用模板生成步骤
        template_func = self.step_templates.get(task_type)
        if template_func:
            return template_func(description, info, context)
        else:
            return self._template_unknown(description, info, context)
    
    def _template_add_feature(self, description: str, info: Dict, context: Optional[Dict]) -> List[Dict]:
        """添加功能的步骤模板"""
        feature_name = info.get("feature_name") or "新功能"
        file_name = info.get("target_file") or f"{feature_name.lower()}_tool.py"
        
        steps = [
            {
                "id": 1,
                "action": "analyze_requirements",
                "description": f"分析 {feature_name} 的需求",
                "tool": "analyze_code_structure",
                "estimated_minutes": 5
            },
            {
                "id": 2,
                "action": "create_file",
                "target": f"tools/{file_name}",
                "description": f"创建 {file_name} 文件",
                "tool": "write_project_file",
                "estimated_minutes": 2
            },
            {
                "id": 3,
                "action": "implement_feature",
                "target": f"tools/{file_name}",
                "description": f"实现 {feature_name} 功能",
                "tool": "write_project_file",
                "estimated_minutes": 20
            },
            {
                "id": 4,
                "action": "register_tool",
                "target": "tools/basic_tools.py",
                "description": "注册工具到工具列表",
                "tool": "write_project_file",
                "estimated_minutes": 5
            },
            {
                "id": 5,
                "action": "write_test",
                "target": f"tests/test_{file_name}",
                "description": "编写测试用例",
                "tool": "write_project_file",
                "estimated_minutes": 15
            },
            {
                "id": 6,
                "action": "run_test",
                "target": f"tests/test_{file_name}",
                "description": "运行测试验证",
                "tool": "run_tests",
                "estimated_minutes": 2
            },
            {
                "id": 7,
                "action": "update_butler",
                "target": "core/butler.py",
                "description": "更新 Butler 提示词",
                "tool": "write_project_file",
                "estimated_minutes": 5
            }
        ]
        
        return steps
    
    def _template_fix_bug(self, description: str, info: Dict, context: Optional[Dict]) -> List[Dict]:
        """修复 Bug 的步骤模板"""
        target_file = info.get("target_file") or "目标文件"
        error_line = info.get("error_line")
        
        steps = [
            {
                "id": 1,
                "action": "locate_error",
                "target": target_file,
                "description": f"定位错误位置",
                "tool": "get_error_context",
                "estimated_minutes": 3
            },
            {
                "id": 2,
                "action": "analyze_code",
                "target": target_file,
                "description": "分析相关代码",
                "tool": "analyze_code_structure",
                "estimated_minutes": 5
            },
            {
                "id": 3,
                "action": "identify_cause",
                "description": "识别错误原因",
                "tool": None,
                "estimated_minutes": 5
            },
            {
                "id": 4,
                "action": "fix_code",
                "target": target_file,
                "description": "修复代码",
                "tool": "write_project_file",
                "estimated_minutes": 10
            },
            {
                "id": 5,
                "action": "run_test",
                "target": target_file,
                "description": "运行测试验证修复",
                "tool": "run_tests",
                "estimated_minutes": 2
            }
        ]
        
        return steps
    
    def _template_refactor(self, description: str, info: Dict, context: Optional[Dict]) -> List[Dict]:
        """重构代码的步骤模板"""
        target_file = info.get("target_file") or "目标文件"
        
        steps = [
            {
                "id": 1,
                "action": "analyze_current",
                "target": target_file,
                "description": "分析当前代码结构",
                "tool": "analyze_code_structure",
                "estimated_minutes": 5
            },
            {
                "id": 2,
                "action": "identify_issues",
                "description": "识别需要改进的地方",
                "tool": "analyze_dependencies",
                "estimated_minutes": 5
            },
            {
                "id": 3,
                "action": "plan_refactor",
                "description": "规划重构方案",
                "tool": None,
                "estimated_minutes": 10
            },
            {
                "id": 4,
                "action": "refactor_code",
                "target": target_file,
                "description": "重构代码",
                "tool": "write_project_file",
                "estimated_minutes": 20
            },
            {
                "id": 5,
                "action": "run_test",
                "description": "运行测试确保功能不变",
                "tool": "run_tests",
                "estimated_minutes": 3
            }
        ]
        
        return steps
    
    def _template_optimize(self, description: str, info: Dict, context: Optional[Dict]) -> List[Dict]:
        """优化性能的步骤模板"""
        target_file = info.get("target_file") or "目标文件"
        
        steps = [
            {
                "id": 1,
                "action": "profile_code",
                "target": target_file,
                "description": "分析性能瓶颈",
                "tool": "analyze_code_structure",
                "estimated_minutes": 10
            },
            {
                "id": 2,
                "action": "identify_bottleneck",
                "description": "识别性能瓶颈",
                "tool": None,
                "estimated_minutes": 5
            },
            {
                "id": 3,
                "action": "optimize_code",
                "target": target_file,
                "description": "优化代码",
                "tool": "write_project_file",
                "estimated_minutes": 15
            },
            {
                "id": 4,
                "action": "benchmark",
                "description": "性能测试对比",
                "tool": "run_tests",
                "estimated_minutes": 5
            }
        ]
        
        return steps
    
    def _template_add_test(self, description: str, info: Dict, context: Optional[Dict]) -> List[Dict]:
        """添加测试的步骤模板"""
        target_file = info.get("target_file") or "目标文件"
        test_file = f"tests/test_{target_file}"
        
        steps = [
            {
                "id": 1,
                "action": "analyze_code",
                "target": target_file,
                "description": "分析需要测试的代码",
                "tool": "analyze_code_structure",
                "estimated_minutes": 5
            },
            {
                "id": 2,
                "action": "design_test_cases",
                "description": "设计测试用例",
                "tool": None,
                "estimated_minutes": 10
            },
            {
                "id": 3,
                "action": "write_test",
                "target": test_file,
                "description": "编写测试代码",
                "tool": "write_project_file",
                "estimated_minutes": 15
            },
            {
                "id": 4,
                "action": "run_test",
                "target": test_file,
                "description": "运行测试",
                "tool": "run_tests",
                "estimated_minutes": 2
            }
        ]
        
        return steps
    
    def _template_update_doc(self, description: str, info: Dict, context: Optional[Dict]) -> List[Dict]:
        """更新文档的步骤模板"""
        target_file = info.get("target_file") or "README.md"
        
        steps = [
            {
                "id": 1,
                "action": "review_code",
                "description": "审查代码变更",
                "tool": "analyze_code_structure",
                "estimated_minutes": 5
            },
            {
                "id": 2,
                "action": "update_doc",
                "target": target_file,
                "description": "更新文档内容",
                "tool": "write_project_file",
                "estimated_minutes": 10
            },
            {
                "id": 3,
                "action": "review_doc",
                "description": "审查文档完整性",
                "tool": "read_project_file",
                "estimated_minutes": 3
            }
        ]
        
        return steps
    
    def _template_unknown(self, description: str, info: Dict, context: Optional[Dict]) -> List[Dict]:
        """未知类型的通用模板"""
        steps = [
            {
                "id": 1,
                "action": "analyze_request",
                "description": "分析任务需求",
                "tool": None,
                "estimated_minutes": 5
            },
            {
                "id": 2,
                "action": "plan_approach",
                "description": "规划实施方案",
                "tool": None,
                "estimated_minutes": 10
            },
            {
                "id": 3,
                "action": "execute",
                "description": "执行任务",
                "tool": None,
                "estimated_minutes": 20
            },
            {
                "id": 4,
                "action": "verify",
                "description": "验证结果",
                "tool": "run_tests",
                "estimated_minutes": 5
            }
        ]
        
        return steps
    
    def estimate_time(self, steps: List[Dict]) -> Dict:
        """
        估算时间
        
        Args:
            steps: 步骤列表
            
        Returns:
            时间估算
        """
        total_minutes = sum(step.get("estimated_minutes", 0) for step in steps)
        
        return {
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 1),
            "formatted": self._format_time(total_minutes)
        }
    
    def _format_time(self, minutes: int) -> str:
        """格式化时间"""
        if minutes < 60:
            return f"{minutes}分钟"
        else:
            hours = minutes // 60
            mins = minutes % 60
            if mins == 0:
                return f"{hours}小时"
            else:
                return f"{hours}小时{mins}分钟"
    
    def analyze_dependencies(self, steps: List[Dict]) -> Dict:
        """
        分析步骤依赖
        
        Args:
            steps: 步骤列表
            
        Returns:
            依赖关系
        """
        dependencies = {}
        
        # 简单的顺序依赖：每个步骤依赖前一个步骤
        for i, step in enumerate(steps):
            if i > 0:
                dependencies[step["id"]] = [steps[i-1]["id"]]
        
        return dependencies


# 全局实例
task_planner = TaskPlanner()
