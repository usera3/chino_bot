"""
图片回复工厂 - 模块化、可扩展的图片回复生成系统
遵循SOLID原则，每个类/函数只做一件事
"""
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import random


# ==================== 第一层：数据提取模块（砖头） ====================

class DescriptionCleaner:
    """描述清理器 - 负责去掉机械化前缀"""
    
    PREFIXES = ['图片中是', '这是一张', '图片中', '这是', '图片里是']
    
    @staticmethod
    def clean(description: str) -> str:
        """清理描述，去掉前缀"""
        clean_desc = description
        for prefix in DescriptionCleaner.PREFIXES:
            if clean_desc.startswith(prefix):
                clean_desc = clean_desc[len(prefix):]
        return clean_desc


class SubjectExtractor:
    """主体提取器 - 负责提取核心主体（如：紫发女孩）"""
    
    SUBJECT_KEYWORDS = ['女孩', '少女', '男孩', '猫咪', '小猫', '狗', '人物', '角色', '树', '花']
    
    @staticmethod
    def extract(clean_description: str) -> str:
        """提取主体"""
        for keyword in SubjectExtractor.SUBJECT_KEYWORDS:
            if keyword in clean_description:
                parts = clean_description.split(keyword)
                if parts:
                    modifiers = parts[0].split('，')[-1].strip()
                    subject = f"{modifiers}{keyword}"
                    # 清理
                    subject = subject.strip('一个').strip('一只').strip('的').strip()
                    # 去重
                    words = subject.split('的')
                    if len(words) > 2 and words[0] == words[1]:
                        subject = '的'.join([words[0]] + words[2:])
                    return subject
        
        # 没找到关键词，取第一句
        first_part = clean_description.split('，')[0].strip()
        return first_part.replace('下', '').replace('中', '').strip()


class FeatureExtractor:
    """特征提取器 - 负责提取特征（如：戴着樱花发饰）"""
    
    FEATURE_KEYWORDS = ['头发', '发饰', '眼睛', '表情', '服', '装', '拿着', '戴着', '穿着']
    
    @staticmethod
    def extract(clean_description: str, max_features: int = 2) -> List[str]:
        """提取特征列表"""
        features = []
        sentences = clean_description.split('，')
        
        for sent in sentences[1:4]:  # 取2-4个特征
            if any(kw in sent for kw in FeatureExtractor.FEATURE_KEYWORDS):
                feat = sent.strip().replace('头上', '').replace('正在', '').replace('她', '')
                if len(feat) < 15:
                    features.append(feat)
                    if len(features) >= max_features:
                        break
        
        return features


class AtmosphereExtractor:
    """氛围提取器 - 负责提取氛围词（如：可爱、梦幻）"""
    
    ATMOSPHERE_KEYWORDS = ['可爱', '萌', '梦幻', '温柔', '少女', '帅气', '酷', '治愈']
    
    @staticmethod
    def extract(description: str) -> Optional[str]:
        """提取氛围词"""
        for word in AtmosphereExtractor.ATMOSPHERE_KEYWORDS:
            if word in description:
                return word
        return None


# ==================== 第二层：数据组装模块（零件） ====================

class ImageElements:
    """图片要素 - 数据传输对象（DTO）"""
    
    def __init__(self, subject: str, features: List[str], atmosphere: Optional[str]):
        self.subject = subject
        self.features = features
        self.atmosphere = atmosphere
    
    def get_feature_desc(self) -> str:
        """获取特征描述"""
        return f"，{self.features[0]}" if self.features else ""


class ImageElementsExtractor:
    """图片要素提取器 - 组合多个提取器，生成完整的图片要素"""
    
    def __init__(self):
        self.cleaner = DescriptionCleaner()
        self.subject_extractor = SubjectExtractor()
        self.feature_extractor = FeatureExtractor()
        self.atmosphere_extractor = AtmosphereExtractor()
    
    def extract(self, description: str) -> ImageElements:
        """提取图片的所有要素"""
        # 清理描述
        clean_desc = self.cleaner.clean(description)
        
        # 提取各个要素
        subject = self.subject_extractor.extract(clean_desc)
        features = self.feature_extractor.extract(clean_desc)
        atmosphere = self.atmosphere_extractor.extract(description)
        
        return ImageElements(subject, features, atmosphere)


# ==================== 第三层：回复生成策略模块（零件） ====================

class ReplyStrategy(ABC):
    """回复策略基类 - 定义回复生成接口"""
    
    @abstractmethod
    def generate(self, elements: ImageElements) -> str:
        """生成回复"""
        pass


class DuSheReplyStrategy(ReplyStrategy):
    """毒舌风格回复策略"""
    
    def generate(self, elements: ImageElements) -> str:
        if elements.atmosphere:
            responses = [
                f"就这？{elements.atmosphere}的{elements.subject}？审美有待提高啊",
                f"切，就算{elements.subject}{elements.get_feature_desc()}，也不会比我好看的",
                f"emmm...{elements.subject}...也就那样吧",
                f"哦，{elements.subject}啊...有点土哦",
            ]
        else:
            responses = [
                f"就这？{elements.subject}也敢发出来？",
                f"切，{elements.subject}而已嘛，没啥特别的",
                f"emmm...{elements.subject}...你的审美真独特呢",
            ]
        return random.choice(responses)


class FuHeiReplyStrategy(ReplyStrategy):
    """腹黑风格回复策略"""
    
    def generate(self, elements: ImageElements) -> str:
        if elements.features:
            responses = [
                f"哇~{elements.subject}{elements.get_feature_desc()}呢~真有你的~（笑",
                f"呵呵，{elements.subject}...{elements.features[0]}...挺有意思的呢~",
                f"原来是{elements.subject}啊~一看就知道你很用心了呢~（温柔微笑",
            ]
        else:
            responses = [
                f"哇~{elements.subject}呢~真有你的~（笑",
                f"呵呵，{elements.subject}...挺有意思的呢~",
                f"嗯嗯~原来是{elements.subject}啊...我完全理解了呢~"
            ]
        return random.choice(responses)


