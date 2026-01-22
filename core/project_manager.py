"""
项目管理器
提供项目文件的读写、列表、搜索等功能
"""
import os
import glob
from typing import List, Dict, Optional
from .security import (
    get_safe_path, 
    get_project_root, 
    get_relative_path,
    audit_log,
    PathValidationError
)


class ProjectManager:
    """项目管理器"""
    
    def __init__(self):
        """初始化项目管理器"""
        self.project_root = get_project_root()
    
    # ==================== 文件读取 ====================
    
    def read_file(self, file_path: str, user_id: str = "system") -> str:
        """
        读取项目文件
        
        Args:
            file_path: 文件路径（相对或绝对）
            user_id: 用户 ID
            
        Returns:
            文件内容
            
        Raises:
            PathValidationError: 路径验证失败
            FileNotFoundError: 文件不存在
        """
        try:
            # 获取安全路径
            safe_path = get_safe_path(file_path)
            
            # 检查文件是否存在
            if not os.path.exists(safe_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 检查是否是文件
            if not os.path.isfile(safe_path):
                raise ValueError(f"不是文件: {file_path}")
            
            # 读取文件
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 审计日志
            audit_log(
                user_id=user_id,
                operation="read_file",
                details={"file_path": get_relative_path(safe_path)},
                success=True
            )
            
            return content
        
        except Exception as e:
            # 审计日志
            audit_log(
                user_id=user_id,
                operation="read_file",
                details={"file_path": file_path, "error": str(e)},
                success=False
            )
            raise
    
    # ==================== 文件写入 ====================
    
    def write_file(self, file_path: str, content: str, user_id: str = "system") -> bool:
        """
        写入项目文件
        
        Args:
            file_path: 文件路径（相对或绝对）
            content: 文件内容
            user_id: 用户 ID
            
        Returns:
            是否成功
            
        Raises:
            PathValidationError: 路径验证失败
        """
        try:
            # 获取安全路径
            safe_path = get_safe_path(file_path)
            
            # 确保目录存在
            dir_path = os.path.dirname(safe_path)
            os.makedirs(dir_path, exist_ok=True)
            
            # 写入文件
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # 审计日志
            audit_log(
                user_id=user_id,
                operation="write_file",
                details={
                    "file_path": get_relative_path(safe_path),
                    "size": len(content)
                },
                success=True
            )
            
            return True
        
        except Exception as e:
            # 审计日志
            audit_log(
                user_id=user_id,
                operation="write_file",
                details={"file_path": file_path, "error": str(e)},
                success=False
            )
            raise
    
    # ==================== 文件列表 ====================
    
    def list_files(
        self, 
        directory: str = ".", 
        pattern: str = "*",
        recursive: bool = False,
        user_id: str = "system"
    ) -> List[str]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径（相对或绝对）
            pattern: 文件匹配模式（如 *.py）
            recursive: 是否递归
            user_id: 用户 ID
            
        Returns:
            文件路径列表（相对于项目根目录）
            
        Raises:
            PathValidationError: 路径验证失败
        """
        try:
            # 获取安全路径
            safe_path = get_safe_path(directory)
            
            # 检查目录是否存在
            if not os.path.exists(safe_path):
                raise FileNotFoundError(f"目录不存在: {directory}")
            
            # 检查是否是目录
            if not os.path.isdir(safe_path):
                raise ValueError(f"不是目录: {directory}")
            
            # 构建搜索模式
            if recursive:
                search_pattern = os.path.join(safe_path, "**", pattern)
            else:
                search_pattern = os.path.join(safe_path, pattern)
            
            # 搜索文件
            files = glob.glob(search_pattern, recursive=recursive)
            
            # 转换为相对路径
            relative_files = [get_relative_path(f) for f in files]
            
            # 审计日志
            audit_log(
                user_id=user_id,
                operation="list_files",
                details={
                    "directory": get_relative_path(safe_path),
                    "pattern": pattern,
                    "count": len(relative_files)
                },
                success=True
            )
            
            return sorted(relative_files)
        
        except Exception as e:
            # 审计日志
            audit_log(
                user_id=user_id,
                operation="list_files",
                details={"directory": directory, "error": str(e)},
                success=False
            )
            raise
    
    # ==================== 文件搜索 ====================
    
    def search_in_files(
        self,
        pattern: str,
        file_pattern: str = "*.py",
        directory: str = ".",
        max_results: int = 50,
        user_id: str = "system"
    ) -> List[Dict[str, any]]:
        """
        在文件中搜索内容
        
        Args:
            pattern: 搜索模式（字符串）
            file_pattern: 文件匹配模式（如 *.py）
            directory: 搜索目录
            max_results: 最多返回结果数
            user_id: 用户 ID
            
        Returns:
            搜索结果列表，每项包含：
            - file: 文件路径
            - line: 行号
            - content: 行内容
            
        Raises:
            PathValidationError: 路径验证失败
        """
        try:
            # 获取安全路径
            safe_path = get_safe_path(directory)
            
            # 获取所有匹配的文件
            files = self.list_files(
                directory=directory,
                pattern=file_pattern,
                recursive=True,
                user_id=user_id
            )
            
            results = []
            
            # 在每个文件中搜索
            for file_path in files:
                try:
                    content = self.read_file(file_path, user_id=user_id)
                    lines = content.split("\n")
                    
                    for line_num, line in enumerate(lines, 1):
                        if pattern.lower() in line.lower():
                            results.append({
                                "file": file_path,
                                "line": line_num,
                                "content": line.strip()
                            })
                            
                            # 限制结果数量
                            if len(results) >= max_results:
                                break
                    
                    if len(results) >= max_results:
                        break
                
                except Exception as e:
                    # 跳过无法读取的文件
                    continue
            
            # 审计日志
            audit_log(
                user_id=user_id,
                operation="search_in_files",
                details={
                    "pattern": pattern,
                    "file_pattern": file_pattern,
                    "count": len(results)
                },
                success=True
            )
            
            return results
        
        except Exception as e:
            # 审计日志
            audit_log(
                user_id=user_id,
                operation="search_in_files",
                details={"pattern": pattern, "error": str(e)},
                success=False
            )
            raise
    
    # ==================== 文件信息 ====================
    
    def get_file_info(self, file_path: str, user_id: str = "system") -> Dict[str, any]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            user_id: 用户 ID
            
        Returns:
            文件信息字典
        """
        try:
            # 获取安全路径
            safe_path = get_safe_path(file_path)
            
            # 检查文件是否存在
            if not os.path.exists(safe_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 获取文件信息
            stat = os.stat(safe_path)
            
            info = {
                "path": get_relative_path(safe_path),
                "size": stat.st_size,
                "size_kb": stat.st_size / 1024,
                "modified": stat.st_mtime,
                "is_file": os.path.isfile(safe_path),
                "is_dir": os.path.isdir(safe_path),
            }
            
            # 如果是文件，获取行数
            if info["is_file"]:
                try:
                    content = self.read_file(file_path, user_id=user_id)
                    info["lines"] = len(content.split("\n"))
                except:
                    info["lines"] = 0
            
            return info
        
        except Exception as e:
            raise
    
    # ==================== 目录树 ====================
    
    def get_directory_tree(
        self,
        directory: str = ".",
        max_depth: int = 3,
        user_id: str = "system"
    ) -> str:
        """
        获取目录树结构
        
        Args:
            directory: 目录路径
            max_depth: 最大深度
            user_id: 用户 ID
            
        Returns:
            目录树字符串
        """
        try:
            # 获取安全路径
            safe_path = get_safe_path(directory)
            
            def build_tree(path: str, prefix: str = "", depth: int = 0) -> List[str]:
                """递归构建目录树"""
                if depth > max_depth:
                    return []
                
                lines = []
                
                try:
                    items = sorted(os.listdir(path))
                    
                    # 过滤隐藏文件和特殊目录
                    items = [
                        item for item in items 
                        if not item.startswith(".") and item not in ["__pycache__", "node_modules"]
                    ]
                    
                    for i, item in enumerate(items):
                        item_path = os.path.join(path, item)
                        is_last = i == len(items) - 1
                        
                        # 构建前缀
                        if is_last:
                            lines.append(f"{prefix}└── {item}")
                            new_prefix = f"{prefix}    "
                        else:
                            lines.append(f"{prefix}├── {item}")
                            new_prefix = f"{prefix}│   "
                        
                        # 递归处理子目录
                        if os.path.isdir(item_path):
                            lines.extend(build_tree(item_path, new_prefix, depth + 1))
                
                except PermissionError:
                    pass
                
                return lines
            
            # 构建树
            tree_lines = [get_relative_path(safe_path)]
            tree_lines.extend(build_tree(safe_path))
            
            return "\n".join(tree_lines)
        
        except Exception as e:
            raise


# ==================== 全局实例 ====================

# 创建全局项目管理器实例
project_manager = ProjectManager()
