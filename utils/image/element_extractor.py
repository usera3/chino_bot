"""
图像元素提取器 - Utils Layer
职责：从图像描述中提取关键要素（主体、特征、氛围）
代码量：~100 行（纯函数，无副作用）
"""
from typing import Dict, List


def extract_key_elements(description: str) -> Dict[str, any]:
    """
    从图像描述中提取关键要素
    
    Args:
        description: 图像描述文本
    
    Returns:
        {
            'subject': 主体（紫发女孩、小猫等）,
            'features': 特征列表（樱花发饰、薯片等）,
            'atmosphere': 氛围（可爱、梦幻等）
        }
    """
    # 清理描述性前缀
    clean_desc = _remove_prefix(description)
    
    # 提取各个要素
    subject = _extract_subject(clean_desc)
    features = _extract_features(clean_desc)
    atmosphere = _extract_atmosphere(description)  # 使用原始描述
    
    return {
        'subject': subject,
        'features': features[:2],  # 最多2个特征
        'atmosphere': atmosphere
    }


def _remove_prefix(text: str) -> str:
    """移除常见的描述性前缀"""
    prefixes = [
        '这张图片展示了', '图片展示了', '这张图片是',
        '图片中是', '这是一张', '图片中', '这是', 
        '图片里是', '图里是', '画面中', '图像中'
    ]
    
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break  # 只移除一次
    
    return text.strip()


def _extract_subject(text: str) -> str:
    """提取主体（名词）"""
    # 主体关键词
    subject_keywords = [
        '女孩', '少女', '男孩', '少年',
        '猫咪', '小猫', '猫', '狗', '小狗',
        '人物', '角色', '动物',
        '树', '花', '建筑', '风景'
    ]
    
    for keyword in subject_keywords:
        if keyword in text:
            # 提取主体及其修饰词
            parts = text.split(keyword)
            if parts:
                # 取关键词前的修饰词（取逗号后的最后一部分）
                modifiers = parts[0].split('，')[-1].strip()
                
                # 清理冗余词汇
                trash_words = ['一位', '一个', '一只', '拥有', '和', '的', '有着', '带着']
                for word in trash_words:
                    modifiers = modifiers.replace(word, ' ')
                
                # 提取最后1-2个关键形容词
                mod_words = [w.strip() for w in modifiers.split() if w.strip()]
                
                # 只保留最核心的修饰词
                if len(mod_words) > 2:
                    # 优先选择颜色词、特征词
                    priority_words = []
                    for word in mod_words:
                        if any(c in word for c in ['色', '发', '眼', '耳']):
                            priority_words.append(word)
                    
                    if priority_words:
                        mod_words = priority_words[:1]  # 只取1个
                    else:
                        mod_words = mod_words[-1:]  # 取最后1个
                
                # 重组主体
                if mod_words:
                    subject = ''.join(mod_words) + keyword
                else:
                    subject = keyword
                
                return subject[:15]  # 限制长度
    
    # 如果没找到关键词，返回第一个逗号前的内容
    first_part = text.split('，')[0].strip()
    # 清理描述性词汇
    first_part = first_part.replace('一位', '').replace('一个', '').replace('拥有', '')
    return first_part[:15]


def _extract_features(text: str) -> List[str]:
    """提取特征（细节描述）"""
    features = []
    
    # 特征关键词
    feature_keywords = [
        '头发', '发饰', '眼睛', '表情',
        '服', '装', '衣', '裙',
        '拿着', '戴着', '穿着', '戴',
        '手里', '身上'
    ]
    
    # 按逗号分割句子
    sentences = text.split('，')
    
    for sent in sentences[1:4]:  # 取2-4个特征
        if any(kw in sent for kw in feature_keywords):
            # 简化特征描述
            feat = sent.strip()
            # 移除冗余词汇
            feat = feat.replace('头上', '').replace('正在', '').replace('她', '').replace('他', '')
            feat = feat.replace('戴着', '').replace('拿着', '').replace('穿着', '')
            feat = feat.replace('有着', '').replace('带着', '')
            feat = feat.strip()
            
            if 3 < len(feat) < 15 and feat:
                features.append(feat)
    
    return features


def _extract_atmosphere(text: str) -> str:
    """提取氛围词"""
    # 氛围关键词
    atmosphere_keywords = [
        '可爱', '萌', '梦幻', '温柔', '少女',
        '帅气', '酷', '霸气', '优雅', '清新',
        '温馨', '治愈', '可怕', '诡异', '神秘'
    ]
    
    for word in atmosphere_keywords:
        if word in text:
            return word
    
    return ""

