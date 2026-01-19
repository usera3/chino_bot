"""
代码操作工具
提供文件读写、列表、搜索等功能
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, List
from core.project_manager import project_manager
from core.security import PathValidationError, get_relative_path


# ==================== 读取项目文件工具 ====================

class ReadProjectFileInput(BaseModel):
    """读取项目文件输入"""
    file_path: str = Field(description="文件路径（相对于项目根目录），例如：bot.py 或 tools/basic_tools.py")


class ReadProjectFileTool(BaseTool):
    """读取项目文件工具"""
    name: str = "read_project_file"
    description: str = """读取项目中的文件内容。

⚠️ 使用场景：
- 查看代码文件内容
- 查看配置文件
- 查看文档内容
- 理解代码结构

参数：
- file_path: 文件路径（相对于项目根目录）

示例：
- read_project_file("bot.py")
- read_project_file("tools/basic_tools.py")
- read_project_file("README.md")

返回：文件内容

⚠️ 注意：
- 只能读取项目目录内的文件
- 路径验证失败会抛出错误
- 大文件可能需要较长时间"""
    args_schema: type[BaseModel] = ReadProjectFileInput
    
    def _run(self, file_path: str) -> str:
        """执行工具"""
        try:
            # 读取文件
            content = project_manager.read_file(file_path, user_id="butler")
            
            # 获取文件信息
            info = project_manager.get_file_info(file_path, user_id="butler")
            
            # 格式化输出
            result = f"""📁 文件: {info['path']}
📊 大小: {info['size_kb']:.2f} KB
📝 行数: {info['lines']}

{'='*60}
{content}
{'='*60}"""
            
            return result
        
        except PathValidationError as e:
            return f"❌ 路径验证失败: {str(e)}"
        except FileNotFoundError as e:
            return f"❌ 文件不存在: {str(e)}"
        except Exception as e:
            return f"❌ 读取文件失败: {str(e)}"
    
    async def _arun(self, file_path: str) -> str:
        """异步执行"""
        return self._run(file_path)


# ==================== 写入项目文件工具 ====================

class WriteProjectFileInput(BaseModel):
    """写入项目文件输入"""
    file_path: str = Field(description="文件路径（相对于项目根目录）")
    content: str = Field(description="文件内容")


class WriteProjectFileTool(BaseTool):
    """写入项目文件工具"""
    name: str = "write_project_file"
    description: str = """写入项目文件。

⚠️ 危险操作！需要管理员权限！

使用场景：
- 创建新文件
- 修改现有文件
- 保存代码

参数：
- file_path: 文件路径（相对于项目根目录）
- content: 文件内容

示例：
- write_project_file("test_new.py", "print('hello')")
- write_project_file("tools/new_tool.py", "...")

返回：写入结果

⚠️ 注意：
- 这是危险操作，会覆盖现有文件
- 只有管理员可以执行
- 所有操作会被审计记录
- 建议先备份重要文件"""
    args_schema: type[BaseModel] = WriteProjectFileInput
    
    def _run(self, file_path: str, content: str) -> str:
        """执行工具"""
        try:
            # 写入文件
            success = project_manager.write_file(file_path, content, user_id="butler")
            
            if success:
                # 获取文件信息
                info = project_manager.get_file_info(file_path, user_id="butler")
                
                return f"""✅ 文件写入成功！
📁 文件: {info['path']}
📊 大小: {info['size_kb']:.2f} KB
📝 行数: {info['lines']}

💡 提示：文件已保存，所有操作已记录到审计日志"""
            else:
                return "❌ 文件写入失败"
        
        except PathValidationError as e:
            return f"❌ 路径验证失败: {str(e)}"
        except PermissionError as e:
            return f"❌ 权限不足: {str(e)}"
        except Exception as e:
            return f"❌ 写入文件失败: {str(e)}"
    
    async def _arun(self, file_path: str, content: str) -> str:
        """异步执行"""
        return self._run(file_path, content)


# ==================== 列出项目文件工具 ====================

class ListProjectFilesInput(BaseModel):
    """列出项目文件输入"""
    directory: str = Field(default=".", description="目录路径（相对于项目根目录），默认为当前目录")
    pattern: str = Field(default="*", description="文件匹配模式，例如：*.py, *.md")
    recursive: bool = Field(default=False, description="是否递归列出子目录，默认 False")


class ListProjectFilesTool(BaseTool):
    """列出项目文件工具"""
    name: str = "list_project_files"
    description: str = """列出项目目录中的文件。

使用场景：
- 查看目录结构
- 查找特定类型的文件
- 了解项目组织

参数：
- directory: 目录路径（可选，默认为当前目录）
- pattern: 文件匹配模式（可选，默认为 *）
- recursive: 是否递归（可选，默认 False）

示例：
- list_project_files()  # 列出根目录所有文件
- list_project_files("tools", "*.py")  # 列出 tools 目录的 Python 文件
- list_project_files(".", "*.md", True)  # 递归列出所有 Markdown 文件

返回：文件列表"""
    args_schema: type[BaseModel] = ListProjectFilesInput
    
    def _run(self, directory: str = ".", pattern: str = "*", recursive: bool = False) -> str:
        """执行工具"""
        try:
            # 列出文件
            files = project_manager.list_files(
                directory=directory,
                pattern=pattern,
                recursive=recursive,
                user_id="butler"
            )
            
            if not files:
                return f"📭 目录 '{directory}' 中没有匹配 '{pattern}' 的文件"
            
            # 格式化输出
            result = f"""📁 目录: {directory}
🔍 模式: {pattern}
📊 找到: {len(files)} 个文件

