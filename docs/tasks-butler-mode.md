# zhinai-bot-v3 实现任务清单（管家模式）

## 📋 核心理念

**只实现管家框架，具体功能用插件（优先使用 NoneBot 插件商店）**

---

## 🎯 阶段 1: 管家框架（核心）

### Task 1.1: 项目初始化
**优先级**: P0  
**预计时间**: 2 小时

**子任务**:
- [ ] 1.1.1 创建 `pyproject.toml` - Poetry 配置
- [ ] 1.1.2 创建 `.env.example` - 环境变量模板
- [ ] 1.1.3 创建 `config/settings.py` - 配置管理
- [ ] 1.1.4 创建 `config/plugins.yaml` - 插件配置模板

**验收标准**:
- `poetry install` 成功
- 配置文件可以加载

**依赖**:
```toml
[tool.poetry.dependencies]
python = "^3.10"
nonebot2 = "^2.3.3"
langchain = "^1.1.0"
langgraph = "^1.0.0"
langsmith = "^0.2.0"
pydantic = "^2.0.0"
pyyaml = "^6.0"
```

---

### Task 1.2: 插件基础设施
**优先级**: P0  
**预计时间**: 6 小时

**子任务**:
- [ ] 1.2.1 创建 `plugins/base_plugin.py` - 插件基类
- [ ] 1.2.2 创建 `core/plugin_manager.py` - 插件管理器
- [ ] 1.2.3 创建 `models/plugin_models.py` - 插件数据模型
- [ ] 1.2.4 实现插件自动发现（扫描 plugins/ 目录）
- [ ] 1.2.5 实现插件生命周期管理（加载/卸载）
- [ ] 1.2.6 创建 `tests/test_plugin_system.py` - 测试

**验收标准**:
- 插件可以自动发现和注册
- 插件可以提供工具列表
- 插件可以加载和卸载
- 单元测试通过

**核心代码**:
```python
# plugins/base_plugin.py
from abc import ABC, abstractmethod
from langchain.tools import BaseTool

class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        pass
```

---

### Task 1.3: 管家中枢
**优先级**: P0  
**预计时间**: 8 小时

**子任务**:
- [ ] 1.3.1 创建 `core/butler.py` - 管家主类
- [ ] 1.3.2 创建 `core/react_agent.py` - ReAct 推理引擎
- [ ] 1.3.3 实现意图分析
- [ ] 1.3.4 实现任务规划
- [ ] 1.3.5 实现插件调度
- [ ] 1.3.6 实现结果整合
- [ ] 1.3.7 创建 `tests/test_butler.py` - 测试

**验收标准**:
- 管家可以理解用户意图
- 管家可以规划多步骤任务
- 管家可以调度插件执行
- 管家可以整合结果并回复

**核心代码**:
```python
# core/butler.py
class Butler:
    def __init__(self, llm, plugin_manager):
        self.llm = llm
        self.plugin_manager = plugin_manager
        self.react_agent = ReActAgent(llm)
    
    async def process(self, user_input: str) -> str:
        # 1. 分析意图
        intent = await self._analyze_intent(user_input)
        # 2. 规划任务
        plan = await self._create_plan(intent)
        # 3. 调度插件
        results = await self._execute_plan(plan)
        # 4. 整合结果
        response = await self._synthesize_response(results)
        return response
```

---

### Task 1.4: NoneBot 集成
**优先级**: P0  
**预计时间**: 4 小时

**子任务**:
- [ ] 1.4.1 创建 `bot.py` - NoneBot 入口
- [ ] 1.4.2 创建 `plugins/nonebot_chat.py` - 聊天插件
- [ ] 1.4.3 实现消息接收和发送
- [ ] 1.4.4 集成 Butler
- [ ] 1.4.5 创建 `tests/test_nonebot_integration.py` - 测试

