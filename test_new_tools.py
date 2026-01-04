"""
测试新集成的工具：Tavily 搜索 和 通义万相图像生成
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.tavily_search_tool import TavilySearchTool
from tools.image_gen_tool import TongyiImageGenTool


async def test_tavily_search():
    """测试 Tavily 智能搜索"""
    print("\n" + "="*60)
    print("🔍 测试 Tavily 智能搜索")
    print("="*60)
    
    tool = TavilySearchTool()
    
    # 检查可用性
    if not tool.is_available():
        print("❌ Tavily 搜索不可用（API密钥未配置）")
        print("💡 配置方法: export TAVILY_API_KEY='your_key'")
        return
    
    print("✅ Tavily 搜索工具已就绪\n")
    
    # 测试搜索
    test_queries = [
        "今天的新闻",
        "比特币价格",
        "Python 最新版本"
    ]
    
    for query in test_queries:
        print(f"\n🔍 搜索: {query}")
        print("-" * 50)
        
        result = await tool.execute(query, max_results=2)
        
        if result.success:
            print(f"✅ 搜索成功")
            print(f"\n{result.message}")
        else:
            print(f"❌ 搜索失败: {result.message}")
        
        print()


async def test_image_generation():
    """测试通义万相图像生成"""
    print("\n" + "="*60)
    print("🎨 测试通义万相图像生成")
    print("="*60)
    
    tool = TongyiImageGenTool()
    
    # 检查可用性
    if not tool.is_available():
        print("❌ 图像生成不可用（API密钥未配置）")
        print("💡 配置方法: export DASHSCOPE_API_KEY='your_key'")
        return
    
    print("✅ 图像生成工具已就绪\n")
    
    # 测试生成
    test_prompts = [
        ("一只可爱的橘猫", "anime", "512x512"),
        ("日落时的海滩", "realistic", "512x512"),
    ]
    
    for prompt, style, size in test_prompts:
        print(f"\n🎨 生成: {prompt} ({style}, {size})")
        print("-" * 50)
        
        result = await tool.execute(prompt, style=style, size=size)
        
        if result.success:
            print(f"✅ 生成成功")
            print(f"\n{result.message}")
            print(f"\n图片URL: {result.data.get('image_url', 'N/A')}")
        else:
            print(f"❌ 生成失败: {result.message}")
        
        print()


async def main():
    """主测试函数"""
    print("\n🚀 开始测试新集成的工具\n")
    
    # 测试 Tavily 搜索
    await test_tavily_search()
    
    # 测试图像生成
    await test_image_generation()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

