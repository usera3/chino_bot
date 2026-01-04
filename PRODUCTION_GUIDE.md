# 🚀 生产环境部署指南

## 📊 性能优化清单

### 1. 数据库迁移（重要！）

**当前问题**：SQLite不支持高并发，适合测试但不适合生产环境

#### 推荐方案A：PostgreSQL（推荐）
```bash
# 安装PostgreSQL
brew install postgresql  # macOS
# 或 sudo apt-get install postgresql  # Ubuntu

# 创建数据库
createdb chatbot

# 安装Python驱动
pip install asyncpg psycopg2-binary
```

**修改配置**（`plugins/chat_plugin_advanced.py`）：
```python
# 将这行：
DATABASE_URL = "sqlite+aiosqlite:///./conversations.db"

# 改为：
DATABASE_URL = "postgresql+asyncpg://username:password@localhost:5432/chatbot"
```

#### 方案B：MySQL
```bash
# 安装MySQL
brew install mysql  # macOS

# 创建数据库
mysql -u root -p
CREATE DATABASE chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 安装Python驱动
pip install aiomysql
```

**配置**：
```python
DATABASE_URL = "mysql+aiomysql://username:password@localhost:3306/chatbot"
```

---

### 2. 添加数据库索引（必须！）

创建 `plugins/database_indexes.py`：

```python
"""
数据库索引优化
执行一次即可，大幅提升查询速度
"""

from sqlalchemy import text
from chat_plugin_advanced import db_manager
import asyncio

async def create_indexes():
    async with db_manager.engine.begin() as conn:
        # 1. 用户表索引
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_user_id ON users(user_id)"
        ))
        
        # 2. 对话表索引（最重要！）
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_conversation_user_id ON conversations(user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_conversation_timestamp ON conversations(timestamp DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_conversation_importance ON conversations(importance_score DESC)"
        ))
        
        # 3. 摘要表索引
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_summary_user_id ON conversation_summaries(user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_summary_timestamp ON conversation_summaries(created_at DESC)"
        ))
        
        print("✅ 数据库索引创建完成！")

if __name__ == "__main__":
    asyncio.run(create_indexes())
```

**执行**：
```bash
python plugins/database_indexes.py
```

---

### 3. 启用缓存和速率限制

修改 `plugins/intelligent_dispatcher.py`，在文件开头添加：

```python
from production_optimizer import (
    user_cache, 
    api_rate_limiter, 
    performance_monitor
)

# 在 _handle_chat 方法中使用缓存
async def _handle_chat(user_message: str, user_id: str, intent: Dict) -> str:
    # 1. 先检查缓存
    start_time = time.time()
    cached_context = user_cache.get(f"context_{user_id}")
    
    if cached_context:
        messages = cached_context
        performance_monitor.record_cache_hit()
    else:
        # 从数据库加载
        messages, _ = await IntelligentMemoryManager.build_context(user_id)
        user_cache.set(f"context_{user_id}", messages)
        performance_monitor.record_cache_miss()
        performance_monitor.record_db_query()
    
    # 2. API调用前获取令牌
    await api_rate_limiter.acquire()
    performance_monitor.record_api_call()
    
    # ... 调用API ...
    
    # 3. 记录性能
    performance_monitor.record_response_time(time.time() - start_time)
    
    return reply
```

---

### 4. 数据清理定时任务

创建 `plugins/cleanup_task.py`：

```python
"""
定时数据清理任务
每天自动运行，清理旧数据
"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from chat_plugin_advanced import db_manager
from nonebot.log import logger

async def cleanup_old_conversations():
    """清理超过90天的对话"""
    try:
        cutoff = datetime.now() - timedelta(days=90)
        
        async with db_manager.async_session() as session:
            result = await session.execute(
                text("""
                    DELETE FROM conversations 
                    WHERE timestamp < :cutoff 
                    AND importance_score < 0.7
                """),
                {"cutoff": cutoff}
            )
            deleted = result.rowcount
            await session.commit()
            
        logger.info(f"✅ 已清理 {deleted} 条旧对话记录")
    except Exception as e:
        logger.error(f"❌ 清理失败: {e}")

async def vacuum_database():
    """压缩数据库（仅SQLite）"""
    try:
        async with db_manager.engine.begin() as conn:
            await conn.execute(text("VACUUM"))
        logger.info("✅ 数据库已压缩")
    except Exception as e:
        logger.error(f"❌ 压缩失败: {e}")

# 启动定时任务
def start_cleanup_scheduler():
    scheduler = AsyncIOScheduler()
    
    # 每天凌晨3点清理
    scheduler.add_job(cleanup_old_conversations, 'cron', hour=3, minute=0)
    
    # 每周日凌晨4点压缩数据库
    scheduler.add_job(vacuum_database, 'cron', day_of_week='sun', hour=4)
    
    scheduler.start()
    logger.info("🕐 定时清理任务已启动")

# 在bot.py中调用
# from cleanup_task import start_cleanup_scheduler
# start_cleanup_scheduler()
```

