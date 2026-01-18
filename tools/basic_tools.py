"""基础工具集（伪代码版本）"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ==================== 时间工具 ====================
class GetTimeTool(BaseTool):
    """获取当前时间"""
    name: str = "get_time"
    description: str = "获取当前的日期和时间，当用户询问时间、日期、星期几时使用"
    
    def _run(self) -> str:
        """执行工具"""
        now = datetime.now()
        return f"现在是 {now.strftime('%Y年%m月%d日 %H:%M:%S')}，星期{['一','二','三','四','五','六','日'][now.weekday()]}"
    
    async def _arun(self) -> str:
        """异步执行"""
        return self._run()


# ==================== 天气工具（高德地图 API）====================
class GetWeatherInput(BaseModel):
    """天气查询输入"""
    city: str = Field(description="城市名称，例如：北京、上海、深圳")


class GetWeatherTool(BaseTool):
    """查询天气（高德地图 API）"""
    name: str = "get_weather"
    description: str = "查询指定城市的实时天气情况，包括温度、天气状况、湿度、风力等"
    args_schema: type[BaseModel] = GetWeatherInput
    
    def _run(self, city: str) -> str:
        """执行工具"""
        import os
        import requests
        
        api_key = os.getenv("AMAP_API_KEY")
        if not api_key:
            return "❌ 天气查询功能未配置（缺少 AMAP_API_KEY）"
        
        try:
            # 1. 先获取城市的 adcode（行政区划代码）
            geo_url = "https://restapi.amap.com/v3/geocode/geo"
            geo_params = {
                "key": api_key,
                "address": city,
                "city": city
            }
            
            geo_response = requests.get(geo_url, params=geo_params, timeout=5)
            geo_data = geo_response.json()
            
            if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
                return f"❌ 未找到城市：{city}"
            
            adcode = geo_data["geocodes"][0]["adcode"]
            
            # 2. 使用 adcode 查询天气
            weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
            weather_params = {
                "key": api_key,
                "city": adcode,
                "extensions": "base"  # base=实况天气，all=预报天气
            }
            
            weather_response = requests.get(weather_url, params=weather_params, timeout=5)
            weather_data = weather_response.json()
            
            if weather_data.get("status") != "1" or not weather_data.get("lives"):
                return f"❌ 获取天气失败：{weather_data.get('info', '未知错误')}"
            
            # 3. 解析天气数据
            live = weather_data["lives"][0]
            
            result = f"""📍 {live['province']} {live['city']}
🌡️ 温度：{live['temperature']}°C
☁️ 天气：{live['weather']}
💨 风向：{live['winddirection']}风
🌪️ 风力：{live['windpower']}级
💧 湿度：{live['humidity']}%
📅 更新时间：{live['reporttime']}"""
            
            return result
            
        except Exception as e:
            return f"❌ 天气查询失败：{str(e)}"
    
    async def _arun(self, city: str) -> str:
        """异步执行"""
        return self._run(city)


# ==================== 情感工具（伪代码）====================
class GetEmotionInput(BaseModel):
    """获取情感值输入"""
    user_id: str = Field(description="用户ID")


class GetEmotionTool(BaseTool):
    """获取用户情感值（伪代码）"""
    name: str = "get_emotion"
    description: str = "获取用户的情感值，包括好感度、亲密度、心情等，用于了解与用户的关系"
    args_schema: type[BaseModel] = GetEmotionInput
    
    def _run(self, user_id: str) -> str:
        """执行工具（伪代码）"""
        # TODO: 实际实现需要从数据库读取
        # 这里返回伪数据
        return f"用户 {user_id} 的情感值：好感度 80/100，亲密度 60/100，当前心情：开心"
    
    async def _arun(self, user_id: str) -> str:
        """异步执行"""
        return self._run(user_id)


class UpdateEmotionInput(BaseModel):
    """更新情感值输入"""
    user_id: str = Field(description="用户ID")
    delta: int = Field(description="情感值变化量，正数增加，负数减少，范围 -10 到 +10")
    reason: str = Field(description="变化原因，例如：用户夸奖、用户生气等")


class UpdateEmotionTool(BaseTool):
    """更新用户情感值（伪代码）"""
    name: str = "update_emotion"
    description: str = "更新用户的情感值，当互动愉快时增加，不愉快时减少"
    args_schema: type[BaseModel] = UpdateEmotionInput
    
    def _run(self, user_id: str, delta: int, reason: str) -> str:
        """执行工具（伪代码）"""
        # TODO: 实际实现需要更新数据库
        # 这里返回伪数据
        new_value = 80 + delta  # 假设当前是 80
        return f"已更新用户 {user_id} 的情感值 {delta:+d}（原因：{reason}），当前好感度：{new_value}/100"
    
    async def _arun(self, user_id: str, delta: int, reason: str) -> str:
        """异步执行"""
        return self._run(user_id, delta, reason)


# ==================== 邮件工具（QQ 邮箱 SMTP）====================
class SendEmailInput(BaseModel):
    """发送邮件输入"""
    receiver_email: str = Field(description="收件人邮箱地址，格式：user@example.com 或 QQ号@qq.com")
    subject: str = Field(description="邮件主题，AI 根据用户意图自动生成")
    content: str = Field(description="邮件正文内容，AI 根据用户要求创作完整内容")


class SendEmailTool(BaseTool):
    """发送邮件（QQ 邮箱 SMTP）"""
    name: str = "send_email"
    description: str = """向指定邮箱地址发送邮件。

