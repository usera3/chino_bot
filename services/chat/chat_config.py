"""
聊天配置 - Config
职责：聊天相关的所有配置项
代码量：~50行
"""


class ChatConfig:
    """聊天配置类"""
    
    # API配置
    API_URL = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/853b883c-b3ae-41bc-aa2d-b147389f6490"
    API_KEY = "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"
    MODEL = "ai-deepseek-v3_1-terminus"
    
    # 数据库配置
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 记忆管理配置
    SHORT_TERM_MEMORY_SIZE = 6  # 短期记忆：最近3轮对话
    LONG_TERM_MEMORY_SIZE = 20  # 长期记忆：总存储对话数
    SUMMARY_THRESHOLD = 10  # 超过此数量触发摘要
    RELEVANCE_THRESHOLD = 0.3  # 相关性阈值
    
    # API配置
    TIMEOUT = 30.0
    MAX_RETRIES = 2
    TEMPERATURE = 0.8  # 提高创造性，更像真人
    
    # 个性化配置
    ENABLE_PERSONALITY = True  # 启用个性化
    ENABLE_EMOTION = True  # 启用情感识别
    
    # 💬 消息分段发送配置（提升用户体验）
    ENABLE_SPLIT_SEND = True  # 启用分段发送
    MIN_LENGTH_TO_SPLIT = 30  # 超过此长度才分段
    TYPING_DELAY_PER_CHAR = 0.03  # 每个字符的打字延迟（秒）
    MIN_TYPING_DELAY = 0.5  # 最小延迟
    MAX_TYPING_DELAY = 2.0  # 最大延迟




