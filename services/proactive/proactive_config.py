"""
主动聊天系统配置
"""


class ProactiveConfig:
    """主动聊天配置类"""
    
    # ==================== 数据库配置 ====================
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # ==================== NVIDIA DeepSeek API配置 ====================
    API_URL = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/853b883c-b3ae-41bc-aa2d-b147389f6490"
    API_KEY = "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"
    MODEL = "ai-deepseek-v3_1-terminus"
    TEMPERATURE = 0.9  # 高温度，更有创造性
    
    # ==================== 时间窗口配置 ====================
    ACTIVE_HOURS = [(9, 23)]  # 活跃时间段 (全天，降低时间限制)
    MIN_SILENCE_MINUTES = 27  # 最少沉默时间（1分钟，临时调小用于测试）
    MAX_SILENCE_HOURS = 24  # 最大沉默时间（1天）
    CHECK_INTERVAL_MINUTES = 15  # 检查间隔（1分钟，测试用）
    MIN_PROACTIVE_INTERVAL_MINUTES = 1  # 最小主动间隔（1分钟，临时调小用于测试）
    
    # ==================== 主动性配置 ====================
    BASE_PROACTIVITY = 0.8  # 基础主动性（80%，大幅提高）
    MAX_PROACTIVITY = 0.95  # 最大主动性（95%，提高）
    MIN_PROACTIVITY = 0.5  # 最小主动性（50%，大幅提高）
    MAX_DAILY_PROACTIVE = 20  # 每天最多主动聊天次数（提高）
    
    # ==================== 决策权重 ====================
    RELATIONSHIP_WEIGHT = 0.4  # 关系权重
    EMOTION_WEIGHT = 0.3  # 情感权重
    INTIMACY_WEIGHT = 0.6  # 亲密度权重
    ACTIVITY_WEIGHT = 0.2  # 活跃度权重
    RANDOM_WEIGHT = 0.1  # 随机权重
    
    # ==================== 强化学习配置 ====================
    POSITIVE_REWARD = 1.0  # 用户积极回应
    NEUTRAL_REWARD = 0.0  # 用户中性回应
    NEGATIVE_REWARD = -1.0  # 用户消极回应
    NO_RESPONSE_PENALTY = -0.5  # 用户不回应
    LEARNING_RATE = 0.1  # 学习率
    
    # ==================== 内容生成配置 ====================
    # 开场白类型
    OPENING_TYPES = [
        "问候",  # "早上好！"
        "关心",  # "最近怎么样？"
        "分享",  # "今天发生了一件有趣的事..."
        "话题",  # "你对XX怎么看？"
        "回忆",  # "还记得上次..."
    ]
    
    # 生成策略
    GENERATION_STRATEGY = {
        "morning": "问候",     # 早上：问候
        "afternoon": "话题",   # 下午：话题讨论
        "evening": "关心",     # 晚上：关心问候
        "night": "分享",       # 夜晚：分享心情
    }




