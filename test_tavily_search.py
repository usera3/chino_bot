"""测试 Tavily 搜索功能（SSL 修复后）"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_tavily_search():
    """测试 Tavily 搜索"""
    print("=" * 60)
    print("测试 Tavily 搜索功能")
    print("=" * 60)
    
    # 导入工具
    from tools.langchain_tools import get_search_tool
    
    # 获取搜索工具
    search_tool = get_search_tool()
    
    if not search_tool:
        print("❌ 搜索工具初始化失败")
        return
    
    print(f"\n✅ 搜索工具初始化成功")
    print(f"工具名称: {search_tool.name}")
    print(f"工具描述: {search_tool.description[:50]}...")
    
    # 测试搜索
    print("\n" + "=" * 60)
    print("测试搜索：特朗普最新新闻")
    print("=" * 60)
    
    try:
        result = search_tool.invoke("特朗普 最新新闻 2026年1月")
        print(f"\n✅ 搜索成功！")
        print(f"\n搜索结果:")
        print(result)
    except Exception as e:
        print(f"\n❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tavily_search()
