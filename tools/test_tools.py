"""
测试和错误分析工具
提供测试运行、错误分析、测试覆盖率等功能
"""
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field
import subprocess
import os
import sys
import re
from pathlib import Path

# 导入项目管理器
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.project_manager import project_manager


# ==================== 输入模型 ====================

class RunTestsInput(BaseModel):
    """运行测试的输入"""
    test_path: str = Field(description="测试文件或目录路径（相对于项目根目录）")
    test_function: Optional[str] = Field(default=None, description="指定测试函数名（可选）")
    verbose: bool = Field(default=False, description="是否显示详细输出")


class GetErrorContextInput(BaseModel):
    """获取错误上下文的输入"""
    file_path: str = Field(description="出错的文件路径（相对于项目根目录）")
    line_number: int = Field(description="错误行号")
    context_lines: int = Field(default=5, description="上下文行数（默认 5 行）")


# ==================== 工具类 ====================

class RunTestsTool(BaseTool):
    """运行测试工具"""
    name: str = "run_tests"
    description: str = """运行 pytest 测试。
    
    功能：
    - 运行单个测试文件
    - 运行测试目录
    - 运行指定测试函数
    - 显示测试结果和错误信息
    
    使用场景：
    - 用户说"运行测试"
    - 用户说"测试 test_butler.py"
    - 用户说"运行所有测试"
    - 用户说"测试 test_code_analyzer.py 的 test_analyze_simple_file 函数"
    
    参数：
    - test_path: 测试文件或目录路径（相对于项目根目录）
    - test_function: 指定测试函数名（可选）
    - verbose: 是否显示详细输出（默认 False）
    
    示例：
    - run_tests("tests/test_butler.py")
    - run_tests("tests", verbose=True)
    - run_tests("tests/test_code_analyzer.py", "test_analyze_simple_file")
    
    返回：
    - 测试结果（通过/失败）
    - 测试统计（总数、通过、失败、跳过）
    - 错误信息（如果有）
    - 执行时间
    """
    args_schema: Type[BaseModel] = RunTestsInput
    
    def _run(self, test_path: str, test_function: Optional[str] = None, verbose: bool = False) -> str:
        """执行测试"""
        try:
            # 构建完整路径
            full_path = os.path.join(project_manager.project_root, test_path)
            
            # 检查路径是否存在
            if not os.path.exists(full_path):
                return f"❌ 路径不存在: {test_path}"
            
            # 构建 pytest 命令
            cmd = ["python", "-m", "pytest"]
            
            # 添加路径
            if test_function:
                cmd.append(f"{full_path}::{test_function}")
            else:
                cmd.append(full_path)
            
            # 添加选项
            cmd.extend([
                "-v" if verbose else "-q",  # 详细或简洁模式
                "--tb=short",  # 简短的错误回溯
                "--color=no",  # 不使用颜色
            ])
            
            # 执行命令
            result = subprocess.run(
                cmd,
                cwd=project_manager.project_root,
                capture_output=True,
                text=True,
                timeout=60  # 60 秒超时
            )
            
            # 解析输出
            output = result.stdout + result.stderr
            
            # 提取测试统计
            stats = self._parse_test_stats(output)
            
            # 格式化输出
            formatted_output = []
            formatted_output.append("🧪 测试执行结果")
            formatted_output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 测试路径
            formatted_output.append(f"\n📁 测试路径: {test_path}")
            if test_function:
                formatted_output.append(f"🎯 测试函数: {test_function}")
            
            # 测试统计
            formatted_output.append(f"\n📊 测试统计:")
            formatted_output.append(f"  - 总数: {stats['total']}")
            formatted_output.append(f"  - 通过: {stats['passed']} ✅")
            if stats['failed'] > 0:
                formatted_output.append(f"  - 失败: {stats['failed']} ❌")
            if stats['skipped'] > 0:
                formatted_output.append(f"  - 跳过: {stats['skipped']} ⏭️")
            if stats['errors'] > 0:
                formatted_output.append(f"  - 错误: {stats['errors']} 💥")
            
            # 执行时间
            if stats['duration']:
                formatted_output.append(f"  - 耗时: {stats['duration']}")
            
            # 结果判断
            if result.returncode == 0:
                formatted_output.append(f"\n✅ 所有测试通过！")
            else:
                formatted_output.append(f"\n❌ 测试失败")
                
                # 提取失败信息
                failures = self._extract_failures(output)
                if failures:
                    formatted_output.append(f"\n💥 失败详情:")
                    for i, failure in enumerate(failures[:3], 1):  # 只显示前 3 个
                        formatted_output.append(f"\n  {i}. {failure['test']}")
                        formatted_output.append(f"     错误: {failure['error'][:100]}...")
                    
                    if len(failures) > 3:
                        formatted_output.append(f"\n  ... 还有 {len(failures) - 3} 个失败")
            
            # 详细输出（如果需要）
            if verbose and len(output) < 2000:
                formatted_output.append(f"\n📝 详细输出:")
                formatted_output.append("```")
                formatted_output.append(output[:1500])
                formatted_output.append("```")
            
            return '\n'.join(formatted_output)
        
        except subprocess.TimeoutExpired:
            return f"❌ 测试超时（超过 60 秒）"
        except Exception as e:
            return f"❌ 测试执行失败: {str(e)}"
    
    def _parse_test_stats(self, output: str) -> dict:
        """解析测试统计"""
        stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'duration': None,
        }
        
        # 匹配 pytest 输出格式
        # 例如: "5 passed, 2 failed in 1.23s"
        match = re.search(r'(\d+) passed', output)
        if match:
            stats['passed'] = int(match.group(1))
        
        match = re.search(r'(\d+) failed', output)
        if match:
            stats['failed'] = int(match.group(1))
        
        match = re.search(r'(\d+) skipped', output)
        if match:
            stats['skipped'] = int(match.group(1))
        
        match = re.search(r'(\d+) error', output)
        if match:
            stats['errors'] = int(match.group(1))
        
        match = re.search(r'in ([\d.]+s)', output)
        if match:
            stats['duration'] = match.group(1)
        
        stats['total'] = stats['passed'] + stats['failed'] + stats['skipped'] + stats['errors']
        
        return stats
    
    def _extract_failures(self, output: str) -> list:
        """提取失败信息"""
        failures = []
        
        # 简单的失败提取（可以改进）
        lines = output.split('\n')
        current_test = None
        current_error = []
        
        for line in lines:
            # 匹配测试名称
            if 'FAILED' in line:
                if current_test and current_error:
                    failures.append({
                        'test': current_test,
                        'error': '\n'.join(current_error)
                    })
                current_test = line.strip()
                current_error = []
            elif current_test and line.strip():
                current_error.append(line.strip())
        
        # 添加最后一个
        if current_test and current_error:
            failures.append({
                'test': current_test,
                'error': '\n'.join(current_error)
            })
        
        return failures


