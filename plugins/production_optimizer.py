"""
生产级优化模块 - 为高并发场景设计
适用于大量用户的实际生产环境
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
from collections import OrderedDict
from nonebot.log import logger

# ==================== 1. 内存缓存系统 ====================
class LRUCache:
    """
    LRU缓存 - 最近最少使用淘汰策略
    用于缓存用户会话数据，减少数据库查询
    """
    
    def __init__(self, capacity: int = 1000, ttl: int = 300):
        """
        Args:
            capacity: 缓存容量（用户数）
            ttl: 过期时间（秒），默认5分钟
        """
        self.cache = OrderedDict()
        self.capacity = capacity
        self.ttl = ttl
        self.timestamps = {}
        logger.info(f"LRU缓存初始化: 容量={capacity}, TTL={ttl}秒")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key not in self.cache:
            return None
        
        # 检查是否过期
        if time.time() - self.timestamps[key] > self.ttl:
            self.remove(key)
            return None
        
        # 移到最后（表示最近使用）
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key: str, value: Any):
        """设置缓存数据"""
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.capacity:
                # 移除最旧的
                oldest = next(iter(self.cache))
                self.remove(oldest)
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def remove(self, key: str):
        """移除缓存"""
        if key in self.cache:
            del self.cache[key]
            del self.timestamps[key]
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.timestamps.clear()
    
    def stats(self) -> Dict:
        """缓存统计"""
        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "usage": f"{len(self.cache)/self.capacity*100:.1f}%"
        }


# ==================== 2. API速率限制器 ====================
class RateLimiter:
    """
    令牌桶算法 - API速率限制
    防止API调用过快被限流
    """
    
    def __init__(self, rate: int = 20, per: int = 60):
        """
        Args:
            rate: 允许的请求数
            per: 时间窗口（秒）
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
        self.lock = asyncio.Lock()
        logger.info(f"速率限制器初始化: {rate}次/{per}秒")
    
    async def acquire(self):
        """获取令牌（等待直到有令牌可用）"""
        async with self.lock:
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current
            
            # 补充令牌
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            
            # 如果令牌不足，等待
            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
                logger.debug(f"API速率限制触发，等待 {sleep_time:.2f} 秒")
                await asyncio.sleep(sleep_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0


# ==================== 3. 数据库连接池配置 ====================
class DatabasePoolConfig:
    """
    数据库连接池配置
    SQLite不支持真正的连接池，建议生产环境使用PostgreSQL
    """
    
    # 推荐的生产环境配置
    POSTGRESQL_URL = "postgresql+asyncpg://user:password@localhost:5432/chatbot"
    MYSQL_URL = "mysql+aiomysql://user:password@localhost:3306/chatbot"
    
    # 连接池参数（针对PostgreSQL/MySQL）
    POOL_SIZE = 20              # 连接池大小
    MAX_OVERFLOW = 10           # 最大溢出连接数
    POOL_TIMEOUT = 30           # 获取连接超时时间（秒）
    POOL_RECYCLE = 3600         # 连接回收时间（秒）
    POOL_PRE_PING = True        # 连接前检查是否有效
    
    # 查询优化
    ECHO_SQL = False            # 生产环境关闭SQL日志
    QUERY_TIMEOUT = 10          # 查询超时时间（秒）


# ==================== 4. 数据归档策略 ====================
class DataArchivePolicy:
    """
    数据归档策略
    定期清理旧数据，保持数据库性能
    """
    
    # 归档配置
    ARCHIVE_AFTER_DAYS = 90     # 90天后归档
    DELETE_AFTER_DAYS = 365     # 1年后删除
    CLEANUP_INTERVAL_HOURS = 24  # 每24小时清理一次
    
    # 每个用户最大存储
    MAX_MESSAGES_PER_USER = 1000
    MAX_SUMMARIES_PER_USER = 50
    
    @staticmethod
    async def cleanup_old_data(db_manager):
        """清理旧数据（需要定期调用）"""
        try:
            cutoff_date = datetime.now() - timedelta(days=DataArchivePolicy.DELETE_AFTER_DAYS)
            logger.info(f"开始清理 {cutoff_date} 之前的数据")
            
            # 这里需要在数据库管理器中实现具体的清理逻辑
            # await db_manager.delete_old_conversations(cutoff_date)
            
            logger.info("数据清理完成")
        except Exception as e:
            logger.error(f"数据清理失败: {e}")


# ==================== 5. 性能监控 ====================
class PerformanceMonitor:
    """
    性能监控
    实时监控系统性能指标
    """
    
    def __init__(self):
        self.metrics = {
            "api_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "db_queries": 0,
            "errors": 0,
            "avg_response_time": 0,
            "start_time": time.time()
        }
        self.response_times = []
    
    def record_api_call(self):
        self.metrics["api_calls"] += 1
    
    def record_cache_hit(self):
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        self.metrics["cache_misses"] += 1
    
    def record_db_query(self):
        self.metrics["db_queries"] += 1
    
    def record_error(self):
        self.metrics["errors"] += 1
    
    def record_response_time(self, duration: float):
        """记录响应时间"""
        self.response_times.append(duration)
        # 只保留最近100条
        if len(self.response_times) > 100:
            self.response_times.pop(0)
        self.metrics["avg_response_time"] = sum(self.response_times) / len(self.response_times)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        uptime = time.time() - self.metrics["start_time"]
        cache_total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        cache_hit_rate = (self.metrics["cache_hits"] / cache_total * 100) if cache_total > 0 else 0
        
        return {
            "运行时间": f"{uptime/3600:.1f} 小时",
            "API调用": self.metrics["api_calls"],
            "数据库查询": self.metrics["db_queries"],
            "缓存命中率": f"{cache_hit_rate:.1f}%",
            "平均响应时间": f"{self.metrics['avg_response_time']:.2f} 秒",
            "错误数": self.metrics["errors"]
        }
    
    def reset(self):
        """重置统计"""
        self.__init__()


# ==================== 6. 批量处理器 ====================
class BatchProcessor:
    """
    批量处理器
    合并多个小请求为批量请求，提高效率
    """
    
    def __init__(self, batch_size: int = 10, wait_time: float = 0.5):
        """
        Args:
            batch_size: 批量大小
            wait_time: 等待时间（秒）
        """
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.queue = []
        self.lock = asyncio.Lock()
    
    async def add(self, item: Any) -> Any:
        """添加到批处理队列"""
        async with self.lock:
            self.queue.append(item)
            
            if len(self.queue) >= self.batch_size:
                return await self._process_batch()
        
        # 等待一段时间后处理
        await asyncio.sleep(self.wait_time)
        async with self.lock:
            if self.queue:
                return await self._process_batch()
    
    async def _process_batch(self) -> List:
        """处理批量请求"""
        batch = self.queue[:self.batch_size]
        self.queue = self.queue[self.batch_size:]
        
        # 这里实现具体的批量处理逻辑
        # 例如：批量保存到数据库
        logger.debug(f"批量处理 {len(batch)} 条记录")
        return batch


# ==================== 全局实例 ====================
# 创建全局实例供其他模块使用
user_cache = LRUCache(capacity=1000, ttl=300)  # 缓存1000个用户，5分钟过期
api_rate_limiter = RateLimiter(rate=20, per=60)  # 每分钟20次API调用
performance_monitor = PerformanceMonitor()


# ==================== 使用示例 ====================
async def example_usage():
    """使用示例"""
    
    # 1. 使用缓存
    user_id = "12345"
    cached_data = user_cache.get(user_id)
    if cached_data:
        performance_monitor.record_cache_hit()
        logger.info("从缓存获取数据")
    else:
        performance_monitor.record_cache_miss()
        performance_monitor.record_db_query()
        # 从数据库获取
        data = {"messages": []}  # 假设从DB获取
        user_cache.set(user_id, data)
    
    # 2. 使用速率限制
    await api_rate_limiter.acquire()  # 等待获取令牌
    performance_monitor.record_api_call()
    # 调用API
    
    # 3. 记录响应时间
    start = time.time()
    # ... 执行操作 ...
    performance_monitor.record_response_time(time.time() - start)
    
    # 4. 查看统计
    stats = performance_monitor.get_stats()
    logger.info(f"性能统计: {stats}")


if __name__ == "__main__":
    # 测试
    asyncio.run(example_usage())

