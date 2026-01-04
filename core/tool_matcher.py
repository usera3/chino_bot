"""
工具匹配器 - 基于关键词树的智能工具匹配
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from nonebot.log import logger


@dataclass
class ToolMatch:
    """工具匹配结果"""
    tool_name: str
    confidence: float  # 置信度 0-1
    matched_keywords: List[str]  # 匹配到的关键词
    priority: int  # 优先级（数字越小越优先）


class ToolMatcher:
    """基于关键词的工具匹配器"""
    
    def __init__(self):
        """初始化工具匹配规则"""
        # 工具关键词库
        # 格式: {工具名: {"keywords": [...], "priority": int, "require_all": bool}}
        self.tool_rules = {
            # 时间日期工具 - 最高优先级
            "get_datetime": {
                "keywords": [
                    "几点", "时间", "星期", "几号", "日期", "今天", "现在",
                    "今日", "当前时间", "什么时候", "几月", "几年", "周几",
                    "今天是", "现在是", "今年", "今天几号", "今天星期"
                ],
                "priority": 1,
                "require_all": False  # 匹配任一关键词即可
            },
            
            # 网络搜索工具
            "web_search": {
                "keywords": [
                    "搜索", "查询", "查找", "查一下", "找一下",
                    "最新", "新闻", "头条", "热点", "热搜",
                    "价格", "指数", "汇率", "股票", "行情", "多少钱",
                    "道琼斯", "比特币", "今日", "实时",
                    "发生了什么", "有什么消息", "最近怎么样"
                ],
                "priority": 2,
                "require_all": False
            },
            
            # 用户信息工具
            "get_user_info": {
                "keywords": [
                    "我的qq", "我的QQ", "我的昵称", "我叫什么", "我是谁",
                    "我的号", "我的账号", "个人信息", "我的名字",
                    "群名", "群叫什么", "这个群", "群信息"
                ],
                "priority": 3,
                "require_all": False
            },
            
            # 群成员列表工具
            "get_group_members": {
                "keywords": [
                    "群成员", "群里有谁", "成员列表", "谁在群里",
                    "群友", "有哪些人", "多少人", "群里都有谁"
                ],
                "priority": 3,
                "require_all": False
            },
            
            # 计算器工具
            "calculator": {
                "keywords": [
                    "计算", "算", "等于", "多少", "加", "减", "乘", "除",
                    "+", "-", "*", "/", "×", "÷", "=", "求和", "平方"
                ],
                "priority": 4,
                "require_all": False,
                "need_numbers": True  # 需要包含数字
            },
            
            # 天气工具
            "get_weather": {
                "keywords": [
                    "天气", "气温", "温度", "下雨", "晴天", "阴天",
                    "冷不冷", "热不热", "穿什么", "天气预报"
                ],
                "priority": 5,
                "require_all": False
            }
        }
        
        # 构建快速查找表（关键词 -> 工具列表）
        self.keyword_to_tools: Dict[str, List[str]] = {}
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """构建关键词索引"""
        for tool_name, rule in self.tool_rules.items():
            for keyword in rule["keywords"]:
                if keyword not in self.keyword_to_tools:
                    self.keyword_to_tools[keyword] = []
                self.keyword_to_tools[keyword].append(tool_name)
        
        logger.info(f"[ToolMatcher] 已索引 {len(self.keyword_to_tools)} 个关键词")
    
    def match(self, user_input: str, top_k: int = 3) -> List[ToolMatch]:
        """
        匹配用户输入到工具
        
        Args:
            user_input: 用户输入文本
            top_k: 返回最多top_k个匹配结果
        
        Returns:
            匹配结果列表，按置信度排序
        """
        user_input_lower = user_input.lower()
        
        # 统计每个工具的匹配情况
        tool_scores: Dict[str, Dict] = {}
        
        # 遍历所有关键词，查找匹配
        for keyword, tool_list in self.keyword_to_tools.items():
            if keyword in user_input_lower:
                for tool_name in tool_list:
                    if tool_name not in tool_scores:
                        tool_scores[tool_name] = {
                            "matched_keywords": [],
                            "score": 0
                        }
                    
                    tool_scores[tool_name]["matched_keywords"].append(keyword)
                    # 关键词越长，权重越高（避免误匹配）
                    weight = len(keyword)
                    tool_scores[tool_name]["score"] += weight
        
        # 特殊检查：计算器需要包含数字
        if "calculator" in tool_scores:
            rule = self.tool_rules["calculator"]
            if rule.get("need_numbers"):
                if not any(c.isdigit() for c in user_input):
                    # 没有数字，移除计算器匹配
                    del tool_scores["calculator"]
        
        # 特殊规则：如果同时匹配到时间和搜索工具，检查是否包含实时数据关键词
        if "get_datetime" in tool_scores and "web_search" in tool_scores:
            realtime_keywords = ["价格", "指数", "汇率", "股票", "行情", "多少钱", "值多少", "比特币", "道琼斯"]
            if any(kw in user_input_lower for kw in realtime_keywords):
                # 包含实时数据关键词，优先搜索工具
                del tool_scores["get_datetime"]
                logger.info(f"[ToolMatcher] 检测到实时数据查询，调整为搜索工具")
        
        # 转换为 ToolMatch 对象
        matches = []
        for tool_name, data in tool_scores.items():
            rule = self.tool_rules[tool_name]
            
            # 计算置信度（新算法）
            matched_count = len(data["matched_keywords"])
            total_score = data["score"]
            
            # 置信度计算：
            # 1. 基础分：匹配到关键词就有 0.3 的基础分
            # 2. 数量分：每多匹配一个关键词增加 0.1
            # 3. 长度分：关键词总长度越长，权重越高（最多 0.4）
            base_confidence = 0.3
            count_bonus = min(0.3, matched_count * 0.1)
            length_bonus = min(0.4, total_score / 20)  # 平均5字符的关键词得0.1分
            
            confidence = min(1.0, base_confidence + count_bonus + length_bonus)
            
            matches.append(ToolMatch(
                tool_name=tool_name,
                confidence=confidence,
                matched_keywords=data["matched_keywords"],
                priority=rule["priority"]
            ))
        
        # 排序：优先级 > 置信度
        matches.sort(key=lambda x: (x.priority, -x.confidence))
        
        return matches[:top_k]
    
    def get_best_match(self, user_input: str, threshold: float = 0.3) -> Optional[ToolMatch]:
        """
        获取最佳匹配工具
        
        Args:
            user_input: 用户输入
            threshold: 置信度阈值（低于此值则不返回）
        
        Returns:
            最佳匹配，如果没有超过阈值则返回 None
        """
        matches = self.match(user_input, top_k=1)
        
        if matches and matches[0].confidence >= threshold:
            logger.info(
                f"[ToolMatcher] 匹配到工具: {matches[0].tool_name} "
                f"(置信度: {matches[0].confidence:.2f}, "
                f"关键词: {matches[0].matched_keywords})"
            )
            return matches[0]
        
        return None
    
    def explain_match(self, user_input: str) -> str:
        """
        解释匹配结果（用于调试）
        
        Args:
            user_input: 用户输入
        
        Returns:
            匹配结果的详细说明
        """
        matches = self.match(user_input, top_k=5)
        
        if not matches:
            return "❌ 未匹配到任何工具"
        
        result = f"🔍 用户输入: \"{user_input}\"\n\n匹配结果:\n"
        for i, match in enumerate(matches, 1):
            result += (
                f"{i}. 工具: {match.tool_name}\n"
                f"   置信度: {match.confidence:.2%}\n"
                f"   优先级: {match.priority}\n"
                f"   匹配关键词: {', '.join(match.matched_keywords)}\n\n"
            )
        
        return result


# 全局单例
_tool_matcher: Optional[ToolMatcher] = None

def get_tool_matcher() -> ToolMatcher:
    """获取全局工具匹配器实例"""
    global _tool_matcher
    if _tool_matcher is None:
        _tool_matcher = ToolMatcher()
    return _tool_matcher

