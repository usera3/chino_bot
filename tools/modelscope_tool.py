"""
ModelScope 工具 - 集成魔搭社区的 AI 模型服务
支持：情感分析、文本分类、实体识别等 NLP 任务
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any, Optional
from nonebot.log import logger


class ModelScopeSentimentTool(BaseTool):
    """
    ModelScope 情感分析工具
    用于分析用户消息的情感倾向（积极/消极/中性）
    可用于增强机器人的情感系统
    """
    
    def __init__(self):
        """初始化 ModelScope 情感分析工具"""
        super().__init__()
        self.pipeline = None
        self._initialize_model()
    
    def _initialize_model(self):
        """延迟加载模型"""
        try:
            from modelscope.pipelines import pipeline
            from modelscope.utils.constant import Tasks
            
            # 使用达摩院的中文情感分析模型
            self.pipeline = pipeline(
                task=Tasks.sentiment_analysis,
                model='damo/nlp_structbert_sentiment-classification_chinese-base'
            )
            logger.success("✅ ModelScope 情感分析模型加载成功")
        except ImportError:
            logger.warning("⚠️ ModelScope SDK 未安装，情感分析功能不可用")
            logger.info("💡 安装命令: pip install modelscope")
            self.pipeline = None
        except Exception as e:
            logger.error(f"❌ ModelScope 模型加载失败: {e}")
            self.pipeline = None
    
    def get_name(self) -> str:
        return "sentiment_analysis"
    
    def get_description(self) -> str:
        return "分析文本的情感倾向（积极/消极/中性），用于理解用户的情绪状态"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "需要分析情感的文本内容"
                }
            },
            "required": ["text"]
        }
    
    async def execute(self, text: str) -> ToolResult:
        """
        执行情感分析
        
        Args:
            text: 需要分析的文本
        
        Returns:
            ToolResult: 情感分析结果
        """
        if not self.is_available():
            return ToolResult(
                success=False,
                message="情感分析功能不可用（ModelScope SDK 未安装）",
                error="MODEL_NOT_AVAILABLE"
            )
        
        try:
            logger.info(f"🔍 开始情感分析: {text[:50]}...")
            
            # 调用模型进行推理
            result = self.pipeline(text)
            
            # 解析结果
            if result and 'output' in result:
                label = result['output']
                # ModelScope 情感分析输出: positive/negative/neutral
                
                emotion_map = {
                    'positive': '积极',
                    'negative': '消极',
                    'neutral': '中性'
                }
                
                emotion_cn = emotion_map.get(label, label)
                
                logger.success(f"✅ 情感分析完成: {emotion_cn}")
                
                return ToolResult(
                    success=True,
                    data={
                        "sentiment": label,
                        "sentiment_cn": emotion_cn,
                        "text": text
                    },
                    message=f"情感倾向：{emotion_cn}"
                )
            else:
                logger.error(f"❌ ModelScope 返回结果异常: {result}")
                return ToolResult(
                    success=False,
                    message="情感分析失败（结果格式异常）",
                    error="INVALID_RESULT"
                )
        
        except Exception as e:
            logger.error(f"❌ 情感分析失败: {e}")
            return ToolResult(
                success=False,
                message=f"情感分析失败：{str(e)}",
                error="ANALYSIS_ERROR"
            )
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        return self.pipeline is not None


class ModelScopeTextClassificationTool(BaseTool):
    """
    ModelScope 文本分类工具
    用于分类用户消息的意图（如：问候/提问/闲聊/求助等）
    """
    
    def __init__(self):
        """初始化 ModelScope 文本分类工具"""
        super().__init__()
        self.pipeline = None
        self._initialize_model()
    
    def _initialize_model(self):
        """延迟加载模型"""
        try:
            from modelscope.pipelines import pipeline
            from modelscope.utils.constant import Tasks
            
            # 使用通用文本分类模型
            self.pipeline = pipeline(
                task=Tasks.text_classification,
                model='damo/nlp_structbert_sentence-similarity_chinese-base'
            )
            logger.success("✅ ModelScope 文本分类模型加载成功")
        except ImportError:
            logger.warning("⚠️ ModelScope SDK 未安装，文本分类功能不可用")
            self.pipeline = None
        except Exception as e:
            logger.error(f"❌ ModelScope 文本分类模型加载失败: {e}")
            self.pipeline = None
    
    def get_name(self) -> str:
        return "text_classification"
    
    def get_description(self) -> str:
        return "对文本进行分类，识别用户消息的意图类型"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "需要分类的文本内容"
                }
            },
            "required": ["text"]
        }
    
    async def execute(self, text: str) -> ToolResult:
        """
        执行文本分类
        
        Args:
            text: 需要分类的文本
        
        Returns:
            ToolResult: 分类结果
        """
        if not self.is_available():
            return ToolResult(
                success=False,
                message="文本分类功能不可用（ModelScope SDK 未安装）",
                error="MODEL_NOT_AVAILABLE"
            )
        
        try:
            logger.info(f"🔍 开始文本分类: {text[:50]}...")
            
            result = self.pipeline(text)
            
            logger.success(f"✅ 文本分类完成: {result}")
            
            return ToolResult(
                success=True,
                data={"classification": result, "text": text},
                message=f"分类结果：{result}"
            )
        
        except Exception as e:
            logger.error(f"❌ 文本分类失败: {e}")
            return ToolResult(
                success=False,
                message=f"文本分类失败：{str(e)}",
                error="CLASSIFICATION_ERROR"
            )
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        return self.pipeline is not None


# 导出工具实例
modelscope_sentiment_tool = ModelScopeSentimentTool()
modelscope_classification_tool = ModelScopeTextClassificationTool()

