"""测试 Butler（管家）"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from core.butler import Butler
from tools.basic_tools import get_all_tools

# 加载环境变量
load_dotenv()


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 zhinai-bot-v3 - Butler 测试")
    print("=" * 60)
    print()
    
    # 1. 初始化 LLM
    print("📡 初始化大语言模型...")
    
    # 方式 1: OpenAI（推荐）
    if os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
        print("✅ 使用 OpenAI GPT-3.5-turbo")
    
    # 方式 2: DeepSeek
    elif os.getenv("DEEPSEEK_API_KEY"):
        llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0.7,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        )
        print("✅ 使用 DeepSeek")
    
    else:
        print("❌ 错误：请在 .env 文件中配置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY")
        return
    
    print()
    
    # 2. 获取工具
    print("🔧 加载工具...")
    tools = get_all_tools()
    print(f"✅ 已加载 {len(tools)} 个工具：")
    for tool in tools:
        print(f"   - {tool.name}: {tool.description}")
    print()
    
    # 3. 创建 Butler
    print("🧠 创建 Butler（管家）...")
    butler = Butler(llm=llm, tools=tools, verbose=True)
    print("✅ Butler 创建成功！")
    print()
    
    # 4. 测试对话
    print("=" * 60)
    print("💬 开始测试对话")
    print("=" * 60)
    print()
    
    test_cases = [
        "你好！",
        "现在几点了？",
        "北京的天气怎么样？",
        "查一下上海明天的天气，如果下雨就发邮件提醒我",
        "我对你的印象很好！",
    ]
    
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}/{len(test_cases)}")
        print(f"{'='*60}")
        print(f"👤 用户: {user_input}")
        print()
        
        try:
            response = butler.process(user_input, user_id="test_user")
            print(f"🤖 智乃: {response}")
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        print()
    
    print("=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
