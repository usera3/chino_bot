"""测试邮件工具"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from tools.basic_tools import SendEmailTool

def test_email():
    """测试邮件发送"""
    print("=" * 60)
    print("测试邮件工具")
    print("=" * 60)
    
    # 检查配置
    sender = os.getenv("QQ_EMAIL_SENDER")
    password = os.getenv("QQ_EMAIL_PASSWORD")
    
    print(f"\n📧 发件人: {sender}")
    print(f"🔑 密码: {'*' * len(password) if password else '未配置'}")
    
    if not sender or not password:
        print("\n❌ 邮件配置不完整，请检查 .env 文件")
        return
    
    tool = SendEmailTool()
    
    # 测试发送邮件
    print("\n发送测试邮件...")
    result = tool._run(
        receiver_email="123456789@qq.com",  # 替换为你的测试邮箱
        subject="来自 zhinai-bot-v3 的测试邮件",
        content="""你好！

这是通过 zhinai-bot-v3 的邮件工具发送的测试邮件。

功能特点：
- 基于 LangChain BaseTool
- 使用 QQ 邮箱 SMTP
- 支持 Agent 自动调用

---
智乃机器人 v3
Powered by LangChain"""
    )
    
    print("\n" + "=" * 60)
    print("测试结果:")
    print("=" * 60)
    print(result)

if __name__ == "__main__":
    test_email()
