"""
调试消息分段器
"""
import re

def split_message(text: str):
    """
    测试分段逻辑
    """
    MIN_LENGTH_TO_SPLIT = 30
    
    if not text or len(text) < MIN_LENGTH_TO_SPLIT:
        print(f"文本太短（{len(text)}字符），不分段")
        return [text]
    
    # 分隔符：中英文标点（包括省略号）
    separators = [
        '\n\n',  # 双换行（段落）
        '。',    # 中文句号
        '！',    # 中文感叹号
        '？',    # 中文问号
        '……',   # 中文省略号
        '...',   # 英文省略号
        '。。。', # 另一种省略号
        '\n',    # 单换行
        '；',    # 分号
        '.',     # 英文句号（但要避免小数点）
        '!',     # 英文感叹号
        '?',     # 英文问号
    ]
    
    segments = []
    current_segment = ""
    i = 0
    
    print(f"\n开始处理文本（长度：{len(text)}）：")
    print(f"'{text}'")
    print("\n" + "="*60)
    
    while i < len(text):
        char = text[i]
        current_segment += char
        
        # 检查是否遇到分隔符
        matched_sep = None
        for sep in separators:
            if text[i:i+len(sep)] == sep:
                # 特殊处理：避免把小数点当成句号
                if sep == '.' and i > 0 and i < len(text) - 1:
                    if text[i-1].isdigit() and text[i+1].isdigit():
                        i += 1
                        continue
                
                matched_sep = sep
                print(f"位置 {i}: 匹配到分隔符 '{matched_sep}'")
                break
        
        if matched_sep:
            # 完整吞掉分隔符
            if len(matched_sep) > 1:
                current_segment += text[i+1:i+len(matched_sep)]
                i += len(matched_sep)
            else:
                i += 1
            
            # 如果当前段落足够长，或遇到段落分隔，则保存
            if len(current_segment.strip()) > 0:
                # 检查长度，如果太长则强制分割
                if len(current_segment) > 100:
                    # 💬 去掉末尾标点（真人聊天习惯）
                    cleaned = current_segment.strip().rstrip('。！？!?…')
                    cleaned = re.sub(r'\.{2,}$', '', cleaned)  # 去掉省略号
                    if cleaned:
                        print(f"✓ 保存段落（长度>{100}）: '{cleaned}'")
                        segments.append(cleaned)
                    current_segment = ""
                elif matched_sep in ['\n\n', '。', '！', '？', '!', '?', '……', '...', '。。。']:
                    # 💬 去掉末尾标点（真人聊天习惯）
                    cleaned = current_segment.strip().rstrip('。！？!?…')
                    cleaned = re.sub(r'\.{2,}$', '', cleaned)  # 去掉省略号
                    if cleaned:
                        print(f"✓ 保存段落（遇到分隔符'{matched_sep}'）: '{cleaned}'")
                        segments.append(cleaned)
                    current_segment = ""
                # 对于其他分隔符，继续累积
        else:
            i += 1
    
    # 添加剩余部分
    if current_segment.strip():
        # 💬 去掉末尾标点（真人聊天习惯）
        cleaned = current_segment.strip().rstrip('。！？!?…')
        cleaned = re.sub(r'\.{2,}$', '', cleaned)
        if cleaned:
            print(f"✓ 保存剩余段落: '{cleaned}'")
            segments.append(cleaned)
    
    # 合并过短的段落（少于5个字符的）
    print(f"\n合并前段落数：{len(segments)}")
    merged_segments = []
    temp_segment = ""
    
    for seg in segments:
        if len(seg) < 5 and temp_segment:
            temp_segment += seg
        else:
            if temp_segment:
                merged_segments.append(temp_segment)
            temp_segment = seg
    
    if temp_segment:
        merged_segments.append(temp_segment)
    
    print(f"合并后段落数：{len(merged_segments)}")
    
    return merged_segments if merged_segments else [text]


# 测试
test_text = "嗯，是的... 又是晚上了呢，你好。今天过得怎么样？有做什么有趣的事情吗？我在Rabbit House忙了一天，虽然有点累，但看到朋友们开心的样子，也觉得很充实。想聊聊你今天的故事吗？我会认真听的。..."

print("=" * 60)
print("测试消息分段")
print("=" * 60)

segments = split_message(test_text)

print("\n" + "=" * 60)
print(f"最终结果：共 {len(segments)} 段")
print("=" * 60)
for i, seg in enumerate(segments, 1):
    print(f"[{i}] {seg}")



