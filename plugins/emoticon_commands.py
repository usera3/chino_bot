"""
表情包管理命令
提供表情包学习系统的管理命令
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from typing import Optional
from pathlib import Path
import json

from .emoticon_learner import emoticon_learner, LearnerConfig
from sqlalchemy import select, desc, and_
from .emoticon_learner import LearnedEmoticon

# ==================== 统计命令 ====================
emoticon_stats = on_command("表情统计", aliases={"学习统计"}, priority=5, block=True)

@emoticon_stats.handle()
async def handle_emoticon_stats(bot: Bot, event: MessageEvent):
    """查看表情包学习统计"""
    try:
        stats = await emoticon_learner.get_statistics()
        
        message = f"""📊 表情包学习统计

🎓 总学习数量: {stats['total_emoticons']} 个
✅ 活跃表情: {stats['active_emoticons']} 个
📈 总使用次数: {stats['total_uses']} 次
💾 存储路径: {stats['storage_path']}

💡 使用 "/表情列表" 查看学习到的表情包
💡 使用 "/测试表情 <情感>" 测试表情匹配
"""
        await emoticon_stats.send(message)
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        await emoticon_stats.send("❌ 获取统计失败")


# ==================== 表情列表命令 ====================
emoticon_list = on_command("表情列表", priority=5, block=True)

@emoticon_list.handle()
async def handle_emoticon_list(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """查看学习到的表情包列表"""
    try:
        # 解析参数
        arg_text = args.extract_plain_text().strip()
        limit = 10
        if arg_text.isdigit():
            limit = min(int(arg_text), 50)  # 最多50个
        
        async with emoticon_learner.async_session() as session:
            result = await session.execute(
                select(LearnedEmoticon)
                .where(LearnedEmoticon.is_active == True)
                .order_by(desc(LearnedEmoticon.quality_score))
                .limit(limit)
            )
            emoticons = result.scalars().all()
        
        if not emoticons:
            await emoticon_list.send("还没有学习到任何表情包呢 🤔")
            return
        
        message = f"📝 学习到的表情包（Top {len(emoticons)}）\n\n"
        
        for i, emo in enumerate(emoticons, 1):
            emotion_tags = json.loads(emo.emotion_tags)
            keywords = json.loads(emo.keywords)
            
            message += f"{i}. {emo.description}\n"
            message += f"   标签: {', '.join(emotion_tags[:3])}\n"
            message += f"   关键词: {', '.join(keywords[:3])}\n"
            message += f"   评分: {emo.quality_score:.2f} | 使用: {emo.use_count}次\n"
            message += f"   来源: {emo.source_user_id}\n\n"
        
        message += "💡 使用 \"/查看表情 <序号>\" 查看具体表情包"
        
        await emoticon_list.send(message)
        
    except Exception as e:
        logger.error(f"获取列表失败: {e}")
        await emoticon_list.send("❌ 获取列表失败")


# ==================== 查看表情命令 ====================
view_emoticon = on_command("查看表情", priority=5, block=True)

@view_emoticon.handle()
async def handle_view_emoticon(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """查看具体的表情包"""
    try:
        arg_text = args.extract_plain_text().strip()
        
        if not arg_text.isdigit():
            await view_emoticon.finish("❌ 请输入表情包序号，例如：/查看表情 1")
        
        index = int(arg_text)
        
        async with emoticon_learner.async_session() as session:
            result = await session.execute(
                select(LearnedEmoticon)
                .where(LearnedEmoticon.is_active == True)
                .order_by(desc(LearnedEmoticon.quality_score))
                .limit(50)
            )
            emoticons = result.scalars().all()
        
        if index < 1 or index > len(emoticons):
            await view_emoticon.finish(f"❌ 序号超出范围（1-{len(emoticons)}）")
        
        emo = emoticons[index - 1]
        
        # 构建信息
        emotion_tags = json.loads(emo.emotion_tags)
        scene_tags = json.loads(emo.scene_tags)
        keywords = json.loads(emo.keywords)
        
        info_msg = f"""📷 表情包详情

📝 描述: {emo.description}
😊 情感: {', '.join(emotion_tags)}
🎬 场景: {', '.join(scene_tags)}
🔍 关键词: {', '.join(keywords)}

📊 统计:
  评分: {emo.quality_score:.2f}
  使用: {emo.use_count}次
  成功: {emo.success_count}次

