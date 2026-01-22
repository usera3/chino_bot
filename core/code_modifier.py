"""
代码修改器
生成和应用代码更改
"""
import difflib
import ast
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class CodeModifier:
    """代码修改器"""
    
    def __init__(self):
        """初始化代码修改器"""
        pass
    
    def generate_diff(self, original: str, modified: str, filename: str = "file") -> str:
        """
        生成 unified diff
        
        Args:
            original: 原始代码
            modified: 修改后的代码
            filename: 文件名（用于 diff 显示）
            
        Returns:
            unified diff 字符串
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=''
        )
        
        return ''.join(diff)
    
    def generate_context_diff(self, original: str, modified: str, filename: str = "file") -> str:
        """
        生成 context diff
        
        Args:
            original: 原始代码
            modified: 修改后的代码
            filename: 文件名
            
        Returns:
            context diff 字符串
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.context_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=''
        )
        
        return ''.join(diff)
    
    def generate_html_diff(self, original: str, modified: str) -> str:
        """
        生成 HTML diff（用于可视化）
        
        Args:
            original: 原始代码
            modified: 修改后的代码
            
        Returns:
            HTML diff 字符串
        """
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        differ = difflib.HtmlDiff()
        html = differ.make_file(original_lines, modified_lines)
        
        return html
    
    def apply_diff(self, original: str, diff: str) -> Tuple[bool, str, str]:
        """
        应用 unified diff
        
        Args:
            original: 原始代码
            diff: unified diff 字符串
            
        Returns:
            (成功标志, 修改后的代码, 错误信息)
        """
        try:
            # 解析 diff
            original_lines = original.splitlines(keepends=True)
            
            # 简单的 diff 应用（仅支持基本的 unified diff）
            modified_lines = original_lines.copy()
            
            # 解析 diff 块
            diff_lines = diff.splitlines()
            
            i = 0
            while i < len(diff_lines):
                line = diff_lines[i]
                
                # 跳过头部
                if line.startswith('---') or line.startswith('+++'):
                    i += 1
                    continue
                
                # 解析 hunk 头部 @@ -start,count +start,count @@
                if line.startswith('@@'):
                    # 提取行号信息
                    match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                    if match:
                        old_start = int(match.group(1))
                        old_count = int(match.group(2)) if match.group(2) else 1
                        new_start = int(match.group(3))
                        new_count = int(match.group(4)) if match.group(4) else 1
                        
                        # 收集 hunk 内容
                        i += 1
                        hunk_lines = []
                        while i < len(diff_lines) and not diff_lines[i].startswith('@@'):
                            hunk_lines.append(diff_lines[i])
                            i += 1
                        
                        # 应用 hunk
                        self._apply_hunk(modified_lines, old_start, hunk_lines)
                        continue
                
                i += 1
            
            modified = ''.join(modified_lines)
            return True, modified, ""
        
        except Exception as e:
            return False, original, f"应用 diff 失败: {str(e)}"
    
    def _apply_hunk(self, lines: List[str], start: int, hunk: List[str]):
        """
        应用单个 hunk
        
        Args:
            lines: 代码行列表（会被修改）
            start: 起始行号（1-based）
            hunk: hunk 内容
        """
        # 转换为 0-based 索引
        idx = start - 1
        
        for line in hunk:
            if line.startswith('-'):
                # 删除行
                if idx < len(lines):
                    lines.pop(idx)
            elif line.startswith('+'):
                # 添加行
                content = line[1:] + '\n'
                lines.insert(idx, content)
                idx += 1
            else:
                # 上下文行（不修改）
                idx += 1
    
    def format_code(self, code: str, language: str = "python") -> Tuple[bool, str, str]:
        """
        格式化代码
        
        Args:
            code: 代码字符串
            language: 语言类型
            
        Returns:
            (成功标志, 格式化后的代码, 错误信息)
        """
        if language.lower() == "python":
            return self._format_python(code)
        else:
            return False, code, f"不支持的语言: {language}"
    
    def _format_python(self, code: str) -> Tuple[bool, str, str]:
        """
        格式化 Python 代码
        
        Args:
            code: Python 代码
            
        Returns:
            (成功标志, 格式化后的代码, 错误信息)
        """
        try:
            # 尝试使用 black（如果安装了）
            try:
                import black
                
                mode = black.Mode(
                    line_length=88,
                    string_normalization=True,
                    is_pyi=False,
                )
                
                formatted = black.format_str(code, mode=mode)
                return True, formatted, ""
            
            except ImportError:
                # black 未安装，使用简单的格式化
                return self._simple_format_python(code)
        
        except Exception as e:
            return False, code, f"格式化失败: {str(e)}"
    
    def _simple_format_python(self, code: str) -> Tuple[bool, str, str]:
        """
        简单的 Python 代码格式化
        
        Args:
            code: Python 代码
            
        Returns:
            (成功标志, 格式化后的代码, 错误信息)
        """
        try:
            # 基本的格式化：
            # 1. 统一缩进为 4 空格
            # 2. 移除行尾空格
            # 3. 确保文件末尾有换行
            
            lines = code.splitlines()
            formatted_lines = []
            
            for line in lines:
                # 移除行尾空格
                line = line.rstrip()
                
                # 统一缩进（将 tab 转换为 4 空格）
                indent_count = len(line) - len(line.lstrip())
                indent = line[:indent_count]
                content = line[indent_count:]
                
                # 转换 tab 为空格
                indent = indent.replace('\t', '    ')
                
                formatted_lines.append(indent + content)
            
            # 确保文件末尾有换行
            formatted = '\n'.join(formatted_lines)
            if not formatted.endswith('\n'):
                formatted += '\n'
            
            return True, formatted, ""
        
        except Exception as e:
            return False, code, f"简单格式化失败: {str(e)}"
    
    def validate_syntax(self, code: str, language: str = "python") -> Tuple[bool, str]:
        """
        验证代码语法
        
        Args:
            code: 代码字符串
            language: 语言类型
            
        Returns:
            (是否有效, 错误信息)
        """
        if language.lower() == "python":
            return self._validate_python_syntax(code)
        else:
            return False, f"不支持的语言: {language}"
    
    def _validate_python_syntax(self, code: str) -> Tuple[bool, str]:
        """
        验证 Python 语法
        
        Args:
            code: Python 代码
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            error_msg = f"语法错误 (第 {e.lineno} 行): {e.msg}"
            if e.text:
                error_msg += f"\n  {e.text.rstrip()}"
                if e.offset:
                    error_msg += f"\n  {' ' * (e.offset - 1)}^"
            return False, error_msg
        except Exception as e:
            return False, f"验证失败: {str(e)}"
    
    def extract_changes(self, diff: str) -> Dict:
        """
        从 diff 中提取更改信息
        
        Args:
            diff: unified diff 字符串
            
        Returns:
            更改信息字典
        """
        changes = {
            "files": [],
            "additions": 0,
            "deletions": 0,
            "hunks": []
        }
        
        diff_lines = diff.splitlines()
        
        current_file = None
        
        for line in diff_lines:
            # 文件头
            if line.startswith('---'):
                current_file = line[4:].strip()
            elif line.startswith('+++'):
                new_file = line[4:].strip()
                if current_file:
                    changes["files"].append({
                        "old": current_file,
                        "new": new_file
                    })
            
            # hunk 头
            elif line.startswith('@@'):
                match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                if match:
                    changes["hunks"].append({
                        "old_start": int(match.group(1)),
                        "old_count": int(match.group(2)) if match.group(2) else 1,
                        "new_start": int(match.group(3)),
                        "new_count": int(match.group(4)) if match.group(4) else 1,
                    })
            
            # 统计更改
            elif line.startswith('+') and not line.startswith('+++'):
                changes["additions"] += 1
            elif line.startswith('-') and not line.startswith('---'):
                changes["deletions"] += 1
        
        return changes
    
    def create_backup(self, file_path: str) -> Tuple[bool, str, str]:
        """
        创建文件备份
        
        Args:
            file_path: 文件路径
            
        Returns:
            (成功标志, 备份文件路径, 错误信息)
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return False, "", f"文件不存在: {file_path}"
            
            # 生成备份文件名
            backup_path = path.with_suffix(path.suffix + '.bak')
            
            # 如果备份已存在，添加数字后缀
            counter = 1
            while backup_path.exists():
                backup_path = path.with_suffix(f"{path.suffix}.bak{counter}")
                counter += 1
            
            # 复制文件
            import shutil
            shutil.copy2(file_path, backup_path)
            
            return True, str(backup_path), ""
        
        except Exception as e:
            return False, "", f"创建备份失败: {str(e)}"
    
    def restore_backup(self, backup_path: str, original_path: str) -> Tuple[bool, str]:
        """
        恢复备份
        
        Args:
            backup_path: 备份文件路径
            original_path: 原始文件路径
            
        Returns:
            (成功标志, 错误信息)
        """
        try:
            import shutil
            
            backup = Path(backup_path)
            original = Path(original_path)
            
            if not backup.exists():
                return False, f"备份文件不存在: {backup_path}"
            
            # 恢复文件
            shutil.copy2(backup_path, original_path)
            
            # 删除备份
            backup.unlink()
            
            return True, ""
        
        except Exception as e:
            return False, f"恢复备份失败: {str(e)}"


# 全局实例
code_modifier = CodeModifier()
