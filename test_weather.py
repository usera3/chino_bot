"""测试天气工具"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from tools.basic_tools import GetWeatherTool

def test_weather():
    """测试天气查询"""
    print("=" * 60)
    print("测试天气工具")
    print("=" * 60)
    
    tool = GetWeatherTool()
    
    # 测试多个城市
    cities = ["北京", "上海", "深圳", "杭州"]
    
    for city in cities:
        print(f"\n查询 {city} 的天气...")
        result = tool._run(city)
        print(result)
        print("-" * 60)

if __name__ == "__main__":
    test_weather()
