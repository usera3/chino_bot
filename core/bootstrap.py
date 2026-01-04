"""
启动器 - 系统启动的指挥中心
就像工厂的总调度室，协调所有环节的启动和运行
"""
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
import sys

from .component_registry import get_registry, Component, ComponentStatus
from .health_checker import get_health_checker


class Bootstrap:
    """
    系统启动器
    负责整个系统的启动、检查、监控
    """
    
    def __init__(self):
        self.registry = get_registry()
        self.health_checker = get_health_checker()
        self.start_time: Optional[datetime] = None
        self._critical_components: List[str] = []
    
    def register_component(self, component: Component) -> None:
        """注册组件"""
        self.registry.register(component)
        
        # 如果有健康检查，注册到健康检查器
        if component.health_check:
            self.health_checker.register_check(component.name, component.health_check)
    
    def mark_as_critical(self, component_name: str) -> None:
        """
        标记为关键组件
        关键组件失败会导致系统无法启动
        """
        if component_name not in self._critical_components:
            self._critical_components.append(component_name)
    
    async def startup(self) -> bool:
        """
        启动系统
        Returns:
            是否启动成功
        """
        self.start_time = datetime.now()
        
        print("\n" + "=" * 80)
        print("🚀 智脑AI机器人 - 系统启动")
        print("=" * 80)
        print(f"启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 第一步：显示所有注册的组件
        print("📦 已注册组件:")
        components = self.registry.get_all()
        for i, comp in enumerate(components, 1):
            critical_mark = "🔴" if comp.name in self._critical_components else "🟢"
            print(f"  {i:2d}. {critical_mark} {comp.name:30} - {comp.description}")
        print(f"\n  总计: {len(components)} 个组件")
        print(f"  关键组件: {len(self._critical_components)} 个")
        
        # 第二步：计算初始化顺序
        print("\n🔗 分析依赖关系...")
        order = self.registry.calculate_initialization_order()
        print(f"  初始化顺序: {' → '.join(order)}")
        
        # 第三步：初始化所有组件
        init_results = await self.registry.initialize_all()
        
        # 第四步：检查关键组件
        print("\n🔍 检查关键组件状态...")
        critical_failed = []
        for name in self._critical_components:
            component = self.registry.get(name)
            if component and component.status != ComponentStatus.HEALTHY:
                critical_failed.append(name)
                print(f"  ❌ 关键组件失败: {name} - {component.error_message}")
        
        if critical_failed:
            print("\n💥 系统启动失败！关键组件不可用。")
            return False
        
        # 第五步：首次健康检查
        print("\n🏥 执行首次健康检查...")
        health_results = await self.health_checker.check_all()
        healthy_count = sum(1 for r in health_results.values() 
                          if r.status.value == "健康")
        print(f"  健康组件: {healthy_count}/{len(health_results)}")
        
        # 第六步：打印系统状态
        self.registry.print_status_report()
        
        # 计算启动耗时
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print(f"✅ 系统启动完成！耗时: {elapsed:.2f} 秒")
        print("=" * 80)
        print()
        
        return True
    
    async def shutdown(self) -> None:
        """关闭系统"""
        print("\n" + "=" * 80)
        print("🛑 系统正在关闭...")
        print("=" * 80)
        
        # 停止健康检查
        self.health_checker.stop_periodic_check()
        
        # 按初始化顺序的反序关闭组件
        components = self.registry.get_all()
        order = self.registry.calculate_initialization_order()
        
        for name in reversed(order):
            component = self.registry.get(name)
            if component and component.shutdown:
                try:
                    print(f"关闭: {component.name}")
                    if asyncio.iscoroutinefunction(component.shutdown):
                        await component.shutdown()
                    else:
                        component.shutdown()
                except Exception as e:
                    print(f"  ⚠️ 关闭失败: {e}")
        
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
            print(f"\n运行时长: {uptime:.2f} 秒")
        
        print("=" * 80)
        print("👋 系统已关闭")
        print("=" * 80)
    
    def get_system_info(self) -> Dict:
        """获取系统信息"""
        components = self.registry.get_all()
        
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() 
                            if self.start_time else 0,
            "total_components": len(components),
            "healthy_components": len(self.registry.get_by_status(ComponentStatus.HEALTHY)),
            "failed_components": len(self.registry.get_by_status(ComponentStatus.FAILED)),
            "critical_components": len(self._critical_components),
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "version": c.version,
                    "category": c.category
                }
                for c in components
            ]
        }
    
    def print_system_info(self) -> None:
        """打印系统信息"""
        info = self.get_system_info()
        
        print("\n" + "=" * 80)
        print("📊 系统信息")
        print("=" * 80)
        
        if info["start_time"]:
            uptime_hours = info["uptime_seconds"] / 3600
            print(f"启动时间: {info['start_time']}")
            print(f"运行时长: {uptime_hours:.2f} 小时")
        
        print(f"组件总数: {info['total_components']}")
        print(f"  ✅ 健康: {info['healthy_components']}")
        print(f"  ❌ 失败: {info['failed_components']}")
        print(f"  🔴 关键: {info['critical_components']}")
        
        print("=" * 80)


# 全局单例
_bootstrap = Bootstrap()

def get_bootstrap() -> Bootstrap:
    """获取全局启动器"""
    return _bootstrap




















