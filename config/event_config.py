"""
事件配置 - 定义所有随机事件
"""
from typing import Dict, List, Any

# ============ 正面事件 ============
POSITIVE_EVENTS: List[Dict[str, Any]] = [
    # 自然/环境
    {"desc": "看到窗外有只可爱的小猫", "impact": {"pleasure": 0.3, "arousal": 0.1}, "prob": 0.1},
    {"desc": "阳光突然变得很好", "impact": {"pleasure": 0.2, "arousal": 0.05}, "prob": 0.15},
    {"desc": "听到窗外有鸟叫声", "impact": {"pleasure": 0.15, "stress": -5}, "prob": 0.12},
    {"desc": "天气凉爽舒适", "impact": {"pleasure": 0.15}, "prob": 0.1},
    
    # 音乐/声音
    {"desc": "听到喜欢的音乐", "impact": {"pleasure": 0.25, "arousal": 0.15}, "prob": 0.15},
    {"desc": "听到熟悉的旋律", "impact": {"pleasure": 0.2}, "prob": 0.1},
    
    # 完成任务
    {"desc": "完成了一件拖了很久的事", "impact": {"dominance": 0.25, "stress": -20, "pleasure": 0.3}, "prob": 0.08},
    {"desc": "顺利完成了今天的任务", "impact": {"dominance": 0.15, "stress": -10, "pleasure": 0.2}, "prob": 0.12},
    {"desc": "意外地效率很高", "impact": {"dominance": 0.2, "pleasure": 0.2, "energy": 5}, "prob": 0.08},
    
    # 发现/找到
    {"desc": "找到了之前丢的东西", "impact": {"pleasure": 0.3, "stress": -15}, "prob": 0.06},
    {"desc": "发现了有趣的东西", "impact": {"pleasure": 0.2, "interest": 10}, "prob": 0.1},
    {"desc": "书里看到特别喜欢的句子", "impact": {"pleasure": 0.25, "interest": 8}, "prob": 0.1},
    
    # 美食
    {"desc": "今天的饭做得不错", "impact": {"pleasure": 0.2, "dominance": 0.1}, "prob": 0.1},
    {"desc": "吃到了喜欢的零食", "impact": {"pleasure": 0.15, "hunger": -10}, "prob": 0.12},
    
    # 社交
    {"desc": "收到朋友的消息", "impact": {"pleasure": 0.2, "loneliness": -15}, "prob": 0.15},
    {"desc": "想起和朋友的有趣对话", "impact": {"pleasure": 0.15, "loneliness": -5}, "prob": 0.1},
    
    # 休息/放松
    {"desc": "突然感觉轻松了", "impact": {"stress": -15, "pleasure": 0.15}, "prob": 0.1},
    {"desc": "睡了个好觉", "impact": {"energy": 20, "pleasure": 0.2, "sleepiness": -30}, "prob": 0.1},
]

# ============ 中性事件 ============
NEUTRAL_EVENTS: List[Dict[str, Any]] = [
    # 回忆
    {"desc": "想起以前的事情", "impact": {}, "prob": 0.15},
    {"desc": "突然想到一些事", "impact": {"arousal": 0.05}, "prob": 0.2},
    
    # 环境变化
    {"desc": "听到外面有声音", "impact": {"arousal": 0.08}, "prob": 0.2},
    {"desc": "天气变化了", "impact": {"arousal": 0.05}, "prob": 0.15},
    {"desc": "街上好像变安静了", "impact": {"arousal": -0.05}, "prob": 0.1},
    
    # 时间感知
    {"desc": "时间过得真快", "impact": {}, "prob": 0.15},
    {"desc": "不知不觉就到这个时间了", "impact": {"arousal": 0.05}, "prob": 0.12},
    {"desc": "感觉时间过得好慢", "impact": {"stress": 5}, "prob": 0.08},
    
    # 身体感知
    {"desc": "伸了个懒腰", "impact": {"arousal": 0.1, "energy": 2}, "prob": 0.15},
    {"desc": "揉了揉眼睛", "impact": {"arousal": -0.05}, "prob": 0.12},
]

# ============ 负面事件 ============
NEGATIVE_EVENTS: List[Dict[str, Any]] = [
    # 丢失/找不到
    {"desc": "东西找不到了", "impact": {"pleasure": -0.25, "stress": 15}, "prob": 0.08},
    {"desc": "好像忘了什么事", "impact": {"stress": 10, "arousal": 0.15}, "prob": 0.12},
    
    # 疲劳
    {"desc": "突然感觉有点累", "impact": {"arousal": -0.3, "energy": -15}, "prob": 0.15},
    {"desc": "眼睛有点酸", "impact": {"energy": -5, "stress": 5}, "prob": 0.12},
    {"desc": "感觉有点困", "impact": {"sleepiness": 15, "arousal": -0.2}, "prob": 0.15},
    
    # 心理/情绪
    {"desc": "想到有点烦心的事", "impact": {"pleasure": -0.2, "stress": 10}, "prob": 0.15},
    {"desc": "突然有点不安", "impact": {"stress": 12, "arousal": 0.15}, "prob": 0.08},
    {"desc": "感觉有点寂寞", "impact": {"loneliness": 15, "pleasure": -0.15}, "prob": 0.1},
    {"desc": "心情有点低落", "impact": {"pleasure": -0.2, "arousal": -0.1}, "prob": 0.1},
    
    # 失败/不顺
    {"desc": "事情没做好", "impact": {"pleasure": -0.25, "dominance": -0.15, "stress": 15}, "prob": 0.08},
    {"desc": "遇到了点小麻烦", "impact": {"stress": 12, "pleasure": -0.15}, "prob": 0.1},
]

# ============ 事件权重配置 ============
DEFAULT_EVENT_WEIGHTS = {
    'positive': 0.35,
    'neutral': 0.35,
    'negative': 0.30
}


