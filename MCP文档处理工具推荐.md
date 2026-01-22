# MCP 文档处理工具推荐

## 问题背景

虽然机器人现在有文件传输功能，但还无法：
- 📖 **阅读文件**：读取 PDF、Word、Excel 等文档内容
- ✍️ **制作文件**：创建和编辑文档

需要安装相应的 MCP 工具来补充这些能力。

## 推荐的 MCP 服务器

### 1. Document Operations (推荐⭐⭐⭐⭐⭐)

**GitHub**: `alejandroballesteros/document-operations`

**功能**：
- ✅ 创建 Word 文档
- ✅ 编辑 Word 文档（添加/编辑/删除段落和标题）
- ✅ 创建 Excel 表格
- ✅ 编辑 Excel 文件（更新单元格、行、列、工作表）
- ✅ 创建 PDF 文件
- ✅ Word 转 PDF
- ✅ TXT 转 Word
- ✅ CSV 转 Excel

**安装方式**：
```bash
# 使用 uvx（推荐）
uvx alejandroballesteros/document-operations
```

**配置示例**（添加到 `.kiro/settings/mcp.json`）：
```json
{
  "mcpServers": {
    "document-operations": {
      "command": "uvx",
      "args": ["alejandroballesteros/document-operations"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 2. MCP Doc Forge

**GitHub**: `cablate/mcp-doc-forge`

**功能**：
- ✅ 读取多种文档格式（DOCX、PDF、TXT、HTML、CSV）
- ✅ 文档转换（DOCX → HTML/PDF、HTML → TXT/Markdown）
- ✅ PDF 合并和分割
- ✅ 文本清理和对比
- ✅ HTML 资源提取

**安装方式**：
```bash
# 使用 npm
npm install -g @cablate/mcp-doc-forge

