"""测试系统工具与 Butler 的集成"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_butler_self_diagnosis():
    """测试 Butler 的自我诊断能力"""
    print("=" * 60)
    print("测试场景：模拟工具调用失败后的自我诊断")
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
    
    print(f"\n✅ 已加载 {len(tools)} 个工具")
    
    # 检查系统工具是否存在
    system_tool_names = [tool.name for tool in tools if tool.name in ['view_logs', 'check_system_status']]
    print(f"✅ 系统工具: {system_tool_names}")
    
    # 初始化 Butler
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=True,
        use_dual_memory=False  # 测试时不使用记忆
    )
    
    # 测试场景 1：查看日志
    print("\n" + "=" * 60)
    print("场景 1：主动查看日志")
    print("=" * 60)
    
    test_message_1 = "帮我看看 NapCat 的最新 5 条日志"
    
    print(f"\n用户: {test_message_1}")
    print("-" * 60)
    
    response_1 = butler.process(test_message_1, user_id="test_user")
    
    print(f"\n机器人: {response_1}")
    
    # 测试场景 2：检查系统状态
    print("\n" + "=" * 60)
    print("场景 2：检查系统状态")
    print("=" * 60)
    
    test_message_2 = "检查一下系统状态"
    
    print(f"\n用户: {test_message_2}")
    print("-" * 60)
    
    response_2 = butler.process(test_message_2, user_id="test_user")
    
    print(f"\n机器人: {response_2}")
    
    # 测试场景 3：模拟错误后的自我诊断
    print("\n" + "=" * 60)
    print("场景 3：模拟工具失败后的自我诊断")
    print("=" * 60)
    
    test_message_3 = """
我刚才尝试发送文件失败了，帮我看看日志分析一下原因。
不要把日志内容直接告诉我，而是分析后给我一个友好的解释。
"""
    
    print(f"\n用户: {test_message_3.strip()}")
    print("-" * 60)
    
    response_3 = butler.process(test_message_3, user_id="test_user")
    
    print(f"\n机器人: {response_3}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_butler_self_diagnosis()
