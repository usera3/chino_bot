#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
链接解析工具
支持解析 B站、YouTube 等平台的链接内容
使用底层库直接解析，不依赖 NoneBot 插件
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type
import asyncio
import re
import httpx


class LinkResolverInput(BaseModel):
    """链接解析输入"""
    url: str = Field(description="要解析的链接 URL")


class LinkResolverTool(BaseTool):
    """链接解析工具"""
    
    name: str = "parse_link"
    description: str = """解析各种平台的链接内容，获取视频、文章等信息。
    
支持的平台：
- B站 (bilibili.com, b23.tv)：视频信息
- YouTube (youtube.com, youtu.be)：视频信息
- GitHub：仓库信息

输入：链接 URL
输出：解析后的内容信息（标题、描述、作者等）

使用场景：
- 用户发送链接，想了解内容
- 需要获取视频/文章信息
- 分析链接内容

示例：
用户: "帮我看看这个视频 https://www.bilibili.com/video/BV1xx411c7mD"
→ 调用 parse_link(url="https://www.bilibili.com/video/BV1xx411c7mD")
"""
    args_schema: Type[BaseModel] = LinkResolverInput
    
    def _run(self, url: str) -> str:
        """
        同步执行（LangChain 要求）
        
        Args:
            url: 要解析的链接
            
        Returns:
            解析结果
        """
        try:
            # 使用 asyncio 运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._arun(url))
            loop.close()
            return result
        except Exception as e:
            return f"链接解析失败: {str(e)}"
    
    async def _arun(self, url: str) -> str:
        """
        异步执行链接解析
        
        Args:
            url: 要解析的链接
            
        Returns:
            解析结果
        """
        try:
            # 判断平台类型
            if "bilibili.com" in url or "b23.tv" in url or "bili2233.cn" in url or re.match(r'^BV[0-9a-zA-Z]{10}$', url):
                return await self._parse_bilibili(url)
            elif "youtube.com" in url or "youtu.be" in url:
                return await self._parse_youtube(url)
            elif "github.com" in url:
                return await self._parse_github(url)
            else:
                return f"暂不支持解析此平台的链接: {url}\n\n目前支持：B站、YouTube、GitHub"
            
        except Exception as e:
            return f"解析链接时出错: {str(e)}\n链接: {url}"
    
    async def _parse_bilibili(self, url: str) -> str:
        """解析 B站 链接（使用 API 直接请求）"""
        try:
            # 处理短链接
            if "b23.tv" in url or "bili2233.cn" in url:
                async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
                    resp = await client.get(url)
                    url = str(resp.url)
            
            # 处理 BV 号
            if re.match(r'^BV[0-9a-zA-Z]{10}$', url):
                url = f'https://www.bilibili.com/video/{url}'
            
            # 提取视频 ID
            video_id = re.search(r"video\/([^\?\/ ]+)", url)
            if not video_id:
                return f"无法从链接中提取视频ID: {url}"
            
            video_id = video_id.group(1)
            
            # 直接调用 B站 API
            api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://www.bilibili.com/'
            }
            
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.get(api_url, headers=headers)
                data = resp.json()
            
            if data.get('code') != 0:
                return f"B站 API 返回错误: {data.get('message', '未知错误')}"
            
            info = data['data']
            
            if not info:
                return f"无法获取视频信息: {url}"
            
            # 格式化输出
            output = []
            output.append("� B站视频解析")
            output.append("━━━━━━━━━━━━━━━━")
            output.append(f"� 标题: {info.get('title', '未知')}")
            output.append(f"👤 UP主: {info.get('owner', {}).get('name', '未知')}")
            
            # 播放数据
            stat = info.get('stat', {})
            if stat:
                output.append(f"👁️ 播放: {stat.get('view', 0):,}")
                output.append(f"👍 点赞: {stat.get('like', 0):,}")
                output.append(f"💬 评论: {stat.get('reply', 0):,}")
                output.append(f"⭐ 收藏: {stat.get('favorite', 0):,}")
            
            # 时长
            duration = info.get('duration', 0)
            if duration:
                minutes = duration // 60
                seconds = duration % 60
                output.append(f"⏱️ 时长: {minutes}:{seconds:02d}")
            
            # 简介
            desc = info.get('desc', '')
            if desc:
                desc = desc[:150] + "..." if len(desc) > 150 else desc
                output.append(f"📄 简介: {desc}")
            
            output.append(f"🔗 链接: {url}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"B站链接解析失败: {str(e)}\n链接: {url}"
    
    async def _parse_youtube(self, url: str) -> str:
        """解析 YouTube 链接"""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            if not info:
                return f"无法获取视频信息: {url}"
            
            # 格式化输出
            output = []
            output.append("🔗 YouTube 视频解析")
            output.append("━━━━━━━━━━━━━━━━")
            output.append(f"📝 标题: {info.get('title', '未知')}")
            output.append(f"👤 频道: {info.get('uploader', '未知')}")
            
            # 播放数据
            if info.get('view_count'):
                output.append(f"👁️ 播放: {info['view_count']:,}")
            if info.get('like_count'):
                output.append(f"👍 点赞: {info['like_count']:,}")
            
            # 时长
            duration = info.get('duration', 0)
            if duration:
                minutes = duration // 60
                seconds = duration % 60
                output.append(f"⏱️ 时长: {minutes}:{seconds:02d}")
            
            # 描述
            desc = info.get('description', '')
            if desc:
                desc = desc[:150] + "..." if len(desc) > 150 else desc
                output.append(f"📄 描述: {desc}")
            
            output.append(f"🔗 链接: {url}")
            
            return "\n".join(output)
            
        except ImportError:
            return "YouTube 解析功能未安装，请先安装: pip install yt-dlp"
        except Exception as e:
            return f"YouTube 链接解析失败: {str(e)}\n链接: {url}"
    
    async def _parse_github(self, url: str) -> str:
        """解析 GitHub 链接"""
        try:
            # 提取仓库信息
            match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
            if not match:
                return f"无法从链接中提取 GitHub 仓库信息: {url}"
            
            owner, repo = match.groups()
            repo = repo.split('?')[0].split('#')[0]  # 移除查询参数
            
            # 调用 GitHub API
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(api_url, timeout=10)
                
                if resp.status_code != 200:
                    return f"无法获取 GitHub 仓库信息（状态码: {resp.status_code}）"
                
                info = resp.json()
            
            # 格式化输出
            output = []
            output.append("🔗 GitHub 仓库解析")
            output.append("━━━━━━━━━━━━━━━━")
            output.append(f"📝 仓库: {info.get('full_name', '未知')}")
            output.append(f"👤 作者: {info.get('owner', {}).get('login', '未知')}")
            
            # 统计数据
            output.append(f"⭐ Stars: {info.get('stargazers_count', 0):,}")
            output.append(f"🍴 Forks: {info.get('forks_count', 0):,}")
            output.append(f"👁️ Watchers: {info.get('watchers_count', 0):,}")
            
            # 语言
            if info.get('language'):
                output.append(f"💻 语言: {info['language']}")
            
            # 描述
            desc = info.get('description', '')
            if desc:
                desc = desc[:150] + "..." if len(desc) > 150 else desc
                output.append(f"📄 描述: {desc}")
            
            # 主题
            topics = info.get('topics', [])
            if topics:
                output.append(f"🏷️ 标签: {', '.join(topics[:5])}")
            
            output.append(f"🔗 链接: {url}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"GitHub 链接解析失败: {str(e)}\n链接: {url}"



def extract_urls(text: str) -> list[str]:
    """
    从文本中提取 URL
    
    Args:
        text: 文本内容
        
    Returns:
        URL 列表
    """
    # URL 正则表达式
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    return urls


# 创建工具实例
link_resolver_tool = LinkResolverTool()


if __name__ == "__main__":
    # 测试
    import sys
    
    print("测试链接解析工具")
    print("=" * 60)
    
    # 测试链接
    test_urls = [
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "https://github.com/usera3/chino_bot",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ]
    
    for url in test_urls:
        print(f"\n测试链接: {url}")
        print("-" * 60)
        result = link_resolver_tool._run(url)
        print(result)
        print()
