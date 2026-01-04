# ModelScope 集成指南

## 📚 概述

ModelScope（魔搭社区）是阿里巴巴达摩院推出的开源模型社区平台，提供丰富的预训练 AI 模型。本指南介绍如何在智脑机器人项目中集成 ModelScope 的服务。

官方网站：https://www.modelscope.cn/

---

## 🎯 集成场景

### 1. **情感分析工具**
- **用途**：分析用户消息的情感倾向（积极/消极/中性）
- **价值**：增强机器人的情感系统，更准确地感知用户情绪
- **模型**：`damo/nlp_structbert_sentiment-classification_chinese-base`

### 2. **文本分类工具**
- **用途**：识别用户消息的意图类型（问候/提问/闲聊/求助等）
- **价值**：提升对话理解能力，更智能地响应用户
- **模型**：`damo/nlp_structbert_sentence-similarity_chinese-base`

### 3. **图像理解**（可选）
- **用途**：替代当前的 Gemini Vision API
- **价值**：更稳定的本地图像识别能力
- **模型**：`damo/multi-modal_clip-vit-large-patch14`

### 4. **语音合成**（可选）
- **用途**：替代或增强当前的 TTS 系统
- **价值**：提供更自然的中文语音合成
- **模型**：`damo/speech_sambert-hifigan_tts_zh-cn_16k`

---

## 📦 安装步骤

### 1. 安装 ModelScope SDK

```bash
# 基础安装
pip install modelscope

# 如果需要使用 PyTorch 模型（推荐）
pip install torch

# 如果需要使用 TensorFlow 模型
pip install tensorflow
```

### 2. 验证安装

```python
from modelscope.pipelines import pipeline
print("✅ ModelScope SDK 安装成功！")
```

---

## 🛠️ 集成方法

### 方法一：作为独立工具集成（推荐）

已为你创建了 `tools/modelscope_tool.py`，包含：
- `ModelScopeSentimentTool` - 情感分析工具
- `ModelScopeTextClassificationTool` - 文本分类工具

#### 启用步骤：

1. **在 `function_calling_agent.py` 中注册工具**：

```python
from tools.modelscope_tool import ModelScopeSentimentTool

# 在 _register_tools 方法中添加
self.tools = {
    # ... 其他工具 ...
    "sentiment_analysis": ModelScopeSentimentTool(),
}
```

2. **更新系统提示词**（在 `role_agent.py` 中）：

```python
# 在 _build_system_prompt 的"何时调用工具"部分添加
8. 用户表达强烈情绪时 → 可调用 sentiment_analysis 了解情感倾向
```

3. **重启机器人**：

```bash
cd new-bot
./stop.sh
./start.sh
```

### 方法二：直接在情感系统中使用

在 `services/emotion_service.py` 中集成情感分析：

```python
from modelscope.pipelines import pipeline

class EmotionService:
    def __init__(self):
        # ... 现有代码 ...
        
        # 初始化 ModelScope 情感分析
        try:
            self.sentiment_pipeline = pipeline(
                'sentiment-analysis',
                model='damo/nlp_structbert_sentiment-classification_chinese-base'
            )
        except:
            self.sentiment_pipeline = None
    
    async def analyze_user_sentiment(self, message: str):
        """使用 ModelScope 分析用户情感"""
        if not self.sentiment_pipeline:
            return None
        
        try:
            result = self.sentiment_pipeline(message)
            sentiment = result['output']  # positive/negative/neutral
            
            # 根据情感调整机器人状态
            if sentiment == 'negative':
                # 用户情绪消极，机器人应该更温柔
                return {'mood': 'concerned', 'arousal': -0.2}
            elif sentiment == 'positive':
                # 用户情绪积极，机器人也更开心
                return {'mood': 'happy', 'pleasure': 0.3}
            
            return {'mood': 'neutral'}
        except Exception as e:
            logger.error(f"情感分析失败: {e}")
            return None
```

---

## 🎨 实用示例

### 示例 1：情感增强对话

```python
# 在 role_agent.py 的 chat 方法中
user_sentiment = await self.emotion_service.analyze_user_sentiment(user_message)

if user_sentiment and user_sentiment['mood'] == 'concerned':
    # 用户情绪低落，给予安慰
    context_parts.append("[系统提示：用户情绪低落，请给予温暖的回应]")
```

### 示例 2：智能意图识别

```python
from modelscope.pipelines import pipeline

intent_classifier = pipeline(
    'text-classification',
    model='damo/nlp_structbert_sentence-similarity_chinese-base'
)

def detect_user_intent(message: str):
    """识别用户意图"""
    # 定义意图模板
    intents = {
        'greeting': ['你好', '早上好', '晚安'],
        'question': ['什么', '为什么', '怎么'],
        'help': ['帮我', '能不能', '可以吗'],
        'chat': ['聊天', '无聊', '陪我']
    }
    
    # 使用 ModelScope 进行相似度匹配
    # ... 实现逻辑 ...
```

---

## 🚀 高级应用

### 1. 多模态理解（图文结合）

```python
from modelscope.pipelines import pipeline

# 图像理解 + 文本生成
vision_pipeline = pipeline('multi-modal-embedding', 
                          model='damo/multi-modal_clip-vit-large-patch14')

# 可以同时理解图片和文字，生成更准确的回复
```

### 2. 语音交互增强

```python
from modelscope.pipelines import pipeline

# 中文语音合成
tts_pipeline = pipeline('text-to-speech',
                        model='damo/speech_sambert-hifigan_tts_zh-cn_16k')

# 生成更自然的中文语音
audio = tts_pipeline('智脑为你服务！')
```

---

## ⚠️ 注意事项

### 1. 性能考虑
- **模型加载时间**：首次加载模型需要下载，可能需要几分钟
- **内存占用**：深度学习模型通常需要较大内存（建议 4GB+）
- **推理速度**：CPU 推理较慢，建议使用 GPU（如果可用）

### 2. 模型缓存
- ModelScope 会自动将模型缓存到 `~/.cache/modelscope/`
- 首次使用需要下载模型，后续使用会直接从缓存加载

### 3. 错误处理
- 建议使用 `try-except` 包裹所有 ModelScope 调用
- 提供降级方案（如模型不可用时使用简单规则）

---

## 📊 推荐集成优先级

### 高优先级（立即可用）
1. ✅ **情感分析工具** - 增强情感系统
   - 易于集成
   - 效果明显
   - 资源占用小

### 中优先级（按需使用）
2. ⚠️ **文本分类工具** - 意图识别
   - 需要调优
   - 可能与现有 AI 重叠
   
### 低优先级（可选）
3. 🔄 **图像理解** - 替代 Gemini
   - 需要 GPU 加速
   - 配置较复杂
   
4. 🔄 **语音合成** - 增强 TTS
   - 当前 TTS 已可用
   - 可作为备选方案

---

## 🔗 参考资源

- [ModelScope 官方文档](https://modelscope.cn/docs)
- [ModelScope Python SDK](https://github.com/modelscope/modelscope)
- [模型浏览](https://modelscope.cn/models)
- [API 文档](https://modelscope.cn/docs/api)

---

## 💡 下一步建议

1. **先安装 SDK 测试**：
   ```bash
   pip install modelscope
   ```

2. **测试情感分析工具**：
   ```bash
   cd new-bot
   python -c "from tools.modelscope_tool import modelscope_sentiment_tool; print(modelscope_sentiment_tool.is_available())"
   ```

3. **如果测试成功，集成到 Function Calling Agent**

4. **观察效果，决定是否扩展更多功能**

有任何问题随时告诉我！😊

