"""
聊天插件 - 集成 Butler Agent
"""
import os
from nonebot import on_message, get_driver
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.rule import to_me
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from core.butler import Butler
from tools.basic_tools import get_all_tools

# 加载环境变量
load_dotenv()

# 全局 Butler 实例
butler = None

# 在启动时初始化 Butler
@get_driver().on_startup
async def init_butler():
    """初始化 Butler"""
    global butler

    print("\n" + "=" * 60)
    print("🧠 初始化 Butler Agent...")
    print("=" * 60)

    try:
        # 设置代理（如果启用）
        use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
        if use_proxy:
            http_proxy = os.getenv("HTTP_PROXY", "")
            https_proxy = os.getenv("HTTPS_PROXY", "")

            if http_proxy and https_proxy:
                os.environ['http_proxy'] = http_proxy
                os.environ['https_proxy'] = https_proxy
                print(f"✅ 代理已启用:")
                print(f"   HTTP:  {http_proxy}")
                print(f"   HTTPS: {https_proxy}")
            else:
                print("⚠️  代理配置不完整，跳过")
        else:
            print("ℹ️  代理未启用")

        # 初始化 LLM（使用环境变量中的模型配置）
        model_name = os.getenv("DEEPSEEK_MODEL", "mistral-small-latest")
        llm = ChatOpenAI(
            model=model_name,
            temperature=0.7,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.mistral.ai/v1")
        )
        print(f"✅ LLM 初始化成功: {model_name}")

        # 获取工具
        tools = get_all_tools()
        print(f"✅ 已加载 {len(tools)} 个工具")

        # 创建 Butler
        butler = Butler(
            llm=llm,
            tools=tools,
            verbose=True,  # 开发阶段显示详细日志
            use_dual_memory=True,  # 启用双向量库记忆（对话库 + 知识库）
            embedding_type="fake"  # 使用改进的 FakeEmbeddings（基于 TF-IDF）
        )
        print("✅ Butler 初始化成功！")

        # 初始化定时任务工具
        try:
            from nonebot import require
            scheduler = require("nonebot_plugin_apscheduler").scheduler

            from tools.scheduler_tool import init_scheduler
            # 注意：这里暂时传 None，因为 bot 实例在消息处理时才有
            init_scheduler(scheduler, None)
            print("✅ 定时任务工具初始化成功")
        except Exception as e:
            print(f"⚠️ 定时任务工具初始化失败: {e}")

        print("=" * 60)
        print()

    except Exception as e:
        print(f"❌ Butler 初始化失败: {e}")
        import traceback
        traceback.print_exc()


# 创建调试处理器（记录所有消息，不阻断）
debug_handler = on_message(priority=1, block=False)

@debug_handler.handle()
async def log_all_messages(event: MessageEvent):
    """记录所有消息用于调试"""
    chat_type = "群聊" if isinstance(event, GroupMessageEvent) else "私聊"
    group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
    user_id = event.user_id
    text = event.get_plaintext().strip()

    # 检查是否 @ 了机器人
    is_tome = False
    for seg in event.message:
        if seg.type == "at":
            at_qq = seg.data.get("qq")
            if at_qq == str(event.self_id):
                is_tome = True
                break

    print(f"[DEBUG] 收到消息 [{chat_type}] 用户:{user_id} 群:{group_id} @我:{is_tome} 内容:{text[:50]}")

# 创建消息处理器（只响应 @机器人 或私聊）
chat = on_message(rule=to_me(), priority=10, block=True)