**验收标准**:
- 机器人可以接收 QQ 消息
- 消息正确路由到 Butler
- Butler 的回复可以发送到 QQ

---

## 🔌 阶段 2: 核心插件（伪代码）

### Task 2.1: 情感系统插件（伪代码）
**优先级**: P1  
**预计时间**: 4 小时

**子任务**:
- [ ] 2.1.1 创建 `plugins/emotion/plugin.py`
- [ ] 2.1.2 创建 `plugins/emotion/tools.py` - 工具定义
- [ ] 2.1.3 实现工具接口（伪代码）
- [ ] 2.1.4 创建 `tests/plugins/test_emotion.py`

**工具列表**:
- `GetEmotionTool` - 获取用户情感值
- `UpdateEmotionTool` - 更新情感值
- `GetEmotionHistoryTool` - 获取情感历史

**伪代码示例**:
```python
class GetEmotionTool(BaseTool):
    name = "get_emotion"
    description = "获取用户的情感值（好感度、亲密度等）"
    
    def _run(self, user_id: str) -> dict:
        # TODO: 实际实现（可能来自 NoneBot 插件）
        return {
            "affection": 80,
            "intimacy": 60,
            "mood": "happy"
        }
```

---

### Task 2.2: 角色扮演插件（伪代码）
**优先级**: P1  
**预计时间**: 3 小时

**子任务**:
- [ ] 2.2.1 创建 `plugins/roleplay/plugin.py`
- [ ] 2.2.2 创建 `plugins/roleplay/tools.py`
- [ ] 2.2.3 实现工具接口（伪代码）

**工具列表**:
- `GetRolePromptTool` - 获取角色 Prompt
- `UpdateRoleTool` - 更新角色设定
- `GetRoleStateTool` - 获取角色状态

---

### Task 2.3: 记忆系统插件（伪代码）
**优先级**: P1  
**预计时间**: 4 小时

**子任务**:
- [ ] 2.3.1 创建 `plugins/memory/plugin.py`
- [ ] 2.3.2 创建 `plugins/memory/tools.py`
- [ ] 2.3.3 实现工具接口（伪代码）

**工具列表**:
- `SaveMemoryTool` - 保存记忆
- `SearchMemoryTool` - 搜索记忆
- `GetContextTool` - 获取对话上下文

---

## 🔄 阶段 3: NoneBot 插件适配器

### Task 3.1: 插件适配器框架
**优先级**: P0  
**预计时间**: 8 小时

**子任务**:
- [ ] 3.1.1 创建 `adapters/nonebot_adapter.py`
- [ ] 3.1.2 实现插件扫描（扫描已安装的 NoneBot 插件）
- [ ] 3.1.3 实现指令式插件转换（@on_command → Tool）
- [ ] 3.1.4 实现事件监听器转换（@on_message → Tool）
- [ ] 3.1.5 实现参数映射（NoneBot Args → Tool Schema）
- [ ] 3.1.6 创建 `tests/test_nonebot_adapter.py`

**验收标准**:
- 可以自动发现已安装的 NoneBot 插件
- 可以将插件转换为 v3 Plugin
- 转换后的插件可以被 Butler 调用

**核心代码**:
```python
# adapters/nonebot_adapter.py
class NoneBotPluginAdapter:
    def scan_plugins(self) -> list[str]:
        """扫描已安装的 NoneBot 插件"""
        pass
    
    def convert_plugin(self, plugin_name: str) -> Plugin:
        """将 NoneBot 插件转换为 v3 Plugin"""
        pass
    
    def convert_command_to_tool(self, command) -> BaseTool:
        """将 @on_command 转换为 Tool"""
        pass
```

---

### Task 3.2: 常见插件适配测试
**优先级**: P1  
**预计时间**: 6 小时

