"""
表情包系统配置
"""


class EmoticonConfig:
    """表情包系统配置类"""
    
    # ==================== 数据库配置 ====================
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    EMOTICON_STORAGE_PATH = "./emoticons/"  # 表情包存储路径
    
    # ==================== AI识别配置 ====================
    # NVIDIA高质量视觉模型配置（替代通义千问-VL，质量更好）
    VISION_API_KEY = "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"
    VISION_MODEL = "llama-3.2-11b"  # 使用Llama-3.2-11B视觉模型（质量更好）
    VISION_BASE_URL = "https://api.nvcf.nvidia.com"
    USE_VISION_AI = True  # 启用图像识别
    
    # ==================== 学习配置 ====================
    ENABLE_LEARNING = True  # 是否启用学习
    MIN_CONTEXT_LENGTH = 1  # 最小上下文长度
    MAX_CONTEXT_MESSAGES = 10  # 上下文消息数量
    AUTO_LEARN_FROM_GROUPS = True  # 是否从群聊自动学习
    AUTO_LEARN_FROM_PRIVATE = True  # 是否从私聊自动学习
    
    # 学习质量阈值
    MIN_CONFIDENCE_SCORE = 0.3  # 最小置信度
    MIN_IMAGE_SIZE = 50 * 1024  # 最小图片大小（50KB）
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 最大图片大小（10MB）
    
    # ==================== 发送配置 ====================
    # 基础发送概率
    BASE_SEND_PROBABILITY = 0.25  # 25%的消息可能带表情
    
    # 情感影响发送概率
    EMOTION_MULTIPLIERS = {
        'happy': 1.8,      # 开心时更容易发表情
        'excited': 2.0,    # 兴奋时最容易发表情
        'sad': 0.8,        # 难过时较少发表情
        'angry': 0.6,      # 生气时很少发表情
        'tired': 0.5,      # 疲惫时很少发表情
        'neutral': 1.0,    # 中性正常发送
    }
    
    # 体力影响发送概率
    ENERGY_THRESHOLDS = {
        'high': (70, 100, 1.2),    # 体力高：增加20%
        'normal': (40, 70, 1.0),   # 体力正常：正常
        'low': (0, 40, 0.6),       # 体力低：减少40%
    }
    
    # 连续消息控制
    CONTINUOUS_NO_EMOTICON_PROB = 0.7  # 连续消息70%不带表情（避免过度使用）
    MAX_CONTINUOUS_EMOTICONS = 2  # 最多连续2条消息带表情
    
    # ==================== 选择配置 ====================
    # 表情类型权重
    EMOTICON_TYPE_WEIGHTS = {
        'emoji': 0.4,      # 40% emoji
        'learned': 0.4,    # 40% 学习的表情包
        'text': 0.2,       # 20% 文本表情（如"哈哈"）
    }
    
    # 匹配配置
    MIN_MATCH_SCORE = 0.3  # 最小匹配分数
    MAX_SEARCH_RESULTS = 5  # 最多搜索5个候选
    
    # 使用频率控制
    SAME_EMOTICON_COOLDOWN = 300  # 同一表情包冷却时间（秒）
    
    # ==================== Emoji库配置 ====================
    EMOJI_LIBRARY = {
        # 积极情感
        "happy": ["😊", "😄", "🥰", "😆", "🤗"],
        "excited": ["😍", "🤩", "✨", "🎉"],
        "love": ["❤️", "💕", "💖", "🥰"],
        
        # 消极情感
        "sad": ["😢", "😔", "🥺", "😞"],
        "angry": ["😠", "💢", "😤"],
        "worried": ["😰", "😟", "😥"],
        "tired": ["😴", "🥱", "💤"],
        
        # 中性/反应
        "laugh": ["😂", "🤣"],
        "thinking": ["🤔", "💭"],
        "confused": ["😕", "❓", "😵"],
        "surprise": ["😮", "😯"],
        
        # 赞同/否定
        "agree": ["👍", "✅"],
        "disagree": ["👎", "❌"],
        
        # 其他常用
        "shy": ["😳", "🙈"],
        "cool": ["😎", "👌"],
        "greeting": ["👋"],
        "thanks": ["🙏"],
    }
    
    # 文本表情库
    TEXT_EMOTICONS = {
        "happy": ["哈哈", "嘿嘿", "嘻嘻"],
        "agree": ["对的", "没错", "确实"],
        "thinking": ["嗯", "唔"],
        "shy": ["害羞", "不好意思"],
        "laugh": ["笑死", "绷不住了"],
    }
    
    # ==================== 用户画像配置 ====================
    USER_TYPE_MULTIPLIERS = {
        "active": 1.5,      # 活跃用户：更多表情
        "normal": 1.0,      # 普通用户：正常
        "reserved": 0.6     # 内向用户：更少表情
    }
    
    # ==================== 索要配置 ====================
    # 用户索要表情包的配置
    REQUEST_MAX_RESULTS = 5  # 最多返回5个表情包
    REQUEST_MIN_CONFIDENCE = 0.3  # 最小匹配置信度
    ENABLE_SMART_MATCH = True  # 启用智能匹配
    
    # 索要关键词模式
    REQUEST_PATTERNS = {
        # 情感类
        "happy": ["开心", "高兴", "快乐", "笑", "哈哈"],
        "sad": ["哭", "难过", "伤心", "悲伤"],
        "angry": ["生气", "愤怒", "气"],
        "excited": ["兴奋", "激动"],
        "thinking": ["思考", "想"],
        "surprise": ["惊讶", "震惊"],
        "love": ["爱", "喜欢"],
        
        # 场景类
        "work": ["工作", "加班", "打工"],
        "eat": ["吃饭", "饿", "美食"],
        "sleep": ["睡觉", "困", "累"],
        "study": ["学习", "考试"],
        
        # 动作类
        "dance": ["跳舞", "蹦迪"],
        "cry": ["哭", "泪"],
        "laugh": ["笑", "哈哈"],
    }




