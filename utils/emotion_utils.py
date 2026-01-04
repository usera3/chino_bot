"""
情感系统工具函数
"""
from typing import Dict, List, Optional, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from config.activity_config import ActivityConfig
    from models.emotion_models import EmotionState


class EmotionUtils:
    """情感系统工具函数"""
    
    @staticmethod
    def calculate_personality_influence(
        personality: Dict[str, float],
        activity_config: 'ActivityConfig'
    ) -> float:
        """
        计算人格对活动概率的影响
        
        Args:
            personality: 人格特质字典
            activity_config: 活动配置
        
        Returns:
            概率调整系数 (0.5 ~ 1.5)
        """
        influence = activity_config.base_probability
        
        # 外向性影响
        if activity_config.extraversion_weight != 0:
            e_score = personality.get('extraversion', 0.5)
            influence *= (1.0 + activity_config.extraversion_weight * (e_score - 0.5))
        
        # 开放性影响
        if activity_config.openness_weight != 0:
            o_score = personality.get('openness', 0.5)
            influence *= (1.0 + activity_config.openness_weight * (o_score - 0.5))
        
        # 限制范围
        return max(0.5, min(1.5, influence))
    
    @staticmethod
    def check_time_suitable(
        time_ranges: List[str],
        current_hour: int
    ) -> bool:
        """
        检查当前时间是否适合某活动
        
        Args:
            time_ranges: 时间范围列表，如 ["9-12", "14-17"]
            current_hour: 当前小时 (0-23)
        
        Returns:
            是否适合
        """
        if "any" in time_ranges:
            return True
        
        for time_range in time_ranges:
            if "-" in time_range:
                start, end = map(int, time_range.split("-"))
                if start <= current_hour < end:
                    return True
        
        return False
    
    @staticmethod
    def select_activity_by_state(
        available_activities: List['ActivityConfig'],
        emotion_state: 'EmotionState',
        personality: Dict[str, float]
    ) -> Optional['ActivityConfig']:
        """
        根据当前状态智能选择活动
        
        Args:
            available_activities: 可用活动列表
            emotion_state: 当前情感状态
            personality: 人格特质
        
        Returns:
            选中的活动，如果没有合适的返回None
        """
        candidates = []
        
        for activity in available_activities:
            # 1. 检查体力要求
            if emotion_state.energy < activity.energy_min:
                continue
            
            # 2. 检查唤醒度范围
            if not (activity.arousal_range[0] <= emotion_state.arousal <= activity.arousal_range[1]):
                continue
            
            # 3. 计算概率权重
            weight = EmotionUtils.calculate_personality_influence(
                personality, activity
            )
            
            # 4. 根据当前状态调整权重
            # 如果很累，休息类活动权重增加
            if emotion_state.energy < 30 and activity.type == "rest":
                weight *= 2.0
            
            # 如果很寂寞，社交类活动权重增加
            if emotion_state.loneliness > 60 and activity.type.startswith("social"):
                weight *= 1.5
            
            # 如果压力大，放松类活动权重增加
            if emotion_state.stress > 60 and activity.type in ["quiet", "rest"]:
                weight *= 1.3
            
            candidates.append((activity, weight))
        
        if not candidates:
            return None
        
        # 加权随机选择
        activities, weights = zip(*candidates)
        return random.choices(activities, weights=weights)[0]
    
    @staticmethod
    def derive_mood_label(pleasure: float, arousal: float, dominance: float) -> str:
        """
        从PAD值派生心情标签
        
        Args:
            pleasure: 愉悦度
            arousal: 唤醒度
            dominance: 支配度
        
        Returns:
            心情标签
        """
        p, a, d = pleasure, arousal, dominance
        
        if p > 0.5 and a > 0.3:
            return "开心"
        elif p > 0.3 and abs(a) < 0.3:
            return "平静"
        elif p < -0.3 and a < -0.3:
            return "疲惫"
        elif p < -0.3 and a > 0.3:
            return "焦虑"
        elif a < -0.5:
            return "困倦"
        elif p > 0.5 and a > 0.6:
            return "兴奋"
        elif p < -0.2:
            return "低落"
        else:
            return "一般"
    
    @staticmethod
    def describe_emotion(pleasure: float, arousal: float) -> str:
        """
        生成情感描述
        
        Args:
            pleasure: 愉悦度
            arousal: 唤醒度
        
        Returns:
            情感描述文本
        """
        p, a = pleasure, arousal
        
        if p > 0.5 and a > 0.3:
            return "心情不错，有点兴奋"
        elif p > 0.3 and abs(a) < 0.3:
            return "挺平静的"
        elif p < -0.3 and a < 0:
            return "有点低落，还有点累"
        elif a < -0.5:
            return "困..."
        elif p < 0 and a > 0.3:
            return "有点烦躁"
        else:
            return "还好"
    
    @staticmethod
    def get_time_slot(hour: int) -> str:
        """
        获取当前时间段名称
        
        Args:
            hour: 当前小时 (0-23)
        
        Returns:
            时间段名称
        """
        if 6 <= hour < 8:
            return "early_morning"
        elif 8 <= hour < 9:
            return "morning_routine"
        elif 9 <= hour < 12:
            return "morning_active"
        elif 12 <= hour < 13:
            return "lunch_time"
        elif 13 <= hour < 14:
            return "afternoon_rest"
        elif 14 <= hour < 18:
            return "afternoon_active"
        elif 18 <= hour < 19:
            return "dinner_time"
        elif 19 <= hour < 21:
            return "evening_leisure"
        elif 21 <= hour < 23:
            return "night_routine"
        else:
            return "sleep_time"
    
    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """限制数值在指定范围内"""
        return max(min_val, min(max_val, value))
    
    @staticmethod
    def add_random_variation(value: float, variation: float = 0.1) -> float:
        """
        给数值添加随机波动
        
        Args:
            value: 原始值
            variation: 波动范围 (0~1)
        
        Returns:
            带随机波动的值
        """
        factor = random.uniform(1.0 - variation, 1.0 + variation)
        return value * factor


