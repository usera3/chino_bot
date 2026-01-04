"""
测试AI回复多样性
发送相同的消息多次，检查回复的多样性
"""
import asyncio
from core.role_agent import get_role_agent

async def test_diversity():
    """测试回复多样性"""
    agent = get_role_agent()
    
    # 测试消息
    test_message = "你好呀"
    user_id = "test_user_123"
    
    print("=" * 60)
    print(f"测试消息：{test_message}")
    print(f"连续发送5次，观察回复多样性")
    print("=" * 60)
    
    responses = []
    
    for i in range(5):
        print(f"\n第 {i+1} 次发送...")
        response = await agent.chat(
            user_message=test_message,
            user_id=user_id,
            group_id=None
        )
        responses.append(response)
        print(f"回复：{response}")
        print("-" * 60)
        
        # 等待一下，模拟真实对话间隔
        await asyncio.sleep(1)
    
    print("\n" + "=" * 60)
    print("多样性分析：")
    print("=" * 60)
    
    # 检查重复
    unique_responses = set(responses)
    print(f"总回复数：{len(responses)}")
    print(f"不同回复数：{len(unique_responses)}")
    print(f"多样性比例：{len(unique_responses)/len(responses)*100:.1f}%")
    
    if len(unique_responses) == len(responses):
        print("✅ 完美！每次回复都不同")
    elif len(unique_responses) >= len(responses) * 0.6:
        print("⚠️ 中等多样性，建议优化")
    else:
        print("❌ 多样性不足，需要优化")

if __name__ == "__main__":
    asyncio.run(test_diversity())


