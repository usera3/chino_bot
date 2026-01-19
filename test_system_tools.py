"""测试系统工具"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_view_logs():
    """测试查看日志工具"""
    print("=" * 60)
    print("测试 1: 查看 NapCat 日志")
    print("=" * 60)
    
    from tools.system_tools import ViewLogsTool
    
    tool = ViewLogsTool()
    
    # 测试查看 QQ 日志
    result = tool._run(log_type="qq", lines=5)
    print(result)
    
    print("\n" + "=" * 60)
    print("测试 2: 查看机器人日志")
    print("=" * 60)
    
    # 测试查看 Bot 日志
    result = tool._run(log_type="bot", lines=5)
    print(result)


def test_check_system_status():
    """测试系统状态检查"""
    print("\n" + "=" * 60)
    print("测试 3: 检查系统状态")
    print("=" * 60)
    
    from tools.system_tools import CheckSystemStatusTool
    
    tool = CheckSystemStatusTool()
    result = tool._run()
    print(result)


def test_with_butler():
    """测试 Butler 使用系统工具"""
    print("\n" + "=" * 60)
    print("测试 4: Butler 自我诊断")
    print("=" * 60)
    
    from core.butler import Butler
    from langchain_openai import ChatOpenAI
    from tools.basic_tools import get_all_tools
    
    # 初始化 LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base="https://api.deepseek.com",
        temperature=0.7,
    )
    
    # 获取所有工具
    tools = get_all_tools()
    
    # 初始化 Butler
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=True,
        use_dual_memory=False  # 测试时不使用记忆
    )
    
    # 测试场景：模拟工具调用失败后的自我诊断
    test_message = """
我刚才尝试发送文件失败了，帮我看看日志，分析一下是什么原因。
不要把日志内容直接告诉我，而是分析后给我一个友好的解释。
"""
    
    print(f"\n用户消息: {test_message.strip()}")
    print("\n" + "-" * 60)
    
    response = butler.process(test_message, user_id="test_user")
    
    print(f"\n机器人回复: {response}")


if __name__ == "__main__":
    # 测试基础工具
    test_view_logs()
    test_check_system_status()
    
    # 测试 Butler 集成
    print("\n" + "=" * 60)
    print("是否测试 Butler 集成？(y/n)")
    print("=" * 60)
    choice = input("> ").strip().lower()
    
    if choice == 'y':
        test_with_butler()
    else:
        print("\n✅ 基础测试完成！")
