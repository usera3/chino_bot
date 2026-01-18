"""知识提取器 - 从对话中提取结构化信息"""
from typing import Dict, List, Optional
import json
import re


class KnowledgeExtractor:
    """从对话中提取结构化知识"""
    
    def __init__(self, llm):
        """
        初始化知识提取器
        
        Args:
            llm: 大语言模型
        """
        self.llm = llm
        
        # 提取提示词
        self.extract_prompt = """你是一个信息提取专家。从用户的对话中提取关键信息。

请从以下对话中提取用户的个人信息、偏好、社交关系等结构化数据。

对话内容：
{conversation}

请以 JSON 格式输出提取的信息，格式如下：
{{
    "personal_info": {{
        "name": "用户姓名（如果提到）",
        "email": "邮箱地址（如果提到）",
        "phone": "电话号码（如果提到）",
        "age": "年龄（如果提到）",
        "location": "所在地（如果提到）"
    }},
    "preferences": {{
        "food": ["喜欢的食物"],
        "hobbies": ["兴趣爱好"],
        "dislikes": ["不喜欢的东西"]
    }},
    "social": {{
        "friends": ["朋友名字"],
        "family": ["家人关系"]
    }},
    "facts": [
        "其他重要事实"
    ]
}}

只输出 JSON，不要其他内容。如果某个字段没有信息，设为 null 或空列表。
"""
    
    def extract_knowledge(
        self, 
        user_input: str, 
        bot_response: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        从对话中提取知识
        
        Args:
            user_input: 用户输入
            bot_response: 机器人回复
            user_id: 用户ID
            
        Returns:
            提取的知识字典，如果没有提取到则返回 None
        """
        # 快速判断：是否包含可能的信息
        info_keywords = [
            "我的", "我是", "我叫", "我喜欢", "我不喜欢",
            "邮箱", "电话", "手机", "地址", "住在",
            "朋友", "家人", "爸爸", "妈妈", "兄弟", "姐妹"
        ]
        
        if not any(kw in user_input for kw in info_keywords):
            return None
        
        try:
            # 构建对话文本
            conversation = f"用户: {user_input}\n智乃: {bot_response}"
            
            # 调用 LLM 提取
            prompt = self.extract_prompt.format(conversation=conversation)
            result = self.llm.invoke(prompt)
            
            # 解析 JSON
            content = result.content if hasattr(result, 'content') else str(result)
            
            # 提取 JSON（可能被包裹在 ```json ``` 中）
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            knowledge = json.loads(content)
            
            # 添加元数据
            knowledge['user_id'] = user_id
            knowledge['source'] = 'conversation'
            
            # 过滤空值
            knowledge = self._filter_empty(knowledge)
            
            if self._has_useful_info(knowledge):
                return knowledge
            
            return None
        
        except Exception as e:
            print(f"⚠️ 知识提取失败: {e}")
            return None
    
    def _filter_empty(self, data):
        """过滤空值"""
        if isinstance(data, dict):
            return {
                k: self._filter_empty(v) 
                for k, v in data.items() 
                if v is not None and v != "" and v != [] and v != {}
            }
        elif isinstance(data, list):
            return [self._filter_empty(item) for item in data if item]
        else:
            return data
    
    def _has_useful_info(self, knowledge: Dict) -> bool:
        """判断是否有有用的信息"""
        if not knowledge:
            return False
        
        # 检查是否有非空的字段
        for key, value in knowledge.items():
            if key in ['user_id', 'source']:
                continue
            
            if isinstance(value, dict) and value:
                return True
            elif isinstance(value, list) and value:
                return True
            elif value:
                return True
        
        return False
    
    def format_knowledge(self, knowledge: Dict) -> str:
        """
        将知识格式化为可读文本
        
        Args:
            knowledge: 知识字典
            
        Returns:
            格式化的文本
        """
        lines = []
        
        # 个人信息
        if 'personal_info' in knowledge and knowledge['personal_info']:
            lines.append("【个人信息】")
            for key, value in knowledge['personal_info'].items():
                if value:
                    key_cn = {
                        'name': '姓名',
                        'email': '邮箱',
                        'phone': '电话',
                        'age': '年龄',
                        'location': '所在地'
                    }.get(key, key)
                    lines.append(f"  {key_cn}: {value}")
        
        # 偏好
        if 'preferences' in knowledge and knowledge['preferences']:
            lines.append("【偏好】")
            for key, values in knowledge['preferences'].items():
                if values:
                    key_cn = {
                        'food': '喜欢的食物',
                        'hobbies': '兴趣爱好',
                        'dislikes': '不喜欢的'
                    }.get(key, key)
                    lines.append(f"  {key_cn}: {', '.join(values)}")
        
        # 社交关系
        if 'social' in knowledge and knowledge['social']:
            lines.append("【社交关系】")
            for key, values in knowledge['social'].items():
                if values:
                    key_cn = {
                        'friends': '朋友',
                        'family': '家人'
                    }.get(key, key)
                    lines.append(f"  {key_cn}: {', '.join(values)}")
        
        # 其他事实
        if 'facts' in knowledge and knowledge['facts']:
            lines.append("【其他信息】")
            for fact in knowledge['facts']:
                lines.append(f"  - {fact}")
        
        return "\n".join(lines) if lines else ""