"""
            
            # 按目录分组
            from collections import defaultdict
            by_dir = defaultdict(list)
            
            for file in files:
                dir_name = file.rsplit('/', 1)[0] if '/' in file else '.'
                file_name = file.rsplit('/', 1)[1] if '/' in file else file
                by_dir[dir_name].append(file_name)
            
            # 输出
            for dir_name in sorted(by_dir.keys()):
                result += f"\n📂 {dir_name}/\n"
                for file_name in sorted(by_dir[dir_name]):
                    result += f"  - {file_name}\n"
            
            return result
        
        except PathValidationError as e:
            return f"❌ 路径验证失败: {str(e)}"
        except Exception as e:
            return f"❌ 列出文件失败: {str(e)}"
    
    async def _arun(self, directory: str = ".", pattern: str = "*", recursive: bool = False) -> str:
        """异步执行"""
        return self._run(directory, pattern, recursive)


# ==================== 搜索文件内容工具 ====================

class SearchInFilesInput(BaseModel):
    """搜索文件内容输入"""
    pattern: str = Field(description="搜索模式（字符串）")
    file_pattern: str = Field(default="*.py", description="文件匹配模式，默认 *.py")
    directory: str = Field(default=".", description="搜索目录，默认为当前目录")
    max_results: int = Field(default=20, description="最多返回结果数，默认 20")


class SearchInFilesTool(BaseTool):
    """搜索文件内容工具"""
    name: str = "search_in_files"
    description: str = """在项目文件中搜索内容。

使用场景：
- 查找函数定义
- 查找类定义
- 查找特定代码
- 查找配置项

参数：
- pattern: 搜索模式（字符串）
- file_pattern: 文件匹配模式（可选，默认 *.py）
- directory: 搜索目录（可选，默认当前目录）
- max_results: 最多返回结果数（可选，默认 20）

示例：
- search_in_files("Butler")  # 在所有 Python 文件中搜索 "Butler"
- search_in_files("def process", "*.py", "core")  # 在 core 目录搜索函数定义
- search_in_files("TODO", "*.py", ".", 50)  # 搜索所有 TODO 注释

返回：搜索结果（文件名、行号、内容）"""
    args_schema: type[BaseModel] = SearchInFilesInput
    
    def _run(
        self, 
        pattern: str, 
        file_pattern: str = "*.py",
        directory: str = ".",
        max_results: int = 20
    ) -> str:
        """执行工具"""
        try:
            # 搜索文件
            results = project_manager.search_in_files(
                pattern=pattern,
                file_pattern=file_pattern,
                directory=directory,
                max_results=max_results,
                user_id="butler"
            )
            
            if not results:
                return f"📭 没有找到匹配 '{pattern}' 的内容"
            
            # 格式化输出
            output = f"""🔍 搜索: {pattern}
📁 目录: {directory}
🔍 文件: {file_pattern}
📊 找到: {len(results)} 个匹配

"""
            
            for i, result in enumerate(results, 1):
                output += f"""[{i}] {result['file']}:{result['line']}
    {result['content']}

"""
            
            if len(results) >= max_results:
                output += f"\n⚠️ 结果已达到上限 ({max_results})，可能还有更多匹配"
            
            return output
        
        except PathValidationError as e:
            return f"❌ 路径验证失败: {str(e)}"
        except Exception as e:
            return f"❌ 搜索失败: {str(e)}"
    
    async def _arun(
        self,
        pattern: str,
        file_pattern: str = "*.py",
        directory: str = ".",
        max_results: int = 20
    ) -> str:
        """异步执行"""
        return self._run(pattern, file_pattern, directory, max_results)


# ==================== 获取目录树工具 ====================

class GetDirectoryTreeInput(BaseModel):
    """获取目录树输入"""
    directory: str = Field(default=".", description="目录路径，默认为当前目录")
    max_depth: int = Field(default=2, description="最大深度，默认 2")


class GetDirectoryTreeTool(BaseTool):
    """获取目录树工具"""
    name: str = "get_directory_tree"
    description: str = """获取目录树结构。

使用场景：
- 查看项目结构
- 了解目录组织
- 快速浏览文件

参数：
- directory: 目录路径（可选，默认当前目录）
- max_depth: 最大深度（可选，默认 2）

示例：
- get_directory_tree()  # 查看根目录结构
- get_directory_tree("tools", 1)  # 查看 tools 目录（深度 1）
- get_directory_tree("core", 3)  # 查看 core 目录（深度 3）

返回：目录树（树形结构）"""
    args_schema: type[BaseModel] = GetDirectoryTreeInput
    
    def _run(self, directory: str = ".", max_depth: int = 2) -> str:
        """执行工具"""
        try:
            # 获取目录树
            tree = project_manager.get_directory_tree(
                directory=directory,
                max_depth=max_depth,
                user_id="butler"
            )
            
            return f"""📂 目录树: {directory}
📊 深度: {max_depth}

{tree}

💡 提示：使用 list_project_files 可以获取更详细的文件列表"""
        
        except PathValidationError as e:
            return f"❌ 路径验证失败: {str(e)}"
        except Exception as e:
            return f"❌ 获取目录树失败: {str(e)}"
    
    async def _arun(self, directory: str = ".", max_depth: int = 2) -> str:
        """异步执行"""
        return self._run(directory, max_depth)


# ==================== 工具列表 ====================

def get_code_tools() -> List[BaseTool]:
    """获取所有代码操作工具"""
    return [
        ReadProjectFileTool(),
        WriteProjectFileTool(),
        ListProjectFilesTool(),
        SearchInFilesTool(),
        GetDirectoryTreeTool(),
    ]