**子任务**:
- [ ] 3.2.1 测试邮件插件适配（nonebot-plugin-email）
- [ ] 3.2.2 测试天气插件适配（nonebot-plugin-weather）
- [ ] 3.2.3 测试定时任务插件适配（nonebot-plugin-apscheduler）
- [ ] 3.2.4 测试搜索插件适配
- [ ] 3.2.5 编写适配指南文档

**验收标准**:
- 至少 3 个 NoneBot 插件成功适配
- 适配后的插件功能正常
- 有清晰的适配文档

---

## 🚀 阶段 4: 测试与文档

### Task 4.1: 端到端测试
**优先级**: P0  
**预计时间**: 6 小时

**子任务**:
- [ ] 4.1.1 编写简单对话测试
- [ ] 4.1.2 编写复杂任务测试（多步骤）
- [ ] 4.1.3 编写插件调用测试
- [ ] 4.1.4 编写错误处理测试
- [ ] 4.1.5 生成测试报告

**测试场景**:
```python
# 场景 1: 简单对话
用户: "你好"
预期: 调用 RolePlayPlugin + EmotionPlugin，生成符合角色的回复

# 场景 2: 复杂任务
用户: "查北京天气，如果下雨就发邮件提醒我"
预期: 调用 WeatherPlugin → 判断 → 调用 EmailPlugin

# 场景 3: 插件故障
模拟: WeatherPlugin 调用失败
预期: Butler 优雅降级，提示用户
```

---

### Task 4.2: 文档完善
**优先级**: P0  
**预计时间**: 4 小时

**子任务**:
- [ ] 4.2.1 编写插件开发指南
- [ ] 4.2.2 编写 NoneBot 插件集成指南
- [ ] 4.2.3 编写 Butler 使用指南
- [ ] 4.2.4 编写故障排查指南

---

### Task 4.3: 部署脚本
**优先级**: P0  
**预计时间**: 2 小时

**子任务**:
- [ ] 4.3.1 创建 `scripts/deploy.sh`
- [ ] 4.3.2 创建 `scripts/start.sh`
- [ ] 4.3.3 创建 `scripts/install_plugin.sh` - 安装 NoneBot 插件

---

## 📊 任务统计

### 按阶段
- **阶段 1**: 4 个任务，20 小时（管家框架）
- **阶段 2**: 3 个任务，11 小时（核心插件伪代码）
- **阶段 3**: 2 个任务，14 小时（插件适配器）
- **阶段 4**: 3 个任务，12 小时（测试与文档）

**总计**: 12 个任务，57 小时（约 7 个工作日）

### 关键路径
```
Task 1.1 → Task 1.2 → Task 1.3 → Task 1.4 → Task 3.1 → Task 4.1
```

---

## 🎯 成功标准

### 核心指标
- ✅ 管家框架完整实现（< 500 行核心代码）
- ✅ 插件系统可用（可以加载和调用插件）
- ✅ NoneBot 插件适配器可用（至少 3 个插件成功适配）
- ✅ 端到端测试通过

### 架构指标
- ✅ 插件完全解耦
- ✅ 新插件集成 < 5 分钟
- ✅ 代码覆盖率 > 70%

---

## 📝 开发原则

### 1. 管家只做调度
- ❌ 不实现具体功能
- ✅ 只负责理解、规划、调度、整合

### 2. 优先使用现有插件
- ✅ 先找 NoneBot 插件商店
- ✅ 再找 MCP 工具
- ⚠️ 最后才自己实现

### 3. 伪代码优先
- ✅ 先定义接口（伪代码）
- ✅ 后续用真实插件替换
- ✅ 保持接口不变

### 4. 测试驱动
- ✅ 先写测试
- ✅ 再写实现
- ✅ 持续集成

---

## 🔗 相关文档

- [架构设计-管家模式](./架构设计-管家模式.md)
- [技术调研](./技术调研-LangChain-2025.md)
- [需求文档](./requirements.md)

---

## 📅 更新日志

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2025-01-18 | 2.0 | 重构为管家模式任务 | Kiro |
