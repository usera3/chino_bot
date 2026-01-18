#!/usr/bin/env python3
"""
测试自然回复风格
验证优化后的系统提示词是否生效
"""
import asyncio
from core.butler import Butler
from langchain_openai import ChatOpenAI
from tools.langchain_tools import get_all_tools
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()


async def test_natural_responses():
    """测试自然回复"""
    print("=" * 80)
    print("🧪 测试自然回复风格")
    print("=" * 80)
    
    # 初始化 LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base="https://api.deepseek.com",
        temperature=0.8,
        max_tokens=200
    )
    
    # 获取工具
    tools = get_all_tools()
    
    # 创建 Butler
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=False,
        use_vector_store=False  # 禁用长期记忆，专注测试回复风格
    )
    
    # 测试用例
    test_cases = [
        {
            "name": "简单问候",
            "message": "你好",
            "expected": "简短回应，不要太长"
        },
        {
            "name": "戳一戳",
            "message": "[空白 戳了戳你]",
            "expected": "简短可爱，不要解释什么是戳一戳"
        },
        {
            "name": "避免鹦鹉学舌",
            "message": "我想吃火锅",
            "expected": "不要重复'你想吃火锅'，直接反应"
        },
        {
            "name": "简洁回复",
            "message": "你是机器人吗",
            "expected": "简短回答，不要超过50字"
        },
        {
            "name": "有态度",
            "message": "请我去洗脚",
            "expected": "不要直接答应，可以害羞或拒绝"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'─' * 80}")
        print(f"测试 {i}/{len(test_cases)}: {test_case['name']}")
        print("─" * 80)
        print(f"用户: {test_case['message']}")
        print(f"期望: {test_case['expected']}")
        
        try:
            response = await butler.aprocess(test_case['message'], user_id="test_user")
            response_length = len(response)
            
            print(f"\n智乃: {response}")
            print(f"字数: {response_length}字")
            
            # 简单检查
            issues = []
            
            # 检查长度
            if response_length > 80:
                issues.append(f"⚠️ 回复过长（{response_length}字 > 80字）")
            
            # 检查鹦鹉学舌
            if "想吃火锅" in test_case['message'] and "想吃火锅" in response:
                issues.append("⚠️ 鹦鹉学舌：重复了用户的话")
            
            # 检查戳一戳解释
            if "戳了戳你" in test_case['message']:
                if "戳一戳" in response or "戳了戳" in response:
                    issues.append("⚠️ 过度解释：不应该解释什么是戳一戳")
            
            if issues:
                print("\n发现问题:")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print("\n✅ 回复风格良好")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 清空记忆，避免影响下一个测试
        butler.clear_memory()
    
    print(f"\n{'=' * 80}")
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_natural_responses())
