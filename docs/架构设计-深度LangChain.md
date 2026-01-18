# zhinai-bot-v3 架构设计 - 深度 LangChain 版

## 🎯 核心理念

**v3 = 智能管家中枢（LangChain Agent）+ 插件生态（LangChain Tools）**

深度使用 LangChain 生态系统：
- 🧠 **Agent**: LangChain ReAct/OpenAI Functions Agent
- 🔧 **Tools**: LangChain BaseTool 标准
- 💾 **Memory**: LangChain Memory 系统
- 🗄️ **VectorStore**: LangChain VectorStore（Chroma/FAISS）
- 🔄 **Chains**: LangChain LCEL（LangChain Expression Language）
- 📊 **Callbacks**: LangChain Callbacks（LangSmith 集成）
- 🌊 **Workflows**: LangGraph（复杂工作流）

---

## 🏗️ 深度 LangChain 架构

```
┌─────────────────────────────────────────────────────┐
│                    用户消息                          │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              Butler（管家中枢）                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  LangChain Agent (ReAct/OpenAI Functions)    │  │
│  │  - AgentExecutor                             │  │
│  │  - Memory (ConversationBufferMemory)         │  │
│  │  - Callbacks (LangSmith)                     │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│           PluginManager（插件管理器）                │
│  - 管理所有 LangChain Tools                         │
│  - 工具注册与发现                                    │
│  - 工具调用路由                                      │
└──────────────────┬──────────────────────────────────┘
                   │
       ┌───────────┴───────────┬───────────┬──────────┐
       ▼                       ▼           ▼          ▼
   ┌────────┐            ┌─────────┐  ┌──────┐   ┌────┐
   │ 情感   │            │ 记忆    │  │ 邮件 │   │天气│
   │ 插件   │            │ 插件    │  │ 插件 │   │插件│
   └────────┘            └─────────┘  └──────┘   └────┘
   LangChain             LangChain    NoneBot    NoneBot
   Tools                 VectorStore  Plugin     Plugin
```

---

## 🤖 核心组件（深度 LangChain）

### 1. Butler（管家中枢）- 基于 LangChain Agent

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from langchain.callbacks import LangChainTracer

class Butler:
    """智能管家 - 基于 LangChain Agent"""
    
    def __init__(self, llm, plugin_manager, vector_store):
        # 1. Memory（记忆系统）
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # 2. Tools（从插件获取）
        self.tools = plugin_manager.get_all_tools()
        
        # 3. Prompt（角色人设）
        self.prompt = self._create_prompt()
        
        # 4. Agent（ReAct 推理）
        self.agent = create_react_agent(
            llm=llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # 5. AgentExecutor（执行器）
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=10,
            callbacks=[LangChainTracer()]  # LangSmith 追踪
        )
        
        # 6. VectorStore（长期记忆）
        self.vector_store = vector_store
    
    async def process(self, user_input: str, user_id: str) -> str:
        """处理用户输入"""
        # 1. 检索长期记忆
        relevant_memories = await self._retrieve_memories(user_input, user_id)
        
        # 2. 增强输入（添加记忆上下文）
        enhanced_input = self._enhance_input(user_input, relevant_memories)
        
        # 3. Agent 执行
        result = await self.executor.ainvoke({
            "input": enhanced_input,
            "user_id": user_id
        })
        
        # 4. 保存到长期记忆
        await self._save_to_memory(user_input, result["output"], user_id)
        
        return result["output"]
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """创建 Agent Prompt"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是智乃，一个可爱的兔耳少女。
            
你有以下工具可以使用：
{tools}

工具名称：{tool_names}

使用以下格式回答：

Question: 用户的问题
Thought: 你应该思考要做什么
Action: 要使用的工具，应该是 [{tool_names}] 中的一个
Action Input: 工具的输入
Observation: 工具的输出
... (这个 Thought/Action/Action Input/Observation 可以重复 N 次)
Thought: 我现在知道最终答案了
Final Answer: 给用户的最终回复

开始！

之前的对话历史：
{chat_history}

Question: {input}
{agent_scratchpad}"""),
        ])
    
    async def _retrieve_memories(self, query: str, user_id: str) -> list:
        """从向量数据库检索相关记忆"""
        results = await self.vector_store.asimilarity_search(
            query,
            filter={"user_id": user_id},
            k=3
        )
        return results
    
    async def _save_to_memory(self, input: str, output: str, user_id: str):
        """保存到长期记忆"""
        await self.vector_store.aadd_texts(
            texts=[f"用户: {input}\n智乃: {output}"],
            metadatas=[{"user_id": user_id, "timestamp": time.time()}]
        )
