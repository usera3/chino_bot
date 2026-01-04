"""
健康检查系统 - 定期巡检所有组件
就像工厂的质检员，定期检查每个车间的运行状况
"""
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "健康"
    DEGRADED = "降级"
    UNHEALTHY = "不健康"
    UNKNOWN = "未知"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component_name: str
    status: HealthStatus
    message: str = ""
    checked_at: datetime = None
    response_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.now()


class HealthChecker:
    """
    健康检查器
    定期巡检所有注册的组件
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Args:
            check_interval: 检查间隔（秒）
        """
        self.check_interval = check_interval
        self._checks: Dict[str, Callable] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """注册健康检查函数"""
        self._checks[name] = check_func
        print(f"🏥 注册健康检查: {name}")
    
    async def check_one(self, name: str) -> HealthCheckResult:
        """检查单个组件"""
        if name not in self._checks:
            return HealthCheckResult(
                component_name=name,
                status=HealthStatus.UNKNOWN,
                message="未注册健康检查"
            )
        
        check_func = self._checks[name]
        start_time = datetime.now()
        
        try:
            if asyncio.iscoroutinefunction(check_func):
                is_healthy = await check_func()
            else:
                is_healthy = check_func()
            
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            result = HealthCheckResult(
                component_name=name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message="检查通过" if is_healthy else "检查失败",
                response_time_ms=elapsed
            )
            
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            result = HealthCheckResult(
                component_name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"检查异常: {str(e)[:100]}",
                response_time_ms=elapsed
            )
        
        self._last_results[name] = result
        return result
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """检查所有组件"""
        results = {}
        
        for name in self._checks:
            results[name] = await self.check_one(name)
        
        return results
    
    async def start_periodic_check(self) -> None:
        """启动定期检查"""
        if self._running:
            return
        
        self._running = True
        print(f"🏥 启动定期健康检查（间隔: {self.check_interval}秒）")
        
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                results = await self.check_all()
                
                # 只打印有问题的组件
                unhealthy = [r for r in results.values() 
                           if r.status != HealthStatus.HEALTHY]
                
                if unhealthy:
                    print(f"\n⚠️ 发现 {len(unhealthy)} 个组件异常:")
                    for result in unhealthy:
                        print(f"  - {result.component_name}: {result.message}")
                
            except Exception as e:
                print(f"❌ 健康检查失败: {e}")
    
    def stop_periodic_check(self) -> None:
        """停止定期检查"""
        self._running = False
        if self._task:
            self._task.cancel()
        print("🏥 已停止定期健康检查")
    
    def get_last_result(self, name: str) -> Optional[HealthCheckResult]:
        """获取最后一次检查结果"""
        return self._last_results.get(name)
    
    def get_all_results(self) -> Dict[str, HealthCheckResult]:
        """获取所有检查结果"""
        return self._last_results.copy()
    
    def print_health_report(self) -> None:
        """打印健康报告"""
        if not self._last_results:
            print("暂无健康检查数据")
            return
        
        print("\n🏥 系统健康报告")
        print("=" * 80)
        
        for name, result in sorted(self._last_results.items()):
            status_icon = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "⚠️",
                HealthStatus.UNHEALTHY: "❌",
                HealthStatus.UNKNOWN: "❓"
            }.get(result.status, "❓")
            
            time_str = result.checked_at.strftime("%H:%M:%S")
            response = f"{result.response_time_ms:.1f}ms"
            
            print(f"{status_icon} {name:30} | {result.status.value:6} | "
                  f"{response:8} | {time_str} | {result.message[:30]}")
        
        print("=" * 80)


# 全局单例
_health_checker = HealthChecker()

def get_health_checker() -> HealthChecker:
    """获取全局健康检查器"""
    return _health_checker




