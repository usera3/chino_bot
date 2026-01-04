"""
组件注册系统 - 统一管理所有功能模块
每个组件就像工厂里的一个车间，可以独立运作也可以协同工作
"""
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


class ComponentStatus(Enum):
    """组件状态"""
    UNINITIALIZED = "未初始化"
    INITIALIZING = "初始化中"
    HEALTHY = "健康"
    DEGRADED = "降级"  # 部分功能不可用但核心功能正常
    UNHEALTHY = "不健康"
    FAILED = "失败"


@dataclass
class Component:
    """
    组件定义 - 每个功能模块的标准接口
    就像工厂里的标准零件，统一规格，哪里需要哪里搬
    """
    name: str
    description: str
    version: str
    category: str  # 分类：core/plugin/service/integration
    
    # 生命周期钩子（工厂流水线）
    initialize: Optional[Callable] = None  # 初始化
    health_check: Optional[Callable] = None  # 健康检查
    shutdown: Optional[Callable] = None  # 关闭清理
    
    # 依赖关系（供应链）
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    
    # 状态信息
    status: ComponentStatus = ComponentStatus.UNINITIALIZED
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComponentRegistry:
    """
    组件注册表 - 工厂的中央调度室
    知道每个车间在哪，做什么，状态如何
    """
    
    def __init__(self):
        self._components: Dict[str, Component] = {}
        self._initialization_order: List[str] = []
    
    def register(self, component: Component) -> None:
        """
        注册组件
        就像在工厂登记一个新车间
        """
        if component.name in self._components:
            raise ValueError(f"组件 {component.name} 已经注册")
        
        self._components[component.name] = component
        print(f"📦 注册组件: {component.name} - {component.description}")
    
    def get(self, name: str) -> Optional[Component]:
        """获取组件"""
        return self._components.get(name)
    
    def get_all(self) -> List[Component]:
        """获取所有组件"""
        return list(self._components.values())
    
    def get_by_category(self, category: str) -> List[Component]:
        """按分类获取组件"""
        return [c for c in self._components.values() if c.category == category]
    
    def get_by_status(self, status: ComponentStatus) -> List[Component]:
        """按状态获取组件"""
        return [c for c in self._components.values() if c.status == status]
    
    def calculate_initialization_order(self) -> List[str]:
        """
        计算初始化顺序（拓扑排序）
        就像安排生产线的开工顺序，先做零件再组装
        """
        # 简单的拓扑排序实现
        visited = set()
        order = []
        
        def visit(name: str):
            if name in visited:
                return
            
            component = self._components.get(name)
            if not component:
                return
            
            # 先访问依赖
            for dep in component.dependencies:
                visit(dep)
            
            visited.add(name)
            order.append(name)
        
        # 访问所有组件
        for name in self._components:
            visit(name)
        
        self._initialization_order = order
        return order
    
    async def initialize_all(self) -> Dict[str, bool]:
        """
        按顺序初始化所有组件
        就像按流水线顺序开启所有车间
        """
        order = self.calculate_initialization_order()
        results = {}
        
        print("\n🏭 开始初始化组件（按依赖顺序）...")
        print("=" * 60)
        
        for name in order:
            component = self._components[name]
            print(f"\n[{len(results)+1}/{len(order)}] 初始化: {component.name}")
            
            try:
                component.status = ComponentStatus.INITIALIZING
                
                if component.initialize:
                    if asyncio.iscoroutinefunction(component.initialize):
                        await component.initialize()
                    else:
                        component.initialize()
                
                component.status = ComponentStatus.HEALTHY
                results[name] = True
                print(f"  ✅ {component.name} 初始化成功")
                
            except Exception as e:
                component.status = ComponentStatus.FAILED
                component.error_message = str(e)
                results[name] = False
                print(f"  ❌ {component.name} 初始化失败: {e}")
        
        print("\n" + "=" * 60)
        print(f"初始化完成: {sum(results.values())}/{len(results)} 成功")
        
        return results
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        健康检查所有组件
        就像工厂巡检，检查每个车间是否正常运作
        """
        results = {}
        
        for name, component in self._components.items():
            try:
                if component.health_check:
                    if asyncio.iscoroutinefunction(component.health_check):
                        is_healthy = await component.health_check()
                    else:
                        is_healthy = component.health_check()
                    
                    if is_healthy:
                        if component.status != ComponentStatus.HEALTHY:
                            component.status = ComponentStatus.HEALTHY
                    else:
                        component.status = ComponentStatus.UNHEALTHY
                    
                    component.last_check = datetime.now()
                    results[name] = is_healthy
                else:
                    # 没有健康检查函数，默认健康
                    results[name] = True
                    
            except Exception as e:
                component.status = ComponentStatus.UNHEALTHY
                component.error_message = str(e)
                results[name] = False
        
        return results
    
    def print_status_report(self) -> None:
        """
        打印状态报告
        就像工厂的仪表盘，一目了然
        """
        print("\n📊 系统组件状态报告")
        print("=" * 80)
        
        # 按分类分组
        categories = {}
        for component in self._components.values():
            if component.category not in categories:
                categories[component.category] = []
            categories[component.category].append(component)
        
        # 打印每个分类
        for category, components in sorted(categories.items()):
            print(f"\n【{category.upper()}】")
            for comp in components:
                status_icon = {
                    ComponentStatus.HEALTHY: "✅",
                    ComponentStatus.DEGRADED: "⚠️",
                    ComponentStatus.UNHEALTHY: "❌",
                    ComponentStatus.FAILED: "💥",
                    ComponentStatus.UNINITIALIZED: "⏸️",
                    ComponentStatus.INITIALIZING: "⏳"
                }.get(comp.status, "❓")
                
                print(f"  {status_icon} {comp.name:30} | {comp.status.value:10} | v{comp.version}")
                if comp.error_message:
                    print(f"     └─ 错误: {comp.error_message[:60]}")
        
        # 统计
        print("\n" + "=" * 80)
        total = len(self._components)
        healthy = len(self.get_by_status(ComponentStatus.HEALTHY))
        failed = len(self.get_by_status(ComponentStatus.FAILED))
        print(f"总计: {total} 个组件 | ✅ {healthy} 健康 | ❌ {failed} 失败")
        print("=" * 80)


# 全局单例
_registry = ComponentRegistry()

def get_registry() -> ComponentRegistry:
    """获取全局组件注册表"""
    return _registry




