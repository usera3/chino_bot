"""双向量库管理器 - 对话库 + 知识库"""
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from typing import List, Optional, Dict
import os
import json
from datetime import datetime

from .vector_store import FakeEmbeddings


class DualVectorStore:
    """双向量库：对话库 + 知识库"""
    
    def __init__(
        self,
        persist_directory: str = "./data",
        embedding_type: str = "fake"
    ):
        """
        初始化双向量库
        
        Args:
            persist_directory: 数据持久化目录
            embedding_type: Embeddings 类型
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化 Embeddings
        print(f"📦 加载 Embeddings 模型 ({embedding_type})...")
        self.embeddings = self._create_embeddings(embedding_type)
        print("✅ Embeddings 模型加载成功")
        
        # 1. 对话向量库（完整对话历史）
        print("🗄️ 初始化对话向量库...")
        self.conversation_store = Chroma(
            collection_name="conversations",
            embedding_function=self.embeddings,
            persist_directory=os.path.join(persist_directory, "conversations")
        )
        print("✅ 对话向量库初始化成功")
        
        # 2. 知识向量库（结构化信息）
        print("🗄️ 初始化知识向量库...")
        self.knowledge_store = Chroma(
            collection_name="knowledge",
            embedding_function=self.embeddings,
            persist_directory=os.path.join(persist_directory, "knowledge")
        )
        print("✅ 知识向量库初始化成功")
    
    def _create_embeddings(self, embedding_type: str):
        """创建 Embeddings"""
        if embedding_type == "fake":
            return FakeEmbeddings()
        elif embedding_type == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings()
        else:
            raise ValueError(f"不支持的 embedding_type: {embedding_type}")
    
    def add_conversation(
        self,
        user_input: str,
        bot_response: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ):
        """
        添加对话到对话库
        
        Args:
            user_input: 用户输入
            bot_response: 机器人回复
            user_id: 用户ID
            metadata: 额外元数据
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建对话文本
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
        
        # 添加到对话库
        self.conversation_store.add_texts(
            texts=[conversation_text],
            metadatas=[meta]
        )
    
    def add_knowledge(
        self,
        knowledge: Dict,
        user_id: str
    ):
        """
        添加结构化知识到知识库
        
        Args:
            knowledge: 知识字典
            user_id: 用户ID
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 格式化知识为文本
        knowledge_text = self._format_knowledge_text(knowledge)
        
        if not knowledge_text:
            return
        
        # 构建元数据
        meta = {
            "user_id": user_id,
            "type": "knowledge",
            "timestamp": timestamp,
            "knowledge_json": json.dumps(knowledge, ensure_ascii=False)
        }
        
        # 添加到知识库
        self.knowledge_store.add_texts(
            texts=[knowledge_text],
            metadatas=[meta]
        )
        
        print(f"💾 已保存知识: {knowledge_text[:100]}...")
    
    def _format_knowledge_text(self, knowledge: Dict) -> str:
        """将知识字典格式化为可搜索的文本"""
        parts = []
        
        # 个人信息
        if 'personal_info' in knowledge:
            for key, value in knowledge['personal_info'].items():
                if value:
                    parts.append(f"{key}: {value}")
        
        # 偏好
        if 'preferences' in knowledge:
            for key, values in knowledge['preferences'].items():
                if values:
                    parts.append(f"{key}: {', '.join(values)}")
        
        # 社交关系
        if 'social' in knowledge:
            for key, values in knowledge['social'].items():
                if values:
                    parts.append(f"{key}: {', '.join(values)}")
        
        # 事实
        if 'facts' in knowledge:
            parts.extend(knowledge['facts'])
        
        return " | ".join(parts)
    
    def search_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        k: int = 5
    ) -> List[Document]:
        """
        搜索对话历史
        
        Args:
            query: 查询文本
            user_id: 用户ID（可选）
            k: 返回结果数量
            
        Returns:
            相关对话列表
        """
        filter_dict = {"user_id": user_id} if user_id else None
        
        results = self.conversation_store.similarity_search(
            query=query,
            k=k,
            filter=filter_dict
        )
        
        return results
    
    def search_knowledge(
        self,
        query: str,
        user_id: Optional[str] = None,
        k: int = 3
    ) -> List[Document]:
        """
        搜索结构化知识
        
        Args:
            query: 查询文本
            user_id: 用户ID（可选）
            k: 返回结果数量
            
        Returns:
            相关知识列表
        """
        filter_dict = {"user_id": user_id} if user_id else None
        
        results = self.knowledge_store.similarity_search(
            query=query,
            k=k,
            filter=filter_dict
        )
        
        return results
    
    def get_user_knowledge(self, user_id: str) -> str:
        """
        获取用户的所有结构化知识
        
        Args:
            user_id: 用户ID
            
        Returns:
            格式化的知识文本
        """
        # 搜索该用户的所有知识
        results = self.knowledge_store.similarity_search(
            query="",  # 空查询
            k=10,
            filter={"user_id": user_id}
        )
        
        if not results:
            return ""
        
        # 合并所有知识
        knowledge_parts = []
        for doc in results:
            if doc.page_content:
                knowledge_parts.append(doc.page_content)
        
        return "\n".join(knowledge_parts) if knowledge_parts else ""
    
    def get_recent_conversations(
        self,
        user_id: str,
        k: int = 20
    ) -> List[Document]:
        """
        获取最近的对话记录
        
        Args:
            user_id: 用户ID
            k: 返回数量
            
        Returns:
            最近的对话列表（按时间倒序）
        """
        # 获取该用户的所有对话
        all_results = self.conversation_store.get(
            where={"user_id": user_id}
        )
        
        if not all_results or not all_results['ids']:
            return []
        
        # 构建 Document 列表
        documents = []
        for i in range(len(all_results['ids'])):
            doc = Document(
                page_content=all_results['documents'][i],
                metadata=all_results['metadatas'][i]
            )
            documents.append(doc)
        
        # 按时间戳排序（最新的在前）
        documents.sort(
            key=lambda x: x.metadata.get('timestamp', ''),
            reverse=True
        )
        
        # 返回最近的 k 条
        return documents[:k]
    
    def get_relevant_context(
        self,
        query: str,
        user_id: str,
        k_conversations: int = 3,
        k_knowledge: int = 2,
        k_recent: int = 20
    ) -> str:
        """
        获取相关上下文（最近对话 + 向量检索对话 + 知识）
        
        Args:
            query: 查询文本
            user_id: 用户ID
            k_conversations: 向量检索对话数量
            k_knowledge: 知识检索数量
            k_recent: 最近对话数量
            
        Returns:
            格式化的上下文
        """
        parts = []
        
        # 1. 获取最近的对话记录（时间倒序）
        recent_conversations = self.get_recent_conversations(user_id, k_recent)
        if recent_conversations:
            parts.append("【最近对话记录】")
            for i, doc in enumerate(recent_conversations, 1):
                timestamp = doc.metadata.get('timestamp', '未知时间')
                user_input = doc.metadata.get('user_input', '')
                bot_response = doc.metadata.get('bot_response', '')
                parts.append(f"[{i}] {timestamp}")
                parts.append(f"用户: {user_input}")
                parts.append(f"智乃: {bot_response}")
                parts.append("")  # 空行分隔
        
        # 2. 检索结构化知识（优先级高）
        knowledge_results = self.search_knowledge(query, user_id, k_knowledge)
        if knowledge_results:
            parts.append("【用户信息】")
            for doc in knowledge_results:
                parts.append(doc.page_content)
            parts.append("")
        
        # 3. 向量检索相关对话（去重：排除已在最近对话中的）
        conversation_results = self.search_conversations(query, user_id, k_conversations)
        if conversation_results:
            # 获取最近对话的时间戳集合（用于去重）
            recent_timestamps = {doc.metadata.get('timestamp') for doc in recent_conversations}
            
            # 过滤掉重复的对话
            unique_results = [
                doc for doc in conversation_results 
                if doc.metadata.get('timestamp') not in recent_timestamps
            ]
            
            if unique_results:
                parts.append("【相关历史对话】")
                for i, doc in enumerate(unique_results, 1):
                    timestamp = doc.metadata.get('timestamp', '未知时间')
                    user_input = doc.metadata.get('user_input', '')
                    bot_response = doc.metadata.get('bot_response', '')
                    parts.append(f"[{i}] {timestamp}")
                    parts.append(f"用户: {user_input}")
                    parts.append(f"智乃: {bot_response}")
                    parts.append("")
        
        return "\n".join(parts) if parts else "（没有找到相关历史）"
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        conv_count = self.conversation_store._collection.count()
        know_count = self.knowledge_store._collection.count()
        
        return {
            "conversations": conv_count,
            "knowledge": know_count,
            "persist_directory": self.persist_directory
        }
