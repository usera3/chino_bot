"""演示脚本 - 展示 Butler 的能力"""
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
    print("🤖 zhinai-bot-v3 - Butler 演示")
    print("=" * 60)
    print()
    
    # 初始化 LLM
    print("📡 初始化 DeepSeek...")
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0.7,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    print("✅ DeepSeek 初始化成功")
    print()
    
    # 创建 Butler
    print("🧠 创建 Butler...")
    tools = get_all_tools()
    butler = Butler(llm=llm, tools=tools, verbose=False)  # 关闭详细日志
    print("✅ Butler 创建成功")
    print()
    
    # 演示对话
    print("=" * 60)
    print("💬 开始演示")
    print("=" * 60)
    print()
    
    demos = [
        ("你好，我是小明", "简单问候 + 自我介绍"),
        ("现在几点了？", "查询时间"),
        ("我叫什么名字？", "测试记忆"),
        ("北京的天气怎么样？", "查询天气"),
        ("查一下广州明天的天气，如果下雨就发邮件提醒我", "复杂任务：条件判断"),
    ]
    
    for i, (user_input, description) in enumerate(demos, 1):
        print(f"\n{'='*60}")
        print(f"演示 {i}/{len(demos)}: {description}")
        print(f"{'='*60}")
        print(f"👤 用户: {user_input}")
        print()
        
        try:
            response = butler.process(user_input, user_id="demo_user")
            print(f"🤖 智乃: {response}")
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        print()
        
        # 暂停一下，避免请求太快
        import time
        time.sleep(1)
    
    print("=" * 60)
    print("✅ 演示完成！")
    print("=" * 60)
    print()
    print("💡 提示:")
    print("   - 运行 'python chat.py' 可以进行交互式对话")
    print("   - 运行 'python test_butler.py' 可以看到详细的推理过程")
    print()


if __name__ == "__main__":
    main()
