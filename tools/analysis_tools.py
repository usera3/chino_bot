"""
代码分析工具
提供代码结构分析、函数查找、依赖分析等功能
"""
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field
import json
import os
from pathlib import Path

# 导入代码分析器
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.code_analyzer import code_analyzer


# ==================== 输入模型 ====================

class AnalyzeCodeInput(BaseModel):
    """分析代码结构的输入"""
    file_path: str = Field(description="要分析的文件路径（相对于项目根目录）")


class FindDefinitionInput(BaseModel):
    """查找定义的输入"""
    file_path: str = Field(description="文件路径（相对于项目根目录）")
    name: str = Field(description="要查找的函数或类名")
    type: str = Field(default="any", description="类型：'function', 'class', 'any'")


class AnalyzeDependenciesInput(BaseModel):
    """分析依赖的输入"""
    file_path: str = Field(description="文件路径（相对于项目根目录）")


# ==================== 工具类 ====================

class AnalyzeCodeStructureTool(BaseTool):
    """分析代码结构工具"""
    name: str = "analyze_code_structure"
    description: str = """分析 Python 文件的代码结构。
    
    返回信息：
    - 类列表（类名、方法、基类、文档字符串）
    - 函数列表（函数名、参数、返回值、文档字符串）
    - 导入列表（依赖的模块）
    - 代码行数
    - 圈复杂度（代码复杂程度）
    
    使用场景：
    - 用户说"分析 bot.py 的结构"
    - 用户说"这个文件有哪些类"
    - 用户说"查看代码复杂度"
    - 用户说"这个文件有什么功能"
    
    参数：
    - file_path: 文件路径（相对于项目根目录）
    
    示例：
    - analyze_code_structure("bot.py")
    - analyze_code_structure("core/butler.py")
    - analyze_code_structure("tools/basic_tools.py")
    """
    args_schema: Type[BaseModel] = AnalyzeCodeInput
    
    def _run(self, file_path: str) -> str:
        """执行分析"""
        try:
            # 构建完整路径
            full_path = os.path.join(code_analyzer.project_root, file_path)
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                return f"❌ 文件不存在: {file_path}"
            
            # 分析文件
            result = code_analyzer.analyze_file(full_path)
            
            # 检查是否有错误
            if 'error' in result:
                return f"❌ 分析失败: {result['error']}"
            
            # 格式化输出
            output = []
            output.append(f"📊 代码结构分析: {file_path}")
            output.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 基本信息
            output.append(f"\n📈 基本信息:")
            output.append(f"  - 代码行数: {result['lines']}")
            output.append(f"  - 圈复杂度: {result['complexity']}")
            output.append(f"  - 类数量: {len(result['classes'])}")
            output.append(f"  - 函数数量: {len(result['functions'])}")
            output.append(f"  - 导入数量: {len(result['imports'])}")
            
            # 类信息
            if result['classes']:
                output.append(f"\n📦 类列表:")
                for cls in result['classes']:
                    output.append(f"\n  🔹 {cls['name']} (行 {cls['line_start']}-{cls['line_end']})")
                    if cls['bases']:
                        output.append(f"     继承: {', '.join(cls['bases'])}")
                    if cls['docstring']:
                        output.append(f"     说明: {cls['docstring'][:60]}...")
                    if cls['methods']:
                        output.append(f"     方法: {', '.join([m['name'] for m in cls['methods']])}")
            
            # 函数信息
            if result['functions']:
                output.append(f"\n🔧 函数列表:")
                for func in result['functions']:
                    args_str = ', '.join(func['args'])
                    output.append(f"\n  🔹 {func['name']}({args_str}) (行 {func['line']})")
                    if func['returns']:
                        output.append(f"     返回: {func['returns']}")
                    if func['docstring']:
                        output.append(f"     说明: {func['docstring'][:60]}...")
            
            # 导入信息
            if result['imports']:
                output.append(f"\n📥 导入列表:")
                for imp in result['imports'][:10]:  # 只显示前 10 个
                    if imp['type'] == 'import':
                        output.append(f"  - import {imp['module']}")
                    else:
                        output.append(f"  - from {imp['module']} import {imp['name']}")
                
                if len(result['imports']) > 10:
                    output.append(f"  ... 还有 {len(result['imports']) - 10} 个导入")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 分析失败: {str(e)}"


class GetFunctionDefinitionTool(BaseTool):
    """获取函数定义工具"""
    name: str = "get_function_definition"
    description: str = """获取函数或类的完整定义和代码。
    
    返回信息：
    - 定义类型（函数/类）
    - 所在文件和行号
    - 完整代码
    - 文档字符串
    
    使用场景：
    - 用户说"找到 process 函数的定义"
    - 用户说"Butler 类在哪里"
    - 用户说"查看 analyze_file 的代码"
    - 用户说"这个函数是怎么实现的"
    
    参数：
    - file_path: 文件路径（相对于项目根目录）
    - name: 函数或类名
    - type: 类型（'function', 'class', 'any'）
    
    示例：
    - get_function_definition("core/butler.py", "Butler", "class")
    - get_function_definition("bot.py", "main", "function")
    """
    args_schema: Type[BaseModel] = FindDefinitionInput
    
    def _run(self, file_path: str, name: str, type: str = "any") -> str:
        """执行查找"""
        try:
            # 构建完整路径
            full_path = os.path.join(code_analyzer.project_root, file_path)
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                return f"❌ 文件不存在: {file_path}"
            
            # 查找定义
            result = code_analyzer.find_definition(full_path, name, type)
            
            # 检查结果
            if result is None:
                return f"❌ 未找到: {name} (类型: {type})"
            
            if 'error' in result:
                return f"❌ 查找失败: {result['error']}"
            
            # 格式化输出
            output = []
            output.append(f"🔍 定义查找: {name}")
            output.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            output.append(f"\n📍 位置信息:")
            output.append(f"  - 类型: {result['type']}")
            output.append(f"  - 文件: {result['file']}")
            output.append(f"  - 行号: {result['line_start']}-{result['line_end']}")
            
            if result.get('docstring'):
                output.append(f"\n📝 文档:")
                output.append(f"  {result['docstring']}")
            
            output.append(f"\n💻 代码:")
            output.append("```python")
            output.append(result['code'])
            output.append("```")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 查找失败: {str(e)}"


