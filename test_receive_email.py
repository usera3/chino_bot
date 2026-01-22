"""
测试邮件接收功能
"""
import os
from dotenv import load_dotenv
from tools.basic_tools import ReceiveEmailTool

# 加载环境变量
load_dotenv()

def test_receive_email():
    """测试接收邮件"""
    print("=" * 60)
    print("📧 测试邮件接收功能")
    print("=" * 60)
    
    # 创建工具实例
    tool = ReceiveEmailTool()
    
    # 测试 1：读取未读邮件（默认）
    print("\n【测试 1】读取未读邮件（最多 5 封）")
    print("-" * 60)
    result = tool._run(max_count=5, unread_only=True)
    print(result)
    
    # 测试 2：读取所有邮件（最新 3 封）
    print("\n【测试 2】读取所有邮件（最新 3 封）")
    print("-" * 60)
    result = tool._run(max_count=3, unread_only=False)
    print(result)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_receive_email()