class GetErrorContextTool(BaseTool):
    """获取错误上下文工具"""
    name: str = "get_error_context"
    description: str = """获取代码错误的上下文信息。
    
    功能：
    - 显示错误行及其上下文
    - 高亮错误行
    - 显示行号
    - 帮助理解错误原因
    
    使用场景：
    - 用户说"查看第 50 行的错误"
    - 用户说"bot.py 第 100 行出错了"
    - 用户说"显示错误上下文"
    - 测试失败时自动调用
    
    参数：
    - file_path: 出错的文件路径（相对于项目根目录）
    - line_number: 错误行号
    - context_lines: 上下文行数（默认 5 行）
    
    示例：
    - get_error_context("bot.py", 50)
    - get_error_context("core/butler.py", 100, 10)
    
    返回：
    - 错误行及其上下文
    - 行号标注
    - 错误行高亮
    """
    args_schema: Type[BaseModel] = GetErrorContextInput
    
    def _run(self, file_path: str, line_number: int, context_lines: int = 5) -> str:
        """执行获取错误上下文"""
        try:
            # 构建完整路径
            full_path = os.path.join(project_manager.project_root, file_path)
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                return f"❌ 文件不存在: {file_path}"
            
            # 读取文件
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 检查行号是否有效
            if line_number < 1 or line_number > len(lines):
                return f"❌ 行号无效: {line_number}（文件共 {len(lines)} 行）"
            
            # 计算上下文范围
            start_line = max(1, line_number - context_lines)
            end_line = min(len(lines), line_number + context_lines)
            
            # 格式化输出
            output = []
            output.append(f"🔍 错误上下文: {file_path}")
            output.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append(f"\n📍 错误位置: 第 {line_number} 行")
            output.append(f"📄 上下文范围: 第 {start_line}-{end_line} 行")
            output.append(f"\n💻 代码:")
            output.append("```python")
            
            # 显示代码
            for i in range(start_line - 1, end_line):
                line_num = i + 1
                line_content = lines[i].rstrip()
                
                if line_num == line_number:
                    # 错误行高亮
                    output.append(f">>> {line_num:4d} | {line_content}  # ❌ 错误行")
                else:
                    output.append(f"    {line_num:4d} | {line_content}")
            
            output.append("```")
            
            # 添加建议
            output.append(f"\n💡 建议:")
            output.append(f"  - 检查第 {line_number} 行的语法")
            output.append(f"  - 查看相关的导入和变量定义")
            output.append(f"  - 使用 analyze_code_structure 分析文件结构")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 获取错误上下文失败: {str(e)}"


