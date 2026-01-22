# HTML 渲染功能说明

## 📖 功能概述

HTML 渲染功能允许用户通过自然语言描述，让 AI 生成 HTML/CSS 代码并渲染成图片发送。这是一个强大的可视化工具，可以快速创建各种图形、图表、卡片等。

## ✨ 使用场景

### 1. 绘制图形
- "帮我画一个红色的爱心"
- "画一个笑脸"
- "生成一个五角星"
- "画一个彩虹"

### 2. 生成图表
- "生成一个数据统计图表"
- "做一个柱状图，显示1-4月的数据"
- "画一个饼图"

### 3. 制作卡片
- "做一张生日贺卡"
- "生成一张节日祝福卡片"
- "做一个名片"

### 4. 创建装饰图
- "生成一个渐变背景"
- "做一个带动画的按钮"
- "创建一个加载动画"

## 🛠️ 技术实现

### 核心组件

1. **nonebot-plugin-htmlrender**
   - 基于 Playwright 的 HTML 渲染引擎
   - 支持完整的 HTML5/CSS3 特性
   - 自动处理字体、图片等资源

2. **LangChain Tool**
   - 工具名称：`render_html`
   - 输入：HTML 代码、宽度、高度
   - 输出：PNG 图片

3. **QQ 消息发送**
   - 自动检测群聊/私聊
   - 直接发送渲染后的图片
   - 同时保存到本地

### 工作流程

```
用户描述 → AI 生成 HTML/CSS → 渲染成图片 → 发送到 QQ
```

## 📝 使用示例

### 示例 1: 红色爱心

**用户输入：**
```
帮我画一个红色的爱心
```

**AI 生成的 HTML：**
```html
<!DOCTYPE html>
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
    </style>
</head>
<body>
    <div class="heart"></div>
</body>
</html>
```

**效果：**
- 渲染成 400x400 的 PNG 图片
- 紫色渐变背景
- 红色爱心居中显示

### 示例 2: 数据统计图表

**用户输入：**
```
生成一个月度数据统计图表
```

**AI 生成的 HTML：**
```html
<!DOCTYPE html>
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
</html>
```

**效果：**
- 渲染成 600x400 的 PNG 图片
- 白色卡片背景
- 柱状图显示 4 个月的数据

### 示例 3: 生日贺卡

**用户输入：**
```
做一张生日贺卡
```

**AI 生成的 HTML：**
```html
<!DOCTYPE html>
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
</html>
```

**效果：**
- 渲染成 600x500 的 PNG 图片
- 橙色渐变背景
- 白色卡片，包含祝福语和装饰

## 🎯 AI 使用指南

### 何时调用此工具

当用户的请求包含以下关键词时，应该调用 `render_html` 工具：

- **绘制类**：画、绘制、生成图形
- **图表类**：图表、统计图、柱状图、饼图
- **卡片类**：贺卡、名片、卡片
- **装饰类**：背景、动画、装饰

### HTML 代码要求

1. **必须包含完整结构**
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <meta charset="UTF-8">
       <style>
           /* CSS 样式 */
       </style>
   </head>
   <body>
       <!-- HTML 内容 -->
   </body>
   </html>
   ```

2. **CSS 写在 `<style>` 标签内**
   - 不要使用外部 CSS 文件
   - 所有样式都内联在 HTML 中

3. **推荐使用的技术**
   - Flexbox 布局
   - CSS Grid 布局
   - CSS 动画（@keyframes）
   - 渐变背景（linear-gradient）
   - 阴影效果（box-shadow）

4. **避免使用**
   - 外部资源（图片、字体等）
   - JavaScript（会被忽略）
   - 复杂的交互（这是静态图片）

### 参数选择

- **width**：图片宽度（像素）
  - 小图形：400-600
  - 图表：600-800
  - 卡片：500-700

- **height**：图片高度（像素）
  - 正方形：与 width 相同
  - 横向：width 的 60-80%
  - 纵向：width 的 120-150%

## 🔧 技术细节

### 渲染参数

```python
image_bytes = await html_to_pic(
    html=html_code,
    viewport={"width": width, "height": height},
    type="png",
    device_scale_factor=2,  # 2倍清晰度
    wait=500,  # 等待 500ms 确保渲染完成
)
```

### 图片保存

- **路径**：`./data/temp_images/`
- **命名**：`render_{timestamp}.png`
- **格式**：PNG（支持透明背景）

### QQ 发送

```python
# 构建图片消息
image_msg = MessageSegment.image(f"file:///{image_path.absolute()}")

# 群聊
await bot.send_group_msg(group_id=group_id, message=image_msg)

# 私聊
await bot.send_private_msg(user_id=user_id, message=image_msg)
```

## 📊 性能指标

- **渲染速度**：1-3 秒
- **图片大小**：20-500 KB
- **支持分辨率**：最高 4K
- **并发支持**：是（每个请求独立）

## ⚠️ 注意事项

1. **首次使用需要下载 Chromium**
   - 大小：约 160 MB
   - 自动下载，无需手动操作

2. **内存占用**
   - 每次渲染约占用 100-200 MB
   - 渲染完成后自动释放

3. **不支持的功能**
   - JavaScript 交互
   - 外部资源加载
   - 视频/音频

4. **最佳实践**
   - 保持 HTML 简洁
   - 使用内联样式
   - 避免过度复杂的布局

## 🚀 未来扩展

### 可能的改进方向

1. **模板库**
   - 预设常用模板
   - 快速生成标准图表

2. **数据绑定**
   - 支持动态数据
   - 自动生成图表

3. **样式库**
   - 预设配色方案
   - 统一视觉风格

4. **批量生成**
   - 一次生成多张图片
   - 支持批量导出

## 📚 相关文档

- [nonebot-plugin-htmlrender 官方文档](https://github.com/kexue-z/nonebot-plugin-htmlrender)
- [Playwright 文档](https://playwright.dev/)
- [HTML5 参考](https://developer.mozilla.org/zh-CN/docs/Web/HTML)
- [CSS3 参考](https://developer.mozilla.org/zh-CN/docs/Web/CSS)

## 🎉 总结

HTML 渲染功能为机器人提供了强大的可视化能力，让用户可以通过自然语言快速生成各种图片。这个功能的核心优势在于：

- ✅ **简单易用**：用户只需描述，AI 自动生成
- ✅ **功能强大**：支持完整的 HTML5/CSS3
- ✅ **即时反馈**：渲染后直接发送到 QQ
- ✅ **灵活扩展**：可以创建任何 HTML 能实现的内容

通过这个功能，机器人不再局限于文字交流，而是可以创造丰富的视觉内容！
