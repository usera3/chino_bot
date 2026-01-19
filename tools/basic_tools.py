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
    attachment_path: Optional[str] = Field(default=None, description="附件文件路径（可选），如果用户要求发送文件，提供文件的完整路径")


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
    
    def _run(self, receiver_email: str, subject: str, content: str, attachment_path: Optional[str] = None) -> str:
        """执行工具"""
        import os
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
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
            
            # 添加附件（如果有）
            attachment_info = ""
            if attachment_path:
                # 检查文件是否存在
                if not os.path.exists(attachment_path):
                    return f"❌ 附件文件不存在: {attachment_path}"
                
                # 读取附件
                with open(attachment_path, 'rb') as f:
                    attachment = MIMEBase('application', 'octet-stream')
                    attachment.set_payload(f.read())
                
                # 编码附件
                encoders.encode_base64(attachment)
                
                # 设置附件文件名
                filename = os.path.basename(attachment_path)
                attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                
                # 添加到邮件
                message.attach(attachment)
                
                # 获取文件大小
                file_size = os.path.getsize(attachment_path)
                file_size_mb = file_size / (1024 * 1024)
                attachment_info = f"\n📎 附件：{filename} ({file_size_mb:.2f} MB)"
            
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
📝 主题：{subject}{attachment_info}
📤 发件人：{sender_email}"""
            
        except smtplib.SMTPAuthenticationError:
            return "❌ 邮件发送失败：SMTP 认证错误，请检查邮箱配置"
        
        except smtplib.SMTPException as e:
            return f"❌ 邮件发送失败：{str(e)}"
        
        except Exception as e:
            return f"❌ 邮件发送失败：{str(e)}"
    
    async def _arun(self, receiver_email: str, subject: str, content: str, attachment_path: Optional[str] = None) -> str:
        """异步执行"""
        return self._run(receiver_email, subject, content, attachment_path)


# ==================== 接收邮件工具（QQ 邮箱 IMAP）====================
class ReceiveEmailInput(BaseModel):
    """接收邮件输入"""
    max_count: int = Field(default=5, description="最多读取的邮件数量，默认 5 封")
    unread_only: bool = Field(default=True, description="是否只读取未读邮件，默认 True")


class ReceiveEmailTool(BaseTool):
    """接收邮件（QQ 邮箱 IMAP）"""
    name: str = "receive_email"
    description: str = """读取收件箱中的邮件。

使用场景：
- 用户说"查看我的邮件"
- 用户说"有没有新邮件"
- 用户说"读一下收件箱"

参数：
- max_count: 最多读取的邮件数量（可选，默认 5）
- unread_only: 是否只读取未读邮件（可选，默认 True）

