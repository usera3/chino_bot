# zhinai-bot-v3 实现任务清单（深度 LangChain 版）

## 📋 核心理念

**深度使用 LangChain 生态系统，充分利用其 Agent、Memory、VectorStore、LangGraph 等功能**

---

## 🎯 阶段 1: LangChain 基础设施（3 天）

### Task 1.1: 项目初始化与 LangChain 配置
**优先级**: P0  
**预计时间**: 4 小时

**子任务**:
- [ ] 1.1.1 创建 `pyproject.toml` - 添加 LangChain 完整依赖
- [ ] 1.1.2 创建 `.env.example` - LangChain 相关配置
- [ ] 1.1.3 创建 `config/langchain_config.py` - LangChain 配置管理
- [ ] 1.1.4 创建 `config/settings.py` - 全局配置

**LangChain 依赖**:
```toml
[tool.poetry.dependencies]
langchain = "^0.1.0"
langchain-core = "^0.1.0"
langchain-community = "^0.0.20"
langchain-openai = "^0.0.5"
langgraph = "^0.0.20"
langsmith = "^0.0.77"
chromadb = "^0.4.22"
sentence-transformers = "^2.2.2"
```

**验收标准**:
- `poetry install` 成功
- LangChain 配置可以加载
- LangSmith 连接成功

---

### Task 1.2: Butler 核心（基于 LangChain Agent）
**优先级**: P0  
**预计时间**: 8 小时

**子任务**:
- [ ] 1.2.1 创建 `core/butler.py` - 管家主类
- [ ] 1.2.2 集成 LangChain AgentExecutor
- [ ] 1.2.3 配置 ReAct Agent
- [ ] 1.2.4 实现 Prompt 模板管理
- [ ] 1.2.5 集成 LangSmith Callbacks
- [ ] 1.2.6 创建 `tests/test_butler.py`

**核心代码**:
```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain.callbacks import LangChainTracer

class Butler:
    def __init__(self, llm, tools, vector_store):
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=self._create_prompt()
        )
        
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=tools,
            memory=self.memory,
            verbose=True,
            callbacks=[LangChainTracer()]
        )
    
    async def process(self, user_input: str) -> str:
        result = await self.executor.ainvoke({"input": user_input})
        return result["output"]
```

**验收标准**:
- Butler 可以执行基础推理
- Agent 可以调用工具
- LangSmith 可以追踪调用链
- 单元测试通过

---

### Task 1.3: Memory 系统（LangChain Memory）
**优先级**: P0  
**预计时间**: 6 小时

**子任务**:
- [ ] 1.3.1 创建 `core/memory_manager.py`
- [ ] 1.3.2 集成 ConversationBufferMemory（短期记忆）
- [ ] 1.3.3 集成 ConversationSummaryMemory（摘要记忆）
- [ ] 1.3.4 集成 VectorStoreRetrieverMemory（向量记忆）
- [ ] 1.3.5 实现记忆检索和保存
- [ ] 1.3.6 创建 `tests/test_memory.py`

**核心代码**:
```python
from langchain.memory import (
    ConversationBufferMemory,
    VectorStoreRetrieverMemory
)
from langchain.vectorstores import Chroma

class MemoryManager:
    def __init__(self, llm, embeddings):
        # 短期记忆
        self.buffer_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # 向量记忆
        vectorstore = Chroma(
            embedding_function=embeddings,
            persist_directory="./data/chroma"
        )
        self.vector_memory = VectorStoreRetrieverMemory(
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3})
        )
    
    async def save_context(self, input: str, output: str):
        """保存对话到记忆"""
        self.buffer_memory.save_context({"input": input}, {"output": output})
        await self.vector_memory.asave_context({"input": input}, {"output": output})
    
    async def retrieve_relevant(self, query: str) -> list:
        """检索相关记忆"""
        return await self.vector_memory.aload_memory_variables({"prompt": query})
```

**验收标准**:
- 短期记忆正常工作
- 向量记忆可以检索
- 记忆可以持久化

---

### Task 1.4: VectorStore 集成（Chroma）
**优先级**: P0  
**预计时间**: 4 小时

**子任务**:
- [ ] 1.4.1 创建 `core/vector_store.py`
- [ ] 1.4.2 配置 Chroma 向量数据库
- [ ] 1.4.3 配置 Embeddings（DashScope/本地）
- [ ] 1.4.4 实现文档添加和检索
- [ ] 1.4.5 创建 `tests/test_vector_store.py`

