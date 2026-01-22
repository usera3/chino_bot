#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试链接解析工具"""
import asyncio
import sys
sys.path.insert(0, '.')

from tools.link_resolver_tool import link_resolver_tool


async def test_links():
    """测试各种链接"""
    
    test_cases = [
        ("GitHub", "https://github.com/usera3/chino_bot"),
        ("B站视频", "https://www.bilibili.com/video/BV1xx411c7mD"),
    ]
    
    for name, url in test_cases:
        print(f"\n{'='*60}")
        print(f"测试 {name}: {url}")
        print('='*60)
        
        try:
            result = await link_resolver_tool._arun(url)
            print(result)
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        print()


if __name__ == "__main__":
    asyncio.run(test_links())
