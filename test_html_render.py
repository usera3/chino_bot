"""测试 HTML 渲染工具"""
import asyncio
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# 初始化 NoneBot
nonebot.init()
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 加载 htmlrender 插件
nonebot.load_plugin("nonebot_plugin_htmlrender")

from tools.html_render_tool import html_render_tool


async def test_render_heart():
    """测试渲染爱心"""
    print("=" * 50)
    print("测试 1: 渲染红色爱心")
    print("=" * 50)
    
    html_code = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .heart {
            width: 100px;
            height: 100px;
            background: red;
            position: relative;
            transform: rotate(-45deg);
            animation: beat 1s infinite;
        }
        .heart::before,
        .heart::after {
            content: "";
            width: 100px;
            height: 100px;
            background: red;
            border-radius: 50%;
            position: absolute;
        }
        .heart::before {
            top: -50px;
            left: 0;
        }
        .heart::after {
            left: 50px;
            top: 0;
        }
        @keyframes beat {
            0%, 100% { transform: rotate(-45deg) scale(1); }
            50% { transform: rotate(-45deg) scale(1.1); }
        }
    </style>
</head>
<body>
    <div class="heart"></div>
</body>
</html>"""
    
    result = await html_render_tool._arun(html_code=html_code, width=400, height=400)
    print(result)
    print()


async def test_render_chart():
    """测试渲染简单图表"""
    print("=" * 50)
    print("测试 2: 渲染数据统计图表")
    print("=" * 50)
    
    html_code = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #f5f5f5;
            font-family: Arial, sans-serif;
        }
        .chart-container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .chart-title {
            text-align: center;
            font-size: 24px;
            margin-bottom: 20px;
            color: #333;
        }
        .bar-chart {
            display: flex;
            align-items: flex-end;
            height: 200px;
            gap: 20px;
        }
        .bar {
            flex: 1;
            background: linear-gradient(to top, #667eea, #764ba2);
            border-radius: 5px 5px 0 0;
            position: relative;
            transition: all 0.3s;
        }
        .bar-label {
            position: absolute;
            bottom: -25px;
            width: 100%;
            text-align: center;
            font-size: 14px;
            color: #666;
        }
        .bar-value {
            position: absolute;
            top: -25px;
            width: 100%;
            text-align: center;
            font-weight: bold;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="chart-container">
        <div class="chart-title">📊 月度数据统计</div>
        <div class="bar-chart">
            <div class="bar" style="height: 60%;">
                <div class="bar-value">60</div>
                <div class="bar-label">一月</div>
            </div>
            <div class="bar" style="height: 80%;">
                <div class="bar-value">80</div>
                <div class="bar-label">二月</div>
            </div>
            <div class="bar" style="height: 45%;">
                <div class="bar-value">45</div>
                <div class="bar-label">三月</div>
            </div>
            <div class="bar" style="height: 90%;">
                <div class="bar-value">90</div>
                <div class="bar-label">四月</div>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    result = await html_render_tool._arun(html_code=html_code, width=600, height=400)
    print(result)
    print()


async def test_render_card():
    """测试渲染生日贺卡"""
    print("=" * 50)
    print("测试 3: 渲染生日贺卡")
    print("=" * 50)
    
    html_code = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        }
        .card {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 400px;
        }
        .emoji {
            font-size: 80px;
            margin-bottom: 20px;
        }
        .title {
            font-size: 32px;
            font-weight: bold;
            color: #ff6b6b;
            margin-bottom: 15px;
        }
        .message {
            font-size: 18px;
            color: #666;
            line-height: 1.6;
        }
        .decoration {
            margin-top: 20px;
            font-size: 24px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="emoji">🎂</div>
        <div class="title">生日快乐！</div>
        <div class="message">
            愿你的每一天都充满欢笑，<br>
            每一刻都洋溢幸福！<br>
            祝你生日快乐，心想事成！
        </div>
        <div class="decoration">🎉 🎈 🎁 🎊</div>
    </div>
</body>
</html>"""
    
    result = await html_render_tool._arun(html_code=html_code, width=600, height=500)
    print(result)
    print()


async def main():
    """运行所有测试"""
    print("\n🎨 HTML 渲染工具测试\n")
    
    await test_render_heart()
    await test_render_chart()
    await test_render_card()
    
    print("=" * 50)
    print("✅ 所有测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
