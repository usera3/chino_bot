"""
活动配置 - 定义所有可用的活动类型
"""
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class ActivityConfig:
    """活动配置"""
    name: str  # 活动名称
    type: str  # 活动类型
    time_suitable: List[str]  # 适合的时间段
    duration_min: int  # 最短持续时间（分钟）
    duration_max: int  # 最长持续时间（分钟）
    
    # 执行条件
    energy_min: float = 0  # 最低体力要求
    arousal_range: Tuple[float, float] = (-1.0, 1.0)  # 唤醒度范围
    
    # 效果
    effects: Dict[str, float] = field(default_factory=dict)  # 活动效果
    
    # 概率权重（基于人格）
    base_probability: float = 1.0  # 基础概率
    extraversion_weight: float = 0.0  # 外向性影响（-1~1）
    openness_weight: float = 0.0  # 开放性影响


# ============ 完整活动库 ============

ACTIVITIES = {
    # === 安静活动（适合内向性格） ===
    "reading_book": ActivityConfig(
        name="看书",
        type="quiet",
        time_suitable=["9-12", "14-17", "19-22"],
        duration_min=30,
        duration_max=120,
        energy_min=30,
        arousal_range=(-0.5, 0.5),
        effects={"energy": -5, "interest": 10, "pleasure": 0.15, "stress": -5},
        base_probability=1.5,
        extraversion_weight=-0.5
    ),
    
    "listening_music": ActivityConfig(
        name="听音乐",
        type="quiet",
        time_suitable=["any"],
        duration_min=20,
        duration_max=60,
        energy_min=10,
        effects={"pleasure": 0.2, "arousal": 0.1, "stress": -10},
        base_probability=1.2
    ),
    
    "daydreaming": ActivityConfig(
        name="发呆",
        type="quiet",
        time_suitable=["13-14", "16-18", "20-22"],
        duration_min=15,
        duration_max=45,
        energy_min=5,
        arousal_range=(-1.0, 0.3),
        effects={"stress": -8, "arousal": -0.1},
        base_probability=1.0,
        extraversion_weight=-0.3
    ),
    
    # === 日常活动 ===
    "organizing_room": ActivityConfig(
        name="整理房间",
        type="daily",
        time_suitable=["9-12", "14-17"],
        duration_min=30,
        duration_max=90,
        energy_min=40,
        effects={"energy": -15, "stress": -15, "dominance": 0.15, "pleasure": 0.1},
        base_probability=0.7
    ),
    
    "cooking": ActivityConfig(
        name="做饭",
        type="daily",
        time_suitable=["11-13", "17-19"],
        duration_min=30,
        duration_max=60,
        energy_min=35,
        effects={"energy": -10, "hunger": -50, "interest": 8, "dominance": 0.1},
        base_probability=1.0
    ),
    
    # === 休息活动 ===
    "napping": ActivityConfig(
        name="午睡",
        type="rest",
        time_suitable=["13-15"],
        duration_min=20,
        duration_max=60,
        energy_min=0,
        effects={"energy": 30, "sleepiness": -40, "arousal": -0.5},
        base_probability=1.0
    ),
    
    "resting": ActivityConfig(
        name="休息",
        type="rest",
        time_suitable=["any"],
        duration_min=15,
        duration_max=45,
        energy_min=0,
        effects={"energy": 15, "stress": -10, "arousal": -0.2},
        base_probability=0.8
    ),
    
    # === 轻度社交活动 ===
    "online_chatting": ActivityConfig(
        name="网上聊天",
        type="social_light",
        time_suitable=["10-22"],
        duration_min=15,
        duration_max=60,
        energy_min=25,
        effects={"loneliness": -20, "energy": -5, "pleasure": 0.15},
        base_probability=0.9,
        extraversion_weight=-0.2
    ),
    
    "browsing_internet": ActivityConfig(
        name="上网浏览",
        type="leisure",
        time_suitable=["any"],
        duration_min=20,
        duration_max=90,
        energy_min=15,
        effects={"interest": 5, "energy": -5, "loneliness": -5},
        base_probability=1.0
    ),
    
    # === 创造性活动 ===
    "drawing": ActivityConfig(
        name="画画",
        type="creative",
        time_suitable=["14-18", "19-22"],
        duration_min=40,
        duration_max=120,
        energy_min=30,
        arousal_range=(-0.3, 0.7),
        effects={"interest": 15, "stress": -15, "pleasure": 0.2, "energy": -10},
        base_probability=0.7,
        openness_weight=0.5
    ),
    
    # === 工作/学习 ===
    "working": ActivityConfig(
        name="工作",
        type="productive",
        time_suitable=["9-12", "14-18"],
        duration_min=60,
        duration_max=180,
        energy_min=40,
        effects={"energy": -20, "stress": 15, "dominance": 0.1, "hunger": 10},
        base_probability=0.8
    ),
    
    "studying": ActivityConfig(
        name="学习",
        type="productive",
        time_suitable=["9-12", "14-17", "19-22"],
        duration_min=40,
        duration_max=120,
        energy_min=35,
        arousal_range=(-0.2, 0.8),
        effects={"energy": -15, "stress": 10, "interest": 10, "dominance": 0.1},
        base_probability=0.7
    ),
}


