"""测试 NVIDIA DeepSeek API"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_nvidia_api():
    """测试 NVIDIA API"""
    import httpx
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    url = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/853b883c-b3ae-41bc-aa2d-b147389f6490"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messages": [
            {"role": "user", "content": "你好"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    print("🔍 测试 NVIDIA DeepSeek API...")
    print(f"URL: {url}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            print(f"\n✅ 状态码: {response.status_code}")
            print(f"📄 响应: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n📊 JSON 数据结构:")
                print(f"  Keys: {list(data.keys())}")
                if "choices" in data:
                    print(f"  Choices: {data['choices']}")
            else:
                print(f"\n❌ 请求失败")
                
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_nvidia_api())




