#!/usr/bin/env python3
"""
代码操作工具 - 快速测试
用于在 QQ 中测试机器人的代码操作能力
"""
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.butler import Butler
from tools.basic_tools import get_all_tools
from langchain_openai import ChatOpenAI


def test_code_tools():
    """测试代码操作工具"""
    print("=" * 60)
    print("🧪 代码操作工具 - 快速测试")
    print("=" * 60)
    
    # 初始化 LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base="https://api.deepseek.com",
        temperature=0.7,
    )
    
    # 获取所有工具
    tools = get_all_tools()
    print(f"\n✅ 已加载 {len(tools)} 个工具")
    
    # 初始化 Butler
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=True,
        use_dual_memory=False  # 快速测试不使用记忆
    )
    print("✅ Butler 初始化成功\n")
    
    # 测试场景
    test_cases = [
        "读取 bot.py",
        "列出 tools 目录的文件",
        "在所有 Python 文件中搜索 Butler",
        "查看项目结构",
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}: {test_input}")
        print(f"{'='*60}")
        
        try:
            response = butler.process(test_input, user_id="test_user")
            print(f"\n🤖 回复:\n{response}")
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("✅ 测试完成！")
    print(f"{'='*60}")


if __name__ == "__main__":
    test_code_tools()