class AnalyzeTestCoverageTool(BaseTool):
    """分析测试覆盖率工具"""
    name: str = "analyze_test_coverage"
    description: str = """分析项目的测试覆盖率。
    
    功能：
    - 统计测试文件数量
    - 统计代码文件数量
    - 计算覆盖率
    - 列出未测试的文件
    
    使用场景：
    - 用户说"查看测试覆盖率"
    - 用户说"有哪些文件没有测试"
    - 用户说"测试完整性如何"
    
    返回：
    - 测试文件统计
    - 代码文件统计
    - 覆盖率百分比
    - 未测试文件列表
    """
    
    def _run(self) -> str:
        """执行分析测试覆盖率"""
        try:
            # 查找所有 Python 文件
            code_files = []
            test_files = []
            
            for root, dirs, files in os.walk(project_manager.project_root):
                # 跳过虚拟环境和隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__', 'node_modules']]
                
                for file in files:
                    if file.endswith('.py'):
                        rel_path = os.path.relpath(os.path.join(root, file), project_manager.project_root)
                        
                        if file.startswith('test_') or '/tests/' in rel_path or '/test/' in rel_path:
                            test_files.append(rel_path)
                        else:
                            code_files.append(rel_path)
            
            # 分析哪些代码文件有对应的测试
            tested_files = set()
            untested_files = []
            
            for code_file in code_files:
                # 跳过一些不需要测试的文件
                if any(skip in code_file for skip in ['__init__.py', 'setup.py', 'config.py']):
                    continue
                
                # 查找对应的测试文件
                base_name = os.path.basename(code_file).replace('.py', '')
                test_name = f"test_{base_name}.py"
                
                has_test = any(test_name in test_file for test_file in test_files)
                
                if has_test:
                    tested_files.add(code_file)
                else:
                    untested_files.append(code_file)
            
            # 计算覆盖率
            total_code_files = len([f for f in code_files if not any(skip in f for skip in ['__init__.py', 'setup.py', 'config.py'])])
            coverage = (len(tested_files) / total_code_files * 100) if total_code_files > 0 else 0
            
            # 格式化输出
            output = []
            output.append("📊 测试覆盖率分析")
            output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 统计
            output.append(f"\n📈 统计:")
            output.append(f"  - 代码文件: {total_code_files}")
            output.append(f"  - 测试文件: {len(test_files)}")
            output.append(f"  - 已测试: {len(tested_files)}")
            output.append(f"  - 未测试: {len(untested_files)}")
            output.append(f"  - 覆盖率: {coverage:.1f}%")
            
            # 覆盖率评级
            if coverage >= 80:
                output.append(f"\n✅ 覆盖率良好！")
            elif coverage >= 60:
                output.append(f"\n⚠️ 覆盖率中等，建议增加测试")
            else:
                output.append(f"\n❌ 覆盖率较低，需要增加测试")
            
            # 未测试文件
            if untested_files:
                output.append(f"\n📝 未测试文件（前 10 个）:")
                for file in untested_files[:10]:
                    output.append(f"  - {file}")
                
                if len(untested_files) > 10:
                    output.append(f"  ... 还有 {len(untested_files) - 10} 个文件")
            
            # 测试文件列表
            if test_files:
                output.append(f"\n🧪 测试文件（前 10 个）:")
                for file in test_files[:10]:
                    output.append(f"  - {file}")
                
                if len(test_files) > 10:
                    output.append(f"  ... 还有 {len(test_files) - 10} 个文件")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 分析测试覆盖率失败: {str(e)}"


# ==================== 工具列表 ====================

def get_test_tools():
    """获取所有测试工具"""
    return [
        RunTestsTool(),
        GetErrorContextTool(),
        AnalyzeTestCoverageTool(),
    ]


if __name__ == '__main__':
    # 测试工具
    print("🧪 测试测试工具...\n")
    
    tools = get_test_tools()
    print(f"✅ 加载了 {len(tools)} 个工具:")
    for tool in tools:
        print(f"  - {tool.name}")
    
    # 测试运行测试
    print("\n" + "="*50)
    print("测试 1: 运行测试")
    print("="*50)
    tool = RunTestsTool()
    result = tool._run("tests/test_code_analyzer.py")
    print(result)
    
    # 测试获取错误上下文
    print("\n" + "="*50)
    print("测试 2: 获取错误上下文")
    print("="*50)
    tool = GetErrorContextTool()
    result = tool._run("core/code_analyzer.py", 50, 3)
    print(result)
    
    # 测试分析测试覆盖率
    print("\n" + "="*50)
    print("测试 3: 分析测试覆盖率")
    print("="*50)
    tool = AnalyzeTestCoverageTool()
    result = tool._run()
    print(result)
    
    print("\n✅ 所有测试完成！")
