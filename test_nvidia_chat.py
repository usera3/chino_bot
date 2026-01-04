#!/usr/bin/env python3
"""
英伟达API简单对话示例
演示如何使用DEEPSEEK_API_KEY与meta/llama-3.3-70b-instruct模型进行对话
"""

import asyncio
from nonebot.log import logger
import os
from dotenv import load_dotenv

# 从utils模块导入DeepSeekClient
from utils.deepseek_client import DeepSeekClient

async def main():
    """主函数 - 执行简单的AI对话"""
    print("英伟达API对话示例")
    print("=" * 50)
    
    # 加载环境变量
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("错误: 未找到DEEPSEEK_API_KEY环境变量")
        print("请确保.env文件中包含正确的API密钥配置")
        return
    
    # 创建客户端实例
    client = DeepSeekClient(api_key=api_key)
    
    if not client.is_available():
        print("错误: API客户端初始化失败")
        return
    
    print(f"模型: meta/llama-3.3-70b-instruct")
    print(f"API地址: {client.api_url}")
    print("=" * 50)
    print("输入'退出'或'q'结束对话")
    print("=" * 50)
    
    # 可选的系统提示词
    system_prompt = "你是一个友好的AI助手，简洁明了地回答问题。"
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n用户: ")
            
            if user_input.lower() in ['退出', 'q', 'quit', 'exit']:
                print("\n对话结束，再见！")
                break
            
            if not user_input.strip():
                continue
            
            print("AI: 正在生成回复...")
            
            # 调用API获取回复
            response = await client.chat_simple(
                user_message=user_input,
                system_prompt=system_prompt
            )
            
            if response:
                print(f"AI: {response}")
            else:
                print("AI: 抱歉，无法获取回复，请重试")
                
        except KeyboardInterrupt:
            print("\n\n用户中断对话，再见！")
            break
        except Exception as e:
            print(f"错误: {e}")
            logger.error(f"对话过程发生错误: {e}")

if __name__ == "__main__":
    try:
        # 运行异步主函数
        asyncio.run(main())
    except Exception as e:
        print(f"程序运行出错: {e}")
