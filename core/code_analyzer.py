"""
代码分析器
使用 AST 解析 Python 代码，提取结构信息
"""
import ast
import os
from typing import Dict, List, Optional
from pathlib import Path


class CodeAnalyzer:
    """Python 代码分析器"""
    
    def __init__(self, project_root: str = None):
        """
        初始化代码分析器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root or os.getcwd()
    
    def analyze_file(self, file_path: str) -> Dict:
        """
        分析单个 Python 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            分析结果字典
        """
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 解析 AST
            tree = ast.parse(source_code, filename=file_path)
            
            # 提取信息
            result = {
                'file': file_path,
                'classes': self.extract_classes(tree, source_code),
                'functions': self.extract_functions(tree, source_code),
                'imports': self.extract_imports(tree),
                'lines': len(source_code.splitlines()),
                'complexity': self.calculate_complexity(tree),
            }
            
            return result
        
        except SyntaxError as e:
            return {
                'file': file_path,
                'error': f'语法错误: {str(e)}',
                'line': e.lineno,
            }
        except Exception as e:
            return {
                'file': file_path,
                'error': f'分析失败: {str(e)}',
            }
    
    def extract_classes(self, tree: ast.AST, source_code: str) -> List[Dict]:
        """
        提取类定义
        
        Args:
            tree: AST 树
            source_code: 源代码
            
        Returns:
            类信息列表
        """
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 提取方法
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append({
                            'name': item.name,
                            'line': item.lineno,
                            'is_async': isinstance(item, ast.AsyncFunctionDef),
                        })
                
                # 提取基类
                bases = [self._get_name(base) for base in node.bases]
                
                classes.append({
                    'name': node.name,
                    'line_start': node.lineno,
                    'line_end': node.end_lineno,
                    'methods': methods,
                    'bases': bases,
                    'docstring': ast.get_docstring(node),
                })
        
        return classes
    
    def extract_functions(self, tree: ast.AST, source_code: str) -> List[Dict]:
        """
        提取函数定义（不包括类方法）
        
        Args:
            tree: AST 树
            source_code: 源代码
            
        Returns:
            函数信息列表
        """
        functions = []
        
        # 只提取模块级别的函数
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 提取参数
                args = []
                for arg in node.args.args:
                    args.append(arg.arg)
                
                # 提取返回类型
                returns = None
                if node.returns:
                    returns = self._get_name(node.returns)
                
                functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': args,
                    'returns': returns,
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'docstring': ast.get_docstring(node),
                })
        
        return functions
    
    def extract_imports(self, tree: ast.AST) -> List[Dict]:
        """
        提取导入语句
        
        Args:
            tree: AST 树
            
        Returns:
            导入信息列表
        """
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno,
                    })
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append({
                        'type': 'from',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno,
                    })
        
        return imports
    
    def calculate_complexity(self, tree: ast.AST) -> int:
        """
        计算圈复杂度（简化版）
        
        Args:
            tree: AST 树
            
        Returns:
            复杂度值
        """
        complexity = 1  # 基础复杂度
        
        for node in ast.walk(tree):
            # 分支语句增加复杂度
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            # 逻辑运算符增加复杂度
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity
    
    def find_definition(self, file_path: str, name: str, type: str = 'any') -> Optional[Dict]:
        """
        查找函数或类的定义
        
        Args:
            file_path: 文件路径
            name: 函数或类名
            type: 类型 ('function', 'class', 'any')
            
        Returns:
            定义信息
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=file_path)
            lines = source_code.splitlines()
            
            for node in ast.walk(tree):
                # 查找类
                if (type in ['class', 'any']) and isinstance(node, ast.ClassDef):
                    if node.name == name:
                        code = '\n'.join(lines[node.lineno-1:node.end_lineno])
                        return {
                            'type': 'class',
                            'name': node.name,
                            'file': file_path,
                            'line_start': node.lineno,
                            'line_end': node.end_lineno,
                            'code': code,
                            'docstring': ast.get_docstring(node),
                        }
                
                # 查找函数
                if (type in ['function', 'any']) and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == name:
                        code = '\n'.join(lines[node.lineno-1:node.end_lineno])
                        return {
                            'type': 'function',
                            'name': node.name,
                            'file': file_path,
                            'line_start': node.lineno,
                            'line_end': node.end_lineno,
                            'code': code,
                            'docstring': ast.get_docstring(node),
                        }
            
            return None
        
        except Exception as e:
            return {'error': str(e)}
    
    def _get_name(self, node: ast.AST) -> str:
        """获取节点名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        else:
            return ast.unparse(node) if hasattr(ast, 'unparse') else ''


# 全局实例
code_analyzer = CodeAnalyzer()
