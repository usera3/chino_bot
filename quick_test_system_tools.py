"""快速测试系统工具是否对 Butler 生效"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from core.butler import Butler
from langchain_openai import ChatOpenAI
from tools.basic_tools import get_all_tools

# 初始化
llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com",
    temperature=0.7,
)

tools = get_all_tools()
print(f"✅ 已加载 {len(tools)} 个工具")

# 检查系统工具
system_tools = [t for t in tools if t.name in ['view_logs', 'check_system_status']]
print(f"✅ 系统工具: {[t.name for t in system_tools]}")

butler = Butler(llm=llm, tools=tools, verbose=True, use_dual_memory=False)

# 测试
print("\n" + "="*60)
print("测试：让 Butler 查看日志")
print("="*60)

response = butler.process("帮我看看 NapCat 的最新 3 条日志", user_id="test")

print(f"\n机器人回复:\n{response}")