class AnalyzeDependenciesTool(BaseTool):
    """分析依赖工具"""
    name: str = "analyze_dependencies"
    description: str = """分析文件的依赖关系。
    
    返回信息：
    - 导入的标准库
    - 导入的第三方库
    - 导入的项目内模块
    - 依赖关系图
    
    使用场景：
    - 用户说"分析 bot.py 的依赖"
    - 用户说"这个文件用了哪些库"
    - 用户说"查看导入关系"
    - 用户说"有哪些外部依赖"
    
    参数：
    - file_path: 文件路径（相对于项目根目录）
    
    示例：
    - analyze_dependencies("bot.py")
    - analyze_dependencies("core/butler.py")
    """
    args_schema: Type[BaseModel] = AnalyzeDependenciesInput
    
    def _run(self, file_path: str) -> str:
        """执行分析"""
        try:
            # 构建完整路径
            full_path = os.path.join(code_analyzer.project_root, file_path)
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                return f"❌ 文件不存在: {file_path}"
            
            # 分析文件
            result = code_analyzer.analyze_file(full_path)
            
            # 检查是否有错误
            if 'error' in result:
                return f"❌ 分析失败: {result['error']}"
            
            imports = result['imports']
            
            # 分类导入
            stdlib = []
            third_party = []
            local = []
            
            # Python 标准库列表（部分）
            stdlib_modules = {
                'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 'typing',
                'collections', 'itertools', 'functools', 're', 'math', 'random',
                'logging', 'asyncio', 'threading', 'multiprocessing', 'subprocess',
                'tempfile', 'shutil', 'glob', 'pickle', 'csv', 'xml', 'html',
            }
            
            for imp in imports:
                module = imp['module']
                base_module = module.split('.')[0]
                
                if base_module in stdlib_modules:
                    stdlib.append(imp)
                elif module.startswith('.') or base_module in ['core', 'tools', 'plugins', 'models', 'config']:
                    local.append(imp)
                else:
                    third_party.append(imp)
            
            # 格式化输出
            output = []
            output.append(f"📦 依赖分析: {file_path}")
            output.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 统计
            output.append(f"\n📊 统计:")
            output.append(f"  - 总导入数: {len(imports)}")
            output.append(f"  - 标准库: {len(stdlib)}")
            output.append(f"  - 第三方库: {len(third_party)}")
            output.append(f"  - 项目内模块: {len(local)}")
            
            # 标准库
            if stdlib:
                output.append(f"\n📚 标准库:")
                for imp in stdlib[:10]:
                    if imp['type'] == 'import':
                        output.append(f"  - {imp['module']}")
                    else:
                        output.append(f"  - {imp['module']}.{imp['name']}")
                if len(stdlib) > 10:
                    output.append(f"  ... 还有 {len(stdlib) - 10} 个")
            
            # 第三方库
            if third_party:
                output.append(f"\n🔧 第三方库:")
                for imp in third_party:
                    if imp['type'] == 'import':
                        output.append(f"  - {imp['module']}")
                    else:
                        output.append(f"  - {imp['module']}.{imp['name']}")
            
            # 项目内模块
            if local:
                output.append(f"\n📁 项目内模块:")
                for imp in local:
                    if imp['type'] == 'import':
                        output.append(f"  - {imp['module']}")
                    else:
                        output.append(f"  - {imp['module']}.{imp['name']}")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 分析失败: {str(e)}"


# ==================== 工具列表 ====================

def get_analysis_tools():
    """获取所有代码分析工具"""
    return [
        AnalyzeCodeStructureTool(),
        GetFunctionDefinitionTool(),
        AnalyzeDependenciesTool(),
    ]


if __name__ == '__main__':
    # 测试工具
    print("🧪 测试代码分析工具...\n")
    
    tools = get_analysis_tools()
    print(f"✅ 加载了 {len(tools)} 个工具:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description.split('.')[0]}")
    
    # 测试分析代码结构
    print("\n" + "="*50)
    print("测试 1: 分析代码结构")
    print("="*50)
    tool = AnalyzeCodeStructureTool()
    result = tool._run("core/code_analyzer.py")
    print(result)
    
    # 测试查找定义
    print("\n" + "="*50)
    print("测试 2: 查找定义")
    print("="*50)
    tool = GetFunctionDefinitionTool()
    result = tool._run("core/code_analyzer.py", "CodeAnalyzer", "class")
    print(result[:500] + "...")  # 只显示前 500 字符
    
    # 测试分析依赖
    print("\n" + "="*50)
    print("测试 3: 分析依赖")
    print("="*50)
    tool = AnalyzeDependenciesTool()
    result = tool._run("core/code_analyzer.py")
    print(result)
    
    print("\n✅ 所有测试完成！")
