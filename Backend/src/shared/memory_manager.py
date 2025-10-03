"""
Memory Manager - Sistema de memoria persistente para la IA
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from src.core.logging import get_logger


logger = get_logger(__name__)


class MemoryManager:
    """
    Gestiona la memoria persistente de conversaciones y contexto de la IA
    """
    
    def __init__(self, memory_root: Path):
        self.memory_root = Path(memory_root)
        self.conversations_dir = self.memory_root / "conversations"
        self.context_dir = self.memory_root / "context"
        self.embeddings_dir = self.memory_root / "embeddings"
        
        # Crear directorios necesarios
        for directory in [self.conversations_dir, self.context_dir, self.embeddings_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def store_conversation(self, 
                          session_id: str, 
                          messages: List[Dict[str, Any]],
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Almacena una conversación completa
        
        Args:
            session_id: ID único de la sesión
            messages: Lista de mensajes de la conversación
            metadata: Metadata adicional de la conversación
        
        Returns:
            Información del almacenamiento
        """
        conversation_data = {
            "session_id": session_id,
            "stored_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "conversation_hash": self._calculate_conversation_hash(messages),
            "metadata": metadata or {},
            "messages": messages
        }
        
        # Guardar conversación
        conversation_file = self.conversations_dir / f"conversation_{session_id}.json"
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Crear índice de búsqueda
        self._index_conversation(session_id, messages, conversation_data["stored_at"])
        
        return {
            "session_id": session_id,
            "stored_at": conversation_data["stored_at"],
            "message_count": len(messages),
            "file_path": str(conversation_file)
        }
    
    def retrieve_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera una conversación específica
        
        Args:
            session_id: ID de la sesión
        
        Returns:
            Conversación completa o None si no existe
        """
        conversation_file = self.conversations_dir / f"conversation_{session_id}.json"
        
        if not conversation_file.exists():
            return None
        
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            logger.exception('Failed to load conversation %s', session_id, extra={'session_id': session_id})
            return None
    
    def retrieve_context(self, 
                        query: str, 
                        session_id: str = None,
                        limit: int = 5,
                        time_window_days: int = 30) -> List[Dict[str, Any]]:
        """
        Recupera contexto relevante basado en una consulta
        
        Args:
            query: Consulta de búsqueda
            session_id: ID de sesión específica (opcional)
            limit: Número máximo de resultados
            time_window_days: Ventana de tiempo en días para buscar
        
        Returns:
            Lista de contexto relevante
        """
        # Buscar en el índice de conversaciones
        relevant_contexts = self._search_conversation_index(
            query, session_id, limit, time_window_days
        )
        
        # Enriquecer con información adicional
        enriched_contexts = []
        for context in relevant_contexts:
            context_session_id = context.get('session_id')
            try:
                conversation = self.retrieve_conversation(context["session_id"])
                if conversation:
                    enriched_context = {
                        "session_id": context["session_id"],
                        "relevance_score": context["score"],
                        "matched_content": context["matched_content"],
                        "timestamp": context["timestamp"],
                        "full_conversation": conversation,
                        "relevant_messages": self._extract_relevant_messages(
                            conversation["messages"], query
                        )
                    }
                    enriched_contexts.append(enriched_context)
            except Exception:
                logger.exception('Failed to enrich context for session %s', context_session_id, extra={'session_id': context_session_id})
                continue
        
        return enriched_contexts[:limit]
    
    def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Genera un resumen de una conversación
        
        Args:
            session_id: ID de la sesión
        
        Returns:
            Resumen de la conversación
        """
        conversation = self.retrieve_conversation(session_id)
        if not conversation:
            return None
        
        messages = conversation["messages"]
        
        # Estadísticas básicas
        user_messages = [m for m in messages if m.get("role") == "user"]
        ai_messages = [m for m in messages if m.get("role") in ["assistant", "agent"]]
        
        # Extraer temas principales (simple keyword analysis)
        all_text = " ".join([m.get("content", "") for m in messages])
        word_freq = self._get_word_frequency(all_text.lower())
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        summary = {
            "session_id": session_id,
            "start_time": conversation["stored_at"],
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "ai_messages": len(ai_messages),
            "top_keywords": [word for word, freq in top_keywords],
            "conversation_length": len(all_text),
            "last_user_message": user_messages[-1]["content"] if user_messages else None,
            "last_ai_message": ai_messages[-1]["content"] if ai_messages else None
        }
        
        return summary
    
    def list_conversations(self, 
                          limit: int = 20,
                          days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Lista conversaciones recientes
        
        Args:
            limit: Número máximo de conversaciones
            days_back: Días hacia atrás para buscar
        
        Returns:
            Lista de conversaciones con resúmenes
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        conversations = []
        
        for conversation_file in self.conversations_dir.glob("conversation_*.json"):
            conversation_session_id = None
            try:
                with open(conversation_file, 'r', encoding='utf-8') as f:
                    conversation_data = json.load(f)
                    conversation_session_id = conversation_data.get('session_id')
                
                stored_at = datetime.fromisoformat(conversation_data["stored_at"])
                if stored_at >= cutoff_date:
                    summary = {
                        "session_id": conversation_data["session_id"],
                        "stored_at": conversation_data["stored_at"],
                        "message_count": conversation_data["message_count"],
                        "metadata": conversation_data.get("metadata", {}),
                        "file_path": str(conversation_file)
                    }
                    conversations.append(summary)
            except Exception:
                logger.exception('Failed to read conversation file %s', conversation_file, extra={'session_id': conversation_session_id, 'log_context': f'file={conversation_file}'})
                continue
        
        # Ordenar por fecha más reciente
        conversations.sort(key=lambda x: x["stored_at"], reverse=True)
        return conversations[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de memoria
        
        Returns:
            Estadísticas de memoria
        """
        total_conversations = len(list(self.conversations_dir.glob("conversation_*.json")))
        
        # Calcular tamaño total
        total_size = 0
        for file_path in self.memory_root.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        # Estadísticas por período
        now = datetime.now()
        periods = {
            "last_day": now - timedelta(days=1),
            "last_week": now - timedelta(days=7),
            "last_month": now - timedelta(days=30)
        }
        
        period_stats = {}
        for period_name, cutoff in periods.items():
            count = 0
            for conversation_file in self.conversations_dir.glob("conversation_*.json"):
                try:
                    with open(conversation_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    stored_at = datetime.fromisoformat(data["stored_at"])
                    if stored_at >= cutoff:
                        count += 1
                except Exception:
                    continue
            period_stats[period_name] = count
        
        return {
            "total_conversations": total_conversations,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "memory_root": str(self.memory_root),
            "period_stats": period_stats,
            "directories": {
                "conversations": len(list(self.conversations_dir.glob("*"))),
                "context": len(list(self.context_dir.glob("*"))),
                "embeddings": len(list(self.embeddings_dir.glob("*")))
            }
        }
    
    def _calculate_conversation_hash(self, messages: List[Dict[str, Any]]) -> str:
        """Calcula hash único de la conversación"""
        conversation_text = json.dumps(messages, sort_keys=True)
        return hashlib.md5(conversation_text.encode()).hexdigest()
    
    def _index_conversation(self, session_id: str, messages: List[Dict[str, Any]], timestamp: str):
        """Crea índice de búsqueda para la conversación"""
        index_file = self.context_dir / f"index_{session_id}.json"
        
        # Extraer contenido de búsqueda
        searchable_content = []
        for i, message in enumerate(messages):
            content = message.get("content", "")
            if content:
                searchable_content.append({
                    "message_index": i,
                    "role": message.get("role", "unknown"),
                    "content": content,
                    "keywords": self._extract_keywords(content)
                })
        
        index_data = {
            "session_id": session_id,
            "created_at": timestamp,
            "content": searchable_content,
            "total_messages": len(messages)
        }
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    def _search_conversation_index(self, query: str, session_id: str, limit: int, time_window_days: int) -> List[Dict[str, Any]]:
        """Busca en los índices de conversaciones"""
        query_lower = query.lower()
        query_keywords = self._extract_keywords(query)
        results = []
        
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        
        index_pattern = f"index_{session_id}.json" if session_id else "index_*.json"
        for index_file in self.context_dir.glob(index_pattern):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                # Verificar ventana de tiempo
                created_at = datetime.fromisoformat(index_data["created_at"])
                if created_at < cutoff_date:
                    continue
                
                # Calcular relevancia
                relevance_score = 0
                matched_content = []
                
                for content_item in index_data["content"]:
                    item_content = content_item["content"].lower()
                    item_keywords = content_item["keywords"]
                    
                    # Búsqueda por coincidencia exacta
                    if query_lower in item_content:
                        relevance_score += 10
                        matched_content.append(content_item["content"])
                    
                    # Búsqueda por keywords
                    matching_keywords = set(query_keywords) & set(item_keywords)
                    if matching_keywords:
                        relevance_score += len(matching_keywords) * 5
                        matched_content.append(content_item["content"])
                
                if relevance_score > 0:
                    results.append({
                        "session_id": index_data["session_id"],
                        "score": relevance_score,
                        "matched_content": matched_content[:3],  # Top 3 matches
                        "timestamp": index_data["created_at"]
                    })
            
            except Exception:
                logger.exception('Failed to search index %s', index_file, extra={'log_context': f'index={index_file}'})
                continue
        
        # Ordenar por relevancia
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrae keywords básicos del texto"""
        # Lista de stop words básica
        stop_words = {
            "el", "la", "de", "que", "y", "a", "en", "un", "es", "se", "no", "te", "lo", "le", 
            "da", "su", "por", "son", "con", "para", "al", "del", "los", "las", "una", "como",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with"
        }
        
        words = text.lower().split()
        keywords = []
        
        for word in words:
            # Limpiar palabra
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) > 3 and clean_word not in stop_words:
                keywords.append(clean_word)
        
        return list(set(keywords))  # Remover duplicados
    
    def _extract_relevant_messages(self, messages: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Extrae mensajes más relevantes a la consulta"""
        query_lower = query.lower()
        relevant_messages = []
        
        for message in messages:
            content = message.get("content", "").lower()
            if query_lower in content:
                relevant_messages.append(message)
        
        return relevant_messages[:5]  # Top 5 mensajes más relevantes
    
    def _get_word_frequency(self, text: str) -> Dict[str, int]:
        """Obtiene frecuencia de palabras en el texto"""
        words = text.split()
        word_freq = defaultdict(int)
        
        for word in words:
            clean_word = ''.join(c for c in word if c.isalnum()).lower()
            if len(clean_word) > 3:
                word_freq[clean_word] += 1
        
        return dict(word_freq)