**核心代码**:
```python
from langchain.vectorstores import Chroma
from langchain.embeddings import DashScopeEmbeddings
from langchain.schema import Document

class VectorStoreManager:
    def __init__(self):
        self.embeddings = DashScopeEmbeddings()
        self.vectorstore = Chroma(
            collection_name="chat_history",
            embedding_function=self.embeddings,
            persist_directory="./data/chroma"
        )
    
    async def add_texts(self, texts: list[str], metadatas: list[dict]):
        """添加文本到向量库"""
        await self.vectorstore.aadd_texts(texts, metadatas=metadatas)
    
    async def similarity_search(self, query: str, k: int = 3, filter: dict = None):
        """语义检索"""
        return await self.vectorstore.asimilarity_search(
            query, k=k, filter=filter
        )
```

**验收标准**:
- Chroma 数据库正常工作
- 文档可以添加和检索
- 语义检索准确

---

## 🔌 阶段 2: 插件系统（LangChain Tools）（4 天）

### Task 2.1: 插件基础设施
**优先级**: P0  
**预计时间**: 4 小时

**子任务**:
- [ ] 2.1.1 创建 `plugins/base_plugin.py` - 插件基类
- [ ] 2.1.2 创建 `core/plugin_manager.py` - 插件管理器
- [ ] 2.1.3 实现插件自动发现
- [ ] 2.1.4 实现工具注册（LangChain Tools）
- [ ] 2.1.5 创建 `tests/test_plugin_system.py`

**核心代码**:
```python
from langchain.tools import BaseTool
from abc import ABC, abstractmethod

class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """返回 LangChain Tools"""
        pass

class PluginManager:
    def __init__(self):
        self.plugins = {}
        self.tools = []
    
    def register_plugin(self, plugin: Plugin):
        self.plugins[plugin.name] = plugin
        self.tools.extend(plugin.get_tools())
    
    def get_all_tools(self) -> list[BaseTool]:
        return self.tools
```

**验收标准**:
- 插件可以自动发现
- 工具可以注册到 Butler
- 插件系统测试通过

---

### Task 2.2: 情感系统插件（LangChain Tools）
**优先级**: P1  
**预计时间**: 6 小时

**子任务**:
- [ ] 2.2.1 创建 `plugins/emotion/plugin.py`
- [ ] 2.2.2 创建 `plugins/emotion/tools.py` - BaseTool 实现
- [ ] 2.2.3 实现 GetEmotionTool
- [ ] 2.2.4 实现 UpdateEmotionTool
- [ ] 2.2.5 实现 GetEmotionHistoryTool
- [ ] 2.2.6 创建 `tests/plugins/test_emotion.py`

**核心代码**:
```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class GetEmotionInput(BaseModel):
    user_id: str = Field(description="用户ID")

class GetEmotionTool(BaseTool):
    name = "get_emotion"
    description = "获取用户的情感值（好感度、亲密度、心情）"
    args_schema = GetEmotionInput
    
    def _run(self, user_id: str) -> dict:
        # 从数据库获取
        return {"affection": 80, "intimacy": 60, "mood": "happy"}
    
    async def _arun(self, user_id: str) -> dict:
        return self._run(user_id)

class EmotionPlugin(Plugin):
    name = "emotion"
    
    def get_tools(self) -> list[BaseTool]:
        return [GetEmotionTool(), UpdateEmotionTool(), ...]
```

**验收标准**:
- 所有工具符合 LangChain BaseTool 标准
- 工具可以被 Agent 调用
- 参数验证正确

---

### Task 2.3: 记忆插件（LangChain Memory Tools）
**优先级**: P1  
**预计时间**: 6 小时

**子任务**:
- [ ] 2.3.1 创建 `plugins/memory/plugin.py`
- [ ] 2.3.2 创建 `plugins/memory/tools.py`
- [ ] 2.3.3 实现 SaveMemoryTool
- [ ] 2.3.4 实现 SearchMemoryTool
- [ ] 2.3.5 实现 GetContextTool
- [ ] 2.3.6 集成 VectorStore

