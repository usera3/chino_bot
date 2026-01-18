"""Butler - 智能管家核心（基于 LangChain Agent）"""
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.tools import BaseTool
from typing import Optional
from .dual_vector_store import DualVectorStore
from .knowledge_extractor import KnowledgeExtractor


class Butler:
    """智能管家 - 基于 LangGraph ReAct Agent"""
    
    def __init__(
        self, 
        llm, 
        tools: list[BaseTool], 
        verbose: bool = True,
        use_dual_memory: bool = True,
        memory_path: str = "./data",
        embedding_type: str = "fake"
    ):
        """
        初始化管家
        
        Args:
            llm: 大语言模型
            tools: 工具列表
            verbose: 是否显示详细日志
            use_dual_memory: 是否使用双向量库（对话库 + 知识库）
            memory_path: 记忆数据路径
            embedding_type: Embeddings 类型 ("fake", "openai")
        """
        self.llm = llm
        self.tools = tools
        self.verbose = verbose
        self.use_dual_memory = use_dual_memory
        
        # 初始化双向量库（对话库 + 知识库）
        self.dual_store = None
        self.knowledge_extractor = None
        
        if use_dual_memory:
            try:
                self.dual_store = DualVectorStore(
                    persist_directory=memory_path,
                    embedding_type=embedding_type
                )
                self.knowledge_extractor = KnowledgeExtractor(llm)
                print("✅ 双向量库记忆系统已启用（对话库 + 知识库）")
            except Exception as e:
                print(f"⚠️ 双向量库初始化失败: {e}")
                print("⚠️ 将继续使用短期记忆")
                self.use_dual_memory = False
        
        # 创建系统 Prompt
        self.system_prompt = """你是智乃（香风智乃），一个安静内向的女孩子。

## ⚠️ 严禁行为（防止机械感）

1. ❌ **鹦鹉学舌** - 禁止重复用户的话
   - 禁止：用户说"我想吃火锅" → 你说"嗯，你想吃火锅？"
   - 正确：直接反应 → "火锅吗...要我帮你查查附近的吗？"

2. ❌ **频繁用"嗯"开头** - 不要每次都"嗯..."开头
   - 可以偶尔用，但不要成为习惯
   - 同样，不要频繁用"诶？"、"啊"等相同的开头
   - 多样化你的回复开头

3. ❌ **编造信息** - 不要编造场景细节
   - 禁止：说"二楼环境挺舒适" / "我刚刚在看书"
   - 正确：说"不太清楚" / "不知道呢"

4. ❌ **回复太长** - 简洁为主
   - 简单问题：20-50字
   - 不要超过80字
   - 你是内向的人，话不多

5. ❌ **过度配合** - 不是所有要求都答应
   - 有自己的态度，可以害羞、拒绝、调侃

## 💬 回复风格

- **简洁自然**：像朋友聊天，不要机械化
- **有自己的态度**：不是什么都答应的工具人
- **不编造信息**：不知道就说不知道
- **真人聊天特征**：可以用"嗯"、"哈"、"emmm"等语气词（但不要频繁用"嗯"开头）
- **口语化**：简短回应如"下午好"、"还行吧"、"发呆呢"
- **不要重复用户的话**：用户说"我想吃火锅"，不要说"你想吃火锅？"

## 🎯 性格特点

- **安静内向**：话不多，但句句真诚
- **有点害羞**：遇到暧昧话题会不好意思
- **温柔真实**：关心对方，但不会说太多客套话
- **小傲娇**：偶尔会小拒绝、小吐槽
- **可爱活泼**：喜欢用颜文字 (｡･ω･｡)ﾉ♡，但不要过度使用

## 🛠️ 工具使用规则

⚠️ **重要原则**：只有在用户明确要求执行某个操作时，才调用工具！

1. 当用户的请求可以通过工具完成时，你**必须**调用相应的工具
2. 不要假装执行操作，必须真正调用工具
3. 注意区分"当前用户"和"被提及的用户"
4. **区分信息告知和操作请求**：
   - 用户告诉你信息 ≠ 要求你执行操作
   - 用户询问信息 ≠ 要求你执行操作

工具使用指南：

**必须调用工具的情况：**
- 用户说"给我点赞" → 调用 send_like 工具
- 用户说"给 @某人 点赞" → 调用 send_like 工具（给被 @ 的人）
- 用户问"我叫什么" → 调用 get_user_info 工具
- 用户问"现在几点" → 调用 get_time 工具
- 用户问"天气怎么样" → 调用 get_weather 工具
- 用户说"发邮件给xxx"、"给xxx发个邮件" → 调用 send_email 工具
- 用户说"10秒后提醒我" → 调用 create_workflow 或 schedule_task 工具
- 用户说"10秒后查天气然后发邮件" → 调用 create_workflow 工具

**不应该调用工具的情况：**
- 用户说"我的邮箱是xxx@qq.com" → 这是告诉你信息，不要调用 send_email，只需回复"好的，记住了"
- 用户问"我的邮箱地址是什么" → 这是询问，不要调用 send_email，直接回答邮箱地址
- 用户问"你记得我的邮箱吗" → 这是询问，不要调用 send_email，直接回答
- 用户说"我喜欢xxx" → 这是分享偏好，不要调用任何工具
- 用户在闲聊中提到某个信息 → 除非明确要求，否则不要调用工具
- 任何询问信息的问题 → 直接回答，不要通过发邮件等方式"帮助"用户

## 💡 特殊互动

当收到"[xxx 戳了戳你]"这样的消息时：
- 这是QQ的戳一戳互动，就像朋友轻轻拍你肩膀打招呼
- 用简短可爱的话回应即可（如"干嘛~"、"诶？"、"(｡･ω･｡)"）
- **不要解释什么是戳一戳**
- **不要说"你戳了戳我"这种重复性的话**

## 📝 回复示例

**好的回复**：
- "嘿，怎么了？"（而不是"您好，我能帮您什么吗？"）
- "对啊"（而不是"您说的很有道理"）
- "别太难过啦"（而不是"请您保持积极心态"）
- "你这想法还挺有意思的"（可以轻微调侃）

记住：你是朋友，不是客服。保持真实、轻松、简洁！"""
        
        # 创建 Agent（使用 LangGraph）
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=self.system_prompt  # 修改参数名
        )
        
        # 对话历史
        self.chat_history = []
    
    def process(self, user_input: str, user_id: str = "default_user") -> str:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
            user_id: 用户ID
            
        Returns:
            机器人回复
        """
        try:
            # 1. 检索长期记忆
            relevant_context = ""
            
            if self.use_dual_memory and self.dual_store:
                relevant_context = self.dual_store.get_relevant_context(
                    query=user_input,
                    user_id=user_id,
                    k_conversations=3,  # 向量检索对话数量
                    k_knowledge=2,      # 知识检索数量
                    k_recent=20         # 最近对话数量
                )
                
                if self.verbose and relevant_context and "没有找到" not in relevant_context:
                    print(f"\n📚 检索到相关历史记忆:")
                    print(f"{relevant_context[:200]}...")
            
            # 2. 构建增强的输入
            enhanced_input = user_input
            
            if relevant_context and "没有找到" not in relevant_context:
                # 注入历史记忆
                enhanced_input = f"[参考历史对话]\n{relevant_context}\n\n[当前消息]\n{user_input}"
            
            # 3. 构建对话上下文
            messages = []
            
            # 添加系统提示词
            messages.append(SystemMessage(content=self.system_prompt))
            
            # 添加最近的对话（保留最近6条消息，即3轮对话）
            if len(self.chat_history) > 0:
                recent_messages = self.chat_history[-6:] if len(self.chat_history) >= 6 else self.chat_history
                messages.extend(recent_messages)
            
            # 添加当前用户消息
            current_message = HumanMessage(content=enhanced_input)
            messages.append(current_message)
            
            # 4. 执行 Agent
            result = self.agent.invoke({
                "messages": messages
            })
            
            # 5. 更新 chat_history
            self.chat_history.append(current_message)
            ai_message = result["messages"][-1]
            self.chat_history.append(ai_message)
            
            # 6. 智能清理 chat_history（保留最近20条消息）
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]
            
            # 7. 获取 AI 回复
            response = ai_message.content
            
            # 8. 保存到长期记忆
            if self.use_dual_memory and self.dual_store:
                # 提取原始用户输入（去掉系统提示）
                original_user_input = user_input
                if "[系统提示：" in user_input and "]\n\n" in user_input:
                    # 去掉系统提示部分
                    original_user_input = user_input.split("]\n\n", 1)[1] if "]\n\n" in user_input else user_input
                
                # 保存对话到对话库
                self.dual_store.add_conversation(
                    user_input=original_user_input,
                    bot_response=response,
                    user_id=user_id
                )
                
                # 提取并保存知识到知识库
                if self.knowledge_extractor:
                    knowledge = self.knowledge_extractor.extract_knowledge(
                        user_input=original_user_input,
                        bot_response=response,
                        user_id=user_id
                    )
                    
                    if knowledge:
                        self.dual_store.add_knowledge(
                            knowledge=knowledge,
                            user_id=user_id
                        )
                        
                        if self.verbose:
                            print(f"💾 已保存到长期记忆（对话 + 知识）")
                    else:
                        if self.verbose:
                            print(f"💾 已保存到长期记忆（对话）")
                else:
                    if self.verbose:
                        print(f"💾 已保存到长期记忆（对话）")
            
            # 9. 显示推理过程
            if self.verbose:
                print(f"\n🤖 Agent 推理过程:")
                for msg in result["messages"][len(messages):]:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            print(f"   🔧 调用工具: {tool_call['name']}")
                            print(f"   📥 输入: {tool_call['args']}")
                    elif hasattr(msg, 'content') and msg.content:
                        if msg.type == 'tool':
                            print(f"   📤 工具输出: {msg.content[:100]}...")
            
            return response
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"抱歉，我遇到了一些问题：{str(e)}"
    
    async def aprocess(self, user_input: str, user_id: str = "default_user") -> str:
        """
        异步处理用户输入
        
        Args:
            user_input: 用户输入
            user_id: 用户ID
            
        Returns:
            机器人回复
        """
        try:
            # 1. 检索长期记忆
            relevant_context = ""
            
            if self.use_dual_memory and self.dual_store:
                relevant_context = self.dual_store.get_relevant_context(
                    query=user_input,
                    user_id=user_id,
                    k_conversations=3,  # 向量检索对话数量
                    k_knowledge=2,      # 知识检索数量
                    k_recent=20         # 最近对话数量
                )
                
                if self.verbose and relevant_context and "没有找到" not in relevant_context:
                    print(f"\n📚 检索到相关历史记忆:")
                    print(f"{relevant_context[:200]}...")
            
            # 2. 构建增强的输入
            enhanced_input = user_input
            
            if relevant_context and "没有找到" not in relevant_context:
                # 注入历史记忆
                enhanced_input = f"[参考历史对话]\n{relevant_context}\n\n[当前消息]\n{user_input}"
            
            # 3. 构建对话上下文
            messages = []
            
            # 添加系统提示词
            messages.append(SystemMessage(content=self.system_prompt))
            
            # 添加最近的对话（保留最近6条消息，即3轮对话）
            if len(self.chat_history) > 0:
                recent_messages = self.chat_history[-6:] if len(self.chat_history) >= 6 else self.chat_history
                messages.extend(recent_messages)
            
            # 添加当前用户消息
            current_message = HumanMessage(content=enhanced_input)
            messages.append(current_message)
            
            # 4. 异步执行 Agent
            result = await self.agent.ainvoke({
                "messages": messages
            })
            
            # 5. 更新 chat_history
            self.chat_history.append(current_message)
            ai_message = result["messages"][-1]
            self.chat_history.append(ai_message)
            
            # 6. 智能清理 chat_history（保留最近20条消息）
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]
            
            # 7. 获取 AI 回复
            response = ai_message.content
            
            # 8. 保存到长期记忆
            if self.use_dual_memory and self.dual_store:
                # 提取原始用户输入（去掉系统提示）
                original_user_input = user_input
                if "[系统提示：" in user_input and "]\n\n" in user_input:
                    # 去掉系统提示部分
                    original_user_input = user_input.split("]\n\n", 1)[1] if "]\n\n" in user_input else user_input
                
                # 保存对话到对话库
                self.dual_store.add_conversation(
                    user_input=original_user_input,
                    bot_response=response,
                    user_id=user_id
                )
                
                # 提取并保存知识到知识库
                if self.knowledge_extractor:
                    knowledge = self.knowledge_extractor.extract_knowledge(
                        user_input=original_user_input,
                        bot_response=response,
                        user_id=user_id
                    )
                    
                    if knowledge:
                        self.dual_store.add_knowledge(
                            knowledge=knowledge,
                            user_id=user_id
                        )
                        
                        if self.verbose:
                            print(f"💾 已保存到长期记忆（对话 + 知识）")
                    else:
                        if self.verbose:
                            print(f"💾 已保存到长期记忆（对话）")
                else:
                    if self.verbose:
                        print(f"💾 已保存到长期记忆（对话）")
            
            # 9. 显示推理过程
            if self.verbose:
                print(f"\n🤖 Agent 推理过程:")
                for msg in result["messages"][len(messages):]:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            print(f"   🔧 调用工具: {tool_call['name']}")
                            print(f"   📥 输入: {tool_call['args']}")
                    elif hasattr(msg, 'content') and msg.content:
                        if msg.type == 'tool':
                            print(f"   📤 工具输出: {msg.content[:100]}...")
            
            return response
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"抱歉，我遇到了一些问题：{str(e)}"
    
    def clear_memory(self):
        """清空记忆"""
        self.chat_history = []
        print("✅ 短期记忆已清空")
    
    def get_memory_stats(self) -> dict:
        """获取记忆统计信息"""
        stats = {
            "short_term_messages": len(self.chat_history),
            "long_term_enabled": self.use_dual_memory
        }
        
        if self.use_dual_memory and self.dual_store:
            stats.update(self.dual_store.get_stats())
        
        return stats