```

---

### 2. 插件系统 - 基于 LangChain Tools

#### 插件基类
```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class Plugin(ABC):
    """插件基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """返回 LangChain Tools"""
        pass
```

#### 情感系统插件（使用 LangChain Tool）
```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class GetEmotionInput(BaseModel):
    """获取情感值的输入"""
    user_id: str = Field(description="用户ID")

class GetEmotionTool(BaseTool):
    name = "get_emotion"
    description = "获取用户的情感值（好感度、亲密度、心情等）"
    args_schema = GetEmotionInput
    
    def _run(self, user_id: str) -> dict:
        # 从数据库获取情感值
        emotion_data = db.get_emotion(user_id)
        return {
            "affection": emotion_data.affection,
            "intimacy": emotion_data.intimacy,
            "mood": emotion_data.mood
        }
    
    async def _arun(self, user_id: str) -> dict:
        return self._run(user_id)

class UpdateEmotionInput(BaseModel):
    user_id: str = Field(description="用户ID")
    delta: int = Field(description="情感值变化量，正数增加，负数减少")

class UpdateEmotionTool(BaseTool):
    name = "update_emotion"
    description = "更新用户的情感值，用于互动后调整好感度"
    args_schema = UpdateEmotionInput
    
    def _run(self, user_id: str, delta: int) -> str:
        db.update_emotion(user_id, delta)
        return f"已更新用户 {user_id} 的情感值 {delta:+d}"
    
    async def _arun(self, user_id: str, delta: int) -> str:
        return self._run(user_id, delta)

class EmotionPlugin(Plugin):
    name = "emotion"
    
    def get_tools(self) -> list[BaseTool]:
        return [
            GetEmotionTool(),
            UpdateEmotionTool(),
            # ... 更多工具
        ]
```

---

### 3. 记忆系统 - 深度使用 LangChain Memory

```python
from langchain.memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    VectorStoreRetrieverMemory
)
from langchain.vectorstores import Chroma
from langchain.embeddings import DashScopeEmbeddings

class MemoryPlugin(Plugin):
    """记忆系统插件 - 基于 LangChain Memory"""
    
    def __init__(self):
        # 1. 短期记忆（对话缓冲）
        self.buffer_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=2000
        )
        
        # 2. 摘要记忆（自动总结）
        self.summary_memory = ConversationSummaryMemory(
            llm=llm,
            memory_key="summary"
        )
        
        # 3. 向量记忆（语义检索）
        embeddings = DashScopeEmbeddings()
        vectorstore = Chroma(
            collection_name="chat_history",
            embedding_function=embeddings,
            persist_directory="./data/chroma"
        )
        self.vector_memory = VectorStoreRetrieverMemory(
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3})
        )
    
    def get_tools(self) -> list[BaseTool]:
        return [
            SaveMemoryTool(self.buffer_memory, self.vector_memory),
            SearchMemoryTool(self.vector_memory),
            GetContextTool(self.buffer_memory),
            SummarizeMemoryTool(self.summary_memory)
        ]
```

---

### 4. 工作流系统 - 使用 LangGraph

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage

class WorkflowState(TypedDict):
    """工作流状态"""
    messages: Annotated[list[BaseMessage], "对话消息"]
    user_id: str
    current_step: str
    results: dict

class WorkflowPlugin(Plugin):
    """工作流插件 - 基于 LangGraph"""
    
    def __init__(self, butler: Butler):
        self.butler = butler
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """创建工作流图"""
        workflow = StateGraph(WorkflowState)
        
        # 定义节点
        workflow.add_node("analyze", self._analyze_intent)
        workflow.add_node("plan", self._create_plan)
        workflow.add_node("execute", self._execute_plan)
        workflow.add_node("synthesize", self._synthesize_result)
        
        # 定义边
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "plan")
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    async def _analyze_intent(self, state: WorkflowState) -> WorkflowState:
        """分析意图"""
        # 使用 LLM 分析用户意图
        pass
    
    async def _create_plan(self, state: WorkflowState) -> WorkflowState:
        """创建执行计划"""
        # 使用 LLM 规划任务步骤
        pass
    
    async def _execute_plan(self, state: WorkflowState) -> WorkflowState:
        """执行计划"""
        # 调用 Butler 执行各个步骤
        pass
    
    async def _synthesize_result(self, state: WorkflowState) -> WorkflowState:
        """整合结果"""
        # 使用 LLM 整合结果
        pass
    
    def get_tools(self) -> list[BaseTool]:
        return [
            CreateWorkflowTool(self.graph),
            ExecuteWorkflowTool(self.graph)
        ]
```

---

### 5. NoneBot 插件适配器 - 转换为 LangChain Tools

```python
from langchain.tools import StructuredTool
import inspect

class NoneBotPluginAdapter:
    """将 NoneBot 插件转换为 LangChain Tools"""
    
    def convert_command_to_tool(self, command_handler) -> BaseTool:
        """将 NoneBot @on_command 转换为 LangChain Tool"""
        
        # 1. 提取函数签名
        sig = inspect.signature(command_handler)
        
        # 2. 创建 Pydantic Schema
        args_schema = self._create_schema_from_signature(sig)
        
        # 3. 创建 LangChain Tool
        tool = StructuredTool(
            name=command_handler.__name__,
            description=command_handler.__doc__ or "NoneBot 插件",
            func=command_handler,
            args_schema=args_schema
        )
        
        return tool
    
    def _create_schema_from_signature(self, sig) -> BaseModel:
        """从函数签名创建 Pydantic Schema"""
        fields = {}
        for param_name, param in sig.parameters.items():
            fields[param_name] = (
                param.annotation,
                Field(description=f"参数 {param_name}")
            )
        
        return create_model("DynamicSchema", **fields)
```

---

## 📦 深度 LangChain 技术栈

### 核心依赖
```toml
[tool.poetry.dependencies]
python = "^3.10"

# NoneBot
nonebot2 = "^2.3.3"

# LangChain 核心
langchain = "^0.1.0"
langchain-core = "^0.1.0"
langchain-community = "^0.0.20"

# LangChain 集成
langchain-openai = "^0.0.5"        # OpenAI 集成
langchain-dashscope = "^0.0.1"     # 通义千问集成

# LangGraph（工作流）
langgraph = "^0.0.20"

# LangSmith（可观测性）
langsmith = "^0.0.77"

# 向量数据库
chromadb = "^0.4.22"               # Chroma
faiss-cpu = "^1.7.4"               # FAISS

# Embeddings
sentence-transformers = "^2.2.2"   # 本地 Embeddings

# 其他
pydantic = "^2.0.0"
pyyaml = "^6.0"
```

---

## 🔄 完整工作流程示例

### 示例：复杂任务处理

```python
# 用户输入
user_input = "查北京明天天气，如果下雨就发邮件提醒我带伞"

# Butler 处理流程
butler = Butler(llm, plugin_manager, vector_store)
response = await butler.process(user_input, user_id="123")

# 内部执行流程（LangChain Agent）:
"""
Thought: 用户想查天气并根据结果发邮件，我需要先查天气
Action: get_weather
Action Input: {"city": "北京", "date": "明天"}
Observation: {"weather": "雨", "temp": "15-20°C"}

