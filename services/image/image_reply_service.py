"""
图像回复生成服务 - Service Layer
职责：根据情感状态生成个性化图像回复
代码量：~400 行（业务逻辑）
"""
from typing import Optional, Dict, List
from nonebot.log import logger
import random
import time


class ImageReplyService:
    """图像回复生成服务"""
    
    async def generate_reply(
        self,
        description: str,
        elements: Dict[str, any],
        emotion_style: Optional[Dict] = None
    ) -> str:
        """
        生成个性化回复
        
        Args:
            description: 图像描述
            elements: 提取的关键元素 {'subject': str, 'features': list, 'atmosphere': str}
            emotion_style: 情感风格 {'style': str, 'happiness': float, ...}
        
        Returns:
            回复文本
        """
        # 智能分析图片内容
        content_analysis = self._analyze_content(description, elements)
        
        # 确定回复风格（增加随机性）
        style = self._determine_style(emotion_style)
        
        # 提取关键信息
        subject = elements.get('subject', '东西')
        features = elements.get('features', [])
        atmosphere = elements.get('atmosphere', '')
        
        # 生成多样化回复
        reply = self._generate_creative_reply(
            style, subject, features, atmosphere, content_analysis, description
        )
        
        logger.info(f"🎭 图片回复风格: {style} | 创意度: {content_analysis['creativity']}")
        
        # 尝试使用AI生成创意回复
        ai_reply = await self._generate_ai_creative_reply(description)
        if ai_reply:
            return ai_reply
        
        return reply
    
    def _analyze_content(self, description: str, elements: Dict) -> Dict:
        """智能分析图片内容"""
        # 分析图片类型
        content_type = self._classify_content(description)
        
        # 分析情感倾向
        emotion_tone = self._analyze_emotion_tone(description)
        
        # 分析创意度
        creativity = self._calculate_creativity(description, elements)
        
        # 分析互动性
        interactivity = self._calculate_interactivity(content_type, emotion_tone)
        
        return {
            'type': content_type,
            'emotion': emotion_tone,
            'creativity': creativity,
            'interactivity': interactivity
        }
    
    def _classify_content(self, description: str) -> str:
        """分类图片内容"""
        if any(word in description for word in ['表情包', '表情', 'emoji', '贴纸']):
            return 'emoticon'
        elif any(word in description for word in ['人物', '人', '女孩', '男孩', '少女', '少年']):
            return 'person'
        elif any(word in description for word in ['动物', '猫', '狗', '鸟', '宠物']):
            return 'animal'
        elif any(word in description for word in ['风景', '景色', '自然', '树', '花', '山', '海']):
            return 'landscape'
        elif any(word in description for word in ['食物', '美食', '吃', '饭', '蛋糕', '甜点']):
            return 'food'
        else:
            return 'other'
    
    def _analyze_emotion_tone(self, description: str) -> str:
        """分析情感倾向"""
        positive_words = ['开心', '快乐', '笑', '可爱', '美丽', '漂亮', '好看', '喜欢']
        negative_words = ['哭', '难过', '伤心', '生气', '愤怒', '累', '疲惫']
        neutral_words = ['普通', '一般', '正常', '平静']
        
        pos_count = sum(1 for word in positive_words if word in description)
        neg_count = sum(1 for word in negative_words if word in description)
        neu_count = sum(1 for word in neutral_words if word in description)
        
        if pos_count > neg_count and pos_count > neu_count:
            return 'positive'
        elif neg_count > pos_count and neg_count > neu_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _calculate_creativity(self, description: str, elements: Dict) -> int:
        """计算创意度 (1-5)"""
        creativity_score = 1
        
        # 描述长度影响创意度
        if len(description) > 100:
            creativity_score += 1
        
        # 特征数量影响创意度
        features = elements.get('features', [])
        if len(features) > 2:
            creativity_score += 1
        
        # 特殊词汇影响创意度
        special_words = ['独特', '特别', '有趣', '创意', '艺术', '设计']
        if any(word in description for word in special_words):
            creativity_score += 1
        
        # 随机增加创意度
        if random.random() < 0.3:
            creativity_score += 1
        
        return min(creativity_score, 5)
    
    def _calculate_interactivity(self, content_type: str, emotion_tone: str) -> int:
        """计算互动性 (1-5)"""
        interactivity = 2  # 基础互动性
        
        # 内容类型影响互动性
        if content_type in ['person', 'emoticon']:
            interactivity += 2
        elif content_type in ['animal', 'food']:
            interactivity += 1
        
        # 情感倾向影响互动性
        if emotion_tone == 'positive':
            interactivity += 1
        elif emotion_tone == 'negative':
            interactivity -= 1
        
        return max(1, min(interactivity, 5))
    
    def _determine_style(self, emotion_style: Optional[Dict]) -> str:
        """确定回复风格（大幅增加随机性）"""
        # 完全随机化风格选择，避免固定模式
        all_styles = [
            "毒舌", "腹黑", "傲娇", "元气", "慵懒", "病娇", 
            "天然", "中二", "吐槽", "温柔", "沙雕", "文艺"
        ]
        
        if not emotion_style:
            return random.choice(all_styles)
        
        style = emotion_style.get("style", "随机")
        if style == "随机":
            return random.choice(all_styles)
        
        return style
    
    def _generate_creative_reply(
        self,
        style: str,
        subject: str,
        features: List[str],
        atmosphere: str,
        content_analysis: Dict,
        description: str
    ) -> str:
        """生成创意回复（大幅优化幽默感和创意）"""
        # 提取图片的有趣特征
        interesting_features = self._extract_interesting_features(description)
        
        # 根据图片内容生成创意回复
        return self._generate_humorous_reply(style, subject, features, interesting_features, content_analysis, description)
    
    def _select_reply_strategy(self, content_analysis: Dict) -> str:
        """选择回复策略"""
        creativity = content_analysis['creativity']
        interactivity = content_analysis['interactivity']
        content_type = content_analysis['type']
        
        # 高创意度 -> 创意回复
        if creativity >= 4:
            return "creative"
        # 高互动性 -> 互动回复
        elif interactivity >= 4:
            return "interactive"
        # 人物/表情包 -> 情感回复
        elif content_type in ['person', 'emoticon']:
            return "emotional"
        # 其他 -> 智能回复
        else:
            return "smart"
    
    def _generate_interactive_reply(self, style: str, subject: str, features: List[str], atmosphere: str, analysis: Dict) -> str:
        """生成互动性回复"""
        if style == "毒舌":
            return self._generate_dushe_interactive(subject, features, atmosphere)
        elif style == "腹黑":
            return self._generate_fuhei_interactive(subject, features, atmosphere)
        elif style == "傲娇":
            return self._generate_aojiao_interactive(subject, features, atmosphere)
        elif style == "元气":
            return self._generate_yuanqi_interactive(subject, features, atmosphere)
        elif style == "沙雕":
            return self._generate_shadiao_interactive(subject, features, atmosphere)
        elif style == "文艺":
            return self._generate_wenyi_interactive(subject, features, atmosphere)
        else:
            return self._generate_smart_interactive(subject, features, atmosphere, style)
    
    def _generate_creative_reply_content(self, style: str, subject: str, features: List[str], atmosphere: str, analysis: Dict, description: str) -> str:
        """生成创意内容回复"""
        # 提取描述中的有趣细节
        interesting_details = self._extract_interesting_details(description)
        
        if style == "中二":
            return self._generate_zhonger_creative(subject, features, interesting_details)
        elif style == "吐槽":
            return self._generate_tucao_creative(subject, features, interesting_details)
        elif style == "天然":
            return self._generate_tianran_creative(subject, features, interesting_details)
        elif style == "沙雕":
            return self._generate_shadiao_creative(subject, features, interesting_details)
        elif style == "文艺":
            return self._generate_wenyi_creative(subject, features, interesting_details)
        else:
            return self._generate_general_creative(subject, features, interesting_details, style)
    
    def _generate_emotional_reply(self, style: str, subject: str, features: List[str], atmosphere: str, analysis: Dict) -> str:
        """生成情感回复"""
        emotion_tone = analysis['emotion']
        
        if style == "温柔":
            return self._generate_wenrou_emotional(subject, features, emotion_tone)
        elif style == "病娇":
            return self._generate_bingjiao_emotional(subject, features, emotion_tone)
        elif style == "慵懒":
            return self._generate_yonglan_emotional(subject, features, emotion_tone)
        elif style == "沙雕":
            return self._generate_shadiao_emotional(subject, features, emotion_tone)
        elif style == "文艺":
            return self._generate_wenyi_emotional(subject, features, emotion_tone)
        else:
            return self._generate_style_emotional(style, subject, features, emotion_tone)
    
    def _generate_smart_reply(self, style: str, subject: str, features: List[str], atmosphere: str, analysis: Dict) -> str:
        """生成智能回复"""
        # 根据时间和内容智能选择回复
        current_hour = time.localtime().tm_hour
        
        if 6 <= current_hour < 12:
            time_context = "早上"
        elif 12 <= current_hour < 18:
            time_context = "下午"
        elif 18 <= current_hour < 22:
            time_context = "晚上"
        else:
            time_context = "深夜"
        
        return self._generate_contextual_reply(style, subject, features, time_context, analysis)
    
    def _generate_dushe(self, subject: str, feat: str, atm: str) -> str:
        """毒舌风格"""
        if atm:
            responses = [
                f"就这？{atm}的{subject}？审美有待提高啊",
                f"切，就算{subject}{feat}，也不会比我好看的",
                f"emmm...{subject}...也就那样吧",
            ]
        else:
            responses = [
                f"就这？{subject}也敢发出来？",
                f"切，{subject}而已嘛",
            ]
        return random.choice(responses)
    
    def _generate_fuhei(self, subject: str, feat: str, atm: str) -> str:
        """腹黑风格"""
        if feat:
            responses = [
                f"哇~{subject}{feat}呢~真有你的~（笑",
                f"呵呵，{subject}...挺有意思的呢~",
            ]
        else:
            responses = [
                f"哇~{subject}呢~真有你的~（笑",
                f"呵呵，{subject}...挺有意思的呢~",
            ]
        return random.choice(responses)
    
    def _generate_aojiao(self, subject: str, feat: str, atm: str) -> str:
        """傲娇风格"""
        if atm:
            responses = [
                f"哼，就算{subject}再{atm}，我、我也不会说什么的！",
                f"{subject}而已嘛...也就还行吧（小声：其实挺{atm}的",
            ]
        else:
            responses = [
                f"哼，{subject}而已嘛...也就还行吧",
                f"切，{subject}...才、才不是因为好看我才看的！",
            ]
        return random.choice(responses)
    
    def _generate_bingjiao(self, subject: str, feat: str, atm: str) -> str:
        """病娇风格"""
        if feat:
            responses = [
                f"呐呐~{subject}{feat}...只给我一个人看的吧？我好喜欢呢❤",
                f"{subject}真{atm if atm else '好看'}...你是特意发给我的吧？❤",
            ]
        else:
            responses = [
                f"呐呐~{subject}...只给我一个人看的吧？❤",
                f"{subject}...是想让我吃醋吗？",
            ]
        return random.choice(responses)
    
    def _generate_yonglan(self, subject: str, feat: str, atm: str) -> str:
        """慵懒风格"""
        responses = [
            f"嗯...{subject}啊...好累不想说话...",
            f"哦...{subject}...还行吧...（打哈欠",
            f"{subject}嘛...懒得评价了...",
        ]
        return random.choice(responses)
    
    def _generate_yuanqi(self, subject: str, feat: str, atm: str) -> str:
        """元气风格"""
        if atm:
            responses = [
                f"哇！好{atm}的{subject}！超级喜欢！！",
                f"天啊！{subject}{feat}！太棒了吧！",
                f"哦哦哦！{atm}的{subject}！！",
            ]
        else:
            responses = [
                f"哇！{subject}！好棒啊！！",
                f"天啊！{subject}{feat}！太有趣了！",
            ]
        return random.choice(responses)
    
    def _extract_interesting_features(self, description: str) -> Dict[str, any]:
        """提取图片的有趣特征"""
        features = {
            'colors': [],
            'objects': [],
            'actions': [],
            'emotions': [],
            'special': []
        }
        
        # 提取颜色
        color_words = ['红色', '蓝色', '绿色', '黄色', '紫色', '粉色', '白色', '黑色', '灰色', '橙色']
        for color in color_words:
            if color in description:
                features['colors'].append(color)
        
        # 提取物体
        object_words = ['头带', '花朵', '纸条', '衣服', '头发', '眼睛', '笑容', '手指', '手套', '耳环']
        for obj in object_words:
            if obj in description:
                features['objects'].append(obj)
        
        # 提取动作
        action_words = ['笑', '哭', '思考', '惊讶', '害羞', '生气', '开心', '难过']
        for action in action_words:
            if action in description:
                features['actions'].append(action)
        
        # 提取特殊特征
        special_words = ['可爱', '搞笑', '奇怪', '神秘', '独特', '特别', '有趣', '漂亮', '帅气']
        for special in special_words:
            if special in description:
                features['special'].append(special)
        
        return features
    
    def _generate_humorous_reply(self, style: str, subject: str, features: List[str], interesting_features: Dict, content_analysis: Dict, description: str) -> str:
        """生成幽默创意回复（大幅增加随机性）"""
        logger.info(f"🎨 幽默回复生成: 风格={style}, 主体={subject}, 特征={interesting_features}")
        
        # 大幅增加随机性，30%概率切换风格
        if random.random() < 0.30:  # 30%概率切换风格
            all_styles = ["毒舌", "腹黑", "傲娇", "元气", "沙雕", "文艺", "吐槽", "中二", "温柔", "天然"]
            style = random.choice(all_styles)
            logger.info(f"🎲 随机切换风格: {style}")
        
        # 根据风格和图片特征生成幽默回复
        if style == "毒舌":
            return self._generate_dushe_humorous(subject, interesting_features, description)
        elif style == "腹黑":
            return self._generate_fuhei_humorous(subject, interesting_features, description)
        elif style == "傲娇":
            return self._generate_aojiao_humorous(subject, interesting_features, description)
        elif style == "元气":
            return self._generate_yuanqi_humorous(subject, interesting_features, description)
        elif style == "沙雕":
            return self._generate_shadiao_humorous(subject, interesting_features, description)
        elif style == "文艺":
            return self._generate_wenyi_humorous(subject, interesting_features, description)
        elif style == "吐槽":
            return self._generate_tucao_humorous(subject, interesting_features, description)
        elif style == "中二":
            return self._generate_zhonger_humorous(subject, interesting_features, description)
        elif style == "温柔":
            return self._generate_wenrou_humorous(subject, interesting_features, description)
        elif style == "天然":
            return self._generate_tianran_humorous(subject, interesting_features, description)
        else:
            return self._generate_random_humorous(subject, interesting_features, description)
    
    def _generate_dushe_humorous(self, subject: str, features: Dict, description: str) -> str:
        """毒舌幽默回复"""
        colors = features.get('colors', [])
        objects = features.get('objects', [])
        actions = features.get('actions', [])
        
        if colors and objects:
            color = colors[0]
            obj = objects[0]
            responses = [
                f"切，{color}的{obj}？就这？我见过更好的~",
                f"哼，{color}{obj}而已，有什么好炫耀的？",
                f"就这？{color}的{obj}？审美有待提高啊~",
                f"切，就算{color}{obj}再好看，也不会比我好看的~"
            ]
        elif "女孩" in subject or "人物" in subject:
            responses = [
                f"哼，{subject}？就这？我见过更好的~",
                f"切，{subject}而已，有什么好炫耀的？",
                f"就这？{subject}？审美有待提高啊~",
                f"切，就算{subject}再好看，也不会比我好看的~"
            ]
        else:
            responses = [
                f"哼，{subject}？就这？我见过更好的~",
                f"切，{subject}而已，有什么好炫耀的？",
                f"就这？{subject}？审美有待提高啊~"
            ]
        
        return random.choice(responses)
    
    def _generate_fuhei_humorous(self, subject: str, features: Dict, description: str) -> str:
        """腹黑幽默回复（彻底重写，增加创意）"""
        # 完全重写，增加更多创意回复
        responses = [
            f"呵，{subject}？这种程度我见过更好的~",
            f"嗯？{subject}？看起来像是随便弄的~",
            f"哦？{subject}？这种质量...有点差呢~",
            f"呵呵，{subject}？我建议换个方式~",
            f"嗯嗯，{subject}...我记住了，下次别这样~",
            f"切，{subject}？就这？我见过更好的~",
            f"哼，{subject}而已，有什么好炫耀的？",
            f"就这？{subject}？审美有待提高啊~",
            f"切，就算{subject}再好看，也不会比我好看的~",
            f"emmm...{subject}...也就那样吧，不过还算可以"
        ]
        
        return random.choice(responses)
    
    def _generate_aojiao_humorous(self, subject: str, features: Dict, description: str) -> str:
        """傲娇幽默回复"""
        colors = features.get('colors', [])
        objects = features.get('objects', [])
        
        if colors and objects:
            color = colors[0]
            obj = objects[0]
            responses = [
                f"哼，{color}的{obj}而已嘛...也就还行吧",
                f"切，{color}{obj}...才、才不是因为好看我才看的！",
                f"哼，就算{color}{obj}再好看，我、我也不会说什么的！",
                f"{color}{obj}而已嘛...也就还行吧（小声：其实挺好看的"
            ]
        else:
            responses = [
                f"哼，{subject}而已嘛...也就还行吧",
                f"切，{subject}...才、才不是因为好看我才看的！",
                f"哼，就算{subject}再好看，我、我也不会说什么的！",
                f"{subject}而已嘛...也就还行吧（小声：其实挺好看的"
            ]
        
        return random.choice(responses)
    
    def _generate_yuanqi_humorous(self, subject: str, features: Dict, description: str) -> str:
        """元气幽默回复（彻底重写，增加创意）"""
        colors = features.get('colors', [])
        objects = features.get('objects', [])
        actions = features.get('actions', [])
        special = features.get('special', [])
        
        # 根据特征组合生成创意回复
        if colors and objects:
            color = colors[0]
            obj = objects[0]
            if "头发" in obj:
                responses = [
                    f"哇！{color}头发！这个发色太棒了！！",
                    f"天啊！{color}头发！这个颜色我超喜欢！！",
                    f"哦哦哦！{color}头发！！这个发色太美了！！",
                    f"哇塞！{color}头发！这个颜色太赞了！！",
                    f"太棒了！{color}头发！这个发色我超爱！！"
                ]
            elif "眼睛" in obj:
                responses = [
                    f"哇！{color}眼睛！这个颜色太美了！！",
                    f"天啊！{color}眼睛！这个颜色我超喜欢！！",
                    f"哦哦哦！{color}眼睛！！这个颜色太棒了！！",
                    f"哇塞！{color}眼睛！这个颜色太赞了！！",
                    f"太棒了！{color}眼睛！这个颜色我超爱！！"
                ]
            else:
                responses = [
                    f"哇！{color}的{obj}！这个搭配太棒了！！",
                    f"天啊！{color}{obj}！这个组合我超喜欢！！",
                    f"哦哦哦！{color}{obj}！！这个搭配太美了！！",
                    f"哇塞！{color}{obj}！这个组合太赞了！！",
                    f"太棒了！{color}{obj}！这个搭配我超爱！！"
                ]
        elif "可爱" in special:
            responses = [
                f"哇！可爱！这个程度我超喜欢！！",
                f"天啊！可爱！这个程度太棒了！！",
                f"哦哦哦！可爱！！这个程度太美了！！",
                f"哇塞！可爱！这个程度太赞了！！",
                f"太棒了！可爱！这个程度我超爱！！"
            ]
        else:
            responses = [
                f"哇！{subject}！这个程度我超喜欢！！",
                f"天啊！{subject}！这个程度太棒了！！",
                f"哦哦哦！{subject}！！这个程度太美了！！",
                f"哇塞！{subject}！这个程度太赞了！！",
                f"太棒了！{subject}！这个程度我超爱！！"
            ]
        
        return random.choice(responses)
    
    def _generate_shadiao_humorous(self, subject: str, features: Dict, description: str) -> str:
        """沙雕幽默回复"""
        colors = features.get('colors', [])
        objects = features.get('objects', [])
        
        if colors and objects:
            color = colors[0]
            obj = objects[0]
            responses = [
                f"哈哈哈哈{color}的{obj}？这是什么鬼畜画风？",
                f"笑死我了{color}{obj}...这画风我服了",
                f"哈哈哈哈{color}{obj}？这是什么沙雕画风？",
                f"笑死我了{color}{obj}...这画风我服了"
            ]
        else:
            responses = [
                f"哈哈哈哈{subject}？这是什么鬼畜画风？",
                f"笑死我了{subject}...这画风我服了",
                f"哈哈哈哈{subject}？这是什么沙雕画风？",
                f"笑死我了{subject}...这画风我服了"
            ]
        
        return random.choice(responses)
    
    def _generate_wenyi_humorous(self, subject: str, features: Dict, description: str) -> str:
        """文艺幽默回复"""
        colors = features.get('colors', [])
        objects = features.get('objects', [])
        
        if colors and objects:
            color = colors[0]
            obj = objects[0]
            responses = [
                f"嗯...{color}的{obj}...有一种说不出的美感呢~",
                f"哇，{color}{obj}...看起来很有艺术感~",
                f"嗯...{color}{obj}...有一种说不出的美感呢~",
                f"哇，{color}{obj}...看起来很有艺术感~"
            ]
        else:
            responses = [
                f"嗯...{subject}...有一种说不出的美感呢~",
                f"哇，{subject}...看起来很有艺术感~",
                f"嗯...{subject}...有一种说不出的美感呢~",
                f"哇，{subject}...看起来很有艺术感~"
            ]
        
        return random.choice(responses)
    
    def _generate_tucao_humorous(self, subject: str, features: Dict, description: str) -> str:
        """吐槽幽默回复"""
        colors = features.get('colors', [])
        objects = features.get('objects', [])
        
        if colors and objects:
            color = colors[0]
            obj = objects[0]
            responses = [
                f"啊这...{color}的{obj}？这是什么奇怪的画风？",
                f"emmm...{color}{obj}...这画风我有点看不懂...",
                f"啊这...{color}{obj}？这画风有点奇怪啊...",
                f"emmm...{color}{obj}...这画风我有点接受不了..."
            ]
        else:
            responses = [
                f"啊这...{subject}？这是什么奇怪的画风？",
                f"emmm...{subject}...这画风我有点看不懂...",
                f"啊这...{subject}？这画风有点奇怪啊...",
                f"emmm...{subject}...这画风我有点接受不了..."
            ]
        
        return random.choice(responses)
    
    def _generate_zhonger_humorous(self, subject: str, features: Dict, description: str) -> str:
        """中二幽默回复"""
        colors = features.get('colors', [])
        objects = features.get('objects', [])
        
        if colors and objects:
            color = colors[0]
            obj = objects[0]
            responses = [
                f"哼！{color}的{obj}吗？这种程度的力量，还不足以让我认真起来！",
                f"呵，{color}{obj}...在我的眼中，不过是蝼蚁般的存在！",
                f"有趣...{color}{obj}...让我看看你的真正实力吧！",
                f"哼！{color}{obj}？这种程度就想挑战我吗？"
            ]
        else:
            responses = [
                f"哼！{subject}吗？这种程度的力量，还不足以让我认真起来！",
                f"呵，{subject}...在我的眼中，不过是蝼蚁般的存在！",
                f"有趣...{subject}...让我看看你的真正实力吧！",
                f"哼！{subject}？这种程度就想挑战我吗？"
            ]
        
        return random.choice(responses)
    
    def _generate_random_humorous(self, subject: str, features: Dict, description: str) -> str:
        """随机幽默回复"""
        responses = [
            f"哦？{subject}？看起来不错呢~",
            f"嗯嗯，{subject}...挺有意思的~",
            f"哇，{subject}！看起来很棒呢~",
            f"哦哦，{subject}...不错不错~",
            f"嗯，{subject}...挺有趣的~"
        ]
        return random.choice(responses)
    
    def _extract_interesting_details(self, description: str) -> List[str]:
        """提取有趣细节"""
        details = []
        interesting_words = ['独特', '特别', '有趣', '可爱', '奇怪', '神秘', '漂亮', '帅气', '搞笑']
        
        for word in interesting_words:
            if word in description:
                details.append(word)
        
        return details[:3]  # 最多返回3个细节
    
    # ==================== 新的回复生成方法 ====================
    
    def _generate_dushe_interactive(self, subject: str, features: List[str], atmosphere: str) -> str:
        """毒舌互动回复"""
        responses = [
            f"哼，{subject}？就这？我见过更好的~",
            f"切，{subject}而已，有什么好炫耀的？",
            f"emmm...{subject}...也就那样吧，不过还算可以",
            f"就这？{subject}？审美有待提高啊~",
            f"切，就算{subject}再好看，也不会比我好看的~"
        ]
        return random.choice(responses)
    
    def _generate_fuhei_interactive(self, subject: str, features: List[str], atmosphere: str) -> str:
        """腹黑互动回复（大幅增加多样性）"""
        # 根据图片内容生成不同的腹黑回复
        if "女孩" in subject or "人物" in subject:
            responses = [
                f"哦？{subject}？看起来不错呢~（意味深长的笑",
                f"呵呵，{subject}...挺有意思的呢~",
                f"哇~{subject}呢~真有你的~（笑",
                f"嗯嗯，{subject}...我记住了呢~",
                f"呵呵呵，{subject}...很有趣呢~",
                f"哦？{subject}？看起来不错呢~（意味深长的笑",
                f"呵呵，{subject}...挺有意思的呢~",
                f"哇~{subject}呢~真有你的~（笑",
                f"嗯嗯，{subject}...我记住了呢~",
                f"呵呵呵，{subject}...很有趣呢~"
            ]
        elif "表情" in subject or "emoji" in subject:
            responses = [
                f"呵呵，{subject}...挺有意思的呢~",
                f"哇~{subject}呢~真有你的~（笑",
                f"嗯嗯，{subject}...我记住了呢~",
                f"呵呵呵，{subject}...很有趣呢~",
                f"哦？{subject}？看起来不错呢~（意味深长的笑"
            ]
        else:
            responses = [
                f"哇~{subject}呢~真有你的~（笑",
                f"呵呵，{subject}...挺有意思的呢~",
                f"哦？{subject}？看起来不错呢~（意味深长的笑",
                f"嗯嗯，{subject}...我记住了呢~",
                f"呵呵呵，{subject}...很有趣呢~"
            ]
        
        # 增加随机性，避免重复
        if random.random() < 0.3:
            responses.extend([
                f"嗯...{subject}...看起来不错呢~",
                f"哦？{subject}？有意思~",
                f"呵呵，{subject}...我记住了~",
                f"哇，{subject}...挺有趣的~"
            ])
        
        return random.choice(responses)
    
    def _generate_aojiao_interactive(self, subject: str, features: List[str], atmosphere: str) -> str:
        """傲娇互动回复"""
        responses = [
            f"哼，{subject}而已嘛...也就还行吧",
            f"切，{subject}...才、才不是因为好看我才看的！",
            f"哼，就算{subject}再好看，我、我也不会说什么的！",
            f"{subject}而已嘛...也就还行吧（小声：其实挺好看的",
            f"切，{subject}...才、才不是特意发给我的吧？"
        ]
        return random.choice(responses)
    
    def _generate_yuanqi_interactive(self, subject: str, features: List[str], atmosphere: str) -> str:
        """元气互动回复"""
        responses = [
            f"哇！{subject}！好棒啊！！",
            f"天啊！{subject}！太有趣了！",
            f"哦哦哦！{subject}！！超级喜欢！！",
            f"哇塞！{subject}！太棒了吧！",
            f"哇！{subject}！好厉害啊！！"
        ]
        return random.choice(responses)
    
    def _generate_smart_interactive(self, subject: str, features: List[str], atmosphere: str, style: str) -> str:
        """智能互动回复"""
        responses = [
            f"哦？{subject}？看起来不错呢~",
            f"嗯嗯，{subject}...挺有意思的~",
            f"哇，{subject}！看起来很棒呢~",
            f"哦哦，{subject}...不错不错~",
            f"嗯，{subject}...挺有趣的~"
        ]
        return random.choice(responses)
    
    def _generate_zhonger_creative(self, subject: str, features: List[str], details: List[str]) -> str:
        """中二创意回复"""
        responses = [
            f"哼！{subject}吗？这种程度的力量，还不足以让我认真起来！",
            f"呵，{subject}...在我的眼中，不过是蝼蚁般的存在！",
            f"有趣...{subject}...让我看看你的真正实力吧！",
            f"哼！{subject}？这种程度就想挑战我吗？",
            f"呵，{subject}...在我的绝对力量面前，一切都是徒劳！"
        ]
        return random.choice(responses)
    
    def _generate_tucao_creative(self, subject: str, features: List[str], details: List[str]) -> str:
        """吐槽创意回复"""
        responses = [
            f"啊这...{subject}？这是什么奇怪的画风？",
            f"emmm...{subject}...这画风我有点看不懂...",
            f"啊这...{subject}？这画风有点奇怪啊...",
            f"emmm...{subject}...这画风我有点接受不了...",
            f"啊这...{subject}？这是什么奇怪的画风？"
        ]
        return random.choice(responses)
    
    def _generate_tianran_creative(self, subject: str, features: List[str], details: List[str]) -> str:
        """天然创意回复"""
        responses = [
            f"诶？{subject}？看起来好有趣的样子~",
            f"哇，{subject}！看起来好棒呢~",
            f"诶？{subject}？这是什么呀？看起来好有趣~",
            f"哇，{subject}！看起来好厉害的样子~",
            f"诶？{subject}？看起来好有趣的样子~"
        ]
        return random.choice(responses)
    
    def _generate_general_creative(self, subject: str, features: List[str], details: List[str], style: str) -> str:
        """通用创意回复"""
        responses = [
            f"哦？{subject}？看起来挺有意思的~",
            f"嗯嗯，{subject}...挺有趣的~",
            f"哇，{subject}！看起来不错呢~",
            f"哦哦，{subject}...挺有意思的~",
            f"嗯，{subject}...挺有趣的~"
        ]
        return random.choice(responses)
    
    def _generate_wenrou_emotional(self, subject: str, features: List[str], emotion_tone: str) -> str:
        """温柔情感回复"""
        if emotion_tone == 'positive':
            responses = [
                f"哇，{subject}看起来好可爱呢~",
                f"嗯嗯，{subject}...看起来好棒~",
                f"哇，{subject}！看起来好有趣~"
            ]
        elif emotion_tone == 'negative':
            responses = [
                f"嗯...{subject}...看起来有点难过呢...",
                f"嗯嗯，{subject}...看起来有点累呢...",
                f"嗯...{subject}...看起来有点辛苦呢..."
            ]
        else:
            responses = [
                f"嗯，{subject}...看起来不错呢~",
                f"嗯嗯，{subject}...看起来挺好的~",
                f"嗯，{subject}...看起来不错呢~"
            ]
        return random.choice(responses)
    
    def _generate_bingjiao_emotional(self, subject: str, features: List[str], emotion_tone: str) -> str:
        """病娇情感回复"""
        responses = [
            f"呐呐~{subject}...只给我一个人看的吧？我好喜欢呢❤",
            f"{subject}...是想让我吃醋吗？",
            f"呐呐~{subject}...只给我一个人看的吧？❤",
            f"{subject}...是想让我吃醋吗？",
            f"呐呐~{subject}...只给我一个人看的吧？我好喜欢呢❤"
        ]
        return random.choice(responses)
    
    def _generate_yonglan_emotional(self, subject: str, features: List[str], emotion_tone: str) -> str:
        """慵懒情感回复"""
        responses = [
            f"嗯...{subject}啊...好累不想说话...",
            f"哦...{subject}...还行吧...（打哈欠",
            f"{subject}嘛...懒得评价了...",
            f"嗯...{subject}啊...好累...",
            f"哦...{subject}...还行吧..."
        ]
        return random.choice(responses)
    
    def _generate_style_emotional(self, style: str, subject: str, features: List[str], emotion_tone: str) -> str:
        """风格情感回复"""
        responses = [
            f"嗯，{subject}...看起来不错呢~",
            f"嗯嗯，{subject}...看起来挺好的~",
            f"嗯，{subject}...看起来不错呢~"
        ]
        return random.choice(responses)
    
    def _generate_contextual_reply(self, style: str, subject: str, features: List[str], time_context: str, analysis: Dict) -> str:
        """上下文回复"""
        if time_context == "早上":
            responses = [
                f"早上好~{subject}看起来很有精神呢~",
                f"早上好~{subject}看起来不错呢~",
                f"早上好~{subject}看起来很有活力呢~"
            ]
        elif time_context == "下午":
            responses = [
                f"下午好~{subject}看起来不错呢~",
                f"下午好~{subject}看起来很有精神呢~",
                f"下午好~{subject}看起来不错呢~"
            ]
        elif time_context == "晚上":
            responses = [
                f"晚上好~{subject}看起来不错呢~",
                f"晚上好~{subject}看起来很有精神呢~",
                f"晚上好~{subject}看起来不错呢~"
            ]
        else:  # 深夜
            responses = [
                f"这么晚了还发{subject}？看起来不错呢~",
                f"深夜的{subject}...看起来不错呢~",
                f"这么晚了还发{subject}？看起来不错呢~"
            ]
        return random.choice(responses)
    
    # ==================== 原有的回复生成方法（保持兼容） ====================
    
    def _generate_by_style(
        self,
        style: str,
        subject: str,
        feat_desc: str,
        atmosphere: str
    ) -> str:
        """根据风格生成回复（兼容性方法）"""
        
        if style == "毒舌":
            return self._generate_dushe(subject, feat_desc, atmosphere)
        elif style == "腹黑":
            return self._generate_fuhei(subject, feat_desc, atmosphere)
        elif style == "傲娇":
            return self._generate_aojiao(subject, feat_desc, atmosphere)
        elif style == "病娇":
            return self._generate_bingjiao(subject, feat_desc, atmosphere)
        elif style == "慵懒":
            return self._generate_yonglan(subject, feat_desc, atmosphere)
        elif style == "元气":
            return self._generate_yuanqi(subject, feat_desc, atmosphere)
        else:
            return self._generate_default(subject, feat_desc, atmosphere)
    
    def _generate_dushe(self, subject: str, feat: str, atm: str) -> str:
        """毒舌风格"""
        if atm:
            responses = [
                f"就这？{atm}的{subject}？审美有待提高啊",
                f"切，就算{subject}{feat}，也不会比我好看的",
                f"emmm...{subject}...也就那样吧",
            ]
        else:
            responses = [
                f"就这？{subject}也敢发出来？",
                f"切，{subject}而已嘛",
            ]
        return random.choice(responses)
    
    def _generate_fuhei(self, subject: str, feat: str, atm: str) -> str:
        """腹黑风格"""
        if feat:
            responses = [
                f"哇~{subject}{feat}呢~真有你的~（笑",
                f"呵呵，{subject}...挺有意思的呢~",
            ]
        else:
            responses = [
                f"哇~{subject}呢~真有你的~（笑",
                f"呵呵，{subject}...挺有意思的呢~",
            ]
        return random.choice(responses)
    
    def _generate_aojiao(self, subject: str, feat: str, atm: str) -> str:
        """傲娇风格"""
        if atm:
            responses = [
                f"哼，就算{subject}再{atm}，我、我也不会说什么的！",
                f"{subject}而已嘛...也就还行吧（小声：其实挺{atm}的",
            ]
        else:
            responses = [
                f"哼，{subject}而已嘛...也就还行吧",
                f"切，{subject}...才、才不是因为好看我才看的！",
            ]
        return random.choice(responses)
    
    def _generate_bingjiao(self, subject: str, feat: str, atm: str) -> str:
        """病娇风格"""
        if feat:
            responses = [
                f"呐呐~{subject}{feat}...只给我一个人看的吧？我好喜欢呢❤",
                f"{subject}真{atm if atm else '好看'}...你是特意发给我的吧？❤",
            ]
        else:
            responses = [
                f"呐呐~{subject}...只给我一个人看的吧？❤",
                f"{subject}...是想让我吃醋吗？",
            ]
        return random.choice(responses)
    
    def _generate_yonglan(self, subject: str, feat: str, atm: str) -> str:
        """慵懒风格"""
        responses = [
            f"嗯...{subject}啊...好累不想说话...",
            f"哦...{subject}...还行吧...（打哈欠",
            f"{subject}嘛...懒得评价了...",
        ]
        return random.choice(responses)
    
    def _generate_yuanqi(self, subject: str, feat: str, atm: str) -> str:
        """元气风格"""
        if atm:
            responses = [
                f"哇！好{atm}的{subject}！超级喜欢！！",
                f"天啊！{subject}{feat}！太棒了吧！",
                f"哦哦哦！{atm}的{subject}！！",
            ]
        else:
            responses = [
                f"哇！{subject}！好棒啊！！",
                f"天啊！{subject}{feat}！太有趣了！",
            ]
        return random.choice(responses)
    
    def _generate_default(self, subject: str, feat: str, atm: str) -> str:
        """默认风格"""
        responses = [
            f"看到{subject}了~",
            f"嗯，{subject}...不错",
        ]
        return random.choice(responses)
    
    # ==================== 新增风格回复方法 ====================
    
    def _generate_shadiao_creative(self, subject: str, features: List[str], details: List[str]) -> str:
        """沙雕创意回复"""
        responses = [
            f"哈哈哈哈{subject}？这是什么鬼畜画风？",
            f"笑死我了{subject}...这画风我服了",
            f"哈哈哈哈{subject}？这是什么沙雕画风？",
            f"笑死我了{subject}...这画风我服了",
            f"哈哈哈哈{subject}？这是什么鬼畜画风？",
            f"笑死我了{subject}...这画风我服了",
            f"哈哈哈哈{subject}？这是什么沙雕画风？",
            f"笑死我了{subject}...这画风我服了"
        ]
        return random.choice(responses)
    
    def _generate_wenyi_creative(self, subject: str, features: List[str], details: List[str]) -> str:
        """文艺创意回复"""
        responses = [
            f"嗯...{subject}...有一种说不出的美感呢~",
            f"哇，{subject}...看起来很有艺术感~",
            f"嗯...{subject}...有一种说不出的美感呢~",
            f"哇，{subject}...看起来很有艺术感~",
            f"嗯...{subject}...有一种说不出的美感呢~",
            f"哇，{subject}...看起来很有艺术感~"
        ]
        return random.choice(responses)
    
    def _generate_shadiao_interactive(self, subject: str, features: List[str], atmosphere: str) -> str:
        """沙雕互动回复"""
        responses = [
            f"哈哈哈哈{subject}？这是什么鬼畜画风？",
            f"笑死我了{subject}...这画风我服了",
            f"哈哈哈哈{subject}？这是什么沙雕画风？",
            f"笑死我了{subject}...这画风我服了",
            f"哈哈哈哈{subject}？这是什么鬼畜画风？",
            f"笑死我了{subject}...这画风我服了"
        ]
        return random.choice(responses)
    
    def _generate_wenyi_interactive(self, subject: str, features: List[str], atmosphere: str) -> str:
        """文艺互动回复"""
        responses = [
            f"嗯...{subject}...有一种说不出的美感呢~",
            f"哇，{subject}...看起来很有艺术感~",
            f"嗯...{subject}...有一种说不出的美感呢~",
            f"哇，{subject}...看起来很有艺术感~",
            f"嗯...{subject}...有一种说不出的美感呢~",
            f"哇，{subject}...看起来很有艺术感~"
        ]
        return random.choice(responses)
    
    def _generate_shadiao_emotional(self, subject: str, features: List[str], emotion_tone: str) -> str:
        """沙雕情感回复"""
        if emotion_tone == 'positive':
            responses = [
                f"哈哈哈哈{subject}？这是什么鬼畜画风？",
                f"笑死我了{subject}...这画风我服了",
                f"哈哈哈哈{subject}？这是什么沙雕画风？"
            ]
        elif emotion_tone == 'negative':
            responses = [
                f"嗯...{subject}...看起来有点难过呢...",
                f"嗯嗯，{subject}...看起来有点累呢...",
                f"嗯...{subject}...看起来有点辛苦呢..."
            ]
        else:
            responses = [
                f"嗯，{subject}...看起来不错呢~",
                f"嗯嗯，{subject}...看起来挺好的~",
                f"嗯，{subject}...看起来不错呢~"
            ]
        return random.choice(responses)
    
    def _generate_wenyi_emotional(self, subject: str, features: List[str], emotion_tone: str) -> str:
        """文艺情感回复"""
        if emotion_tone == 'positive':
            responses = [
                f"嗯...{subject}...有一种说不出的美感呢~",
                f"哇，{subject}...看起来很有艺术感~",
                f"嗯...{subject}...有一种说不出的美感呢~"
            ]
        elif emotion_tone == 'negative':
            responses = [
                f"嗯...{subject}...看起来有点难过呢...",
                f"嗯嗯，{subject}...看起来有点累呢...",
                f"嗯...{subject}...看起来有点辛苦呢..."
            ]
        else:
            responses = [
                f"嗯，{subject}...看起来不错呢~",
                f"嗯嗯，{subject}...看起来挺好的~",
                f"嗯，{subject}...看起来不错呢~"
            ]
        return random.choice(responses)
    
    def _generate_wenrou_humorous(self, subject: str, features: Dict, description: str) -> str:
        """温柔幽默回复"""
        responses = [
            f"哇，{subject}看起来好温柔呢~",
            f"嗯...{subject}...感觉好治愈~",
            f"哦？{subject}？看起来好可爱~",
            f"呵呵，{subject}...让人心情变好了~",
            f"嗯嗯，{subject}...好喜欢这种风格~",
            f"哇，{subject}！看起来好舒服~",
            f"嗯...{subject}...感觉好温暖~",
            f"哦？{subject}？看起来好治愈~"
        ]
        
        return random.choice(responses)
    
    def _generate_tianran_humorous(self, subject: str, features: Dict, description: str) -> str:
        """天然幽默回复"""
        responses = [
            f"诶？{subject}？这是什么？",
            f"嗯...{subject}...看起来好奇怪~",
            f"哦？{subject}？好有趣的样子~",
            f"哇，{subject}！看起来好神奇~",
            f"嗯嗯，{subject}...好特别~",
            f"诶？{subject}？好奇怪的感觉~",
            f"嗯...{subject}...好有趣~",
            f"哦？{subject}？好神奇的样子~"
        ]
        
        return random.choice(responses)
    
    async def _generate_ai_creative_reply(self, description: str) -> str:
        """使用NVIDIA DeepSeek生成创意回复"""
        try:
            from utils.ai_clients.deepseek_client import get_deepseek_client
            
            # 构建创意提示词，让AI根据完整描述生成有趣回复
            prompt = f"""你是一个有趣、幽默的AI助手。请根据这张图片的详细描述，生成一个生动有趣的回复。

要求：
1. 回复要生动有趣，不要模板化
2. 可以调侃、吐槽、赞美或开玩笑
3. 语言要自然，像真人聊天一样
4. 长度控制在15-25字之间
5. 要有创意，避免重复
6. 可以针对图片中的具体细节进行评论

图片详细描述：{description}

请直接生成一个有趣的回复，不要解释："""
            
            # 使用NVIDIA DeepSeek聊天模型
            client = get_deepseek_client()
            messages = [{"role": "user", "content": prompt}]
            response = await client.chat(messages)
            
            if response and len(response.strip()) > 0:
                logger.info(f"🤖 AI创意回复: {response}")
                return response.strip()
            
        except Exception as e:
            logger.error(f"❌ AI创意回复生成失败: {e}")
        
        return None

