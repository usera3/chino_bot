"""
动态情感系统配置
定义情感参数、时间规则、关键词等配置
"""


class EmotionConfig:
    """动态情感系统配置"""
    
    # 数据库配置
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 情感参数范围
    MIN_VALUE = 0.0
    MAX_VALUE = 100.0
    
    # 时间相关配置
    LONELINESS_INCREASE_RATE = 5.0  # 寂寞值每小时增加率（提高，让机器人更容易寂寞）
    ENERGY_RECOVERY_RATE = 6.0  # 体力每小时恢复率
    ENERGY_NIGHT_DRAIN = 30.0  # 夜晚体力扣除量
    NIGHT_START_HOUR = 23  # 夜晚开始时间
    NIGHT_END_HOUR = 6  # 夜晚结束时间
    
    # 聊天影响配置
    CHAT_LONELINESS_REDUCTION = 15.0  # 聊天减少的寂寞值
    CHAT_ENERGY_COST = 8.0  # 聊天消耗的体力
    CHAT_HAPPINESS_GAIN = 10.0  # 聊天获得的快乐值
    CHAT_CONFIDENCE_GAIN = 5.0  # 聊天获得的自信值
    
    # 心情影响社交需求的配置
    MOOD_EXTREME_THRESHOLD = 15.0  # 心情极端阈值（距离50的差值，降低让机器人更容易主动）
    MOOD_SOCIAL_IMPACT_FACTOR = 2.5  # 极端心情对社交需求的影响因子（提高）
    
    # 情感参数对社交需求的影响权重
    EMOTION_SOCIAL_WEIGHTS = {
        'happiness': 0.2,      # 快乐值影响
        'loneliness': 0.3,     # 寂寞值影响（主要）
        'confidence': 0.15,    # 自信值影响
        'stress_level': -0.1,  # 压力值影响（负相关）
        'mood_extreme': 0.25   # 心情极端影响
    }
    
    # 用户消息情感分析配置
    POSITIVE_KEYWORDS = ['开心', '高兴', '快乐', '兴奋', '棒', '好', '喜欢', '爱', '成功', '胜利']
    NEGATIVE_KEYWORDS = ['难过', '伤心', '痛苦', '糟糕', '坏', '讨厌', '失败', '失望', '生气', '愤怒']
    CONFIDENCE_KEYWORDS = ['自信', '厉害', '强', '牛', '优秀', '完美', '成功', '胜利']
    STRESS_KEYWORDS = ['压力', '累', '忙', '紧张', '焦虑', '担心', '害怕']

























