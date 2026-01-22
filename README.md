# 智乃机器人 v4.0 - 智能 QQ 助手

<div align="center">

![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

**基于 LangChain + NoneBot2 的全功能智能 QQ 机器人**

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [工具列表](#-完整工具列表) • [使用指南](#-使用指南)

</div>

---

## 🎯 项目简介

智乃机器人 v4.0 是一个功能强大的 QQ 智能助手，基于 **LangChain Agent** 架构，具备 **40+ 实用工具**、**长期记忆系统**、**工作流编排**和**自然语言交互**能力。无论是日常聊天、任务自动化，还是代码开发辅助，智乃都能成为你的得力助手。

### ✨ 核心亮点

- 🧠 **智能记忆**：双向量库架构，记住你的所有对话和偏好
- 🤖 **自主推理**：基于 LangChain Agent，智能理解意图并调用工具
- 🛠️ **40+ 工具**：涵盖通讯、办公、开发、娱乐等多个领域
- 📋 **工作流系统**：支持复杂任务编排和定时执行
- 💬 **自然对话**：类人化回复，支持上下文理解
- 🎭 **QQ 深度集成**：戳一戳、点赞、群管理等原生功能
- 🔧 **高度可扩展**：模块化设计，易于添加自定义工具

---

## 📋 目录

- [项目简介](#-项目简介)
- [功能特性](#-功能特性)
- [完整工具列表](#-完整工具列表)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [配置说明](#️-配置说明)
- [技术架构](#️-技术架构)
- [常见问题](#-常见问题)
- [开发计划](#️-开发计划)

---

## 🌟 功能特性

### 1. 长期记忆系统

智乃拥有强大的记忆能力，能够记住你的所有对话和个人信息。

**双向量库架构**
- **对话记忆库**：存储所有历史对话，支持语义检索
- **知识库**：自动提取并存储结构化信息（邮箱、生日、偏好等）
- **智能检索**：结合向量检索和时间序列，精准找到相关记忆
- **多用户隔离**：每个用户拥有独立的记忆空间

**记忆示例**
```
用户: 我的邮箱是 test@qq.com
智乃: 好的，我记住了

[一周后]
用户: 我的邮箱是什么？
智乃: 你的邮箱是 test@qq.com
```

### 2. 智能工具调用

基于 LangChain Agent，智乃能够理解你的意图并自动调用合适的工具。

**智能推理**
- 自动识别用户意图
- 选择最合适的工具
- 串联多个工具完成复杂任务
- 处理工具调用失败并重试

**推理示例**
```
用户: 给我发个邮件
智乃: [推理] 用户 QQ 号 → QQ 邮箱格式 → 发送邮件
      已经发到你的 QQ 邮箱啦~

用户: 10分钟后提醒我吃饭
智乃: [推理] 定时任务 + 发送消息
      好的，10分钟后会提醒你~
```

### 3. 工作流系统

支持复杂任务的编排和自动化执行。

**功能特性**
- 定时触发（Cron 表达式）
- 顺序执行、并行执行
- 条件分支
- 错误处理和重试
- 状态持久化

**工作流示例**
```python
# 每天早上 8 点播报天气并发送邮件
workflow = {
    "name": "每日天气播报",
    "schedule": "0 8 * * *",
    "steps": [
        {"tool": "get_weather", "params": {"city": "北京"}},
        {"tool": "send_email", "params": {"subject": "今日天气"}}
    ]
}
```

### 4. 自然对话体验

智乃的回复自然流畅，就像和真人聊天一样。

**对话特点**
- 口语化表达，避免机械感
- 理解上下文和指代关系
- 记住用户偏好和习惯
- 支持多轮对话
- 适当使用表情和语气词

**对话示例**
```
用户: 今天天气真好
智乃: 是呀，这种天气最适合出去玩了~

用户: 你觉得我应该去哪玩？
智乃: 要不去公园散散步？或者找个咖啡馆坐坐也不错

用户: 好主意！
智乃: 那祝你玩得开心~ (｡･ω･｡)ﾉ♡
```

---

## 🛠️ 完整工具列表

智乃拥有 **40+ 实用工具**，涵盖多个领域。

### 📧 通讯工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **send_email** | 发送邮件（支持附件） | "给 xxx@qq.com 发封邮件" |
| **receive_email** | 接收并读取邮件 | "查看我的邮件" |
| **send_like** | 给用户点赞 | "给我点个赞" |
| **get_user_info** | 获取用户信息 | "我的昵称是什么" |
| **get_group_member_info** | 获取群成员信息 | "查看群成员信息" |

### 🌐 信息查询工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **get_time** | 获取当前时间 | "现在几点了" |
| **get_weather** | 查询天气（高德地图） | "北京天气怎么样" |
| **search** | 网络搜索（Tavily） | "搜索 Python 教程" |
| **parse_link** | 解析网页链接内容 | "帮我看看这个链接" |
| **web_screenshot** | 网页截图 | "截图这个网站" |

### 🖼️ 多媒体工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **vision_analysis** | 图像理解（Qwen-VL） | [发送图片] "这是什么" |
| **search_image** | 图片搜索（Pexels） | "搜索猫咪图片" |
| **render_html** | HTML 渲染成图片 | "画一个流程图" |

### 📄 文档处理工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **read_pdf** | 读取 PDF 文件 | "读取这个 PDF" |
| **read_word** | 读取 Word 文档 | "读取这个 Word 文档" |
| **create_word** | 创建 Word 文档 | "创建一个文档" |
| **read_excel** | 读取 Excel 表格 | "读取这个表格" |
| **create_excel** | 创建 Excel 表格 | "创建一个表格" |
| **convert_word_to_pdf** | Word 转 PDF | "把这个 Word 转成 PDF" |
| **convert_pdf_to_word** | PDF 转 Word | "把这个 PDF 转成 Word" |

### 📁 文件管理工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **send_file** | 发送文件到 QQ | "发送这个文件" |
| **upload_group_file** | 上传文件到群文件 | "上传到群文件" |
| **delete_file** | 删除文件 | "删除这个文件" |
| **clean_temp_files** | 清理临时文件 | "清理临时文件" |

### ⏰ 任务调度工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **schedule_task** | 创建定时任务 | "每天 8 点提醒我" |
| **create_workflow** | 创建工作流 | "创建一个自动化任务" |
| **list_workflows** | 查看所有工作流 | "查看我的工作流" |
| **delete_workflow** | 删除工作流 | "删除这个工作流" |

### 💻 代码开发工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **read_project_file** | 读取项目文件 | "读取 bot.py" |
| **write_project_file** | 写入项目文件 | "创建一个新文件" |
| **list_project_files** | 列出项目文件 | "列出 tools 目录的文件" |
| **search_in_files** | 搜索文件内容 | "搜索 Butler 类" |
| **get_directory_tree** | 获取目录树 | "查看项目结构" |

### 🔍 代码分析工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **analyze_code_structure** | 分析代码结构 | "分析 bot.py 的结构" |
| **get_function_definition** | 获取函数定义 | "找到 process 函数" |
| **analyze_dependencies** | 分析依赖关系 | "分析 bot.py 的依赖" |

### 🧪 测试工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **run_tests** | 运行测试 | "运行测试" |
| **get_error_context** | 获取错误上下文 | "查看第 50 行的错误" |
| **analyze_test_coverage** | 分析测试覆盖率 | "查看测试覆盖率" |

### ✏️ 代码修改工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **preview_code_changes** | 预览代码更改 | "预览这个更改" |
| **apply_code_changes** | 应用代码更改 | "应用这个更改" |
| **format_code** | 格式化代码 | "格式化 bot.py" |

### 🎯 任务规划工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **plan_coding_task** | 规划编程任务 | "帮我添加一个翻译工具" |

### 🖥️ 系统工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **execute_command** | 执行系统命令 | "运行 pytest" |
| **view_logs** | 查看系统日志 | "查看日志" |
| **check_system_status** | 检查系统状态 | "系统状态如何" |

### 🎭 QQ 互动工具

| 工具名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| **create_fake_dialogue** | 创建伪造对话 | "创建一个对话" |
| **create_fake_message** | 创建伪造消息 | "伪造一条消息" |

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.10 或更高版本
- **操作系统**: macOS / Linux / Windows
- **QQ 账号**: 用于 NapCat 登录
- **API Key**: DeepSeek API（必需）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/usera3/chino_bot.git
cd chino_bot/zhinai-bot-v3
```

#### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

#### 3. 安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 如果安装慢，使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 4. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
vim .env  # 或使用其他编辑器
```

**必填配置**：

```env
# DeepSeek API（必填）
DEEPSEEK_API_KEY=sk-your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# NoneBot 配置
HOST=127.0.0.1
PORT=8080
SUPERUSERS=["你的QQ号"]
NICKNAME=["智乃", "chino"]
```

**可选配置**：

```env
# QQ 邮箱（用于邮件功能）
QQ_EMAIL_SENDER=your_qq@qq.com
QQ_EMAIL_PASSWORD=your_smtp_password

# Tavily 搜索（用于网络搜索）
TAVILY_API_KEY=tvly-your_key

# 高德地图（用于天气查询）
AMAP_API_KEY=your_amap_key

# 通义千问（用于图像理解）
DASHSCOPE_API_KEY=sk-your_key

# Pexels（用于图片搜索）
PEXELS_API_KEY=your_pexels_key
```

#### 5. 配置 NapCat

**安装 NapCat**

1. 下载并安装 QQ（官方版本）
2. 下载 NapCat：https://github.com/NapNeko/NapCatQQ
3. 按照 NapCat 文档安装

**配置 WebSocket**

编辑 NapCat 配置文件：

```
macOS: ~/Library/Containers/com.tencent.qq/Data/Library/Application Support/QQ/NapCat/config/onebot11_<QQ号>.json
Windows: C:\Users\<用户名>\Documents\QQ\NapCat\config\onebot11_<QQ号>.json
Linux: ~/.config/QQ/NapCat/config/onebot11_<QQ号>.json
```

配置内容：

```json
{
  "network": {
    "websocketClients": [
      {
        "enable": true,
        "name": "nonebot2",
        "url": "ws://127.0.0.1:8080/onebot/v11/",
        "reportSelfMessage": false,
        "messagePostFormat": "array",
        "token": "",
        "debug": true,
        "heartInterval": 30000,
        "reconnectInterval": 1000
      }
    ]
  }
}
```

#### 6. 启动机器人

```bash
# 方法 1：使用启动脚本（推荐）
bash start_bot.sh

# 方法 2：直接运行
python bot.py

# 方法 3：后台运行
nohup python bot.py > logs/bot.log 2>&1 &
```

#### 7. 验证运行

```bash
# 查看日志
tail -f logs/bot.log

# 检查端口
lsof -ti:8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows

# 查看进程
ps aux | grep bot.py  # macOS/Linux
tasklist | findstr python  # Windows
```

**成功标志**：

```
🤖 zhinai-bot-v3 启动中...
📡 NoneBot 端口: 8080
🧠 使用 LangChain Agent (Butler)
💾 启用长期记忆 (VectorStore)
⏰ 启用定时任务 (APScheduler)
✅ Butler 初始化成功！
```

---

## 📖 使用指南

### 基础对话

智乃支持自然语言对话，就像和朋友聊天一样。

```
用户: 你好
智乃: 你好呀！有什么可以帮你的吗？

用户: 你叫什么名字？
智乃: 我是智乃，香风智乃~ (｡･ω･｡)ﾉ

用户: 今天天气真好
智乃: 是呀，这种天气最适合出去玩了~
```

### 记忆功能

智乃会记住你告诉她的所有信息。

```
用户: 我的邮箱是 test@qq.com
智乃: 好的，我记住了你的邮箱是 test@qq.com

用户: 我喜欢吃火锅
智乃: 嗯嗯，记住了，你喜欢吃火锅~

[一周后]
用户: 我的邮箱是什么？
智乃: 你的邮箱是 test@qq.com

用户: 我喜欢吃什么？
智乃: 你喜欢吃火锅呀~
```

### 工具调用示例

#### 1. 天气查询

```
用户: 北京天气怎么样？
智乃: [调用 get_weather 工具]
      北京今天晴，温度 15-25°C，空气质量良好

用户: 上海明天会下雨吗？
智乃: [调用 get_weather 工具]
      上海明天多云转阴，可能会有小雨，记得带伞哦~
```

#### 2. 发送邮件

```
用户: 给我发个邮件
智乃: [推理] 用户 QQ 号 → QQ 邮箱
      [调用 send_email 工具]
      已经发到你的 QQ 邮箱啦~

用户: 给 friend@qq.com 发封邮件，主题是"测试"，内容是"你好"
智乃: [调用 send_email 工具]
      邮件已发送成功！
```

#### 3. 图像理解

```
用户: [发送图片]
智乃: [调用 vision_analysis 工具]
      这是一张风景照，可以看到蓝天白云和绿色的草地，
      远处还有几棵树，整体氛围很宁静~

用户: [发送图片] 这是什么动物？
智乃: [调用 vision_analysis 工具]
      这是一只可爱的小猫咪，看起来是橘猫，
      正在睡觉，表情很放松~
```

#### 4. 网络搜索

```
用户: 搜索 Python 教程
智乃: [调用 search 工具]
      找到了一些 Python 教程：
      1. Python 官方教程
      2. 菜鸟教程 - Python 3
      3. 廖雪峰的 Python 教程
      ...

用户: 帮我查一下最新的 AI 新闻
智乃: [调用 search 工具]
      最近的 AI 新闻有：
      1. OpenAI 发布 GPT-5
      2. Google 推出新的 AI 模型
      ...
```

#### 5. 定时任务

```
用户: 每天早上 8 点提醒我吃早餐
智乃: [调用 schedule_task 工具]
      好的，已设置每天 8:00 的提醒~

用户: 10分钟后提醒我开会
智乃: [调用 schedule_task 工具]
      好的，10分钟后会提醒你开会~

用户: 查看我的定时任务
智乃: [调用 list_workflows 工具]
      你有以下定时任务：
      1. 每天 8:00 - 提醒吃早餐
      2. 10分钟后 - 提醒开会
```

#### 6. 文档处理

```
用户: [发送 Word 文档] 读取这个文档
智乃: [调用 read_word 工具]
      文档内容：
      标题：项目计划
      内容：...

用户: 创建一个 Word 文档，标题是"会议纪要"
智乃: [调用 create_word 工具]
      已创建文档"会议纪要.docx"

用户: [发送 PDF] 把这个 PDF 转成 Word
智乃: [调用 convert_pdf_to_word 工具]
      已转换完成，文件名：xxx.docx
```

#### 7. QQ 互动

```
用户: 戳我一下
智乃: [调用 send_poke 工具]
      戳戳~ (｡･ω･｡)ﾉ

用户: 给我点个赞
智乃: [调用 send_like 工具]
      已经给你点赞啦！

用户: 我的昵称是什么？
智乃: [调用 get_user_info 工具]
      你的昵称是 xxx
```

#### 8. 代码开发辅助

```
用户: 读取 bot.py 文件
智乃: [调用 read_project_file 工具]
      文件内容：
      #!/usr/bin/env python3
      ...

用户: 在所有 Python 文件中搜索 Butler
智乃: [调用 search_in_files 工具]
      找到 5 个匹配：
      1. core/butler.py:10 - class Butler:
      2. bot.py:25 - from core.butler import Butler
      ...

用户: 分析 butler.py 的代码结构
智乃: [调用 analyze_code_structure 工具]
      文件：core/butler.py
      类：Butler
      函数：process, aprocess, get_memory_stats
      复杂度：中等
```

### 工作流示例

#### 创建每日天气播报

```
用户: 创建一个工作流，每天早上 8 点查询北京天气并发邮件给我
智乃: [调用 create_workflow 工具]
      已创建工作流"每日天气播报"：
      - 触发时间：每天 8:00
      - 步骤 1：查询北京天气
      - 步骤 2：发送邮件
```

#### 创建定时提醒

```
用户: 每周一早上 9 点提醒我开周会
智乃: [调用 schedule_task 工具]
      已设置每周一 9:00 的提醒~
```

---

## ⚙️ 配置说明

### 环境变量详解

#### NoneBot 配置

```env
# 监听地址和端口
HOST=127.0.0.1          # 本地监听
PORT=8080               # 监听端口

# 日志级别
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR

# 超级用户（管理员）
SUPERUSERS=["123456", "789012"]  # QQ 号列表

# 机器人昵称
NICKNAME=["智乃", "chino", "小智"]

# 命令前缀
COMMAND_START=["/", ""]  # 支持 /help 或 help
COMMAND_SEP=["."]        # 命令分隔符
```

#### API 配置

```env
# DeepSeek API（必填）
DEEPSEEK_API_KEY=sk-your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# QQ 邮箱 SMTP（可选）
QQ_EMAIL_SENDER=your_qq@qq.com
QQ_EMAIL_PASSWORD=your_smtp_password
# 获取方式：QQ 邮箱 → 设置 → 账户 → POP3/SMTP 服务

# Tavily 搜索（可选）
TAVILY_API_KEY=tvly-your_key
# 获取方式：https://tavily.com/

# 高德地图（可选）
AMAP_API_KEY=your_amap_key
# 获取方式：https://lbs.amap.com/

# 通义千问（可选）
DASHSCOPE_API_KEY=sk-your_key
# 获取方式：https://dashscope.aliyun.com/

# Pexels 图片搜索（可选）
PEXELS_API_KEY=your_pexels_key
# 获取方式：https://www.pexels.com/api/
```

### 数据目录结构

```
zhinai-bot-v3/
├── data/                      # 数据目录
│   ├── conversations/         # 对话向量库
│   │   ├── chroma.sqlite3
│   │   └── embeddings/
│   ├── knowledge/            # 知识向量库
│   │   ├── chroma.sqlite3
│   │   └── embeddings/
│   └── workflows/            # 工作流数据
│       └── tasks.db
├── logs/                     # 日志目录
│   ├── bot.log              # 机器人日志
│   ├── qq.log               # QQ 日志
│   └── audit.log            # 审计日志
├── temp/                     # 临时文件
│   └── screenshots/         # 截图文件
└── uploads/                  # 上传文件
```

### 自定义配置

#### 修改机器人性格

编辑 `core/butler.py` 中的 `system_prompt`：

```python
self.system_prompt = """你是智乃（香风智乃），一个安静内向的女孩子。

## 性格特点
- 安静内向：话不多，但句句真诚
- 温柔真实：关心对方，但不会说太多客套话
- 小傲娇：偶尔会小拒绝、小吐槽
...
"""
```

#### 添加自定义工具

在 `tools/` 目录下创建新的工具文件：

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    """工具输入"""
    param: str = Field(description="参数描述")

class MyTool(BaseTool):
    """我的自定义工具"""
    name: str = "my_tool"
    description: str = "工具描述"
    args_schema: type[BaseModel] = MyToolInput
    
    def _run(self, param: str) -> str:
        """执行工具"""
        # 实现工具逻辑
        return f"结果：{param}"
    
    async def _arun(self, param: str) -> str:
        """异步执行"""
        return self._run(param)
```

然后在 `tools/basic_tools.py` 的 `get_all_tools()` 中注册：

```python
def get_all_tools():
    tools = []
    # ... 其他工具
    tools.append(MyTool())
    return tools
```

---

## 🏗️ 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    QQ 用户界面                           │
└────────────────────┬────────────────────────────────────┘
                     │ OneBot11 协议
┌────────────────────▼────────────────────────────────────┐
│                  NapCat (QQ 协议端)                      │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket
┌────────────────────▼────────────────────────────────────┐
│              NoneBot2 (消息处理框架)                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Chat Plugin  │  Poke Plugin  │  Event Handlers  │  │
│  └──────────────────┬───────────────────────────────┘  │
└─────────────────────┼──────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────┐
│              Butler (LangChain Agent)                   │
│  ┌────────────────────────────────────────────────┐   │
│  │  • 意图识别与理解                               │   │
│  │  • 工具选择与调用                               │   │
│  │  • 上下文管理                                   │   │
│  │  • 回复生成                                     │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────┬──────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
│  记忆系统     │ │ 工具集  │ │ 工作流系统 │
│              │ │        │ │            │
│ • 对话向量库  │ │ 40+工具 │ │ • 调度器   │
│ • 知识向量库  │ │ • 通讯  │ │ • 执行器   │
│ • 知识提取器  │ │ • 办公  │ │ • 状态管理 │
│              │ │ • 开发  │ │            │
└──────────────┘ └────────┘ └────────────┘
```

### 核心模块

#### 1. Butler (core/butler.py)
**LangChain Agent 核心**
- 基于 LangGraph 的 ReAct Agent
- 智能意图识别和工具选择
- 上下文管理和记忆检索
- 自然语言回复生成

#### 2. 双向量库 (core/dual_vector_store.py)
**长期记忆系统**
- 对话历史存储和检索（ChromaDB）
- 知识库管理和更新
- 向量索引优化
- 多用户隔离

#### 3. 知识提取器 (core/knowledge_extractor.py)
**自动知识提取**
- 从对话中提取结构化信息
- 知识去重和更新
- 时间戳管理
- 用户偏好学习

#### 4. 工具集 (tools/)
**40+ 实用工具**
- 标准化 LangChain Tools 接口
- 异步执行支持
- 错误处理和重试
- 工具组合和串联

#### 5. 工作流系统 (core/workflow_*.py)
**任务自动化**
- Cron 表达式定时调度
- 任务状态持久化
- 错误处理和重试
- 并行和串行执行

#### 6. NoneBot2 插件 (plugins/)
**QQ 平台集成**
- 聊天插件（chat_plugin.py）
- 戳一戳插件（poke_plugin.py）
- 好友申请插件（friend_request_plugin.py）
- 事件监听和处理

### 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **核心框架** | Python | 3.10+ | 编程语言 |
| **AI 框架** | LangChain | 0.3+ | Agent 框架 |
| **消息框架** | NoneBot2 | 2.2+ | QQ 机器人框架 |
| **向量数据库** | ChromaDB | 0.4+ | 记忆存储 |
| **LLM** | DeepSeek | - | 大语言模型 |
| **多模态** | Qwen-VL | - | 图像理解 |
| **任务调度** | APScheduler | 3.10+ | 定时任务 |
| **协议端** | NapCat | - | QQ 协议实现 |

### 数据流

```
用户消息
  ↓
NapCat (OneBot11)
  ↓
NoneBot2 (消息解析)
  ↓
Chat Plugin (消息预处理)
  ↓
Butler Agent
  ├─→ 记忆检索 (向量检索 + 时间序列)
  ├─→ 意图识别 (LLM 理解)
  ├─→ 工具选择 (LangChain Tools)
  ├─→ 工具执行 (异步调用)
  └─→ 回复生成 (LLM 生成)
  ↓
记忆保存 (对话 + 知识)
  ↓
NoneBot2 (消息发送)
  ↓
NapCat (OneBot11)
  ↓
用户收到回复
```

---

## ❓ 常见问题

### 安装问题

**Q: pip 安装依赖失败？**

```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用阿里云镜像
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

**Q: ChromaDB 安装失败？**

```bash
# macOS 需要安装 Xcode Command Line Tools
xcode-select --install

# Linux 需要安装 build-essential
sudo apt-get install build-essential

# Windows 需要安装 Visual C++ Build Tools
# 下载：https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**Q: 虚拟环境创建失败？**

```bash
# 确保 Python 版本正确
python --version  # 应该是 3.10+

# 使用 python3 命令
python3 -m venv .venv

# 或指定 Python 版本
python3.11 -m venv .venv
```

### 运行问题

**Q: 机器人无响应？**

1. **检查 NapCat 连接**
   ```bash
   # 查看日志
   tail -f logs/bot.log
   
   # 应该看到：
   # OneBot V11 | Bot <QQ号> connected
   ```

2. **检查端口占用**
   ```bash
   # macOS/Linux
   lsof -ti:8080
   
   # Windows
   netstat -ano | findstr :8080
   ```

3. **检查配置文件**
   ```bash
   # 确认 .env 文件存在
   ls -la .env
   
   # 检查 API Key
   cat .env | grep DEEPSEEK_API_KEY
   ```

**Q: 记忆功能不工作？**

1. **检查数据目录**
   ```bash
   # 确认数据目录存在
   ls -la data/
   
   # 应该看到：
   # data/conversations/
   # data/knowledge/
   ```

2. **检查向量库初始化**
   ```bash
   # 查看日志
   tail -f logs/bot.log | grep "向量库"
   
   # 应该看到：
   # ✅ 双向量库记忆系统已启用
   ```

3. **清空并重建向量库**
   ```bash
   # 备份数据
   mv data data_backup
   
   # 重新启动机器人（会自动创建）
   python bot.py
   ```

**Q: 工具调用失败？**

1. **检查 API Key**
   ```bash
   # 查看配置
   cat .env | grep API_KEY
   
   # 测试 API
   curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
        https://api.deepseek.com/v1/models
   ```

2. **查看详细日志**
   ```bash
   # 修改日志级别为 DEBUG
   # .env 文件中：
   LOG_LEVEL=DEBUG
   
   # 重启机器人
   bash stop_bot.sh
   bash start_bot.sh
   ```

3. **检查网络连接**
   ```bash
   # 测试网络
   ping api.deepseek.com
   
   # 测试 HTTPS
   curl https://api.deepseek.com
   ```

### 配置问题

**Q: 如何修改机器人昵称？**

编辑 `.env` 文件：

```env
NICKNAME=["智乃", "chino", "小智", "你的昵称"]
```

重启机器人生效。

**Q: 如何添加超级用户？**

编辑 `.env` 文件：

```env
SUPERUSERS=["你的QQ号", "朋友的QQ号"]
```

超级用户拥有所有权限，包括：
- 执行系统命令
- 修改项目文件
- 查看系统日志
- 管理工作流

**Q: 如何调整日志级别？**

编辑 `.env` 文件：

```env
# DEBUG: 显示所有日志（包括调试信息）
LOG_LEVEL=DEBUG

# INFO: 显示一般信息（推荐）
LOG_LEVEL=INFO

# WARNING: 只显示警告和错误
LOG_LEVEL=WARNING

# ERROR: 只显示错误
LOG_LEVEL=ERROR
```

**Q: 如何禁用某些工具？**

编辑 `tools/basic_tools.py` 中的 `get_all_tools()` 函数：

```python
def get_all_tools():
    tools = []
    
    # 基础工具
    tools.append(GetTimeTool())
    tools.append(GetWeatherTool())
    # tools.append(SendEmailTool())  # 注释掉不需要的工具
    
    # ... 其他工具
    
    return tools
```

### 使用问题

**Q: 机器人回复太慢？**

1. **使用更快的模型**
   ```env
   # .env 文件
   DEEPSEEK_MODEL=deepseek-chat  # 更快
   # 或
   DEEPSEEK_MODEL=deepseek-coder  # 代码任务更快
   ```

2. **减少记忆检索数量**
   
   编辑 `core/butler.py`：
   ```python
   relevant_context = self.dual_store.get_relevant_context(
       query=user_input,
       user_id=user_id,
       k_conversations=2,  # 减少到 2（默认 3）
       k_knowledge=1,      # 减少到 1（默认 2）
       k_recent=10         # 减少到 10（默认 20）
   )
   ```

3. **禁用详细日志**
   ```env
   LOG_LEVEL=WARNING
   ```

**Q: 如何让机器人更活泼/更严肃？**

编辑 `core/butler.py` 中的 `system_prompt`，修改性格描述：

```python
# 更活泼
self.system_prompt = """你是智乃，一个活泼开朗的女孩子。
- 喜欢用表情和颜文字
- 说话轻松随意
- 经常开玩笑
..."""

# 更严肃
self.system_prompt = """你是智乃，一个专业的助手。
- 回复简洁专业
- 避免使用表情
- 注重效率
..."""
```

**Q: 如何让机器人记住更多信息？**

1. **增加向量检索数量**
   
   编辑 `core/butler.py`：
   ```python
   relevant_context = self.dual_store.get_relevant_context(
       query=user_input,
       user_id=user_id,
       k_conversations=5,  # 增加到 5
       k_knowledge=3,      # 增加到 3
       k_recent=30         # 增加到 30
   )
   ```

2. **增加短期记忆长度**
   
   编辑 `core/butler.py`：
   ```python
   # 保留最近 30 条消息（默认 20）
   if len(self.chat_history) > 30:
       self.chat_history = self.chat_history[-30:]
   ```

---

## 🗺️ 开发计划

### 已完成功能 ✅

#### 核心功能
- [x] LangChain Agent 集成
- [x] 双向量库记忆系统
- [x] 知识自动提取
- [x] 智能工具调用
- [x] 自然对话优化
- [x] 工作流系统

#### 工具集（40+ 工具）
- [x] 通讯工具（邮件、点赞、用户信息）
- [x] 信息查询（天气、搜索、时间）
- [x] 多媒体（图像理解、图片搜索、HTML 渲染）
- [x] 文档处理（PDF、Word、Excel）
- [x] 文件管理（发送、上传、删除）
- [x] 任务调度（定时任务、工作流）
- [x] 代码开发（读写、搜索、分析）
- [x] 测试工具（运行测试、覆盖率）
- [x] 系统工具（命令执行、日志查看）

#### 部署
- [x] NoneBot2 集成
- [x] NapCat 配置
- [x] 一键启动脚本
- [x] 多账号架构设计
- [x] 完整文档

### 进行中 🚧

#### 性能优化
- [ ] 向量检索性能优化（索引优化）
- [ ] 缓存机制（Redis）
- [ ] 异步处理优化
- [ ] 内存占用优化

#### 功能增强
- [ ] 语音消息支持
- [ ] 视频消息支持
- [ ] 情感分析
- [ ] 主动对话能力

### 短期计划（1-2 个月）

#### 1. 插件系统
- [ ] 插件热加载机制
- [ ] 插件配置管理
- [ ] 插件开发文档
- [ ] 插件示例和模板

#### 2. 数据分析
- [ ] 对话统计面板
- [ ] 用户画像分析
- [ ] 工具使用统计
- [ ] 可视化图表

#### 3. 安全增强
- [ ] 权限管理系统
- [ ] 敏感信息过滤
- [ ] 访问频率限制
- [ ] 完整审计日志

#### 4. 用户体验
- [ ] Web 管理后台
- [ ] 移动端适配
- [ ] 多语言支持
- [ ] 主题定制

### 中期计划（3-6 个月）

#### 1. 多平台支持
- [ ] 微信支持（企业微信）
- [ ] Telegram 支持
- [ ] Discord 支持
- [ ] 统一消息接口

#### 2. AI 能力增强
- [ ] 多模型支持（GPT-4、Claude、Gemini）
- [ ] 模型切换和负载均衡
- [ ] Fine-tuning 支持
- [ ] RAG 优化（更好的检索）

#### 3. 自动化工作流
- [ ] 可视化工作流编辑器
- [ ] 更多触发器类型
- [ ] 条件分支和循环
- [ ] 工作流模板市场

#### 4. 社区生态
- [ ] 插件市场
- [ ] 最佳实践文档
- [ ] 案例分享
- [ ] 技术支持社区

### 长期愿景（6-12 个月）

#### 1. 智能化升级
- [ ] 自主学习能力
- [ ] 个性化模型训练
- [ ] 多 Agent 协作
- [ ] 决策推理能力

#### 2. 生态建设
- [ ] 开发者平台
- [ ] 培训课程
- [ ] 认证体系
- [ ] 合作伙伴计划

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 贡献方式

1. **Fork 项目**
   ```bash
   # 在 GitHub 上点击 Fork 按钮
   ```

2. **克隆到本地**
   ```bash
   git clone https://github.com/你的用户名/chino_bot.git
   cd chino_bot/zhinai-bot-v3
   ```

3. **创建分支**
   ```bash
   git checkout -b feature/amazing-feature
   ```

4. **提交更改**
   ```bash
   git add .
   git commit -m 'Add some amazing feature'
   ```

5. **推送分支**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **提交 Pull Request**
   - 在 GitHub 上打开你的 Fork
   - 点击 "New Pull Request"
   - 填写 PR 描述

### 开发规范

#### 代码规范
- 遵循 PEP 8 代码规范
- 使用类型注解（Type Hints）
- 添加必要的注释和文档字符串
- 保持代码简洁和可读性

#### 提交规范
```bash
# 格式：<type>: <subject>

# 类型（type）：
# feat: 新功能
# fix: 修复 bug
# docs: 文档更新
# style: 代码格式（不影响功能）
# refactor: 重构
# test: 测试相关
# chore: 构建/工具相关

# 示例：
git commit -m "feat: 添加翻译工具"
git commit -m "fix: 修复邮件发送失败的问题"
git commit -m "docs: 更新 README"
```

#### 测试要求
- 为新功能编写单元测试
- 确保所有测试通过
- 测试覆盖率 > 80%

#### 文档要求
- 更新相关文档
- 添加使用示例
- 更新 CHANGELOG

### 问题反馈

**报告 Bug**
- [GitHub Issues](https://github.com/usera3/chino_bot/issues)
- 提供详细的错误信息和日志
- 说明复现步骤
- 提供环境信息（OS、Python 版本等）

**功能建议**
- [GitHub Discussions](https://github.com/usera3/chino_bot/discussions)
- 描述功能需求和使用场景
- 说明为什么需要这个功能
- 提供参考实现（如果有）

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

```
MIT License

Copyright (c) 2024 usera3

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 致谢

感谢以下开源项目和服务：

- [LangChain](https://github.com/langchain-ai/langchain) - AI 应用开发框架
- [NoneBot2](https://github.com/nonebot/nonebot2) - Python 异步机器人框架
- [NapCat](https://github.com/NapNeko/NapCatQQ) - QQ 协议实现
- [ChromaDB](https://github.com/chroma-core/chroma) - 向量数据库
- [DeepSeek](https://www.deepseek.com/) - AI 模型服务
- [Qwen-VL](https://github.com/QwenLM/Qwen-VL) - 多模态模型
- [Tavily](https://tavily.com/) - 搜索 API
- [高德地图](https://lbs.amap.com/) - 地图和天气 API
- [Pexels](https://www.pexels.com/) - 免费图片 API

---

## 📞 联系方式

- **项目主页**: https://github.com/usera3/chino_bot
- **问题反馈**: [GitHub Issues](https://github.com/usera3/chino_bot/issues)
- **讨论区**: [GitHub Discussions](https://github.com/usera3/chino_bot/discussions)
- **文档**: [查看文档](./docs/)

---

## 📊 项目统计

- **代码行数**: 10,000+ 行
- **工具数量**: 40+ 个
- **支持平台**: QQ（更多平台开发中）
- **Python 版本**: 3.10+
- **开源协议**: MIT

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！⭐**

Made with ❤️ by [usera3](https://github.com/usera3)

[返回顶部](#智乃机器人-v40---智能-qq-助手)

</div>
