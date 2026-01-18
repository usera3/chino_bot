"""VectorStore - 向量数据库管理（长期记忆）"""
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from typing import List, Optional
import os


class FakeEmbeddings(Embeddings):
    """改进的 Fake Embeddings（基于 TF-IDF 的简单语义理解）
    
    使用 TF-IDF 和字符 n-gram 来生成向量，比纯哈希更有语义意义
    """
    
    def __init__(self):
        """初始化"""
        self.dim = 384
        # 常见词汇表（用于 TF-IDF）
        self.vocab = {}
        self.doc_count = 0
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        return [self._embed_text(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询"""
        return self._embed_text(text)
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词：提取字符 bigram 和 trigram"""
        tokens = []
        text = text.lower()
        
        # 单字符
        for char in text:
            if char.strip():
                tokens.append(char)
        
        # bigram
        for i in range(len(text) - 1):
            tokens.append(text[i:i+2])
        
        # trigram  
        for i in range(len(text) - 2):
            tokens.append(text[i:i+3])
        
        # 词（按空格分）
        words = text.split()
        tokens.extend(words)
        
        return tokens
    
    def _embed_text(self, text: str) -> List[float]:
        """
        将文本转换为向量
        
        使用改进的策略：
        - 字符 n-gram 特征
        - 简单的 TF-IDF 权重
        - 位置编码
        """
        vector = [0.0] * self.dim
        
        if not text:
            return vector
        
        # 分词
        tokens = self._tokenize(text)
        
        # 计算词频
        token_freq = {}
        for token in tokens:
            token_freq[token] = token_freq.get(token, 0) + 1
        
        # 生成向量
        for token, freq in token_freq.items():
            # 使用 token 的哈希值来确定影响哪些维度
            token_hash = hash(token)
            
            # 每个 token 影响多个维度
            for i in range(5):
                idx = (token_hash + i * 7919) % self.dim  # 7919 是质数
                # TF 权重
                weight = freq / len(tokens)
                vector[idx] += weight
        
        # 归一化
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]
        
        return vector


class VectorStoreManager:
    """向量数据库管理器 - 用于长期记忆"""
    
    def __init__(
        self, 
        persist_directory: str = "./data/chroma",
        embedding_type: str = "fake"
    ):
        """
        初始化向量数据库
        
        Args:
            persist_directory: 数据持久化目录
            embedding_type: Embeddings 类型 ("fake", "openai", "huggingface")
        """
        self.persist_directory = persist_directory
        
        # 创建目录
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化 Embeddings
        print(f"📦 加载 Embeddings 模型 ({embedding_type})...")
        self.embeddings = self._create_embeddings(embedding_type)
        print("✅ Embeddings 模型加载成功")
        
        # 初始化 Chroma
        print("🗄️ 初始化 Chroma 向量数据库...")
        self.vectorstore = Chroma(
            collection_name="chat_memory",
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        print("✅ Chroma 初始化成功")
    
    def _create_embeddings(self, embedding_type: str) -> Embeddings:
        """
        创建 Embeddings
        
        Args:
            embedding_type: Embeddings 类型
            
        Returns:
            Embeddings 实例
        """
        if embedding_type == "fake":
            return FakeEmbeddings()
        
        elif embedding_type == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings()
        
        elif embedding_type == "huggingface":
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                # 使用更小的模型，并设置本地缓存
                return HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2",  # 更小的英文模型
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True},
                    cache_folder="./models"  # 本地缓存
                )
            except Exception as e:
                print(f"⚠️ HuggingFace Embeddings 加载失败: {e}")
                print("⚠️ 回退到 Fake Embeddings")
                return FakeEmbeddings()
        
        else:
            raise ValueError(f"不支持的 embedding_type: {embedding_type}")
    
    def add_conversation(
        self, 
        user_input: str, 
        bot_response: str, 
        user_id: str,
        metadata: Optional[dict] = None
    ):
        """
        添加对话到向量数据库
        
        Args:
            user_input: 用户输入
            bot_response: 机器人回复
            user_id: 用户ID
            metadata: 额外的元数据
        """
        from datetime import datetime
        
        # 获取当前时间
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建对话文本（添加时间戳）
        conversation_text = f"[{timestamp}] 用户: {user_input}\n智乃: {bot_response}"
        
        # 构建元数据
        meta = {
            "user_id": user_id,
            "user_input": user_input,
            "bot_response": bot_response,
            "type": "conversation",
            "timestamp": timestamp
        }
        if metadata:
            meta.update(metadata)
        
        # 添加到向量数据库
        self.vectorstore.add_texts(
            texts=[conversation_text],
            metadatas=[meta]
        )
    
    def search_similar_conversations(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        k: int = 3
    ) -> List[Document]:
        """
        搜索相似的对话
        
        Args:
            query: 查询文本
            user_id: 用户ID（可选，用于过滤）
            k: 返回结果数量
            
        Returns:
            相似的对话列表
        """
        # 构建过滤条件
        filter_dict = None
        if user_id:
            filter_dict = {"user_id": user_id}
        
        # 搜索
        results = self.vectorstore.similarity_search(
            query=query,
            k=k,
            filter=filter_dict
        )
        
        return results
    
    def get_relevant_context(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        k: int = 3
    ) -> str:
        """
        获取相关的上下文（格式化为字符串）
        
        Args:
            query: 查询文本
            user_id: 用户ID
            k: 返回结果数量
            
        Returns:
            格式化的上下文字符串
        """
        from datetime import datetime, timedelta
        
        results = self.search_similar_conversations(query, user_id, k)
        
        if not results:
            return "（没有找到相关的历史对话）"
        
        context_parts = []
        current_time = datetime.now()
        
        for i, doc in enumerate(results, 1):
            # 获取时间戳
            timestamp_str = doc.metadata.get("timestamp", "未知时间")
            
            # 计算时间差
            time_desc = ""
            try:
                msg_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                time_diff = current_time - msg_time
                
                if time_diff < timedelta(minutes=5):
                    time_desc = "（刚才）"
                elif time_diff < timedelta(hours=1):
                    minutes = int(time_diff.total_seconds() / 60)
                    time_desc = f"（{minutes}分钟前）"
                elif time_diff < timedelta(days=1):
                    hours = int(time_diff.total_seconds() / 3600)
                    time_desc = f"（{hours}小时前）"
                else:
                    days = time_diff.days
                    time_desc = f"（{days}天前）"
            except:
                time_desc = f"（{timestamp_str}）"
            
            context_parts.append(f"[历史对话 {i}] {time_desc}\n{doc.page_content}")
        
        return "\n\n".join(context_parts)
    
    def clear_user_memory(self, user_id: str):
        """
        清空指定用户的记忆
        
        Args:
            user_id: 用户ID
        """
        # Chroma 不支持直接删除，需要重新创建集合
        # 这里简单实现，实际使用中可以优化
        print(f"⚠️ 清空用户 {user_id} 的记忆（需要手动实现）")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        collection = self.vectorstore._collection
        count = collection.count()
        
        return {
            "total_conversations": count,
            "persist_directory": self.persist_directory
        }