👤 来源: {emo.source_user_id}
📅 学习时间: {emo.learned_at.strftime('%Y-%m-%d %H:%M')}
"""
        
        # 发送信息
        await view_emoticon.send(info_msg)
        
        # 发送图片
        file_path = Path(emo.file_path)
        if file_path.exists():
            await view_emoticon.send(MessageSegment.image(file_path))
        else:
            await view_emoticon.send("⚠️ 图片文件不存在")
        
    except Exception as e:
        logger.error(f"查看表情失败: {e}")
        await view_emoticon.finish("❌ 查看表情失败")


# ==================== 测试表情命令 ====================
test_emoticon = on_command("测试表情", priority=5, block=True)

@test_emoticon.handle()
async def handle_test_emoticon(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """测试表情匹配"""
    try:
        arg_text = args.extract_plain_text().strip()
        
        if not arg_text:
            await test_emoticon.finish("❌ 请输入情感类型，例如：/测试表情 happy")
        
        # 获取匹配的表情
        result = await emoticon_learner.get_matching_emoticon(
            emotion=arg_text,
            context="测试上下文",
            keywords=[arg_text]
        )
        
        if not result:
            await test_emoticon.finish(f"❌ 没有找到匹配 '{arg_text}' 的表情包")
        
        file_path, emoticon_id = result
        
        # 获取表情包信息
        async with emoticon_learner.async_session() as session:
            db_result = await session.execute(
                select(LearnedEmoticon).where(LearnedEmoticon.id == emoticon_id)
            )
            emo = db_result.scalar_one_or_none()
        
        if emo:
            info = f"✅ 匹配到表情包: {emo.description}\n评分: {emo.quality_score:.2f}"
            await test_emoticon.send(info)
        
        # 发送图片
        file_path_obj = Path(file_path)
        if file_path_obj.exists():
            await test_emoticon.send(MessageSegment.image(file_path_obj))
        else:
            await test_emoticon.send("⚠️ 图片文件不存在")
        
    except Exception as e:
        logger.error(f"测试表情失败: {e}")
        await test_emoticon.finish("❌ 测试表情失败")


# ==================== 学习开关命令（管理员）====================
toggle_learning = on_command("学习开关", permission=SUPERUSER, priority=5, block=True)

@toggle_learning.handle()
async def handle_toggle_learning(bot: Bot, event: MessageEvent):
    """切换学习功能开关"""
    LearnerConfig.ENABLE_LEARNING = not LearnerConfig.ENABLE_LEARNING
    
    status = "✅ 开启" if LearnerConfig.ENABLE_LEARNING else "❌ 关闭"
    await toggle_learning.finish(f"表情包学习功能已{status}")


# ==================== 删除表情命令（管理员）====================
delete_emoticon = on_command("删除表情", permission=SUPERUSER, priority=5, block=True)

@delete_emoticon.handle()
async def handle_delete_emoticon(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """删除表情包（仅停用，不真正删除文件）"""
    try:
        arg_text = args.extract_plain_text().strip()
        
        if not arg_text.isdigit():
            await delete_emoticon.finish("❌ 请输入表情包ID，例如：/删除表情 123")
        
        emoticon_id = int(arg_text)
        
        async with emoticon_learner.async_session() as session:
            result = await session.execute(
                select(LearnedEmoticon).where(LearnedEmoticon.id == emoticon_id)
            )
            emo = result.scalar_one_or_none()
            
            if not emo:
                await delete_emoticon.finish(f"❌ 表情包ID {emoticon_id} 不存在")
            
            emo.is_active = False
            await session.commit()
        
        await delete_emoticon.finish(f"✅ 已停用表情包: {emo.description}")
        
    except Exception as e:
        logger.error(f"删除表情失败: {e}")
        await delete_emoticon.finish("❌ 删除表情失败")


# ==================== 清空学习命令（管理员）====================
clear_emoticons = on_command("清空表情", permission=SUPERUSER, priority=5, block=True)

@clear_emoticons.handle()
async def handle_clear_emoticons(bot: Bot, event: MessageEvent):
    """清空所有学习到的表情包（慎用）"""
    try:
        async with emoticon_learner.async_session() as session:
            result = await session.execute(select(LearnedEmoticon))
            emoticons = result.scalars().all()
            
            count = len(emoticons)
            
            for emo in emoticons:
                emo.is_active = False
            
            await session.commit()
        
        await clear_emoticons.finish(f"✅ 已停用所有表情包（共{count}个）")
        
    except Exception as e:
        logger.error(f"清空表情失败: {e}")
        await clear_emoticons.finish("❌ 清空表情失败")

