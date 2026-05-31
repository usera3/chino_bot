"""
代码修改工具
提供代码更改预览和应用功能
"""
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field
import sys
from pathlib import Path

# 导入代码修改器
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.code_modifier import code_modifier
from core.project_manager import project_manager


# ==================== 输入模型 ====================

class PreviewChangesInput(BaseModel):
    """预览代码更改的输入"""
    file_path: str = Field(description="文件路径（相对于项目根目录）")
    new_content: str = Field(description="新的文件内容")


class ApplyChangesInput(BaseModel):
    """应用代码更改的输入"""
    file_path: str = Field(description="文件路径（相对于项目根目录）")
    new_content: str = Field(description="新的文件内容")
    create_backup: bool = Field(default=True, description="是否创建备份（默认 True）")


class FormatCodeInput(BaseModel):
    """格式化代码的输入"""
    file_path: str = Field(description="文件路径（相对于项目根目录）")


# ==================== 工具类 ====================

class PreviewChangesTool(BaseTool):
    """预览代码更改工具"""
    name: str = "preview_code_changes"
    description: str = """预览代码更改，生成 diff 对比。
    
    功能：
    - 对比原文件和新内容
    - 生成 unified diff
    - 显示添加/删除的行数
    - 不会修改文件
    
    使用场景：
    - 在应用更改前预览
    - 确认更改是否正确
    - 向用户展示将要进行的修改
    
    参数：
    - file_path: 文件路径
    - new_content: 新的文件内容
    
    示例：
    - preview_code_changes("core/butler.py", "新的代码内容...")
    
    返回：
    - diff 对比
    - 统计信息（添加/删除行数）
    """
    args_schema: Type[BaseModel] = PreviewChangesInput
    
    def _run(self, file_path: str, new_content: str) -> str:
        """执行预览"""
        try:
            # 读取原文件
            success, original_content, error = project_manager.read_file(file_path)
            
            if not success:
                return f"❌ 读取文件失败: {error}"
            
            # 生成 diff
            diff = code_modifier.generate_diff(
                original_content,
                new_content,
                file_path
            )
            
            if not diff:
                return "✅ 文件内容没有变化"
            
            # 提取更改信息
            changes = code_modifier.extract_changes(diff)
            
            # 格式化输出
            output = []
            output.append(f"📝 预览代码更改: {file_path}")
            output.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 统计信息
            output.append(f"\n📊 更改统计:")
            output.append(f"  ✅ 添加: {changes['additions']} 行")
            output.append(f"  ❌ 删除: {changes['deletions']} 行")
            output.append(f"  📍 修改块: {len(changes['hunks'])} 个")
            
            # diff 内容
            output.append(f"\n🔍 详细对比:")
            output.append(f"```diff")
            output.append(diff)
            output.append(f"```")
            
            # 提示
            output.append(f"\n💡 提示:")
            output.append(f"  - 使用 apply_code_changes 应用更改")
            output.append(f"  - 会自动创建备份文件")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 预览失败: {str(e)}"


class ApplyChangesTool(BaseTool):
    """应用代码更改工具"""
    name: str = "apply_code_changes"
    description: str = """应用代码更改到文件。⚠️ 需要管理员权限！
    
    功能：
    - 将新内容写入文件
    - 自动创建备份
    - 验证语法（Python 文件）
    - 记录审计日志
    
    使用场景：
    - 修改代码文件
    - 更新配置文件
    - 重构代码
    
    参数：
    - file_path: 文件路径
    - new_content: 新的文件内容
    - create_backup: 是否创建备份（默认 True）
    
    示例：
    - apply_code_changes("core/butler.py", "新的代码...", True)
    
    返回：
    - 操作结果
    - 备份文件路径
    
    ⚠️ 注意：
    - 只有管理员（QQ: 123456789）可以执行
    - 会自动验证 Python 语法
    - 所有操作会被审计记录
    """
    args_schema: Type[BaseModel] = ApplyChangesInput
    
    def _run(self, file_path: str, new_content: str, create_backup: bool = True) -> str:
        """执行应用更改"""
        try:
            # 检查文件是否存在
            success, original_content, error = project_manager.read_file(file_path)
            
            if not success:
                return f"❌ 读取文件失败: {error}"
            
            # 验证语法（如果是 Python 文件）
            if file_path.endswith('.py'):
                is_valid, syntax_error = code_modifier.validate_syntax(new_content)
                if not is_valid:
                    return f"❌ 语法错误:\n{syntax_error}"
            
            # 创建备份
            backup_path = ""
            if create_backup:
                success, backup_path, error = code_modifier.create_backup(
                    project_manager.get_full_path(file_path)
                )
                if not success:
                    return f"❌ 创建备份失败: {error}"
            
            # 写入文件
            success, error = project_manager.write_file(file_path, new_content)
            
            if not success:
                # 如果写入失败，恢复备份
                if backup_path:
                    code_modifier.restore_backup(
                        backup_path,
                        project_manager.get_full_path(file_path)
                    )
                return f"❌ 写入文件失败: {error}"
            
            # 生成 diff（用于显示）
            diff = code_modifier.generate_diff(
                original_content,
                new_content,
                file_path
            )
            
            changes = code_modifier.extract_changes(diff)
            
            # 格式化输出
            output = []
            output.append(f"✅ 代码更改已应用: {file_path}")
            output.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 统计信息
            output.append(f"\n📊 更改统计:")
            output.append(f"  ✅ 添加: {changes['additions']} 行")
            output.append(f"  ❌ 删除: {changes['deletions']} 行")
            output.append(f"  📍 修改块: {len(changes['hunks'])} 个")
            
            # 备份信息
            if backup_path:
                output.append(f"\n💾 备份文件: {Path(backup_path).name}")
            
            # 提示
            output.append(f"\n💡 建议:")
            output.append(f"  - 运行测试验证更改")
            output.append(f"  - 如有问题可以恢复备份")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 应用更改失败: {str(e)}"