Thought: 天气是雨，需要发邮件提醒
Action: send_email
Action Input: {
    "to": "user@example.com",
    "subject": "明天记得带伞",
    "body": "北京明天有雨，温度15-20°C，记得带伞哦~"
}
Observation: 邮件发送成功

Thought: 任务完成，需要更新情感值（因为帮了用户）
Action: update_emotion
Action Input: {"user_id": "123", "delta": 5}
Observation: 已更新用户 123 的情感值 +5

Thought: 我现在知道最终答案了
Final Answer: 北京明天有雨，温度15-20°C，我已经发邮件提醒你带伞了~
"""
```

---

## 🎨 深度 LangChain 的优势

### 1. 开箱即用的功能
- ✅ Memory 系统（短期、长期、摘要）
- ✅ VectorStore 集成（Chroma、FAISS、Pinecone）
- ✅ Agent 推理（ReAct、OpenAI Functions）
- ✅ Callbacks（LangSmith 追踪）
- ✅ LCEL（链式调用）

### 2. 强大的生态系统
- ✅ 100+ LLM 集成
- ✅ 50+ VectorStore 集成
- ✅ 数百个预制 Tools
- ✅ 活跃的社区

### 3. 标准化
- ✅ 统一的接口（BaseTool、BaseMemory）
- ✅ 统一的数据格式（Messages、Documents）
- ✅ 统一的调用方式（LCEL）

### 4. 可观测性
- ✅ LangSmith 自动追踪
- ✅ 完整的调用链
- ✅ 性能分析
- ✅ 成本统计

---

## 📊 项目结构（深度 LangChain）

```
zhinai-bot-v3/
├── bot.py                          # NoneBot 入口
│
├── core/
│   ├── butler.py                   # 管家（LangChain Agent）⭐
│   ├── plugin_manager.py           # 插件管理器
│   └── langchain_config.py         # LangChain 配置
│
├── plugins/                        # 插件目录
│   ├── base_plugin.py              # 插件基类
│   ├── emotion/                    # 情感插件（LangChain Tools）
│   │   ├── plugin.py
│   │   └── tools.py                # BaseTool 实现
│   ├── memory/                     # 记忆插件（LangChain Memory）
│   │   ├── plugin.py
│   │   └── memory.py               # Memory 实现
│   ├── workflow/                   # 工作流插件（LangGraph）
│   │   ├── plugin.py
│   │   └── graphs.py               # StateGraph 定义
│   └── ...
│
├── adapters/
│   └── nonebot_adapter.py          # NoneBot → LangChain Tool
│
├── config/
│   ├── settings.py
│   ├── plugins.yaml
│   └── langchain.yaml              # LangChain 配置
│
├── data/
│   ├── chroma/                     # Chroma 向量数据库
│   └── bot.db                      # SQLite
│
└── tests/
    ├── test_butler.py
    ├── test_langchain_integration.py
    └── ...
```

---

## 🚀 实现优先级

### 阶段 1: LangChain 基础（3 天）
- [ ] 配置 LangChain（LLM、Embeddings）
- [ ] 实现 Butler（基于 AgentExecutor）
- [ ] 集成 Memory（ConversationBufferMemory）
- [ ] 集成 VectorStore（Chroma）

### 阶段 2: 插件系统（4 天）
- [ ] 实现插件基类（返回 BaseTool）
- [ ] 实现情感插件（LangChain Tools）
- [ ] 实现记忆插件（LangChain Memory）
- [ ] 实现 NoneBot 适配器

### 阶段 3: 高级功能（5 天）
- [ ] 集成 LangGraph（工作流）
- [ ] 集成 LangSmith（可观测性）
- [ ] 实现复杂工作流
- [ ] 性能优化

### 阶段 4: 测试与文档（3 天）
- [ ] 端到端测试
- [ ] 文档完善
- [ ] 部署脚本

**总计**: 15 天

---

## 🎯 成功标准

### 技术指标
- ✅ 完全基于 LangChain 生态
- ✅ Agent 推理准确率 > 90%
- ✅ 工具调用成功率 > 95%
- ✅ 记忆检索准确率 > 85%

### 功能指标
- ✅ 支持复杂多步骤任务
- ✅ 长期记忆可用
- ✅ 工作流可视化
- ✅ 完整的可观测性

---

## 📚 相关文档

- [LangChain 官方文档](https://python.langchain.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangSmith 文档](https://docs.smith.langchain.com/)

---

## 📝 更新日志

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2025-01-18 | 3.0 | 深度 LangChain 版本 | Kiro |
