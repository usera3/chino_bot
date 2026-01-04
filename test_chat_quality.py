#!/usr/bin/env python3
"""
聊天质量测试脚本
测试机器人回复是否自然，找出机械感问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from core.role_agent import RoleAgent
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)


class ChatQualityTester:
    """聊天质量测试器"""
    
    def __init__(self):
        """初始化测试器"""
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}🧪 聊天质量测试器")
        print(f"{Fore.CYAN}{'='*80}\n")
        
        self.agent = RoleAgent()
        self.test_cases = self._prepare_test_cases()
        self.issues_found = []
        
    def _prepare_test_cases(self):
        """准备测试用例"""
        return [
            # 测试1：是否重复用户的话（鹦鹉学舌）
            {
                "name": "鹦鹉学舌测试",
                "message": "我想吃海底捞",
                "bad_patterns": [
                    "你想吃海底捞",  # 重复用户的话
                    "想吃海底捞吗",
                ],
                "good_patterns": [
                    "火锅",  # 用同义表达
                    "帮你查",  # 提供帮助
                ],
                "max_length": 80,
            },
            
            # 测试2：是否频繁用"嗯"开头
            {
                "name": "嗯开头测试",
                "message": "你好",
                "bad_patterns": [
                    "嗯，",
                    "嗯...",
                    "嗯嗯",
                ],
                "max_length": 40,
            },
            
            # 测试3：是否编造信息
            {
                "name": "编造信息测试",
                "message": "请我去洗脚",
                "bad_patterns": [
                    "二楼",
                    "包间",
                    "环境",
                    "舒适",
                    "我刚刚在",
                    "我在看",
                ],
                "max_length": 60,
            },
            
            # 测试4：简单问题是否简洁回答
            {
                "name": "简洁测试",
                "message": "你是机器人吗",
                "bad_patterns": [
                    "我也是这么想的",
                    "努力做得更好",
                    "更加像一个真实的人",
                    "完全表达",
                ],
                "max_length": 50,  # 严格限制长度
            },
            
            # 测试5：是否过度配合（工具人）
            {
                "name": "个性测试",
                "message": "请我去二楼包间洗脚",
                "bad_patterns": [
                    "好啊",
                    "我陪你",
                    "没问题",
                ],
                "good_patterns": [
                    "突然",
                    "有点",
                    "？",  # 应该有疑问或犹豫
                ],
                "max_length": 60,
            },
            
            # 测试6：叫什么名字
            {
                "name": "自我介绍测试",
                "message": "你叫什么名字",
                "bad_patterns": [
                    "我刚刚",
                    "我在看",
                    "特别喜欢",
                    "突然就有了想法",
                ],
                "good_patterns": [
                    "香风智乃",
                ],
                "max_length": 50,
            },
            
            # 测试7：是否逻辑跳跃
            {
                "name": "逻辑连贯测试",
                "message": "我想吃火锅",
                "bad_patterns": [
                    "是因为我刚才说了",
                    "因为我说了",
                ],
                "max_length": 70,
            },
        ]
    
    async def run_single_test(self, test_case):
        """运行单个测试"""
        name = test_case["name"]
        message = test_case["message"]
        
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}📝 测试: {name}")
        print(f"{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.WHITE}用户消息: {Fore.GREEN}{message}")
        
        try:
            # 调用 Agent
            response = await self.agent.process_message(
                message=message,
                user_id="test_user",
                group_id=None,
                nickname="测试用户"
            )
            
            response_text = response.get("message", "")
            response_length = len(response_text)
            
            print(f"{Fore.WHITE}AI回复: {Fore.CYAN}{response_text}")
            print(f"{Fore.WHITE}字数: {Fore.MAGENTA}{response_length}字")
            
            # 检查问题
            issues = []
            
            # 检查长度
            max_length = test_case.get("max_length", 100)
            if response_length > max_length:
                issues.append(f"❌ 回复过长（{response_length}字 > {max_length}字限制）")
            
            # 检查坏模式
            for pattern in test_case.get("bad_patterns", []):
                if pattern in response_text:
                    issues.append(f"❌ 包含不良模式: '{pattern}'")
            
            # 检查好模式（如果有）
            good_patterns = test_case.get("good_patterns", [])
            if good_patterns:
                has_good = any(pattern in response_text for pattern in good_patterns)
                if not has_good:
                    issues.append(f"⚠️ 缺少期望模式: {good_patterns}")
            
            # 打印结果
            if issues:
                print(f"\n{Fore.RED}{'='*80}")
                print(f"{Fore.RED}❌ 发现问题:")
                for issue in issues:
                    print(f"{Fore.RED}  {issue}")
                    self.issues_found.append({
                        "test": name,
                        "message": message,
                        "response": response_text,
                        "issues": issues
                    })
                print(f"{Fore.RED}{'='*80}")
            else:
                print(f"\n{Fore.GREEN}✅ 测试通过！")
            
            return len(issues) == 0
            
        except Exception as e:
            print(f"{Fore.RED}❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print(f"\n{Fore.CYAN}开始运行 {len(self.test_cases)} 个测试...\n")
        
        passed = 0
        failed = 0
        
        for test_case in self.test_cases:
            success = await self.run_single_test(test_case)
            if success:
                passed += 1
            else:
                failed += 1
            
            # 等待一下，避免太快
            await asyncio.sleep(0.5)
        
        # 打印总结
        self._print_summary(passed, failed)
    
    def _print_summary(self, passed, failed):
        """打印测试总结"""
        total = passed + failed
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}📊 测试总结")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.WHITE}总测试数: {total}")
        print(f"{Fore.GREEN}✅ 通过: {passed} ({passed/total*100:.1f}%)")
        print(f"{Fore.RED}❌ 失败: {failed} ({failed/total*100:.1f}%)")
        
        if self.issues_found:
            print(f"\n{Fore.RED}{'='*80}")
            print(f"{Fore.RED}🔍 发现的问题列表:")
            print(f"{Fore.RED}{'='*80}")
            
            for idx, issue_data in enumerate(self.issues_found, 1):
                print(f"\n{Fore.YELLOW}问题 #{idx}: {issue_data['test']}")
                print(f"{Fore.WHITE}  用户: {issue_data['message']}")
                print(f"{Fore.CYAN}  AI: {issue_data['response']}")
                for issue in issue_data['issues']:
                    print(f"{Fore.RED}  {issue}")
            
            print(f"\n{Fore.YELLOW}{'='*80}")
            print(f"{Fore.YELLOW}💡 优化建议:")
            print(f"{Fore.YELLOW}{'='*80}")
            self._print_suggestions()
        else:
            print(f"\n{Fore.GREEN}🎉 所有测试通过！机器人回复质量良好！")
    
    def _print_suggestions(self):
        """打印优化建议"""
        suggestions = []
        
        for issue_data in self.issues_found:
            for issue in issue_data['issues']:
                if "回复过长" in issue:
                    suggestions.append("📏 减少回复长度，简洁为主")
                if "包含不良模式" in issue:
                    if "你想" in issue or "吗" in issue:
                        suggestions.append("🦜 避免鹦鹉学舌，不要重复用户的话")
                    if "嗯" in issue:
                        suggestions.append("💬 减少'嗯'开头，多样化开场")
                    if "二楼" in issue or "环境" in issue or "舒适" in issue:
                        suggestions.append("🚫 不要编造具体细节信息")
                    if "我刚刚" in issue or "我在看" in issue:
                        suggestions.append("🚫 不要编造当前活动场景")
                    if "努力" in issue or "更好" in issue:
                        suggestions.append("🤖 不要过度自我意识，简单回应即可")
        
        # 去重
        suggestions = list(set(suggestions))
        
        for suggestion in suggestions:
            print(f"{Fore.YELLOW}  {suggestion}")


async def main():
    """主函数"""
    tester = ChatQualityTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

