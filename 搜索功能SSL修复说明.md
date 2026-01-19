# 搜索功能 SSL 修复说明

## 问题描述

Tavily 搜索 API 在调用时出现 SSL 证书验证错误：
```
ClientConnectorCertificateError: Cannot connect to host api.tavily.com:443 ssl:True
```

## 根本原因

`TavilySearchResults` 工具使用 `aiohttp` 库进行异步 HTTP 请求，而 `aiohttp` 的 SSL 验证无法通过简单的环境变量禁用。需要在创建 `ClientSession` 时显式配置 SSL 上下文。

## 解决方案

通过 Monkey Patch 的方式修改 `aiohttp.ClientSession` 的初始化方法，强制使用不验证 SSL 的连接器：

```python
import ssl
import aiohttp

# 创建不验证 SSL 的 SSL 上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Monkey patch aiohttp 的 SSL 上下文
original_init = aiohttp.ClientSession.__init__

def patched_init(self, *args, **kwargs):
    # 强制使用不验证 SSL 的上下文
    if 'connector' not in kwargs:
        kwargs['connector'] = aiohttp.TCPConnector(ssl=False)
    original_init(self, *args, **kwargs)

aiohttp.ClientSession.__init__ = patched_init
```

## 修改文件

- `zhinai-bot-v3/tools/langchain_tools.py` - `get_search_tool()` 函数

## 测试结果

✅ **搜索功能已恢复正常**

测试命令：
```bash
python test_tavily_search.py
```

测试结果：
```
✅ 搜索成功！

搜索结果:
[{'title': '对不支持美国吞并格陵兰岛的国家，特朗普威胁要征收关税 - RFI', 
  'url': 'https://www.rfi.fr/cn/...', 
  'content': '...', 
  'score': 0.8858788}, 
 ...]
```

## 验证方法

### 1. 通过测试脚本验证
```bash
cd zhinai-bot-v3
python test_tavily_search.py
```

### 2. 通过机器人验证
在 QQ 中 @ 机器人并发送：
```
查一下特朗普最新新闻
```

机器人应该能够成功调用搜索工具并返回结果。

## 注意事项

⚠️ **安全警告**：此方案禁用了 SSL 证书验证，仅适用于开发/测试环境。生产环境建议：
1. 修复系统的 SSL 证书配置
2. 使用正确的 CA 证书
3. 或使用其他搜索工具（如 DuckDuckGo）

## 日志确认

启动日志中应显示：
```
✅ Tavily 搜索工具已启用（SSL 验证已禁用 - aiohttp patched）
```

## 相关文件

- `zhinai-bot-v3/tools/langchain_tools.py` - 搜索工具实现
- `zhinai-bot-v3/test_tavily_search.py` - 搜索功能测试脚本
- `zhinai-bot-v3/搜索功能SSL修复说明.md` - 本文档

## 更新时间

2026-01-19 16:45
