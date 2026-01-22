#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
好友申请功能测试脚本
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from config.friend_request_config import *


def should_approve_test(user_id: int, comment: str) -> tuple[bool, str]:
    """
    测试版本的判断逻辑（不依赖 NoneBot）
    """
    # 检查黑名单
    if user_id in BLACKLIST:
        return False, "用户在黑名单中"
    
    # 检查白名单模式
    if WHITELIST_MODE:
        if user_id not in WHITELIST:
            return False, "白名单模式：用户不在白名单中"
    
    # 检查拒绝关键词
    if REJECT_KEYWORDS and comment:
        for keyword in REJECT_KEYWORDS:
            if keyword in comment:
                return False, f"备注包含拒绝关键词: {keyword}"
    
    # 检查必须关键词
    if REQUIRED_KEYWORDS:
        if not comment:
            return False, "未填写备注，且设置了必须关键词"
        
        has_required = False
        for keyword in REQUIRED_KEYWORDS:
            if keyword in comment:
                has_required = True
                break
        
        if not has_required:
            return False, f"备注未包含必须关键词: {REQUIRED_KEYWORDS}"
    
    return True, "通过所有检查"


def test_should_approve():
    """测试好友申请判断逻辑"""
    
    print("=" * 60)
    print("好友申请功能测试")
    print("=" * 60)
    print()
    
    # 测试用例
    test_cases = [
        {
            "name": "正常申请",
            "user_id": 123456789,
            "comment": "你好，想加个好友",
            "expected": True
        },
        {
            "name": "黑名单用户",
            "user_id": BLACKLIST[0] if BLACKLIST else 999999999,
            "comment": "你好",
            "expected": False if BLACKLIST else True
        },
        {
            "name": "空备注",
            "user_id": 111111111,
            "comment": "",
            "expected": True if not REQUIRED_KEYWORDS else False
        },
        {
            "name": "包含拒绝关键词",
            "user_id": 222222222,
            "comment": "广告推广" if REJECT_KEYWORDS else "正常备注",
            "expected": False if REJECT_KEYWORDS else True
        },
        {
            "name": "包含必须关键词",
            "user_id": 333333333,
            "comment": REQUIRED_KEYWORDS[0] if REQUIRED_KEYWORDS else "正常备注",
            "expected": True
        },
    ]
    
    print("当前配置：")
    print(f"  AUTO_APPROVE: {AUTO_APPROVE}")
    print(f"  SEND_WELCOME: {SEND_WELCOME}")
    print(f"  WHITELIST_MODE: {WHITELIST_MODE}")
    print(f"  BLACKLIST: {BLACKLIST}")
    print(f"  WHITELIST: {WHITELIST}")
    print(f"  REJECT_KEYWORDS: {REJECT_KEYWORDS}")
    print(f"  REQUIRED_KEYWORDS: {REQUIRED_KEYWORDS}")
    print()
    
    print("测试用例：")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        result, reason = should_approve_test(case["user_id"], case["comment"])
        
        status = "✓ PASS" if result == case["expected"] else "✗ FAIL"
        if result == case["expected"]:
            passed += 1
        else:
            failed += 1
        
        print(f"{i}. {case['name']}")
        print(f"   用户: {case['user_id']}")
        print(f"   备注: {case['comment']}")
        print(f"   结果: {'同意' if result else '拒绝'}")
        print(f"   原因: {reason}")
        print(f"   状态: {status}")
        print()
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


def test_welcome_message():
    """测试欢迎消息"""
    print()
    print("=" * 60)
    print("欢迎消息预览")
    print("=" * 60)
    print()
    print(WELCOME_MESSAGE)
    print()
    print("=" * 60)
    print(f"消息长度: {len(WELCOME_MESSAGE)} 字符")
    print("=" * 60)


def main():
    """主函数"""
    print()
    print("🤖 智乃机器人 - 好友申请功能测试")
    print()
    
    # 测试判断逻辑
    success = test_should_approve()
    
    # 测试欢迎消息
    test_welcome_message()
    
    print()
    if success:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败，请检查配置")
    print()
    
    # 使用建议
    print("💡 使用建议：")
    print()
    
    if not AUTO_APPROVE:
        print("⚠️  自动同意已禁用，好友申请不会被自动处理")
    else:
        print("✓ 自动同意已启用")
    
    if WHITELIST_MODE:
        print(f"✓ 白名单模式已启用，只同意 {len(WHITELIST)} 个用户")
    
    if BLACKLIST:
        print(f"✓ 黑名单已设置，拒绝 {len(BLACKLIST)} 个用户")
    
    if REJECT_KEYWORDS:
        print(f"✓ 拒绝关键词已设置: {REJECT_KEYWORDS}")
    
    if REQUIRED_KEYWORDS:
        print(f"✓ 必须关键词已设置: {REQUIRED_KEYWORDS}")
    
    if SEND_WELCOME:
        print("✓ 欢迎消息已启用")
    
    if NOTIFY_SUPERUSER:
        print("✓ 超级用户通知已启用")
    
    print()
    print("📝 修改配置: config/friend_request_config.py")
    print("📖 查看文档: 好友申请功能说明.md")
    print()


if __name__ == "__main__":
    main()
