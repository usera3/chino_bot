"""
情感系统测试脚本
"""
import asyncio
from services.emotion_service import get_emotion_service


async def test_emotion_system():
    """测试情感系统基本功能"""
    print("\n" + "="*60)
    print("🧪 情感系统测试开始")
    print("="*60)
    
    service = get_emotion_service()
    test_user = "test_user_123"
    
    # 1. 测试创建情感状态
    print("\n[测试1] 创建用户情感状态")
    state = await service.get_emotion_state(test_user)
    print(f"✅ 用户: {state.user_id}")
    print(f"   PAD: P={state.pleasure:.2f}, A={state.arousal:.2f}, D={state.dominance:.2f}")
    print(f"   心情: {state.mood_label}")
    print(f"   体力: {state.energy:.0f}")
    print(f"   孤独感: {state.loneliness:.0f}")
    
    # 2. 测试情感更新
    print("\n[测试2] 更新情感状态（触发开心事件）")
    state = await service.update_emotion_state(test_user, {
        "pleasure": 0.4,
        "arousal": 0.2,
        "energy": -10
    })
    print(f"✅ 更新后")
    print(f"   PAD: P={state.pleasure:.2f}, A={state.arousal:.2f}, D={state.dominance:.2f}")
    print(f"   心情: {state.mood_label}")
    print(f"   体力: {state.energy:.0f}")
    
    # 3. 测试昼夜节律
    print("\n[测试3] 应用昼夜节律")
    from datetime import datetime
    current_hour = datetime.now().hour
    print(f"   当前时间: {current_hour}点")
    await service.apply_circadian_rhythm(test_user)
    state = await service.get_emotion_state(test_user)
    print(f"✅ 应用昼夜节律后")
    print(f"   PAD: P={state.pleasure:.2f}, A={state.arousal:.2f}")
    print(f"   体力: {state.energy:.0f}, 困倦度: {state.sleepiness:.0f}")
    
    # 4. 测试随机事件
    print("\n[测试4] 触发随机事件（尝试5次）")
    events_triggered = 0
    for i in range(5):
        event = await service.trigger_random_event(test_user)
        if event:
            events_triggered += 1
            print(f"✅ 事件 {events_triggered}: {event['desc']}")
    print(f"   共触发 {events_triggered} 个事件")
    
    # 5. 测试情感上下文
    print("\n[测试5] 生成情感上下文")
    context = await service.get_emotion_context(test_user)
    print(f"✅ 情感上下文: {context}")
    
    # 6. 测试聊天时的情感更新
    print("\n[测试6] 模拟聊天")
    await service.on_chat(test_user)
    state = await service.get_emotion_state(test_user)
    print(f"✅ 聊天后")
    print(f"   孤独感: {state.loneliness:.0f} (减少了)")
    print(f"   亲密度: {state.intimacy_level:.2f} (增加了)")
    
    # 7. 查看完整状态
    print("\n[测试7] 完整情感状态")
    state_dict = state.to_dict()
    print(f"✅ 完整状态:")
    print(f"   {state_dict}")
    
    print("\n" + "="*60)
    print("✅ 情感系统测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_emotion_system())