@chat.handle()
async def handle_message(bot: Bot, event: MessageEvent):
    """处理消息"""
    global butler

    # 设置 Bot 实例到 QQ 互动工具和定时任务工具
    from tools.qq_interaction_tools import set_bot_instance, set_current_context
    from tools.scheduler_tool import get_scheduler_wrapper
    from tools.file_transfer_tool import set_bot_instance as set_file_bot_instance
    from tools.send_file_tool import set_bot_instance as set_send_file_bot_instance

    set_bot_instance(bot)
    set_file_bot_instance(bot)  # 设置到文件传输工具
    set_send_file_bot_instance(bot)  # 设置到发送文件工具
    get_scheduler_wrapper().set_bot(bot)  # 设置 bot 到定时任务工具

    # 检查 Butler 是否初始化
    if butler is None:
        await chat.finish("抱歉，我还没有准备好...")
        return

    # 获取用户 ID
    user_id = str(event.user_id)

    # 判断是群聊还是私聊
    chat_type = "群聊" if isinstance(event, GroupMessageEvent) else "私聊"
    group_id = event.group_id if isinstance(event, GroupMessageEvent) else None

    # 提取文本、图片、文件和 @ 信息
    user_input = event.get_plaintext().strip()
    image_urls = []
    file_info = []  # 文件信息列表
    mentioned_users = []  # 被 @ 的用户列表
    mentioned_users_info = {}  # 存储被 @ 用户的详细信息 {qq: nickname}
    reply_message_id = None  # 回复的消息 ID

    # 遍历消息段，提取图片、文件、@ 信息和回复信息
    # 使用 original_message 而不是 message，因为 to_me() 会过滤掉 @ 和 reply
    message_to_parse = event.original_message if hasattr(event, 'original_message') else event.message
    for seg in message_to_parse:
        if seg.type == "image":
            # 获取图片 URL
            img_url = seg.data.get("url") or seg.data.get("file")
            if img_url:
                image_urls.append(img_url)
        elif seg.type == "file":
            # 获取文件信息
            file_name = seg.data.get("file", "未知文件")
            file_id = seg.data.get("file_id", "")
            file_size = seg.data.get("file_size", 0)
            file_info.append({
                "name": file_name,
                "id": file_id,
                "size": file_size
            })
        elif seg.type == "at":
            # 获取被 @ 的用户 QQ 号
            at_qq = seg.data.get("qq")
            if at_qq and at_qq != "all":  # 排除 @全体成员
                mentioned_users.append(str(at_qq))
        elif seg.type == "reply":
            # 获取回复的消息 ID
            reply_message_id = seg.data.get("id")

    # 如果是回复消息且当前消息没有图片，尝试获取被回复消息中的图片
    if reply_message_id and not image_urls:
        try:
            # 获取被回复的消息
            replied_msg = await bot.get_msg(message_id=int(reply_message_id))
            # 解析被回复消息中的图片和文件
            if replied_msg and "message" in replied_msg:
                # replied_msg["message"] 是一个字典列表，不是 Message 对象
                message_list = replied_msg["message"]
                for seg_dict in message_list:
                    seg_type = seg_dict.get("type")
                    seg_data = seg_dict.get("data", {})
                    if seg_type == "image":
                        img_url = seg_data.get("url") or seg_data.get("file")
                        if img_url:
                            image_urls.append(img_url)
                    elif seg_type == "file":
                        # 获取被回复消息中的文件
                        file_name = seg_data.get("file", "未知文件")
                        file_id = seg_data.get("file_id", "")
                        file_size = seg_data.get("file_size", 0)
                        file_info.append({
                            "name": file_name,
                            "id": file_id,
                            "size": file_size
                        })
        except Exception as e:
            print(f"⚠️ 获取回复消息失败: {e}")

    # 获取被 @ 用户的昵称
    for qq in mentioned_users:
        try:
            # 尝试获取用户信息
            if isinstance(event, GroupMessageEvent):
                # 群聊中获取群名片
                info = await bot.get_group_member_info(group_id=event.group_id, user_id=int(qq), no_cache=False)
                nickname = info.get('card') or info.get('nickname', qq)
            else:
                # 私聊中获取昵称
                info = await bot.get_stranger_info(user_id=int(qq), no_cache=False)
                nickname = info.get('nickname', qq)
            mentioned_users_info[qq] = nickname
        except Exception as e:
            # 获取失败，使用 QQ 号
            mentioned_users_info[qq] = qq
            print(f"⚠️ 获取用户 {qq} 信息失败: {e}")

    # 重新构建消息文本，将 @ 替换为"昵称(QQ号)"
    enhanced_text_parts = []
    for seg in event.message:
        if seg.type == "text":
            enhanced_text_parts.append(seg.data.get("text", ""))
        elif seg.type == "at":
            at_qq = seg.data.get("qq")
            if at_qq and at_qq != "all":
                nickname = mentioned_users_info.get(str(at_qq), at_qq)
                # 格式：昵称(QQ:xxx)
                enhanced_text_parts.append(f"{nickname}(QQ:{at_qq})")

    user_input = "".join(enhanced_text_parts).strip()

    # 设置当前上下文（供工具使用），包含被 @ 的用户
    # 过滤掉机器人自己
    bot_id = str(bot.self_id) if hasattr(bot, 'self_id') else "2509109290"
    other_mentioned_users = [u for u in mentioned_users if u != bot_id]

    set_current_context(
        user_id=user_id,
        group_id=group_id,
        mentioned_users=other_mentioned_users
    )

    # 设置工作流工具的用户上下文
    for tool in butler.tools:
        if hasattr(tool, 'name') and tool.name == 'create_workflow':
            tool.current_user_id = user_id
            tool.current_group_id = str(group_id) if group_id else None
            break

    # 构建增强的用户输入，添加发送者信息和 QQ 号信息
    context_info = f"[系统提示：发送此消息的用户是"

    # 获取发送者昵称
    try:
        if isinstance(event, GroupMessageEvent):
            sender_info = await bot.get_group_member_info(group_id=event.group_id, user_id=int(user_id), no_cache=False)
            sender_nickname = sender_info.get('card') or sender_info.get('nickname', user_id)
        else:
            sender_info = await bot.get_stranger_info(user_id=int(user_id), no_cache=False)
            sender_nickname = sender_info.get('nickname', user_id)
    except:
        sender_nickname = user_id

    context_info += f"{sender_nickname}(QQ:{user_id})"
    if group_id:
        context_info += f"，当前在群{group_id}中"

    # 添加文件信息
    if file_info:
        context_info += f"，发送了{len(file_info)}个文件："
        for f in file_info:
            file_size = int(f['size']) if isinstance(f['size'], str) else f['size']
            file_size_mb = file_size / (1024 * 1024)
            context_info += f"\n  - {f['name']} ({file_size_mb:.2f} MB, ID: {f['id']})"

    # 添加机器人自己的 QQ 号信息（用于伪造消息工具）
    bot_qq = str(bot.self_id) if hasattr(bot, 'self_id') else "2509109290"
    context_info += f"。你的 QQ 号是 {bot_qq}，用户的 QQ 号是 {user_id}"
    context_info += "]\n\n"

    # 如果没有文本但有图片，添加默认提示
    if not user_input and image_urls:
        user_input = "请分析这张图片"

    # 如果没有文本但有文件，添加默认提示
    if not user_input and file_info:
        file_names = ", ".join([f['name'] for f in file_info])
        user_input = f"请阅读这些文件：{file_names}"

    # 如果既没有文本也没有图片也没有文件，忽略
    if not user_input and not image_urls and not file_info:
        return

    enhanced_user_input = context_info + user_input

    conversation_context = {
        "chat_type": "group" if isinstance(event, GroupMessageEvent) else "direct",
        "group_id": str(group_id) if group_id else None,
        "engaged_directly": True,
        "is_reply": bool(reply_message_id),
        "has_images": bool(image_urls),
        "platform": "qq",
        "bot_name": "智乃",
        "sender_name": sender_nickname,
    }

    # 日志
    print(f"\n{'=' * 60}")
    print(f"📨 收到消息 [{chat_type}]")
    if group_id:
        print(f"   群号: {group_id}")
    print(f"   用户: {user_id}")
    print(f"   原始文本: {event.get_plaintext().strip()}")
    print(f"   处理后文本: {user_input}")
    if other_mentioned_users:
        print(f"   @ 其他用户: {', '.join([f'{mentioned_users_info.get(u, u)}({u})' for u in other_mentioned_users])}")
    if image_urls:
        print(f"   图片: {len(image_urls)} 张")
    if file_info:
        print(f"   文件: {len(file_info)} 个")
        for f in file_info:
            file_size = int(f['size']) if isinstance(f['size'], str) else f['size']
            print(f"     - {f['name']} ({file_size/1024:.2f} KB)")
        for i, url in enumerate(image_urls, 1):
            print(f"      [{i}] {url[:80]}...")
    print(f"{'=' * 60}\n")

    try:
        # 如果有图片，使用 Pixtral 原生多模态能力
        if image_urls:
            print(f"🖼️ 检测到 {len(image_urls)} 张图片，使用 Pixtral 多模态处理...")

            # 临时切换到 Pixtral 模型
            original_model = butler.llm.model_name
            butler.llm.model_name = "pixtral-12b-latest"

            try:
                # 使用 Butler 的多模态处理（Pixtral 原生支持）
                response = await butler.aprocess_with_images(
                    enhanced_user_input,
                    image_urls=image_urls,
                    user_id=user_id,
                    conversation_context=conversation_context,
                )
            finally:
                # 恢复原始模型
                butler.llm.model_name = original_model
        else:
            # 没有图片，直接处理文本 - 使用异步方法
            response = await butler.aprocess(
                enhanced_user_input,
                user_id=user_id,
                conversation_context=conversation_context,
            )

        # 发送回复
        await chat.send(response)

        print(f"\n✅ 回复成功: {response[:50]}...\n")

    except Exception as e:
        error_msg = f"抱歉，我遇到了一些问题：{str(e)}"
        await chat.send(error_msg)

        print(f"\n❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