---

### 5. 监控和日志

添加性能监控命令：

```python
# 在 bot.py 或新建 plugins/admin_plugin.py
from nonebot.plugin import on_command
from nonebot.permission import SUPERUSER
from production_optimizer import performance_monitor, user_cache

stats_cmd = on_command("stats", permission=SUPERUSER, priority=1)

@stats_cmd.handle()
async def show_stats():
    perf_stats = performance_monitor.get_stats()
    cache_stats = user_cache.stats()
    
    message = f"""
📊 系统性能统计

⏱️ 运行时间: {perf_stats['运行时间']}
🔥 API调用: {perf_stats['API调用']}
💾 数据库查询: {perf_stats['数据库查询']}
⚡ 缓存命中率: {perf_stats['缓存命中率']}
🎯 平均响应: {perf_stats['平均响应时间']}
❌ 错误数: {perf_stats['错误数']}

📦 缓存状态:
- 当前大小: {cache_stats['size']}/{cache_stats['capacity']}
- 使用率: {cache_stats['usage']}
    """
    await stats_cmd.send(message.strip())
```

---

## 🔧 生产环境配置建议

### 系统配置

```toml
# pyproject.toml

[tool.nonebot]
log_level = "INFO"  # 生产环境使用INFO，避免过多DEBUG日志

[project]
dependencies = [
    "nonebot2>=2.3.0",
    "nonebot-adapter-onebot>=2.4.0",
    "httpx>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "aiosqlite>=0.20.0",
    
    # 生产环境额外依赖
    "asyncpg>=0.29.0",      # PostgreSQL驱动
    "redis>=5.0.0",          # Redis缓存（可选）
    "apscheduler>=3.10.0",   # 定时任务
    "prometheus-client",     # 监控指标（可选）
]
```

### Nginx配置（如果需要）

```nginx
upstream chatbot {
    server 127.0.0.1:8080;
    keepalive 64;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://chatbot;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Systemd服务配置

```ini
# /etc/systemd/system/chatbot.service

[Unit]
Description=ChatBot Service
After=network.target

[Service]
Type=simple
User=chatbot
WorkingDirectory=/path/to/chino_bot/zhinai-bot
ExecStart=/path/to/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable chatbot
sudo systemctl start chatbot
sudo systemctl status chatbot
```

---

## 📈 性能基准测试

### 预期性能指标

| 指标 | SQLite（开发） | PostgreSQL（生产） |
|------|----------------|-------------------|
| 并发用户 | ~10 | ~1000+ |
| 平均响应时间 | 1-2秒 | 0.5-1秒 |
| 数据库QPS | ~50 | ~5000 |
| API调用限制 | 20/分钟 | 可配置 |

### 压力测试

```python
# 使用locust进行压力测试
# pip install locust

from locust import HttpUser, task

class ChatBotUser(HttpUser):
    @task
    def send_message(self):
        self.client.post("/chat", json={"message": "你好"})
```

---

## 🔐 安全建议

1. **API密钥管理**：
   ```python
   import os
   API_KEY = os.getenv("DEEPSEEK_API_KEY")  # 从环境变量读取
   ```

2. **速率限制**：每个用户每分钟最多10条消息

3. **输入验证**：过滤恶意输入和SQL注入

4. **日志脱敏**：不记录用户敏感信息

---

## 📝 检查清单

部署前检查：

- [ ] 已迁移到PostgreSQL/MySQL
- [ ] 已创建数据库索引
- [ ] 已启用缓存系统
- [ ] 已配置API速率限制
- [ ] 已设置定时清理任务
- [ ] 已配置监控和日志
- [ ] 已进行压力测试
- [ ] API密钥使用环境变量
- [ ] 已配置进程管理（systemd/supervisor）
- [ ] 已设置备份策略

---

## 🆘 故障排查

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查数据库是否运行
   sudo systemctl status postgresql
   
   # 检查连接
   psql -U username -d chatbot
   ```

2. **API调用失败**
   ```bash
   # 检查网络
   curl https://api.deepseek.com/v1/models
   
   # 检查API密钥
   echo $DEEPSEEK_API_KEY
   ```

3. **内存占用过高**
   ```python
   # 减少缓存容量
   user_cache = LRUCache(capacity=500, ttl=180)
   ```

---

## 📞 技术支持

如有问题，请提供以下信息：
- 系统版本（`uname -a`）
- Python版本（`python --version`）
- 数据库版本
- 完整错误日志
- 性能统计数据（`/stats`命令输出）





