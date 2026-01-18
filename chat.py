"""交互式聊天测试"""
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
    print("🤖 zhinai-bot-v3 - 交互式聊天")
    print("=" * 60)
    print()
    
    # 1. 初始化 LLM
    print("📡 初始化大语言模型...")
    
    if os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
        print("✅ 使用 OpenAI GPT-3.5-turbo")
    elif os.getenv("DEEPSEEK_API_KEY"):
        llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0.7,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        )
        print("✅ 使用 DeepSeek")
    else:
        print("❌ 错误：请在 .env 文件中配置 API Key")
        return
    
    # 2. 创建 Butler
    print("🔧 加载工具...")
    tools = get_all_tools()
    print(f"✅ 已加载 {len(tools)} 个工具")
    
    print("🧠 创建 Butler...")
    butler = Butler(llm=llm, tools=tools, verbose=False)  # 关闭详细日志
    print("✅ Butler 创建成功！")
    print()
    
    # 3. 交互式对话
    print("=" * 60)
    print("💬 开始聊天（输入 'quit' 或 'exit' 退出）")
    print("=" * 60)
    print()
    
    while True:
        try:
            # 获取用户输入
            user_input = input("👤 你: ").strip()
            
            # 退出命令
            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print("\n👋 再见！")
                break
            
            # 清空记忆命令
            if user_input.lower() in ['clear', '清空', 'reset']:
                butler.clear_memory()
                print("✅ 记忆已清空\n")
                continue
            
            # 跳过空输入
            if not user_input:
                continue
            
            # 处理输入
            print()
            response = butler.process(user_input, user_id="interactive_user")
            print(f"🤖 智乃: {response}")
            print()
        
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}\n")


if __name__ == "__main__":
    main()