class AojiaoReplyStrategy(ReplyStrategy):
    """傲娇风格回复策略"""
    
    def generate(self, elements: ImageElements) -> str:
        if elements.atmosphere:
            responses = [
                f"哼，就算{elements.subject}再{elements.atmosphere}，我、我也不会说什么的！",
                f"切，{elements.subject}...才、才不是因为{elements.atmosphere}我才看的！",
                f"{elements.subject}而已嘛...也就还行吧（小声：其实挺{elements.atmosphere}的",
            ]
        else:
            responses = [
                f"哼，{elements.subject}而已嘛...也就还行吧",
                f"切，{elements.subject}...才、才不是因为好看我才看的！",
                f"你、你不要以为我会夸你...{elements.subject}确实...还可以啦",
            ]
        return random.choice(responses)


class BingjiaoReplyStrategy(ReplyStrategy):
    """病娇风格回复策略"""
    
    def generate(self, elements: ImageElements) -> str:
        if elements.features:
            responses = [
                f"呐呐~{elements.subject}{elements.get_feature_desc()}...只给我一个人看的吧？我好喜欢呢❤",
                f"{elements.subject}真{elements.atmosphere if elements.atmosphere else '好看'}...你是特意发给我的吧？❤",
                f"你发的每张图我都会好好收藏的哦~{elements.subject}❤",
            ]
        else:
            responses = [
                f"呐呐~{elements.subject}...只给我一个人看的吧？❤",
                f"{elements.subject}...是想让我吃醋吗？",
                f"这张{elements.subject}...我会永远记住的❤"
            ]
        return random.choice(responses)


class YonglanReplyStrategy(ReplyStrategy):
    """慵懒风格回复策略"""
    
    def generate(self, elements: ImageElements) -> str:
        responses = [
            f"嗯...{elements.subject}啊...好累不想说话...",
            f"哦...{elements.subject}...还行吧...（打哈欠",
            f"{elements.subject}嘛...懒得评价了...我要睡觉",
            f"看到{elements.subject}了...反正就那样..."
        ]
        return random.choice(responses)


class YuanqiReplyStrategy(ReplyStrategy):
    """元气风格回复策略"""
    
    def generate(self, elements: ImageElements) -> str:
        if elements.atmosphere:
            responses = [
                f"哇！好{elements.atmosphere}的{elements.subject}！超级喜欢！！",
                f"天啊！{elements.subject}{elements.get_feature_desc()}！太棒了吧！",
                f"哦哦哦！{elements.atmosphere}的{elements.subject}！！我也想要！",
            ]
        else:
            responses = [
                f"哇！{elements.subject}！好棒啊！！",
                f"天啊！{elements.subject}{elements.get_feature_desc()}！太有趣了！",
                f"好喜欢！{elements.subject}在哪找到的呀！"
            ]
        return random.choice(responses)


class DefaultReplyStrategy(ReplyStrategy):
    """默认风格回复策略"""
    
    def generate(self, elements: ImageElements) -> str:
        if elements.atmosphere:
            responses = [
                f"哦~{elements.atmosphere}的{elements.subject}呢",
                f"看到了~{elements.subject}...挺{elements.atmosphere}的",
                f"嗯，{elements.subject}{elements.get_feature_desc()}...不错"
            ]
        else:
            responses = [
                f"{elements.subject}呢",
                f"看到了~{elements.subject}...挺有意思的",
                f"嗯，{elements.subject}"
            ]
        return random.choice(responses)


# ==================== 第四层：策略工厂模块（流水线） ====================

class ReplyStrategyFactory:
    """回复策略工厂 - 根据风格名称创建对应的策略"""
    
    _strategies = {
        "毒舌": DuSheReplyStrategy,
        "腹黑": FuHeiReplyStrategy,
        "傲娇": AojiaoReplyStrategy,
        "病娇": BingjiaoReplyStrategy,
        "慵懒": YonglanReplyStrategy,
        "元气": YuanqiReplyStrategy,
    }
    
    @classmethod
    def create_strategy(cls, style: str) -> ReplyStrategy:
        """创建策略实例"""
        strategy_class = cls._strategies.get(style, DefaultReplyStrategy)
        return strategy_class()
    
    @classmethod
    def register_strategy(cls, style: str, strategy_class: type):
        """注册新策略（支持扩展）"""
        cls._strategies[style] = strategy_class


# ==================== 第五层：完整的回复生成器（产品） ====================

class ImageReplyGenerator:
    """图片回复生成器 - 完整的工厂流水线"""
    
    def __init__(self):
        self.elements_extractor = ImageElementsExtractor()
        self.strategy_factory = ReplyStrategyFactory()
    
    def generate_reply(self, description: str, style: str) -> str:
        """
        生成图片回复
        
        Args:
            description: 图片描述
            style: 风格（毒舌、腹黑、傲娇等）
        
        Returns:
            生成的回复文本
        """
        # 1. 提取图片要素
        elements = self.elements_extractor.extract(description)
        
        # 2. 创建对应风格的策略
        strategy = self.strategy_factory.create_strategy(style)
        
        # 3. 生成回复
        reply = strategy.generate(elements)
        
        return reply


# ==================== 便捷接口 ====================

# 全局单例
_generator = ImageReplyGenerator()

def generate_image_reply(description: str, style: str) -> str:
    """便捷函数：生成图片回复"""
    return _generator.generate_reply(description, style)




