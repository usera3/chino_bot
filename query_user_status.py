#!/usr/bin/env python3
"""
查询用户当前状态和主动聊天预测
"""
import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

async def query_user_status():
    """查询用户状态"""
    
    # 连接数据库
    db_path = Path("chat_memory.db")
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询用户1446437177的情感数据
    user_id = "1446437177"
    
    print(f"📊 查询用户 {user_id} 的当前状态")
    print("=" * 50)
    
    try:
        # 查询情感档案
        cursor.execute("""
            SELECT happiness, loneliness, energy, confidence, social_need, 
                   intimacy_level, mood, stress_level, last_chat_time, 
                   last_proactive_time, last_update
            FROM dynamic_emotion_profiles 
            WHERE user_id = ?
        """, (user_id,))
        
        emotion_data = cursor.fetchone()
        
        if emotion_data:
            happiness, loneliness, energy, confidence, social_need, intimacy_level, mood, stress_level, last_chat_time, last_proactive_time, last_update = emotion_data
            
            print("💝 情感状态:")
            print(f"  😊 快乐值: {happiness:.1f}/100")
            print(f"  😢 寂寞值: {loneliness:.1f}/100")
            print(f"  ⚡ 体力值: {energy:.1f}/100")
            print(f"  💪 自信值: {confidence:.1f}/100")
            print(f"  👥 社交需求: {social_need:.1f}/100")
            print(f"  💕 亲密度: {intimacy_level:.2f}/1.0")
            print(f"  🎭 当前心情: {mood}")
            print(f"  😰 压力值: {stress_level:.1f}/100")
            print(f"  🕒 最后聊天: {last_chat_time}")
            print(f"  🤖 最后主动: {last_proactive_time}")
            
            print("\n📈 主动聊天评分分析:")
            
            # 计算主动聊天评分
            score = 0
            reasons = []
            
            # 1. 社交需求高
            if social_need > 70:
                score += 30
                reasons.append(f"社交需求高({social_need:.1f}) +30分")
            else:
                reasons.append(f"社交需求正常({social_need:.1f}) +0分")
            
            # 2. 寂寞值高
            if loneliness > 60:
                score += 25
                reasons.append(f"感到寂寞({loneliness:.1f}) +25分")
            else:
                reasons.append(f"不寂寞({loneliness:.1f}) +0分")
            
            # 3. 心情极端
            mood_score = happiness - 50  # 简化的心情计算
            if abs(mood_score) > 30:
                score += 20
                reasons.append(f"心情{'很好' if mood_score > 0 else '很差'}({mood_score:.1f}) +20分")
            else:
                reasons.append(f"心情普通({mood_score:.1f}) +0分")
            
            # 4. 很久没聊天
            if last_chat_time:
                last_chat = datetime.fromisoformat(last_chat_time.replace('T', ' ').replace('Z', ''))
                hours_since_chat = (datetime.now() - last_chat).total_seconds() / 3600
                if hours_since_chat > 4:
                    score += 15
                    reasons.append(f"很久没聊天({hours_since_chat:.1f}小时) +15分")
                else:
                    reasons.append(f"最近聊过天({hours_since_chat:.1f}小时) +0分")
            else:
                reasons.append("从未聊天 +0分")
            
            print(f"\n  当前总分: {score}/50 (需要50分触发)")
            for reason in reasons:
                print(f"  - {reason}")
            
            print(f"\n  ⚖️ 判断结果: {'✅ 会主动聊天' if score >= 50 else '❌ 不会主动聊天'}")
            
            # 计算下次检查时间
            print("\n⏰ 时间信息:")
            print("  检查间隔: 每15分钟")
            print("  活跃时间: 9-12点、14-18点、19-23点")
            
            now = datetime.now()
            next_check = now + timedelta(minutes=15 - (now.minute % 15))
            print(f"  下次检查: {next_check.strftime('%H:%M')}")
            
            # 预测主动聊天时间
            if score < 50:
                # 计算什么时候会达到50分
                needed_score = 50 - score
                print(f"\n🔮 预测主动聊天时间:")
                print(f"  还需要: {needed_score}分")
                
                if needed_score <= 15:
                    hours_needed = 4 - (hours_since_chat if 'hours_since_chat' in locals() else 0)
                    if hours_needed > 0:
                        predicted_time = now + timedelta(hours=hours_needed)
                        print(f"  预计时间: {predicted_time.strftime('%Y-%m-%d %H:%M')} (4小时没聊天后)")
                    else:
                        print("  随时可能触发 (已满足4小时条件)")
                elif needed_score <= 25:
                    print("  需要寂寞值达到60+ 或 社交需求达到70+")
                else:
                    print("  需要多个条件同时满足，或等待长时间不聊天")
            
        else:
            print("❌ 未找到用户情感数据")
        
        # 查询行为档案
        cursor.execute("""
            SELECT total_messages, total_proactive_chats, successful_proactive_chats,
                   relationship_score, intimacy_level, proactivity_score,
                   last_user_message_time, last_bot_proactive_time,
                   today_proactive_count
            FROM user_behavior_profiles
            WHERE user_id = ?
        """, (user_id,))
        
        behavior_data = cursor.fetchone()
        
        if behavior_data:
            total_msg, total_proactive, success_proactive, rel_score, intimacy, proactivity, last_user_msg, last_proactive, today_count = behavior_data
            
            print(f"\n📋 行为档案:")
            print(f"  💬 总消息数: {total_msg}")
            print(f"  🤖 总主动次数: {total_proactive}")
            print(f"  ✅ 成功主动次数: {success_proactive}")
            print(f"  📊 成功率: {(success_proactive/total_proactive*100) if total_proactive > 0 else 0:.1f}%")
            print(f"  💕 关系评分: {rel_score:.2f}")
            print(f"  🎯 主动性评分: {proactivity:.2f}")
            print(f"  📅 今日主动次数: {today_count}/3")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(query_user_status())



