# 或使用 npx
npx @cablate/mcp-doc-forge
```

**配置示例**：
```json
{
  "mcpServers": {
    "doc-forge": {
      "command": "npx",
      "args": ["@cablate/mcp-doc-forge"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 3. MCP PDF Reader

**GitHub**: `labeveryday/mcp_pdf_reader`

**功能**：
- ✅ PDF 文本提取
- ✅ PDF 图片提取
- ✅ OCR（识别图片中的文字）
- ✅ 强大的 PDF 处理能力

**安装方式**：
```bash
# 使用 uvx
uvx labeveryday/mcp_pdf_reader
```

**配置示例**：
```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uvx",
      "args": ["labeveryday/mcp_pdf_reader"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 4. MCP Server Office

**GitHub**: `famano/mcp-server-office`

**功能**：
- ✅ 读取 DOCX 文件
- ✅ 创建 DOCX 文件
- ✅ 编辑 DOCX 段落
- ✅ 插入新段落

**安装方式**：
```bash
# 使用 uvx
uvx famano/mcp-server-office
```

**配置示例**：
```json
{
  "mcpServers": {
    "office": {
      "command": "uvx",
      "args": ["famano/mcp-server-office"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 5. Doc Reading and Converter

**GitHub**: `mffrydman/doc-reading-mcp`

**功能**：
- ✅ 读取和转换文档
- ✅ PDF ↔ DOCX ↔ Markdown
- ✅ 使用 marker-pdf 和 pandoc

**安装方式**：
```bash
# 使用 uvx
uvx mffrydman/doc-reading-mcp
```

**配置示例**：
```json
{
  "mcpServers": {
    "doc-converter": {
      "command": "uvx",
      "args": ["mffrydman/doc-reading-mcp"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 推荐配置方案

### 方案 1：全能型（推荐）

适合需要完整文档处理能力的场景。

```json
{
  "mcpServers": {
    "document-operations": {
      "command": "uvx",
      "args": ["alejandroballesteros/document-operations"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "doc-forge": {
      "command": "npx",
      "args": ["@cablate/mcp-doc-forge"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**能力**：
- ✅ 创建和编辑 Word、Excel、PDF
- ✅ 读取多种文档格式
- ✅ 文档格式转换
- ✅ PDF 合并和分割

### 方案 2：轻量型

适合只需要基本文档处理的场景。

```json
{
  "mcpServers": {
    "document-operations": {
      "command": "uvx",
      "args": ["alejandroballesteros/document-operations"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**能力**：
- ✅ 创建和编辑 Word、Excel、PDF
- ✅ 基本格式转换

### 方案 3：PDF 专精型

适合主要处理 PDF 的场景。

```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uvx",
      "args": ["labeveryday/mcp_pdf_reader"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "doc-forge": {
      "command": "npx",
      "args": ["@cablate/mcp-doc-forge"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**能力**：
- ✅ 强大的 PDF 处理（提取文本、图片、OCR）
- ✅ PDF 合并和分割
- ✅ 文档格式转换

## 安装步骤

### 1. 确保已安装依赖

**Python 工具（uvx）**：
```bash
# 检查是否已安装
uvx --version

# 如果未安装，安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或使用 pip
pip install uv
```

**Node.js 工具（npx）**：
```bash
# 检查是否已安装
npx --version

# 如果未安装，安装 Node.js
# macOS
brew install node

# 或从官网下载
# https://nodejs.org/
```

### 2. 创建或编辑 MCP 配置文件

**位置**：`.kiro/settings/mcp.json`

如果文件不存在，创建它：
```bash
mkdir -p .kiro/settings
touch .kiro/settings/mcp.json
```

### 3. 添加配置

将上面推荐的配置方案复制到 `mcp.json` 文件中。

### 4. 重启 Kiro 或重新连接 MCP 服务器

配置会自动生效，MCP 服务器会在需要时自动启动。

## 使用示例

### 示例 1：创建 Word 文档

```
用户：@智乃 帮我创建一个 Word 文档，标题是"会议记录"，内容是"今天讨论了项目进度"

机器人推理过程：
1. 识别用户意图：创建 Word 文档
2. 调用 document-operations 的 create_word 工具
3. 保存文件到本地
4. 可选：上传到群文件

机器人回复：
✅ Word 文档创建成功！
📁 文件名：会议记录.docx
📂 位置：/path/to/file
```

### 示例 2：读取 PDF 文件

```
用户：@智乃 帮我读一下这个 PDF 文件的内容
[用户发送 PDF 文件]

机器人推理过程：
1. 接收 PDF 文件
2. 下载到本地
3. 调用 pdf-reader 的 extract_text 工具
4. 提取文本内容
5. 总结或回答用户问题

机器人回复：
📄 PDF 内容摘要：
这是一份关于...的文档，主要内容包括...
```

### 示例 3：转换文档格式

```
用户：@智乃 把这个 Word 文档转成 PDF

机器人推理过程：
1. 接收 Word 文档
2. 调用 document-operations 的 convert_word_to_pdf 工具
3. 生成 PDF 文件
4. 可选：上传到群文件

机器人回复：
✅ 转换成功！
📁 原文件：文档.docx
📁 新文件：文档.pdf
📊 大小：1.2 MB
```

### 示例 4：编辑 Excel 表格

```
用户：@智乃 创建一个 Excel 表格，第一行是"姓名、年龄、职位"，第二行是"张三、25、工程师"

机器人推理过程：
1. 识别用户意图：创建 Excel 表格
2. 解析数据结构
3. 调用 document-operations 的 create_excel 工具
4. 保存文件

机器人回复：
✅ Excel 表格创建成功！
📁 文件名：数据表.xlsx
📊 包含 1 个工作表，2 行数据
```

## 与文件传输功能的结合

有了文档处理 MCP 工具后，机器人可以实现完整的文档工作流：

### 工作流 1：接收 → 阅读 → 回复

```
1. 用户发送 PDF 文件
2. 机器人下载文件
3. 使用 MCP 工具读取内容
4. 理解并回答用户问题
```

### 工作流 2：创建 → 上传 → 分享

```
1. 用户要求创建文档
2. 机器人使用 MCP 工具创建
3. 使用文件传输工具上传到群文件
4. 通知用户完成
```

### 工作流 3：下载 → 转换 → 上传

```
1. 用户要求转换群文件中的文档
2. 机器人下载文件
3. 使用 MCP 工具转换格式
4. 上传转换后的文件到群文件
```

## 注意事项

1. **依赖安装**
   - Python 工具需要 Python 3.10+
   - Node.js 工具需要 Node.js 14+
   - 某些工具可能需要额外的系统依赖

2. **文件路径**
   - MCP 工具处理的文件必须在本地文件系统上
   - 需要配置合适的工作目录

3. **权限问题**
   - 确保机器人有读写文件的权限
   - 某些操作可能需要特定的系统权限

4. **性能考虑**
   - 大文件处理可能需要较长时间
   - 建议设置合理的超时时间

5. **安全性**
   - 不要处理不信任的文件
   - 注意文件内容的隐私保护

## 下一步

1. **选择配置方案**：根据需求选择上面的配置方案
2. **安装依赖**：确保 uvx 和 npx 已安装
3. **配置 MCP**：编辑 `.kiro/settings/mcp.json`
4. **测试功能**：尝试创建和读取文档
5. **集成工作流**：结合文件传输功能实现完整工作流

## 参考资料

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [Document Operations GitHub](https://github.com/alejandroballesteros/document-operations)
- [MCP Doc Forge](https://github.com/cablate/mcp-doc-forge)
- [MCP PDF Reader](https://github.com/labeveryday/mcp_pdf_reader)
- [MCP Servers 目录](https://mcpservers.org/)
