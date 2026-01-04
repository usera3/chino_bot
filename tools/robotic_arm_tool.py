"""
机械臂小车控制工具
提供远程控制农田机械臂系统的功能
支持移动小车、控制机械臂、控制抓手、执行预设动作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any, Optional
from nonebot.log import logger
import httpx


class RoboticArmTool(BaseTool):
    """
    机械臂小车控制工具
    提供远程控制农田机械臂系统的完整功能
    """
    
    def __init__(self):
        """初始化机械臂工具"""
        super().__init__()
        self.base_url = os.getenv("ROBOTIC_ARM_API_URL", "http://localhost:7070")
        self.timeout = 10.0
        
        # 默认参数
        self.default_duration = {
            "cart_move": 1.5,
            "arm_move": 1.0
        }
        
        logger.info(f"🤖 机械臂小车工具初始化: {self.base_url}")
    
    def get_name(self) -> str:
        return "control_robotic_arm"
    
    def get_description(self) -> str:
        return """控制农田机械臂系统。包括：
1. 移动小车到指定位置（支持指定x、z坐标）
2. 控制机械臂角度（支持设置shoulder、elbow、wrist三个关节）
3. 控制抓手开关（open/closed）
4. 执行预设动作（拔草、播种、完整循环）
当用户询问"移动小车"、"控制机械臂"、"执行拔草"等时使用"""
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "要执行的动作类型",
                    "enum": [
                        "get_status",  # 获取系统状态
                        "move_cart",  # 移动小车
                        "move_arm",  # 移动机械臂
                        "control_gripper",  # 控制抓手
                        "pull_grass",  # 拔草
                        "plant_seed",  # 播种
                        "full_cycle",  # 完整循环
                        "reset"  # 重置系统
                    ]
                },
                # 小车参数
                "x": {
                    "type": "number",
                    "description": "小车X轴位置（-1.5到1.5），用于move_cart动作"
                },
                "z": {
                    "type": "number",
                    "description": "小车Z轴位置（-1.5到1.5），用于move_cart动作"
                },
                # 机械臂参数
                "shoulder": {
                    "type": "number",
                    "description": "肩关节角度（-180到180），用于move_arm动作"
                },
                "elbow": {
                    "type": "number",
                    "description": "肘关节角度（-180到180），用于move_arm动作"
                },
                "wrist": {
                    "type": "number",
                    "description": "腕关节角度（-180到180），用于move_arm动作"
                },
                # 抓手参数
                "gripper_state": {
                    "type": "string",
                    "description": "抓手状态：'open'或'closed'，用于control_gripper动作",
                    "enum": ["open", "closed"]
                },
                # 动作参数
                "cell": {
                    "type": "integer",
                    "description": "格子索引（0-15），用于pull_grass和plant_seed动作",
                    "default": 0
                },
                "duration": {
                    "type": "number",
                    "description": "动画时长（秒），用于move_cart和move_arm动作",
                    "default": 1.5
                }
            },
            "required": ["action"]
        }
    
    async def execute(
        self,
        action: str,
        x: Optional[float] = None,
        z: Optional[float] = None,
        shoulder: Optional[float] = None,
        elbow: Optional[float] = None,
        wrist: Optional[float] = None,
        gripper_state: Optional[str] = None,
        cell: int = 0,
        duration: Optional[float] = None
    ) -> ToolResult:
        """
        执行机械臂控制操作
        
        Args:
            action: 动作类型
            x, z: 小车位置（用于move_cart）
            shoulder, elbow, wrist: 机械臂角度（用于move_arm）
            gripper_state: 抓手状态（用于control_gripper）
            cell: 格子索引（用于pull_grass和plant_seed）
            duration: 动画时长
        
        Returns:
            ToolResult: 执行结果
        """
        try:
            logger.info(f"🤖 执行机械臂动作: {action}")
            
            if action == "get_status":
                return await self._get_status()
            
            elif action == "move_cart":
                if x is None or z is None:
                    return ToolResult(
                        success=False,
                        message="移动小车需要提供x和z坐标",
                        error="MISSING_PARAMS"
                    )
                return await self._move_cart(x, z, duration)
            
            elif action == "move_arm":
                if all(a is None for a in [shoulder, elbow, wrist]):
                    return ToolResult(
                        success=False,
                        message="移动机械臂需要提供至少一个关节角度",
                        error="MISSING_PARAMS"
                    )
                return await self._move_arm(shoulder, elbow, wrist, duration)
            
            elif action == "control_gripper":
                if not gripper_state:
                    return ToolResult(
                        success=False,
                        message="控制抓手需要提供gripper_state（'open'或'closed'）",
                        error="MISSING_PARAMS"
                    )
                return await self._control_gripper(gripper_state)
            
            elif action == "pull_grass":
                return await self._execute_action("pull_grass", cell)
            
            elif action == "plant_seed":
                return await self._execute_action("plant_seed", cell)
            
            elif action == "full_cycle":
                return await self._execute_full_cycle()
            
            elif action == "reset":
                return await self._reset_system()
            
            else:
                return ToolResult(
                    success=False,
                    message=f"未知动作类型: {action}",
                    error="INVALID_ACTION"
                )
        
        except httpx.TimeoutException:
            logger.error("❌ 机械臂请求超时")
            return ToolResult(
                success=False,
                message="机械臂响应超时，请检查系统连接",
                error="TIMEOUT"
            )
        
        except Exception as e:
            logger.error(f"❌ 机械臂操作失败: {e}")
            return ToolResult(
                success=False,
                message=f"机械臂操作失败：{str(e)}",
                error="OPERATION_FAILED"
            )
    
    async def _get_status(self) -> ToolResult:
        """获取系统状态"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/status")
            
            if response.status_code == 200:
                data = response.json()
                logger.success("✅ 成功获取系统状态")
                return ToolResult(
                    success=True,
                    data=data.get("state", {}),
                    message="成功获取系统状态"
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"获取状态失败: HTTP {response.status_code}",
                    error="HTTP_ERROR"
                )
    
    async def _move_cart(self, x: float, z: float, duration: Optional[float]) -> ToolResult:
        """移动小车"""
        params = {
            "x": x,
            "z": z,
            "duration": duration or self.default_duration["cart_move"]
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/cart/move",
                json=params
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.success(f"✅ 小车移动成功: ({x}, {z})")
                return ToolResult(
                    success=True,
                    data=data,
                    message=f"小车已移动到位置 ({x}, {z})"
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"小车移动失败: HTTP {response.status_code}",
                    error="MOVE_FAILED"
                )
    
    async def _move_arm(self, shoulder: Optional[float], elbow: Optional[float], 
                       wrist: Optional[float], duration: Optional[float]) -> ToolResult:
        """移动机械臂"""
        params = {}
        if shoulder is not None:
            params["shoulder"] = shoulder
        if elbow is not None:
            params["elbow"] = elbow
        if wrist is not None:
            params["wrist"] = wrist
        if duration is not None:
            params["duration"] = duration
        else:
            params["duration"] = self.default_duration["arm_move"]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/arm/move",
                json=params
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.success(f"✅ 机械臂移动成功: {params}")
                return ToolResult(
                    success=True,
                    data=data,
                    message=f"机械臂已移动到目标位置"
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"机械臂移动失败: HTTP {response.status_code}",
                    error="MOVE_FAILED"
                )
    
    async def _control_gripper(self, state: str) -> ToolResult:
        """控制抓手"""
        params = {"state": state}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/gripper",
                json=params
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.success(f"✅ 抓手控制成功: {state}")
                return ToolResult(
                    success=True,
                    data=data,
                    message=f"抓手已{'打开' if state == 'open' else '关闭'}"
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"抓手控制失败: HTTP {response.status_code}",
                    error="GRIPPER_CONTROL_FAILED"
                )
    
    async def _execute_action(self, action_type: str, cell: int) -> ToolResult:
        """执行预设动作（拔草或播种）"""
        params = {"cell": cell}
        
        action_map = {
            "pull_grass": "拔草",
            "plant_seed": "播种"
        }
        action_name = action_map.get(action_type, action_type)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/action/{action_type}",
                json=params
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.success(f"✅ {action_name}动作执行成功: 格子{cell}")
                return ToolResult(
                    success=True,
                    data=data,
                    message=f"{action_name}动作已执行（格子{cell}）"
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"{action_name}动作失败: HTTP {response.status_code}",
                    error="ACTION_FAILED"
                )
    
    async def _execute_full_cycle(self) -> ToolResult:
        """执行完整16格循环"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/action/full_cycle")
            
            if response.status_code == 200:
                data = response.json()
                logger.success("✅ 完整循环开始执行")
                return ToolResult(
                    success=True,
                    data=data,
                    message="完整16格循环已开始执行"
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"完整循环执行失败: HTTP {response.status_code}",
                    error="CYCLE_FAILED"
                )
    
    async def _reset_system(self) -> ToolResult:
        """重置系统"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/reset")
            
            if response.status_code == 200:
                data = response.json()
                logger.success("✅ 系统已重置")
                return ToolResult(
                    success=True,
                    data=data,
                    message="系统已重置到初始状态"
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"系统重置失败: HTTP {response.status_code}",
                    error="RESET_FAILED"
                )
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        # 可以通过ping服务器来检查
        return True


# 导出工具实例
robotic_arm_tool = RoboticArmTool()