**核心代码**:
```python
class SearchMemoryTool(BaseTool):
    name = "search_memory"
    description = "搜索历史对话记忆，找到相关的过往对话"
    
    def __init__(self, vector_store):
        super().__init__()
        self.vector_store = vector_store
    
    def _run(self, query: str, user_id: str) -> list:
        results = self.vector_store.similarity_search(
            query,
            filter={"user_id": user_id},
            k=3
        )
        return [doc.page_content for doc in results]
```

**验收标准**:
- 记忆可以保存和检索
- 语义搜索准确
- 与 VectorStore 集成正常

---

### Task 2.4: NoneBot 插件适配器
**优先级**: P1  
**预计时间**: 8 小时

**子任务**:
- [ ] 2.4.1 创建 `adapters/nonebot_adapter.py`
- [ ] 2.4.2 实现插件扫描
- [ ] 2.4.3 实现 @on_command → BaseTool 转换
- [ ] 2.4.4 实现参数映射（自动生成 Pydantic Schema）
- [ ] 2.4.5 测试常见插件（邮件、天气）
- [ ] 2.4.6 创建 `tests/test_nonebot_adapter.py`

**核心代码**:
```python
from langchain.tools import StructuredTool
import inspect

class NoneBotPluginAdapter:
    def convert_command_to_tool(self, command_handler) -> BaseTool:
        """将 NoneBot 命令转换为 LangChain Tool"""
        sig = inspect.signature(command_handler)
        args_schema = self._create_schema(sig)
        
        return StructuredTool(
            name=command_handler.__name__,
            description=command_handler.__doc__ or "NoneBot 插件",
            func=command_handler,
            args_schema=args_schema
        )
```

**验收标准**:
- 可以自动转换 NoneBot 插件
- 至少 3 个插件成功适配
- 转换后的工具可以被 Agent 调用

---

## 🌊 阶段 3: 高级功能（LangGraph + LangSmith）（5 天）

### Task 3.1: LangGraph 工作流引擎
**优先级**: P1  
**预计时间**: 10 小时

**子任务**:
- [ ] 3.1.1 创建 `core/workflow_engine.py`
- [ ] 3.1.2 定义工作流状态（StateGraph）
- [ ] 3.1.3 实现基础工作流节点
- [ ] 3.1.4 实现条件分支
- [ ] 3.1.5 实现循环与迭代
- [ ] 3.1.6 创建 `tests/test_workflow.py`

**核心代码**:
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class WorkflowState(TypedDict):
    messages: list
    user_id: str
    current_step: str
    results: dict

