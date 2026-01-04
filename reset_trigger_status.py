#!/usr/bin/env python3
"""
重新设置主动聊天触发状态
数据库重置后重新创建测试数据
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.emotion import get_emotion_service

async def setup_trigger_users():
    """设置测试用户的情感参数，确保能触发主动聊天"""
    
    # 初始化情感服务
    emotion_service = get_emotion_service()
    await emotion_service.initialize()
    
    # 测试用户ID
    test_users = [
        "1446437177",  # 主要测试用户
        "3937775081",  # 次要测试用户
        "1876724923",  # 备用测试用户
        "1503036641",  # 备用测试用户
        "2408983169",
        "2126979584",
        "2443685384"
    ]
    
    print("🔧 开始设置测试用户参数...")
    
    for user_id in test_users:
        # 获取或创建情感档案
        profile = await emotion_service.get_or_create_profile(user_id)
        
        # 设置高触发参数
        profile.happiness = 40  # 低快乐值
        profile.confidence = 100  # 高自信值  
        profile.energy = 30  # 低体力值
        profile.loneliness = 80  # 高寂寞值
        profile.social_need = 100  # 最高社交需求
        profile.stress_level = 20  # 低压力值
        profile.intimacy_level = 0.8  # 高亲密度
        
        # 设置最后聊天时间为5小时前（触发"很久没聊天"）
        from datetime import datetime, timedelta
        profile.last_chat_time = datetime.now() - timedelta(hours=5)
        profile.last_proactive_time = None  # 重置主动聊天时间
        
        # 保存到数据库
        await emotion_service.db_service.save_emotion_profile(profile)
        
        print(f"✅ 用户 {user_id}: 社交需求={profile.social_need}, 寂寞值={profile.loneliness}, 亲密度={profile.intimacy_level}")
    
    print("\n🎯 所有用户参数设置完成！预期情感评分：")
    print("  • 社交需求高(100.0) → +30分")
    print("  • 感到寂寞(80.0) → +25分") 
    print("  • 很久没聊天(5小时) → +15分")
    print("  • 总分: 70分 (≥50分阈值) ✅")
    
    print("\n⏰ 等待下次检查时间...")

if __name__ == "__main__":
    asyncio.run(setup_trigger_users())



















