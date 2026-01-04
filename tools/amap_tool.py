"""
高德地图工具 - 地理位置和导航服务
提供位置查询、路线规划、周边搜索等功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any, Optional
from nonebot.log import logger
import httpx


class AmapTool(BaseTool):
    """
    高德地图工具
    提供地理位置查询、周边搜索、路线规划等功能
    """
    
    def __init__(self):
        """初始化高德地图工具"""
        super().__init__()
        self.api_key = os.getenv("AMAP_API_KEY", "")
        self.base_url = "https://restapi.amap.com/v3"
        
        # 城市关键词映射
        self.city_keywords = {
            "北京": ["北京", "beijing"],
            "上海": ["上海", "shanghai"],
            "广州": ["广州", "guangzhou"],
            "深圳": ["深圳", "shenzhen"],
            "杭州": ["杭州", "hangzhou"],
            "成都": ["成都", "chengdu"],
            "武汉": ["武汉", "wuhan"],
            "西安": ["西安", "xian"],
            "南京": ["南京", "nanjing"],
            "天津": ["天津", "tianjin"],
            "重庆": ["重庆", "chongqing"],
            "苏州": ["苏州", "suzhou"],
        }
        
        if self.api_key:
            logger.success("✅ 高德地图工具初始化完成")
        else:
            logger.warning("⚠️ AMAP_API_KEY 未设置，地图功能不可用")
            logger.info("💡 获取API密钥: https://lbs.amap.com/api/webservice/guide/create-project/get-key")
    
    def _extract_city_from_location(self, location: str) -> str:
        """
        从地点名称中提取城市信息
        
        Args:
            location: 地点名称，如"上海大学"、"北京朝阳区"
        
        Returns:
            城市名称，如"上海"、"北京"
        """
        location_lower = location.lower()
        
        for city, keywords in self.city_keywords.items():
            for keyword in keywords:
                if keyword in location_lower or keyword in location:
                    logger.info(f"🏙️ 从地点'{location}'中识别出城市: {city}")
                    return city
        
        logger.warning(f"⚠️ 无法从地点'{location}'中识别城市，将不限制搜索范围")
        return ""
    
    def get_name(self) -> str:
        return "search_nearby"
    
    def get_description(self) -> str:
        return "搜索指定地点附近的场所。当用户询问'XXX附近有什么'、'XXX周边的餐厅'时使用。支持搜索：餐厅、咖啡店、超市、医院等。必须指定location（地点名称，如'上海大学'）和keyword（搜索类型，如'餐厅'）"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "地点名称，如：'上海大学'、'北京大学'、'人民广场'等。AI必须从用户消息中提取具体地点名"
                },
                "keyword": {
                    "type": "string",
                    "description": "搜索类型，如：餐厅、咖啡店、超市、医院等"
                },
                "city": {
                    "type": "string",
                    "description": "城市名称（可选），如：北京、上海。如果能从location中判断出城市，建议提供",
                    "default": ""
                }
            },
            "required": ["location", "keyword"]
        }
    
    async def execute(
        self, 
        location: str = "",
        keyword: str = None,
        type: str = None,  # 兼容参数，AI 可能会传递
        city: str = ""
    ) -> ToolResult:
        """
        执行地点搜索
        
        Args:
            location: 地点名称（如"上海大学"）
            keyword: 搜索关键词（如"餐厅"）
            type: 类型（兼容参数，等同于keyword）
            city: 城市名称（可选）
        
        Returns:
            ToolResult: 搜索结果
        """
        # 兼容多种参数名
        search_keyword = keyword or type
        if not search_keyword:
            return ToolResult(
                success=False,
                message="缺少搜索关键词",
                error="MISSING_KEYWORD"
            )
        
        # 如果没有提供location，给出提示
        if not location:
            return ToolResult(
                success=False,
                message="请提供地点名称，如'上海大学'、'人民广场'等",
                error="MISSING_LOCATION"
            )
        
        # 尝试从location中提取城市信息
        if not city:
            city = self._extract_city_from_location(location)
        if not self.is_available():
            return ToolResult(
                success=False,
                message="地图搜索功能不可用（API密钥未配置）",
                error="API_NOT_CONFIGURED"
            )
        
        try:
            # 组合搜索关键词：location + keyword
            combined_keywords = f"{location} {search_keyword}"
            logger.info(f"🗺️ 高德地图搜索: {combined_keywords} (城市: {city or '未指定'})")
            
            # 构建请求参数
            params = {
                "key": self.api_key,
                "keywords": combined_keywords,
                "types": "",  # 自动识别类型
                "offset": 5,  # 返回5条结果
                "extensions": "base"  # 基础信息
            }
            
            # 如果识别出城市，限制搜索范围
            if city:
                params["city"] = city
                logger.info(f"🏙️ 限制搜索城市: {city}")
            
            # 调用高德地图 POI 搜索 API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/place/text",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "1":  # 成功
                        pois = data.get("pois", [])
                        
                        if not pois:
                            logger.warning("⚠️ 未找到相关地点")
                            return ToolResult(
                                success=True,
                                data={"location": location, "keyword": search_keyword, "results": []},
                                message=f"未找到'{location}'附近的'{search_keyword}'"
                            )
                        
                        # 格式化结果
                        formatted_results = []
                        for idx, poi in enumerate(pois[:5], 1):
                            name = poi.get("name", "未知")
                            address = poi.get("address", "地址未知")
                            distance = poi.get("distance", "")
                            type_name = poi.get("type", "")
                            
                            formatted_results.append({
                                "name": name,
                                "address": address,
                                "distance": distance,
                                "type": type_name
                            })
                        
                        # 构建回复消息
                        city_text = f"（{city}）" if city else ""
                        message_parts = [f"🗺️ '{location}'{city_text}附近的'{search_keyword}'：\n"]
                        
                        for idx, result in enumerate(formatted_results, 1):
                            distance_text = f"（距离: {result['distance']}米）" if result['distance'] else ""
                            message_parts.append(
                                f"{idx}. {result['name']}\n"
                                f"   📍 {result['address']} {distance_text}"
                            )
                        
                        result_message = "\n".join(message_parts)
                        
                        logger.success(f"✅ 高德地图搜索成功，找到 {len(formatted_results)} 个结果")
                        
                        return ToolResult(
                            success=True,
                            data={
                                "location": location,
                                "keyword": search_keyword,
                                "city": city,
                                "results": formatted_results,
                                "count": len(formatted_results)
                            },
                            message=result_message
                        )
                    
                    else:
                        error_info = data.get("info", "未知错误")
                        logger.error(f"❌ 高德地图API错误: {error_info}")
                        return ToolResult(
                            success=False,
                            message=f"地图搜索失败: {error_info}",
                            error="API_ERROR"
                        )
                
                else:
                    logger.error(f"❌ HTTP错误: {response.status_code}")
                    return ToolResult(
                        success=False,
                        message="地图服务暂时不可用",
                        error=f"HTTP_{response.status_code}"
                    )
        
        except httpx.TimeoutException:
            logger.error("❌ 高德地图请求超时")
            return ToolResult(
                success=False,
                message="地图搜索超时，请稍后重试",
                error="TIMEOUT"
            )
        
        except Exception as e:
            logger.error(f"❌ 高德地图搜索失败: {e}")
            return ToolResult(
                success=False,
                message=f"地图搜索失败：{str(e)}",
                error="SEARCH_ERROR"
            )
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        return bool(self.api_key)


# 导出工具实例
amap_tool = AmapTool()