返回：邮件列表"""
    args_schema: type[BaseModel] = ReceiveEmailInput
    
    def _run(self, max_count: int = 5, unread_only: bool = True) -> str:
        """执行工具"""
        import os
        import imaplib
        import email
        from email.header import decode_header
        
        sender_email = os.getenv("QQ_EMAIL_SENDER")
        sender_password = os.getenv("QQ_EMAIL_PASSWORD")
        
        if not sender_email or not sender_password:
            return "❌ 邮件功能未配置（缺少 QQ_EMAIL_SENDER 或 QQ_EMAIL_PASSWORD）"
        
        try:
            # 连接 IMAP 服务器
            imap_server = "imap.qq.com"
            imap_port = 993
            
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
            mail.login(sender_email, sender_password)
            
            # 选择收件箱
            mail.select("INBOX")
            
            # 搜索邮件
            if unread_only:
                status, messages = mail.search(None, "UNSEEN")
            else:
                status, messages = mail.search(None, "ALL")
            
            if status != "OK":
                return "❌ 搜索邮件失败"
            
            # 获取邮件 ID 列表
            email_ids = messages[0].split()
            
            if not email_ids:
                if unread_only:
                    return "📭 没有未读邮件"
                else:
                    return "📭 收件箱为空"
            
            # 读取所有邮件（先不限制数量，需要按日期排序）
            emails_info = []
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                
                if status != "OK":
                    continue
                
                # 解析邮件
                msg = email.message_from_bytes(msg_data[0][1])
                
                # 解码主题
                subject = ""
                subject_header = msg.get("Subject", "")
                if subject_header:
                    decoded_parts = decode_header(subject_header)
                    for part, encoding in decoded_parts:
                        if isinstance(part, bytes):
                            try:
                                # 处理特殊编码
                                if encoding and encoding.lower() in ['unknown-8bit', 'unknown']:
                                    subject += part.decode("utf-8", errors="ignore")
                                else:
                                    subject += part.decode(encoding or "utf-8", errors="ignore")
                            except (LookupError, UnicodeDecodeError):
                                # 编码失败，尝试常见编码
                                for enc in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                                    try:
                                        subject += part.decode(enc, errors="ignore")
                                        break
                                    except:
                                        continue
                        else:
                            subject += part
                
                # 获取发件人
                from_header = msg.get("From", "")
                
                # 获取日期
                date_header = msg.get("Date", "")
                
                # 解析日期用于排序
                from email.utils import parsedate_to_datetime
                try:
                    date_obj = parsedate_to_datetime(date_header)
                except:
                    # 如果解析失败，使用一个很早的日期
                    from datetime import datetime, timezone
                    date_obj = datetime(1970, 1, 1, tzinfo=timezone.utc)
                
                # 获取邮件正文
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except:
                        body = msg.get_payload()
                
                # 限制正文长度
                if len(body) > 200:
                    body = body[:200] + "..."
                
                emails_info.append({
                    "subject": subject or "(无主题)",
                    "from": from_header,
                    "date": date_header,
                    "date_obj": date_obj,  # 用于排序
                    "body": body or "(无内容)"
                })
            
            # 按日期排序（从新到旧）
            emails_info.sort(key=lambda x: x["date_obj"], reverse=True)
            
            # 限制数量
            emails_info = emails_info[:max_count]
            
            # 关闭连接
            mail.close()
            mail.logout()
            
            # 格式化输出
            if not emails_info:
                return "📭 没有找到邮件"
            
            result = f"📬 收件箱邮件（共 {len(emails_info)} 封）\n\n"
            
            for i, email_info in enumerate(emails_info, 1):
                result += f"【邮件 {i}】\n"
                result += f"📧 主题：{email_info['subject']}\n"
                result += f"👤 发件人：{email_info['from']}\n"
                result += f"📅 时间：{email_info['date']}\n"
                result += f"📝 内容：{email_info['body']}\n"
                result += f"{'-'*50}\n\n"
            
            return result
            
        except imaplib.IMAP4.error as e:
            return f"❌ IMAP 连接失败：{str(e)}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ 接收邮件失败：{str(e)}"
    
    async def _arun(self, max_count: int = 5, unread_only: bool = True) -> str:
        """异步执行"""
        return self._run(max_count, unread_only)


# ==================== 工具列表 ====================
def get_all_tools() -> list[BaseTool]:
    """获取所有工具（基础工具 + LangChain 工具 + QQ 互动工具 + 工作流工具 + 链接解析工具 + HTML 渲染工具）"""
    from .langchain_tools import get_all_langchain_tools, build_tool_registry
    from .qq_interaction_tools import get_all_qq_interaction_tools
    from .workflow_tool import get_workflow_tool
    from .link_resolver_tool import link_resolver_tool
    from .html_render_tool import html_render_tool
    from .image_search_tool import image_search_tool
    
    # 基础工具
    basic_tools = [
        GetTimeTool(),
        GetWeatherTool(),
        GetEmotionTool(),
        UpdateEmotionTool(),
        SendEmailTool(),
        ReceiveEmailTool(),
    ]
    
    # LangChain 工具
    langchain_tools = get_all_langchain_tools()
    
    # QQ 互动工具
    qq_tools = get_all_qq_interaction_tools()
    
    # 链接解析工具
    link_tools = [link_resolver_tool]
    print("✅ 已加载: 链接解析工具")
    
    # HTML 渲染工具
    render_tools = [html_render_tool]
    print("✅ 已加载: HTML 渲染工具")
    
    # 图片搜索工具
    search_tools = [image_search_tool]
    print("✅ 已加载: 图片搜索工具")
    
    # 文件传输工具
    from .file_transfer_tool import get_all_file_transfer_tools
    file_tools = get_all_file_transfer_tools()
    print("✅ 已加载: 文件传输工具")
    
    # 文档处理工具
    from .document_tools import get_all_document_tools
    doc_tools = get_all_document_tools()
    print("✅ 已加载: 文档处理工具")
    
    # 发送文件工具
    from .send_file_tool import get_send_file_tool
    send_file_tools = [get_send_file_tool()]
    print("✅ 已加载: 发送文件工具")
    
    # 网页截图工具
    from .screenshot_tool import get_screenshot_tool
    screenshot_tools = [get_screenshot_tool()]
    print("✅ 已加载: 网页截图工具")
    
    # 文件管理工具
    from .file_management_tool import get_file_management_tools
    file_mgmt_tools = get_file_management_tools()
    print("✅ 已加载: 文件管理工具")
    
    # 系统工具
    from .system_tools import get_system_tools
    system_tools = get_system_tools()
    print("✅ 已加载: 系统工具")
    
    # 代码操作工具
    from .code_tools import get_code_tools
    code_tools = get_code_tools()
    print("✅ 已加载: 代码操作工具")
    
    # 命令执行工具
    from .command_tool import get_command_tool
    command_tool = get_command_tool()
    print("✅ 已加载: 命令执行工具")
    
    # 代码分析工具
    from .analysis_tools import get_analysis_tools
    analysis_tools = get_analysis_tools()
    print("✅ 已加载: 代码分析工具")
    
    # 测试工具
    from .test_tools import get_test_tools
    test_tools = get_test_tools()
    print("✅ 已加载: 测试工具")
    
    # 任务规划工具
    from .planning_tools import get_planning_tools
    planning_tools = get_planning_tools()
    print("✅ 已加载: 任务规划工具")
    
    # 代码修改工具
    from .code_modifier_tools import get_code_modifier_tools
    modifier_tools = get_code_modifier_tools()
    print("✅ 已加载: 代码修改工具")
    
    # 合并（不包括工作流工具，因为它需要工具注册表）
    all_tools = basic_tools + langchain_tools + qq_tools + link_tools + render_tools + search_tools + file_tools + doc_tools + send_file_tools + screenshot_tools + file_mgmt_tools + system_tools + code_tools + [command_tool] + analysis_tools + test_tools + planning_tools + modifier_tools
    
    # 构建工具注册表
    tool_registry = build_tool_registry(all_tools)
    
    # 添加工作流工具（需要工具注册表）
    workflow_tool = get_workflow_tool(tool_registry)
    all_tools.append(workflow_tool)
    print("✅ 已加载: 工作流工具")
    
    return all_tools