class WorkflowEngine:
    def __init__(self, butler: Butler):
        self.butler = butler
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        workflow = StateGraph(WorkflowState)
        
        # 定义节点
        workflow.add_node("analyze", self._analyze)
        workflow.add_node("plan", self._plan)
        workflow.add_node("execute", self._execute)
        workflow.add_node("synthesize", self._synthesize)
        
        # 定义边
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "plan")
        workflow.add_conditional_edges(
            "plan",
            self._should_continue,
            {
                "continue": "execute",
                "end": END
            }
        )
        workflow.add_edge("execute", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    async def run(self, input: dict) -> dict:
        return await self.graph.ainvoke(input)
```

**验收标准**:
- 工作流可以定义和执行
- 条件分支正常工作
- 工作流可以可视化

---

### Task 3.2: LangSmith 深度集成
**优先级**: P1  
**预计时间**: 4 小时

**子任务**:
- [ ] 3.2.1 配置 LangSmith API Key
- [ ] 3.2.2 集成 LangChainTracer
- [ ] 3.2.3 添加自定义 Metadata
- [ ] 3.2.4 配置 Feedback 收集
- [ ] 3.2.5 创建监控面板

**核心代码**:
```python
from langchain.callbacks import LangChainTracer
from langsmith import Client

class LangSmithIntegration:
    def __init__(self):
        self.client = Client()
        self.tracer = LangChainTracer(
            project_name="zhinai-bot-v3",
            client=self.client
        )
    
    def get_callbacks(self):
        return [self.tracer]
    
    async def add_feedback(self, run_id: str, score: float, comment: str):
        """添加用户反馈"""
        self.client.create_feedback(
            run_id=run_id,
            key="user_satisfaction",
            score=score,
            comment=comment
        )
```

**验收标准**:
- 所有调用自动追踪到 LangSmith
- 可以查看完整调用链
- 性能数据可视化

---

### Task 3.3: LCEL 链式调用
**优先级**: P2  
**预计时间**: 6 小时

**子任务**:
- [ ] 3.3.1 创建 `core/chains.py`
- [ ] 3.3.2 实现常用 Chain（摘要、翻译等）
- [ ] 3.3.3 使用 LCEL 组合 Chain
- [ ] 3.3.4 集成到 Butler
- [ ] 3.3.5 创建 `tests/test_chains.py`

**核心代码**:
```python
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 使用 LCEL 创建链
summarize_chain = (
    {"text": RunnablePassthrough()}
    | ChatPromptTemplate.from_template("请总结以下内容：\n{text}")
    | llm
    | StrOutputParser()
)

# 组合多个链
complex_chain = (
    {"input": RunnablePassthrough()}
    | summarize_chain
    | translate_chain
    | format_chain
)
```

**验收标准**:
- Chain 可以正常执行
- LCEL 组合正确
- 性能良好

---

## ✅ 阶段 4: 测试与文档（3 天）

### Task 4.1: 端到端测试
**优先级**: P0  
**预计时间**: 8 小时

**子任务**:
- [ ] 4.1.1 编写简单对话测试
- [ ] 4.1.2 编写复杂任务测试
- [ ] 4.1.3 编写工作流测试
- [ ] 4.1.4 编写记忆系统测试
- [ ] 4.1.5 生成测试报告

**测试场景**:
```python
# 场景 1: 简单对话 + 记忆
async def test_simple_conversation():
    butler = Butler(llm, tools, vector_store)
    
    # 第一轮对话
    response1 = await butler.process("我叫小明", user_id="123")
    assert "小明" in response1
    
    # 第二轮对话（测试记忆）
    response2 = await butler.process("我叫什么名字？", user_id="123")
    assert "小明" in response2

# 场景 2: 复杂任务 + 工具调用
async def test_complex_task():
    response = await butler.process(
        "查北京天气，如果下雨就发邮件",
        user_id="123"
    )
    # 验证调用了 get_weather 和 send_email
    assert "天气" in response
    assert "邮件" in response
```

**验收标准**:
- 所有测试通过
- 代码覆盖率 > 80%
- 性能指标达标

---

### Task 4.2: 文档完善
**优先级**: P0  
**预计时间**: 6 小时

**子任务**:
- [ ] 4.2.1 编写 LangChain 使用指南
- [ ] 4.2.2 编写插件开发指南
- [ ] 4.2.3 编写工作流开发指南
- [ ] 4.2.4 编写 LangSmith 使用指南
- [ ] 4.2.5 编写故障排查指南

---

### Task 4.3: 部署与优化
**优先级**: P0  
**预计时间**: 4 小时

**子任务**:
- [ ] 4.3.1 创建部署脚本
- [ ] 4.3.2 优化 LangChain 性能
- [ ] 4.3.3 配置生产环境
- [ ] 4.3.4 监控告警配置

---

## 📊 任务统计

### 按阶段
- **阶段 1**: 4 个任务，22 小时（LangChain 基础）
- **阶段 2**: 4 个任务，24 小时（插件系统）
- **阶段 3**: 3 个任务，20 小时（高级功能）
- **阶段 4**: 3 个任务，18 小时（测试文档）

**总计**: 14 个任务，84 小时（约 10 个工作日）

### 关键路径
```
Task 1.1 → Task 1.2 → Task 1.3 → Task 2.1 → Task 2.2 → Task 3.1 → Task 4.1
```

---

## 🎯 成功标准

### 技术指标
- ✅ 完全基于 LangChain 生态
- ✅ Agent 推理准确率 > 90%
- ✅ 工具调用成功率 > 95%
- ✅ 记忆检索准确率 > 85%
- ✅ LangSmith 追踪覆盖率 100%

### 功能指标
- ✅ 支持复杂多步骤任务
- ✅ 长期记忆可用
- ✅ 工作流可执行
- ✅ 完整的可观测性

---

## 📚 LangChain 学习资源

- [LangChain 官方文档](https://python.langchain.com/)
- [LangChain Cookbook](https://github.com/langchain-ai/langchain/tree/master/cookbook)
- [LangGraph 教程](https://langchain-ai.github.io/langgraph/tutorials/)
- [LangSmith 文档](https://docs.smith.langchain.com/)

---

## 📝 更新日志

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2025-01-18 | 3.0 | 深度 LangChain 任务清单 | Kiro |
