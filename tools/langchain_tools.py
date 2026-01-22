"""
LangChain 工具集成
使用 LangChain Community 提供的现成工具
"""
import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_experimental.tools import PythonREPLTool
from langchain_core.tools import Tool


def get_search_tool():
    """获取搜索工具（Tavily）- 禁用 SSL 验证"""
    api_key = os.getenv("TAVILY_API_KEY")
    
    if not api_key:
        print("⚠️ TAVILY_API_KEY 未配置，搜索功能将不可用")
        return None
    
    try:
        # 禁用 SSL 警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 设置环境变量禁用 SSL 验证
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        
        # 创建不验证 SSL 的 SSL 上下文
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Monkey patch aiohttp 的 SSL 上下文
        import aiohttp
        original_init = aiohttp.ClientSession.__init__
        
        def patched_init(self, *args, **kwargs):
            # 强制使用不验证 SSL 的上下文
            if 'connector' not in kwargs:
                kwargs['connector'] = aiohttp.TCPConnector(ssl=False)
            original_init(self, *args, **kwargs)
        
        aiohttp.ClientSession.__init__ = patched_init
        
        search = TavilySearchResults(
            api_key=api_key,
            max_results=3,
            search_depth="basic",  # "basic" 或 "advanced"
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )
        
        # 设置工具描述（中文）
        search.name = "search"
        search.description = """搜索互联网获取最新信息。
使用场景：
- 查询最新新闻、事件
- 搜索技术文档、教程
- 查找产品信息、价格
- 获取实时数据

输入：搜索关键词（字符串）
输出：搜索结果摘要"""
        
        print("✅ Tavily 搜索工具已启用（SSL 验证已禁用 - aiohttp patched）")
        return search
    
    except Exception as e:
        print(f"⚠️ Tavily 搜索工具初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_wikipedia_tool():
    """获取维基百科工具"""
    try:
        api_wrapper = WikipediaAPIWrapper(
            top_k_results=2,
            doc_content_chars_max=2000,
            lang="zh"  # 中文维基百科
        )
        
        wiki = WikipediaQueryRun(api_wrapper=api_wrapper)
        
        # 设置工具描述（中文）
        wiki.name = "wikipedia"
        wiki.description = """查询维基百科获取百科知识。
使用场景：
- 查询人物、事件、概念的详细信息
- 了解历史事件、科学知识
- 获取权威的百科资料

输入：查询关键词（字符串）
输出：维基百科摘要"""
        
        return wiki
    
    except Exception as e:
        print(f"⚠️ Wikipedia 工具初始化失败: {e}")
        return None


def get_python_repl_tool():
    """获取 Python REPL 工具（代码执行）"""
    try:
        python_repl = PythonREPLTool()
        
        # 设置工具描述（中文）
        python_repl.name = "python_repl"
        python_repl.description = """执行 Python 代码进行复杂计算和数据处理。

⚠️ 使用场景（只在以下情况使用）：
1. 大数运算（如 2**1000、阶乘等）
2. 复杂数学计算（需要 math、numpy 等库）
3. 数据处理（列表、字典、排序、统计）
4. 日期时间计算（需要 datetime 库）
5. 字符串复杂处理（正则表达式、编码等）
6. 需要精确结果的科学计算

❌ 不要用于：
- 简单的加减乘除（LLM 可以直接计算）
- 基础的数学运算（如 123 * 456）

⚠️ 安全提示：
- 只执行安全的计算代码
- 不执行文件操作、网络请求等危险操作

输入：Python 代码（字符串）
输出：执行结果"""
        
        return python_repl
    
    except Exception as e:
        print(f"⚠️ Python REPL 工具初始化失败: {e}")
        return None


def get_duckduckgo_tool():
    """获取 DuckDuckGo 搜索工具（免费备选）"""
    try:
        wrapper = DuckDuckGoSearchAPIWrapper(max_results=3)
        
        search = Tool(
            name="duckduckgo_search",
            description="""使用 DuckDuckGo 搜索引擎搜索信息（免费）。
适用于一般性搜索查询。

输入：搜索关键词（字符串）
输出：搜索结果摘要""",
            func=wrapper.run,
        )
        
        return search
    
    except Exception as e:
        print(f"⚠️ DuckDuckGo 搜索工具初始化失败: {e}")
        return None


def get_all_langchain_tools():
    """获取所有 LangChain 工具"""
    tools = []
    
    # 1. Tavily 搜索（优先）
    tavily_tool = get_search_tool()
    if tavily_tool:
        tools.append(tavily_tool)
        print("✅ 已加载: Tavily 搜索工具")
    
    # 2. Wikipedia 百科
    wiki_tool = get_wikipedia_tool()
    if wiki_tool:
        tools.append(wiki_tool)
        print("✅ 已加载: Wikipedia 百科工具")
    
    # 3. Python REPL（代码执行）
    python_tool = get_python_repl_tool()
    if python_tool:
        tools.append(python_tool)
        print("✅ 已加载: Python REPL 工具")
    
    # 4. 图像识别（Qwen-VL）
    from .vision_tool import get_vision_tool
    vision_tool = get_vision_tool()
    if vision_tool:
        tools.append(vision_tool)
        print("✅ 已加载: 图像识别工具 (Qwen-VL)")
    
    # 5. 定时任务（旧版，保留兼容）
    from .scheduler_tool import get_scheduler_tool
    scheduler_tool = get_scheduler_tool()
    if scheduler_tool:
        tools.append(scheduler_tool)
        print("✅ 已加载: 定时任务工具")
    
    # 6. DuckDuckGo 搜索（备选）
    # duckduckgo_tool = get_duckduckgo_tool()
    # if duckduckgo_tool:
    #     tools.append(duckduckgo_tool)
    #     print("✅ 已加载: DuckDuckGo 搜索工具")
    
    return tools


def build_tool_registry(tools: list) -> dict:
    """
    构建工具注册表
    
    Args:
        tools: 工具列表
    
    Returns:
        工具注册表 {tool_name: tool_instance}
    """
    registry = {}
    
    for tool in tools:
        # 获取工具名称
        if hasattr(tool, 'name'):
            tool_name = tool.name
        elif hasattr(tool, '__name__'):
            tool_name = tool.__name__
        else:
            tool_name = tool.__class__.__name__
        
        registry[tool_name] = tool
    
    return registry
