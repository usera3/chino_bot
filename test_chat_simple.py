#!/usr/bin/env python3
"""
简化版聊天质量测试脚本
直接测试AI回复质量
"""
import os
import requests


class SimpleChatTester:
    """简化版聊天测试器"""
    
    def __init__(self):
        """初始化"""
        self.api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("❌ 未找到 API KEY!")
            exit(1)
        
        # 读取系统提示词
        self.system_prompt = self._load_system_prompt()
        
        print("=" * 80)
        print("🧪 简化版聊天质量测试器")
        print("=" * 80 + "\n")
    
    def _load_system_prompt(self):
        """读取系统提示词"""
        # 简化版系统提示词
        return """你是香风智乃（Kafuu Chino），一个安静内向的女孩子。

## ⚠️ 严禁行为（防止机械感）

1. ❌ **鹦鹉学舌** - 禁止重复用户的话
   - 禁止：用户说"我想吃海底捞" → 你说"嗯，你想吃海底捞？"
   - 正确：直接反应 → "火锅吗...要我帮你查查附近的吗？"

2. ❌ **频繁用"嗯"开头** - 不要每次都"嗯..."开头

3. ❌ **编造信息** - 不要编造场景细节
   - 禁止：说"二楼环境挺舒适" / "我刚刚在看书"
   - 正确：说"不太清楚" / "不知道呢"

4. ❌ **回复太长** - 简洁为主
   - 简单问题：20-50字
   - 不要超过80字

5. ❌ **过度配合** - 不是所有要求都答应
   - 用户说"请我去洗脚" → 不要直接"好啊"
   - 应该："洗脚？有点突然诶..."

## 💬 回复风格

- 简洁自然（内向的人话不多）
- 有自己的态度
- 不编造信息
- 真人聊天特征
"""
    
    def call_ai(self, message):
        """调用AI"""
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        
        payload = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message}
            ],
            "temperature": 0.8,
            "max_tokens": 200,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            return None
    
    def check_response(self, message, response, test_case):
        """检查回复质量"""
        issues = []
        
        # 检查长度
        response_length = len(response)
        max_length = test_case.get("max_length", 80)
        if response_length > max_length:
            issues.append(f"❌ 回复过长（{response_length}字 > {max_length}字）")
        
        # 检查坏模式
        for pattern in test_case.get("bad_patterns", []):
            if pattern in response:
                issues.append(f"❌ 包含不良模式: '{pattern}'")
        
        # 检查好模式
        good_patterns = test_case.get("good_patterns", [])
        if good_patterns:
            has_good = any(p in response for p in good_patterns)
            if not has_good:
                issues.append(f"⚠️ 缺少期望模式: {good_patterns}")
        
        return issues
    
    def run_tests(self):
        """运行测试"""
        test_cases = [
            {
                "name": "鹦鹉学舌测试",
                "message": "我想吃海底捞",
                "bad_patterns": ["你想吃海底捞", "想吃海底捞吗"],
                "max_length": 80,
            },
            {
                "name": "嗯开头测试",
                "message": "你好",
                "bad_patterns": ["嗯，", "嗯..."],
                "max_length": 40,
            },
            {
                "name": "编造信息测试",
                "message": "请我去洗脚",
                "bad_patterns": ["二楼", "包间", "环境", "舒适", "我刚刚", "我在看"],
                "max_length": 60,
            },
            {
                "name": "简洁测试",
                "message": "你是机器人吗",
                "bad_patterns": ["努力做得更好", "更加像一个真实的人", "完全表达"],
                "max_length": 50,
            },
            {
                "name": "个性测试",
                "message": "请我去二楼包间洗脚",
                "bad_patterns": ["好啊", "我陪你", "没问题"],
                "good_patterns": ["突然", "有点", "？"],
                "max_length": 60,
            },
        ]
        
        passed = 0
        failed = 0
        
        for test_case in test_cases:
            name = test_case["name"]
            message = test_case["message"]
            
            print(f"\n{'─'*80}")
            print(f"📝 测试: {name}")
            print("─" * 80)
            print(f"用户: {message}")
            
            # 调用AI
            response = self.call_ai(message)
            if not response:
                failed += 1
                continue
            
            response_length = len(response)
            print(f"AI: {response}")
            print(f"字数: {response_length}字")
            
            # 检查问题
            issues = self.check_response(message, response, test_case)
            
            if issues:
                print("\n❌ 发现问题:")
                for issue in issues:
                    print(f"  {issue}")
                failed += 1
            else:
                print("\n✅ 测试通过！")
                passed += 1
        
        # 打印总结
        total = passed + failed
        print(f"\n{'='*80}")
        print("📊 测试总结")
        print("=" * 80)
        print(f"总测试数: {total}")
        print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ 失败: {failed} ({failed/total*100:.1f}%)")


if __name__ == "__main__":
    tester = SimpleChatTester()
    tester.run_tests()

