"""
表情包索要状态管理
管理用户的表情包选择状态
"""

from typing import Dict, List, Optional
import time
from dataclasses import dataclass
from nonebot.log import logger

@dataclass
class UserRequestState:
    """用户请求状态"""
    user_id: str
    emoticons: List[Dict]
    requested_tags: List[str]
    timestamp: float
    expires_in: float = 300  # 5分钟过期

class EmoticonRequestStateManager:
    """表情包请求状态管理器"""
    
    def __init__(self):
        self.user_states: Dict[str, UserRequestState] = {}
        self.cleanup_interval = 60  # 1分钟清理一次过期状态
        self.last_cleanup = time.time()
    
    def set_user_state(self, user_id: str, emoticons: List[Dict], requested_tags: List[str]):
        """设置用户状态"""
        self.user_states[user_id] = UserRequestState(
            user_id=user_id,
            emoticons=emoticons,
            requested_tags=requested_tags,
            timestamp=time.time()
        )
        logger.info(f"🎨 设置用户 {user_id} 的表情包选择状态，共 {len(emoticons)} 个选项")
    
    def get_user_state(self, user_id: str) -> Optional[UserRequestState]:
        """获取用户状态"""
        self._cleanup_expired_states()
        
        state = self.user_states.get(user_id)
        if state and time.time() - state.timestamp < state.expires_in:
            return state
        elif state:
            # 状态已过期，删除
            del self.user_states[user_id]
            logger.info(f"🎨 用户 {user_id} 的表情包选择状态已过期")
        return None
    
    def clear_user_state(self, user_id: str):
        """清除用户状态"""
        if user_id in self.user_states:
            del self.user_states[user_id]
            logger.info(f"🎨 清除用户 {user_id} 的表情包选择状态")
    
    def _cleanup_expired_states(self):
        """清理过期状态"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_users = []
        for user_id, state in self.user_states.items():
            if current_time - state.timestamp >= state.expires_in:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.user_states[user_id]
            logger.info(f"🎨 清理过期状态: 用户 {user_id}")
        
        self.last_cleanup = current_time

# 全局状态管理器
state_manager = EmoticonRequestStateManager()
