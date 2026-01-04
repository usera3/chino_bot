#!/usr/bin/env python3
"""
设置用户情感状态为能够触发主动聊天的参数
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

def set_trigger_status():
    """设置触发状态"""
    
    # 连接数据库
    db_path = Path("chat_memory.db")
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    user_id = "1446437177"
    
    print(f"🎯 设置用户 {user_id} 为可触发主动聊天状态")
    print("=" * 50)
    
    try:
        # 查询当前状态
        cursor.execute("""
            SELECT happiness, loneliness, energy, confidence, social_need, 
                   intimacy_level, mood, stress_level, last_chat_time
            FROM dynamic_emotion_profiles 
            WHERE user_id = ?
        """, (user_id,))
        
        current_data = cursor.fetchone()
        
        if current_data:
            print("📊 当前状态:")
            happiness, loneliness, energy, confidence, social_need, intimacy_level, mood, stress_level, last_chat_time = current_data
            print(f"  😊 快乐值: {happiness}")
            print(f"  😢 寂寞值: {loneliness}")
            print(f"  👥 社交需求: {social_need}")
            print(f"  🕒 最后聊天: {last_chat_time}")
            
            # 设置触发参数
            # 方案1: 设置高寂寞值 + 高社交需求，确保触发
            new_loneliness = 75.0    # >60 触发 +25分
            new_social_need = 80.0   # >70 触发 +30分
            # 保持其他参数不变，但稍微调整让情况更自然
            new_happiness = 40.0     # 降低快乐值，更符合寂寞的状态
            new_energy = 30.0        # 低体力
            new_mood = "lonely"      # 寂寞心情
            
            # 设置last_chat_time为5小时前，额外触发 +15分
            five_hours_ago = datetime.now() - timedelta(hours=5)
            
            print(f"\n🎯 设置新状态 (目标: >50分触发):")
            print(f"  😢 寂寞值: {loneliness} → {new_loneliness} (+25分)")
            print(f"  👥 社交需求: {social_need} → {new_social_need} (+30分)")
            print(f"  😊 快乐值: {happiness} → {new_happiness}")
            print(f"  ⚡ 体力值: {energy} → {new_energy}")
            print(f"  🎭 心情: {mood} → {new_mood}")
            print(f"  🕒 最后聊天: 设置为5小时前 (+15分)")
            print(f"  📊 预计总分: 25+30+15 = 70分 (远超50分阈值)")
            
            # 更新数据库
            cursor.execute("""
                UPDATE dynamic_emotion_profiles 
                SET loneliness = ?, social_need = ?, happiness = ?, 
                    energy = ?, mood = ?, last_chat_time = ?, last_update = ?
                WHERE user_id = ?
            """, (new_loneliness, new_social_need, new_happiness, 
                  new_energy, new_mood, five_hours_ago.isoformat(), 
                  datetime.now().isoformat(), user_id))
            
            conn.commit()
            print("\n✅ 状态已更新!")
            
            # 验证更新
            cursor.execute("""
                SELECT happiness, loneliness, energy, confidence, social_need, 
                       intimacy_level, mood, stress_level, last_chat_time
                FROM dynamic_emotion_profiles 
                WHERE user_id = ?
            """, (user_id,))
            
            updated_data = cursor.fetchone()
            if updated_data:
                happiness, loneliness, energy, confidence, social_need, intimacy_level, mood, stress_level, last_chat_time = updated_data
                print(f"\n📊 更新后状态:")
                print(f"  😊 快乐值: {happiness}")
                print(f"  😢 寂寞值: {loneliness}")
                print(f"  ⚡ 体力值: {energy}")
                print(f"  👥 社交需求: {social_need}")
                print(f"  🎭 心情: {mood}")
                print(f"  🕒 最后聊天: {last_chat_time}")
                
                # 重新计算得分
                score = 0
                if social_need > 70:
                    score += 30
                if loneliness > 60:
                    score += 25
                if abs(happiness - 50) > 30:
                    score += 20
                
                # 计算时间差
                if last_chat_time:
                    try:
                        last_chat = datetime.fromisoformat(last_chat_time.replace('T', ' ').replace('Z', ''))
                        hours_since_chat = (datetime.now() - last_chat).total_seconds() / 3600
                        if hours_since_chat > 4:
                            score += 15
                    except:
                        pass
                
                print(f"\n📈 新的主动聊天评分: {score}/50")
                print(f"  ⚖️ 判断结果: {'✅ 会主动聊天' if score >= 50 else '❌ 不会主动聊天'}")
                
                if score >= 50:
                    print(f"\n🎉 成功！下次检查时(每15分钟)应该会触发主动聊天")
                    print(f"  ⏰ 当前时间: {datetime.now().strftime('%H:%M')}")
                    next_check = datetime.now() + timedelta(minutes=15 - (datetime.now().minute % 15))
                    print(f"  ⏰ 下次检查: {next_check.strftime('%H:%M')}")
                    print(f"  📋 建议: 观察日志或等待机器人主动发消息")
                
        else:
            print("❌ 未找到用户数据")
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    set_trigger_status()



















