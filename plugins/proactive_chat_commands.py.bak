"""
主动聊天命令 - Proactive Chat Commands
提供主动聊天系统的管理命令
"""

from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.params import CommandArg
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message
import json

# 导入主动聊天决策引擎和情感系统
try:
    from .proactive_decision_engine import proactive_decision_engine
    from .emotion_system import emotion_system
    PROACTIVE_AVAILABLE = True
except ImportError:
    PROACTIVE_AVAILABLE = False
    logger.warning("主动聊天系统未加载")

# ==================== 命令定义 ====================

# 主动聊天状态命令 - 已禁用，使用增强版本
# proactive_status = on_command("主动聊天状态", aliases={"主动状态", "聊天状态"}, priority=5)

# @proactive_status.handle()
# async def handle_proactive_status(event: MessageEvent):
    # """查看主动聊天状态 - 已禁用，使用增强版本"""
    #     pass

# 强制主动聊天命令
force_proactive = on_command("强制主动", aliases={"强制聊天", "主动找我"}, priority=5)

@force_proactive.handle()
async def handle_force_proactive(event: MessageEvent):
    """强制主动聊天（管理员功能）"""
    if not PROACTIVE_AVAILABLE:
        await force_proactive.finish("❌ 主动聊天系统未启用")
    
    user_id = str(event.user_id)
    
    # 检查管理员权限（这里简化处理，实际应该从配置读取）
    admin_users = ["1446437177"]  # 管理员QQ号
    if user_id not in admin_users:
        await force_proactive.finish("❌ 此功能仅限管理员使用")
    
    try:
        # 获取当前情感状态
        profile = await emotion_system.get_or_create_profile(user_id)
        emotion_state = {
            'happiness': profile.happiness,
            'loneliness': profile.loneliness,
            'energy': profile.energy,
            'confidence': profile.confidence,
            'mood': profile.mood,
            'charm': profile.charm,
            'intelligence': profile.intelligence,
            'creativity': profile.creativity,
            'empathy': profile.empathy
        }
        
        # 调用主动聊天
        await proactive_decision_engine._execute_proactive_chat(user_id, emotion_state)
        
        await force_proactive.finish("✅ 已触发主动聊天")
        
    except Exception as e:
        logger.error(f"强制主动聊天失败: {e}")
        await force_proactive.finish(f"❌ 强制主动聊天失败: {str(e)}")

# 情感调试命令
emotion_debug = on_command("情感调试", aliases={"情感信息", "心情状态"}, priority=5)

@emotion_debug.handle()
async def handle_emotion_debug(event: MessageEvent):
    """查看详细的情感调试信息"""
    if not PROACTIVE_AVAILABLE:
        await emotion_debug.finish("❌ 情感系统未启用")
    
    user_id = str(event.user_id)
    
    try:
        profile = await emotion_system.get_or_create_profile(user_id)
        
        debug_msg = f"""🔍 情感调试信息

【原始数据】
快乐值: {profile.happiness}
寂寞值: {profile.loneliness}
体力值: {profile.energy}
自信值: {profile.confidence}
魅力值: {profile.charm}
智力值: {profile.intelligence}
创造力: {profile.creativity}
同理心: {profile.empathy}
心情: {profile.mood}
压力值: {profile.stress_level}
社交需求: {profile.social_need}

【时间信息】
最后更新: {profile.last_update}
最后聊天: {profile.last_chat_time or '从未聊天'}
最后主动: {profile.last_proactive_time or '从未主动'}

【阈值检查】
寂寞阈值: {profile.loneliness >= 30} (需要: >=30)
体力阈值: {profile.energy >= 20} (需要: >=20)
社交需求: {profile.social_need >= 70} (需要: >=70)"""
        
        await emotion_debug.finish(debug_msg)
        
    except Exception as e:
        logger.error(f"获取情感调试信息失败: {e}")
        await emotion_debug.finish(f"❌ 获取调试信息失败: {str(e)}")

# 情感调整命令（管理员）
emotion_adjust = on_command("调整情感", aliases={"修改情感", "设置情感"}, priority=5)

@emotion_adjust.handle()
async def handle_emotion_adjust(event: MessageEvent, args: Message = CommandArg()):
    """调整情感参数（管理员功能）"""
    if not PROACTIVE_AVAILABLE:
        await emotion_adjust.finish("❌ 情感系统未启用")
    
    user_id = str(event.user_id)
    
    # 检查管理员权限
    admin_users = ["1446437177"]
    if user_id not in admin_users:
        await emotion_adjust.finish("❌ 此功能仅限管理员使用")
    
    try:
        args_text = args.extract_plain_text().strip()
        if not args_text:
            await emotion_adjust.finish(
                "💝 情感调整命令\n\n"
                "用法: /调整情感 <参数>=<值>\n\n"
                "可用参数:\n"
                "happiness=快乐值 (0-100)\n"
                "loneliness=寂寞值 (0-100)\n"
                "energy=体力值 (0-100)\n"
                "confidence=自信值 (0-100)\n"
                "charm=魅力值 (0-100)\n"
                "intelligence=智力值 (0-100)\n"
                "creativity=创造力 (0-100)\n"
                "empathy=同理心 (0-100)\n"
                "stress_level=压力值 (0-100)\n"
                "social_need=社交需求 (0-100)\n\n"
                "示例: /调整情感 happiness=80 loneliness=20"
            )
        
        # 解析参数
        changes = {}
        for pair in args_text.split():
            if '=' in pair:
                key, value = pair.split('=', 1)
                try:
                    changes[key] = float(value)
                except ValueError:
                    await emotion_adjust.finish(f"❌ 无效数值: {value}")
        
        if not changes:
            await emotion_adjust.finish("❌ 没有有效的参数")
        
        # 应用变化
        await emotion_system.update_emotion(
            user_id, 
            changes, 
            "manual_adjust", 
            f"管理员调整: {changes}"
        )
        
        await emotion_adjust.finish(f"✅ 情感参数已调整: {changes}")
        
    except Exception as e:
        logger.error(f"调整情感参数失败: {e}")
        await emotion_adjust.finish(f"❌ 调整失败: {str(e)}")

# 导出
__all__ = ['proactive_status', 'force_proactive', 'emotion_debug', 'emotion_adjust']