⚠️ 关键判断：这个工具的唯一作用是"发送邮件"，不是查询、记忆或告知邮箱信息！

✅ 必须同时满足以下条件才能使用：
1. 用户明确使用了"发"、"发送"、"写"等动作词
2. 用户提到了"邮件"或"email"
3. 用户指定了收件人（可以是邮箱地址或人名）

✅ 正确使用场景：
- "发邮件给xxx@qq.com"
- "给xxx发个邮件"
- "帮我写封邮件发给xxx"
- "邮件通知xxx"

❌ 错误使用场景（绝对不要使用）：
- "我的邮箱是xxx@qq.com" → 这是告诉你信息，只需要记住
- "我的邮箱地址是什么" → 这是询问，直接回答即可
- "你记得我的邮箱吗" → 这是询问，直接回答即可
- "xxx的邮箱是什么" → 这是询问，不是要发邮件

AI 的职责（仅在确认要发邮件时）：
- 根据用户的描述，自动生成合适的邮件主题（subject）
- 根据用户的要求，创作完整的邮件内容（content）"""
    args_schema: type[BaseModel] = SendEmailInput
    
    def _run(self, receiver_email: str, subject: str, content: str) -> str:
        """执行工具"""
        import os
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.header import Header
        
        sender_email = os.getenv("QQ_EMAIL_SENDER")
        sender_password = os.getenv("QQ_EMAIL_PASSWORD")
        
        if not sender_email or not sender_password:
            return "❌ 邮件功能未配置（缺少 QQ_EMAIL_SENDER 或 QQ_EMAIL_PASSWORD）"
        
        # 验证邮箱格式
        if "@" not in receiver_email:
            return f"❌ 邮箱地址格式不正确: {receiver_email}"
        
        try:
            # 创建邮件对象
            message = MIMEMultipart()
            message['From'] = sender_email
            message['To'] = receiver_email
            message['Subject'] = Header(subject, 'utf-8')
            
            # 添加邮件正文
            message.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 连接 SMTP 服务器（使用 STARTTLS）
            smtp_server = "smtp.qq.com"
            smtp_port = 587
            
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
            
            # 登录
            server.login(sender_email, sender_password)
            
            # 发送邮件
            server.sendmail(sender_email, [receiver_email], message.as_string())
            
            # 关闭连接
            server.quit()
            
            return f"""✅ 邮件发送成功！
📧 收件人：{receiver_email}
📝 主题：{subject}
📤 发件人：{sender_email}"""
            
        except smtplib.SMTPAuthenticationError:
            return "❌ 邮件发送失败：SMTP 认证错误，请检查邮箱配置"
        
        except smtplib.SMTPException as e:
            return f"❌ 邮件发送失败：{str(e)}"
        
        except Exception as e:
            return f"❌ 邮件发送失败：{str(e)}"
    
    async def _arun(self, receiver_email: str, subject: str, content: str) -> str:
        """异步执行"""
        return self._run(receiver_email, subject, content)


# ==================== 工具列表 ====================
def get_all_tools() -> list[BaseTool]:
    """获取所有工具（基础工具 + LangChain 工具 + QQ 互动工具 + 工作流工具）"""
    from .langchain_tools import get_all_langchain_tools, build_tool_registry
    from .qq_interaction_tools import get_all_qq_interaction_tools
    from .workflow_tool import get_workflow_tool
    
    # 基础工具
    basic_tools = [
        GetTimeTool(),
        GetWeatherTool(),
        GetEmotionTool(),
        UpdateEmotionTool(),
        SendEmailTool(),
    ]
    
    # LangChain 工具
    langchain_tools = get_all_langchain_tools()
    
    # QQ 互动工具
    qq_tools = get_all_qq_interaction_tools()
    
    # 合并（不包括工作流工具，因为它需要工具注册表）
    all_tools = basic_tools + langchain_tools + qq_tools
    
    # 构建工具注册表
    tool_registry = build_tool_registry(all_tools)
    
    # 添加工作流工具（需要工具注册表）
    workflow_tool = get_workflow_tool(tool_registry)
    all_tools.append(workflow_tool)
    print("✅ 已加载: 工作流工具")
    
    return all_tools
