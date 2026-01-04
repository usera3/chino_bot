"""
工具基类 - Tool Base
所有工具都继承此类，实现标准化接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = False
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """工具定义 - 符合 Function Calling 规范"""
    name: str = Field(..., description="工具名称（唯一标识）")
    description: str = Field(..., description="工具功能描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数定义")


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Any] = Field(None, description="返回数据")
    message: str = Field("", description="结果消息")
    error: Optional[str] = Field(None, description="错误信息")


class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self):
        self.name = self.get_name()
        self.description = self.get_description()
    
    @abstractmethod
    def get_name(self) -> str:
        """返回工具名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """返回工具描述"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """返回参数定义（JSON Schema 格式）"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        pass
    
    def get_definition(self) -> ToolDefinition:
        """获取工具定义（用于 Function Calling）"""
        return ToolDefinition(
            name=self.get_name(),
            description=self.get_description(),
            parameters=self.get_parameters()
        )
    
    def validate_params(self, **kwargs) -> bool:
        """验证参数（可选实现）"""
        return True




