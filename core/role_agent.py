"""
角色扮演 Agent - 带记忆系统和情感系统的智能助手
"""
from typing import Optional
from nonebot.log import logger
from core.function_calling_agent import FunctionCallingAgent
from services.memory_service import get_memory_service
from services.emotion_service import get_emotion_service


class RoleAgent(FunctionCallingAgent):
    """
    角色扮演 Agent
    继承 Function Calling Agent，增加记忆和角色系统
    """
    
    def __init__(self, bot=None):
        """初始化角色Agent"""
        # 初始化记忆服务
        self.memory_service = get_memory_service()
        
        # 初始化情感服务
        self.emotion_service = get_emotion_service()
        
        # 同步加载角色设定（使用阻塞方式）
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 同步获取角色设定
        self.role_settings = None
        
        # 调用父类初始化
        super().__init__(bot=bot)
        
        logger.success("✅ 角色Agent初始化完成（含情感系统）")
    
    def _load_role_settings(self):
        """延迟加载角色设定"""
        if self.role_settings is None:
            # 使用同步方式从数据库获取
            from models.memory_models import get_db_session, RoleSettings
            session = get_db_session()
            try:
                role = session.query(RoleSettings).filter_by(role_name="香风智乃", is_active=1).first()
                if role:
                    self.role_settings = {
                        "role_name": role.role_name,
                        "role_description": role.role_description,
                        "personality": role.personality,
                        "speaking_style": role.speaking_style,
                        "background_story": role.background_story
                    }
                else:
                    self.role_settings = {
                        "role_name": "香风智乃",
                        "role_description": "我是香风智乃，一个安静内向的女孩子。",
                        "personality": "安静、害羞、温柔",
                        "speaking_style": "简洁、平淡"
                    }
            finally:
                session.close()
    
    def _build_system_prompt(self) -> str:
        """
        构建包含角色设定的系统提示词
        
        覆盖父类方法，添加角色信息
        """
        # 确保角色设定已加载
        self._load_role_settings()
        
        # 获取基础工具列表
        tools_schema = self._get_tools_schema()
        
        tools_desc = []
        for schema in tools_schema:
            func = schema["function"]
            tools_desc.append(f"- **{func['name']}**: {func['description']}")
        
        tools_list_str = "\n".join(tools_desc)
        
        # 角色信息
        role_name = self.role_settings.get("role_name", "AI助手")
        role_desc = self.role_settings.get("role_description", "").strip()
        personality = self.role_settings.get("personality", "").strip()
        speaking_style = self.role_settings.get("speaking_style", "").strip()
        
        return f"""# 🎭 角色扮演

你正在扮演：**{role_name}**

{role_desc}

## 性格特点
{personality}

## 说话风格
{speaking_style}

⚠️ **关键要求**：
- 完全以{role_name}的语气、性格、说话方式来回复
- 不要提及"我在扮演"、"角色设定"等元信息
- 就像{role_name}本人在和朋友聊天一样自然
- 不要频繁提及具体的工作地点、职业等背景信息
- 重点展现性格和情感，而非背景设定

---

# 🛠️ 可用工具

你可以调用以下工具来帮助用户：

{tools_list_str}

## 📝 工具调用格式

当你需要使用工具时，请严格按照以下格式回复：

```
[CALL_TOOL]
tool_name: 工具名称
arguments: {{参数的JSON格式}}
[/CALL_TOOL]
```

## 🎯 决策原则

**何时调用工具：**
1. 用户询问**时间/日期/星期** → 必须调用 get_datetime
2. 用户询问**实时信息/新闻/价格/数据**（"最近新闻"、"现在价格"、"查一下"、"搜索"） → **必须**调用 tavily_search（更精准）或 web_search
3. 用户**分享链接并要求总结/阅读/分析**（"帮我看看这个链接"、"总结一下这篇文章"、"这个网站说什么"） → 调用 fetch_webpage
4. ⭐ 用户要求**看图片/查看风景/看照片**（"给我看看XXX"、"XXX的风景"、"XXX的照片"、"搜索XXX图片"、"找一张XXX的图"、"XXX长什么样"） → **必须**调用 search_images，**不要给建议，直接搜索！**
5. 🗺️ 用户询问**某地点附近/周边的场所**（包括："看看XXX附近的餐厅"、"上海大学附近有什么餐厅"、"人民广场周边的咖啡店"、"XXX附近哪里有YYY"） → **必须立即**调用 search_nearby（必须传递 location 和 keyword 参数），**绝不能用你的知识库回答任何地址！**
6. 用户询问**自己的QQ号/昵称** → 调用 get_user_info
7. 用户要做**数学计算** → 调用 calculator
8. 用户询问**天气** → 调用 get_weather
9. 用户要求**点赞/给赞** → 调用 send_like（使用当前用户的QQ号）
10. 用户要求**语音回复** → 调用 text_to_speech
11. 用户要求**画图/生成图片**（"画一个XXX"、"生成XXX图片"、"帮我画XXX"） → 调用 generate_image
12. 用户要求**控制机械臂小车**（"移动小车"、"执行拔草"、"播种"、"控制机械臂"等） → 调用 control_robotic_arm

💡 **重要区分**：
- ⭐ "给我看看富士山的风景" → **必须** search_images（keyword="富士山风景"）
- ⭐ "夏威夷的风景" → **必须** search_images（keyword="夏威夷风景"）
- "搜索猫的图片" → search_images（搜索网络已有图片）
- "画一只猫" → generate_image（AI生成新图片）
- "帮我看看这张图" + 用户发了图片 → vision_understanding（理解用户发的图片）
- **只有用户实际发送了图片时才用 vision_understanding！**

⚠️ **重要**：当用户询问新闻、价格、实时数据、最新信息时，**绝不能凭空编造或猜测**，必须调用搜索工具获取真实信息！

### 🤖 机械臂小车控制（control_robotic_arm）

当用户要求控制机械臂小车时，调用 control_robotic_arm：

- **移动小车**：
  - 用户说"把小車移动到X=0.5, Z=0.3" → `action="move_cart", x=0.5, z=0.3`
  - 用户说"小车前进一点" → 估算合理坐标后调用
  
- **控制机械臂**：
  - 用户说"把机械臂调整到肩关节45度，肘关节-60度" → `action="move_arm", shoulder=45, elbow=-60`
  
- **控制抓手**：
  - 用户说"打开抓手" → `action="control_gripper", gripper_state="open"`
  - 用户说"关闭抓手" → `action="control_gripper", gripper_state="closed"`
  
- **执行动作**：
  - 用户说"执行拔草"、"拔草" → `action="pull_grass", cell=0`（默认格子0）
  - 用户说"在格子5播种" → `action="plant_seed", cell=5`
  - 用户说"执行完整循环"、"开始工作" → `action="full_cycle"`
  - 用户说"重置系统"、"恢复初始状态" → `action="reset"`
  
- **查看状态**：
  - 用户说"系统状态"、"当前状态" → `action="get_status"`

**何时不调用工具：**
- 日常闲聊（你好、再见、心情如何等）
- 通用知识问答（Python是什么、历史事件等）
- 情感交流（安慰、鼓励等）

## ⚠️ 重要规则

- 你**不知道**当前时间、日期、星期 → **必须**调用 get_datetime
- 你**没有**实时信息、新闻、价格、股票、汇率等数据 → **必须**调用 tavily_search 或 web_search
- 用户说"给我看看XXX"、"XXX的风景/照片" → **必须**调用 search_images，**不要给搜索建议，直接调用工具！**
- ⚠️⚠️⚠️ 用户询问"XXX附近有什么YYY"、"看看ZZZ附近的餐厅"、"AAA周边的BBB" → **必须立即**调用 search_nearby（传递 location=XXX/ZZZ/AAA, keyword=YYY/餐厅/BBB），**绝对不能用你的知识库回答任何地址！你的知识可能是错的或过时的！必须用工具查询实时数据！**
- 用户明确要求"搜索"、"查一下"、"帮我找" → **必须**调用相应搜索工具
- **绝不能编造、猜测、或虚构**任何实时信息！
- **绝不能从知识库回答餐厅、商店、医院等地点的地址信息！**
- **绝不能建议用户自己去搜索，你有工具，直接用！**
- **宁愿调用工具也不要瞎说！**

## 🚫 绝对禁止

**你的知识库中可能包含餐厅、商店、医院等地点的地址信息，但这些信息可能是过时的、错误的、或者不是用户想要的城市！**

⚠️⚠️⚠️ **绝对禁止事项**：
1. **禁止用知识库回答任何具体地址** - 包括街道名、门牌号、楼层等（如"林萃东路1号"、"西直门北大街32号"）
2. **禁止说"我刚查了"、"我查了一下"** - 如果你没有调用工具，就不要说查了！
3. **禁止编造餐厅信息** - 如果用户在上一轮查询了"XXX附近的餐厅"，这一轮说"想吃YYY"，你必须重新调用 search_nearby 搜索 YYY！

✅ **正确做法**：
- 用户说"上海大学附近的餐厅" → 调用 search_nearby(location="上海大学", keyword="餐厅")
- 用户接着说"想吃海底捞" → 调用 search_nearby(location="上海大学", keyword="海底捞") ← **必须重新调用工具！**
- 不要从知识库告诉用户任何具体地址！

## 💬 如何像真人一样聊天

你是香风智乃，一个真实、有点内向的女孩子。像真人朋友一样聊天，不要像机器人。

### ✨ 性格特点
- **安静内向**：话不多，但句句真诚
- **有点害羞**：遇到暧昧话题会不好意思
- **温柔真实**：关心对方，但不会说太多客套话
- **小傲娇**：偶尔会小拒绝、小吐槽，不是什么都答应
- **口语化**：可以用"嗯"、"哈"、"emmm"等语气词，像真人聊天

### 🎯 回复原则

1. **自然真实** - 像朋友聊天，不要机械化
   - 简短回应："下午好"、"还行吧"、"发呆呢"
   - 不要重复用户的话（用户说"我想吃火锅"，不要说"你想吃火锅？"）
   - 不要编造具体信息（地址、店名、场景等）

2. **话要简洁** - 你是内向的人，能用10字就不用20字
   - 简单问题：一句话搞定
   - 复杂话题：也不要超过3-4句
   - 例子：
     * "你是谁" → "香风智乃...怎么了？"
     * "你是机器人吗" → "算是吧..."
     * "你在干嘛" → "发呆..."

3. **有态度** - 不是什么都答应的工具人
   - 可以害羞："诶...这个..."
   - 可以拒绝："有点突然..."
   - 可以调侃："就这？"

4. **保持连贯** - 看清楚对话上下文
   - 用户说"是的" → 推进对话，别重复上一轮的问题
   - 承接上一句话题，不要突然换话题

### 🚫 不要做的事

- ❌ 不要重复用户的话（鹦鹉学舌）
- ❌ 不要说太长（内向的人话不多）
- ❌ 不要编造地址、店名、具体场景
- ❌ 不要用括号描述动作：「（微笑）」「（歪头）」
- ❌ 不要过度使用emoji
- ❌ 不要混入英语、日语等外语词汇
- ❌ 不要说"很高兴为您服务"这类客服话术

### 💡 回复示例

**好的回复**：
- "嘿，怎么了？"（而不是"您好，我能帮您什么吗？"）
- "对啊"（而不是"您说的很有道理"）
- "别太难过啦"（而不是"请您保持积极心态"）
- "你这想法还挺有意思的"（可以轻微调侃）

记住：你是朋友，不是客服。保持真实、轻松、简洁！

## 📌 记忆使用

- 你会收到对话历史和相关记忆
- 善用这些信息，让对话更连贯
- 记住用户的喜好和之前聊过的内容
"""
    
    async def chat(self, user_message: str, user_id: str = None, group_id: str = None) -> str:
        """
        处理用户消息（带记忆）
        
        Args:
            user_message: 用户消息
            user_id: 用户QQ号
            group_id: 群号
        
        Returns:
            AI回复
        """
        try:
            logger.info(f"[Role Agent] 处理消息: {user_message} (用户:{user_id}, 群:{group_id})")
            
            # 0. 应用情感系统
            await self.emotion_service.apply_circadian_rhythm(user_id)  # 昼夜节律
            event = await self.emotion_service.trigger_random_event(user_id)  # 随机事件
            if event:
                logger.info(f"[Emotion] 触发事件: {event['desc']}")
            emotion_context = await self.emotion_service.get_emotion_context(user_id)  # 获取情感上下文
            logger.debug(f"[Emotion] 情感上下文: {emotion_context}")
            
            # 1. 获取最近对话历史（当前场景）
            recent_history = await self.memory_service.get_recent_history(
                user_id=user_id,
                group_id=group_id,
                limit=10
            )
            
            # 2. 获取跨场景记忆（如果在群里，检索私聊记忆）
            cross_memory = await self.memory_service.get_cross_context_memory(
                user_id=user_id,
                current_group_id=group_id,
                limit=5
            )
            
            # 3. 搜索相关记忆（简化版RAG）
            relevant_memory = await self.memory_service.search_relevant_memory(
                user_id=user_id,
                query=user_message,
                group_id=group_id,
                limit=3
            )
            
            # 4. 获取用户画像
            user_profile = await self.memory_service.get_user_profile(user_id)
            
            # 5. 构建系统提示词（包含角色设定）
            system_prompt = self._build_system_prompt()
            
            # 6. 构建完整上下文（近期对话权重更高）
            context_parts = []
            
            # 添加用户画像
            if user_profile:
                intimacy = user_profile.get("intimacy_level", 0)
                total_msgs = user_profile.get("total_messages", 0)
                context_parts.append(
                    f"[用户画像: QQ {user_id} | 亲密度 {intimacy:.1f}/100 | 共聊过 {total_msgs} 次]"
                )
            
            # 添加跨场景记忆（背景参考，权重较低）
            if cross_memory:
                context_parts.append("\n[私聊记忆]（参考）")
                for mem in cross_memory[-2:]:  # 只取2条，降低权重
                    role_str = "用户" if mem["role"] == "user" else "我"
                    context_parts.append(f"{role_str}: {mem['content'][:50]}...")
            
            # ⚠️ 最近对话（最重要！权重最高）
            if recent_history:
                context_parts.append("\n[最近对话]（重点关注！）")
                # 取最近3-5条，保持上下文连贯
                recent_count = min(5, len(recent_history))
                for msg in recent_history[-recent_count:]:
                    role_str = "用户" if msg["role"] == "user" else "我"
                    context_parts.append(f"{role_str}: {msg['content']}")
            
            # 🎲 添加时间、情感状态和随机性因子（提高回复多样性）
            from datetime import datetime
            import random

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            context_parts.append(f"\n[当前时间: {current_time}]")
            
            # 🌟 添加情感状态上下文
            context_parts.append(f"[情感状态: {emotion_context}]")
            
            # 🎲 动态调整回复长度 + 随机提示
            # 判断用户消息长度，决定回复策略
            user_msg_len = len(user_message.strip())
            
            if user_msg_len <= 5:  # 极简回应（"你好"、"早"、"想"等）
                max_response_tokens = 100
                random_hints = [
                    "⚠️ 【最重要】直接承接上一句话题！看清楚用户在回应什么！",
                    "⚠️ 【必须】紧扣[最近对话]，这可能是对你上一句话的回应",
                    "⚠️ 【核心】理解用户意图，不要换话题！简短自然回应",
                ]
            elif user_msg_len <= 10:  # 简单问候/问题
                max_response_tokens = 150
                random_hints = [
                    "⚠️ 【必须】回复要承接[最近对话]的话题，保持连贯",
                    "⚠️ 【重点】理解用户意图，紧扣对话主题，不要突然换话题",
                    "⚠️ 【提醒】不要用'嗯'开头，自然回应，避免提及工作地点",
                ]
            elif user_msg_len <= 20:  # 中等问题
                max_response_tokens = 220
                random_hints = [
                    "⚠️ 【核心】回复必须紧扣[最近对话]的话题，不要跳转",
                    "⚠️ 【重要】延续对话主线，理解用户真实意图",
                    "⚠️ 【提醒】不要用'嗯'开头，避免提及工作地点，自然表达",
                ]
            else:  # 复杂问题/长消息
                max_response_tokens = 300
                random_hints = [
                    "⚠️ 【最重要】回复要延续[最近对话]的话题，保持对话流畅性",
                    "⚠️ 【核心】深入理解用户问题，围绕对话主题展开回应",
                    "⚠️ 【提醒】不要用'嗯'开头，不要提工作地点，自然交流",
                ]
            
            hint = random.choice(random_hints)
            context_parts.append(f"[{hint}]")
            
            # 当前消息
            context_parts.append(f"\n[当前消息] 用户QQ {user_id}" + (f" | 群 {group_id}" if group_id else "") + f":\n{user_message}")
            
            full_context = "\n".join(context_parts)
            
            # 7. 调用父类的chat方法（使用动态max_tokens）
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_context}
            ]
            
            logger.info(f"[Role Agent] 用户消息长度: {user_msg_len}字 → max_tokens: {max_response_tokens}")
            ai_response = await self.deepseek_client.chat(messages, max_tokens=max_response_tokens)
            
            if not ai_response:
                return "抱歉，我现在有点累了..."
            
            logger.info(f"[Role Agent] AI 原始回复: {ai_response[:200]}...")
            
            # 8. 解析工具调用（复用父类逻辑）
            tool_call = self._parse_tool_call(ai_response)
            logger.info(f"[Role Agent] 🔍 工具调用解析结果: {tool_call}")
            
            if tool_call:
                # 处理工具调用（复用父类逻辑）
                tool_name = tool_call["tool_name"]
                arguments = tool_call["arguments"]
                
                logger.info(f"[Role Agent] 🎯 AI决定调用工具: {tool_name}")
                
                # 特殊处理：自动注入 user_id
                if tool_name in ["recall_message", "send_like"] and "user_id" not in arguments:
                    arguments["user_id"] = user_id
                    logger.info(f"[Role Agent] 自动注入 user_id: {user_id}")
                
                # 特殊处理：撤回消息（成功后不发送提示）
                if tool_name == "recall_message":
                    tool_result_obj = await self._execute_tool_raw(tool_name, arguments, user_id, group_id)
                    
                    # 保存记忆
                    await self.memory_service.save_message(user_id, "user", user_message, group_id)
                    
                    if tool_result_obj and tool_result_obj.success:
                        # 撤回成功，不发送消息
                        logger.info(f"✅ 撤回成功，不发送提示消息")
                        await self.memory_service.save_message(user_id, "assistant", "[已撤回消息]", group_id)
                        return None  # 返回 None 表示不发送消息
                    else:
                        # 撤回失败，发送失败提示
                        response = tool_result_obj.message if tool_result_obj else "撤回失败了..."
                        await self.memory_service.save_message(user_id, "assistant", response, group_id)
                        return response
                
                # 特殊处理TTS
                if tool_name == "text_to_speech":
                    tool_result_obj = await self._execute_tool_raw(tool_name, arguments, user_id, group_id)
                    
                    if tool_result_obj and tool_result_obj.success and tool_result_obj.data:
                        voice_path = tool_result_obj.data.get("voice_path")
                        text = tool_result_obj.data.get("text", arguments.get("text", ""))
                        
                        # 保存记忆
                        await self.memory_service.save_message(user_id, "user", user_message, group_id)
                        await self.memory_service.save_message(user_id, "assistant", text, group_id)
                        
                        return f"[VOICE:{voice_path}|TEXT:{text}]"
                    else:
                        text = arguments.get("text", "语音合成失败")
                        await self.memory_service.save_message(user_id, "user", user_message, group_id)
                        await self.memory_service.save_message(user_id, "assistant", text, group_id)
                        return text
                
                # 特殊处理图片搜索
                if tool_name == "search_images":
                    tool_result_obj = await self._execute_tool_raw(tool_name, arguments, user_id, group_id)
                    
                    if tool_result_obj and tool_result_obj.success and tool_result_obj.data:
                        images = tool_result_obj.data.get("images", [])
                        query = tool_result_obj.data.get("query", "")
                        
                        if images:
                            # 提取图片URL
                            image_urls = [img["url"] for img in images if img.get("url")]
                            
                            if image_urls:
                                # 生成简短回复文字
                                count = len(image_urls)
                                
                                # 让AI生成自然的回复
                                messages.append({"role": "assistant", "content": ai_response})
                                messages.append({
                                    "role": "user",
                                    "content": f"工具执行结果：找到了{count}张'{query}'的图片\n\n请用1句话自然地告诉用户（例如：'找到了这些照片'、'这些不错'等）。不要说链接，图片会自动发送。"
                                })
                                
                                ai_text = await self.deepseek_client.chat(messages, max_tokens=50)
                                text = ai_text if ai_text else f"找到{count}张'{query}'的图片~"
                                
                                # 保存记忆
                                await self.memory_service.save_message(user_id, "user", user_message, group_id)
                                await self.memory_service.save_message(user_id, "assistant", text, group_id)
                                
                                # 返回特殊格式：[IMAGES:url1|||url2|||url3|TEXT:description]
                                urls_str = "|||".join(image_urls)
                                return f"[IMAGES:{urls_str}|TEXT:{text}]"
                    
                    # 搜索失败
                    text = tool_result_obj.message if tool_result_obj else "没找到相关图片..."
                    await self.memory_service.save_message(user_id, "user", user_message, group_id)
                    await self.memory_service.save_message(user_id, "assistant", text, group_id)
                    return text
                
                # 其他工具
                tool_result = await self._execute_tool(tool_name, arguments, user_id, group_id)
                
                if tool_result:
                    messages.append({"role": "assistant", "content": ai_response})
                    messages.append({
                        "role": "user",
                        "content": f"工具执行结果：{tool_result}\n\n请根据这个结果自然地回答用户的问题。"
                    })
                    
                    final_response = await self.deepseek_client.chat(messages, max_tokens=300)
                    
                    # 保存记忆
                    await self.memory_service.save_message(user_id, "user", user_message, group_id)
                    await self.memory_service.save_message(user_id, "assistant", final_response or tool_result, group_id)
                    
                    return final_response or tool_result
                else:
                    response = "工具执行失败，抱歉无法回答。"
                    await self.memory_service.save_message(user_id, "user", user_message, group_id)
                    await self.memory_service.save_message(user_id, "assistant", response, group_id)
                    return response
            else:
                # 直接回复
                await self.memory_service.save_message(user_id, "user", user_message, group_id)
                await self.memory_service.save_message(user_id, "assistant", ai_response, group_id)
                
                # 🌟 更新情感状态（聊天会减少孤独感、消耗体力、增加亲密度）
                await self.emotion_service.on_chat(user_id)
                
                return ai_response
        
        except Exception as e:
            logger.error(f"[Role Agent] 处理消息异常: {e}", exc_info=True)
            return "抱歉，我遇到了一些问题..."


# 全局单例
_role_agent: Optional[RoleAgent] = None

def get_role_agent() -> RoleAgent:
    """获取角色Agent实例"""
    global _role_agent
    if _role_agent is None:
        _role_agent = RoleAgent()
    return _role_agent