class FormatCodeTool(BaseTool):
    """格式化代码工具"""
    name: str = "format_code"
    description: str = """格式化代码文件。⚠️ 需要管理员权限！
    
    功能：
    - 自动格式化代码
    - 统一代码风格
    - 支持 Python（使用 black 或简单格式化）
    
    使用场景：
    - 格式化新创建的文件
    - 统一代码风格
    - 修复缩进问题
    
    参数：
    - file_path: 文件路径
    
    示例：
    - format_code("core/butler.py")
    
    返回：
    - 格式化结果
    - 更改统计
    
    ⚠️ 注意：
    - 只有管理员（QQ: 123456789）可以执行
    - 会自动创建备份
    - 所有操作会被审计记录
    """
    args_schema: Type[BaseModel] = FormatCodeInput
    
    def _run(self, file_path: str) -> str:
        """执行格式化"""
        try:
            # 读取文件
            success, original_content, error = project_manager.read_file(file_path)
            
            if not success:
                return f"❌ 读取文件失败: {error}"
            
            # 确定语言
            language = "python" if file_path.endswith('.py') else "unknown"
            
            if language == "unknown":
                return f"❌ 不支持的文件类型: {file_path}"
            
            # 格式化代码
            success, formatted_content, error = code_modifier.format_code(
                original_content,
                language
            )
            
            if not success:
                return f"❌ 格式化失败: {error}"
            
            # 检查是否有变化
            if formatted_content == original_content:
                return f"✅ 代码已经是格式化的: {file_path}"
            
            # 创建备份
            success, backup_path, error = code_modifier.create_backup(
                project_manager.get_full_path(file_path)
            )
            if not success:
                return f"❌ 创建备份失败: {error}"
            
            # 写入文件
            success, error = project_manager.write_file(file_path, formatted_content)
            
            if not success:
                # 恢复备份
                code_modifier.restore_backup(
                    backup_path,
                    project_manager.get_full_path(file_path)
                )
                return f"❌ 写入文件失败: {error}"
            
            # 生成 diff
            diff = code_modifier.generate_diff(
                original_content,
                formatted_content,
                file_path
            )
            
            changes = code_modifier.extract_changes(diff)
            
            # 格式化输出
            output = []
            output.append(f"✅ 代码已格式化: {file_path}")
            output.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 统计信息
            output.append(f"\n📊 更改统计:")
            output.append(f"  ✅ 添加: {changes['additions']} 行")
            output.append(f"  ❌ 删除: {changes['deletions']} 行")
            output.append(f"  📍 修改块: {len(changes['hunks'])} 个")
            
            # 备份信息
            output.append(f"\n💾 备份文件: {Path(backup_path).name}")
            
            return '\n'.join(output)
        
        except Exception as e:
            return f"❌ 格式化失败: {str(e)}"


# ==================== 工具列表 ====================

def get_code_modifier_tools():
    """获取所有代码修改工具"""
    return [
        PreviewChangesTool(),
        ApplyChangesTool(),
        FormatCodeTool(),
    ]


if __name__ == '__main__':
    # 测试工具
    print("🧪 测试代码修改工具...\n")
    
    tools = get_code_modifier_tools()
    print(f"✅ 加载了 {len(tools)} 个工具:")
    for tool in tools:
        print(f"  - {tool.name}")
    
    print("\n✅ 所有工具加载成功！")
