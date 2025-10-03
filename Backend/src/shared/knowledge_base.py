"""
Knowledge Base - Sistema de base de conocimiento para la IA
"""

import os
import json
import uuid
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import defaultdict, Counter
import re


class KnowledgeBase:
    """
    Gestiona una base de conocimiento con capacidades de búsqueda y organización
    """
    
    def __init__(self, knowledge_root: Path):
        self.knowledge_root = Path(knowledge_root)
        self.documents_dir = self.knowledge_root / "documents"
        self.index_file = self.knowledge_root / "search_index.db"
        self.stats_file = self.knowledge_root / "stats.json"
        
        # Crear directorios necesarios
        for directory in [self.knowledge_root, self.documents_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Inicializar base de datos de índices
        self._init_search_database()
    
    def _init_search_database(self):
        """Inicializa la base de datos SQLite para búsquedas"""
        with sqlite3.connect(self.index_file) as conn:
            cursor = conn.cursor()
            
            # Tabla principal de documentos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    doc_type TEXT DEFAULT 'general',
                    file_path TEXT,
                    metadata TEXT
                )
            ''')
            
            # Tabla de palabras clave para búsqueda
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE
                )
            ''')
            
            # Índices para optimizar búsquedas
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_keywords_keyword 
                ON keywords (keyword)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_keywords_doc_id 
                ON keywords (doc_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_documents_type 
                ON documents (doc_type)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_documents_created 
                ON documents (created_at)
            ''')
            
            conn.commit()
    
    def add_document(self, 
                    doc_id: str,
                    content: str,
                    title: str = None,
                    doc_type: str = "general",
                    file_path: str = None,
                    metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Añade un documento a la base de conocimiento
        
        Args:
            doc_id: ID único del documento
            content: Contenido del documento
            title: Título del documento
            doc_type: Tipo de documento
            file_path: Ruta del archivo asociado
            metadata: Metadata adicional
        
        Returns:
            Información del documento añadido
        """
        if not title:
            title = f"Document {doc_id[:8]}"
        
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        now = datetime.now()
        
        # Extraer palabras clave del contenido
        keywords = self._extract_keywords_advanced(content)
        
        # Guardar en base de datos
        with sqlite3.connect(self.index_file) as conn:
            cursor = conn.cursor()
            
            # Verificar si el documento ya existe
            cursor.execute("SELECT doc_id FROM documents WHERE doc_id = ?", (doc_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Actualizar documento existente
                cursor.execute('''
                    UPDATE documents 
                    SET content = ?, content_hash = ?, updated_at = ?, 
                        title = ?, doc_type = ?, file_path = ?, metadata = ?
                    WHERE doc_id = ?
                ''', (content, content_hash, now, title, doc_type, 
                     file_path, json.dumps(metadata or {}), doc_id))
                
                # Limpiar palabras clave existentes
                cursor.execute("DELETE FROM keywords WHERE doc_id = ?", (doc_id,))
            else:
                # Insertar nuevo documento
                cursor.execute('''
                    INSERT INTO documents 
                    (doc_id, title, content, content_hash, created_at, updated_at, 
                     doc_type, file_path, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (doc_id, title, content, content_hash, now, now, 
                     doc_type, file_path, json.dumps(metadata or {})))
            
            # Insertar palabras clave
            for keyword, frequency in keywords.items():
                cursor.execute('''
                    INSERT INTO keywords (doc_id, keyword, frequency)
                    VALUES (?, ?, ?)
                ''', (doc_id, keyword, frequency))
            
            conn.commit()
        
        # Actualizar estadísticas
        self._update_stats()
        
        return {
            "doc_id": doc_id,
            "title": title,
            "content_length": len(content),
            "keywords_count": len(keywords),
            "action": "updated" if exists else "created",
            "created_at": now.isoformat()
        }
    
    def search_documents(self, 
                        query: str,
                        limit: int = 10,
                        doc_type: str = None,
                        days_back: int = None) -> List[Dict[str, Any]]:
        """
        Busca documentos en la base de conocimiento
        
        Args:
            query: Consulta de búsqueda
            limit: Número máximo de resultados
            doc_type: Filtrar por tipo de documento
            days_back: Buscar solo en documentos de los últimos N días
        
        Returns:
            Lista de documentos relevantes con puntuaciones
        """
        query_keywords = self._extract_keywords_advanced(query.lower())
        
        if not query_keywords:
            return []
        
        # Construir consulta SQL
        base_query = '''
            SELECT d.doc_id, d.title, d.content, d.created_at, d.updated_at,
                   d.doc_type, d.file_path, d.metadata,
                   SUM(k.frequency) as relevance_score
            FROM documents d
            JOIN keywords k ON d.doc_id = k.doc_id
            WHERE k.keyword IN ({})
        '''.format(','.join(['?' for _ in query_keywords]))
        
        params = list(query_keywords.keys())
        
        # Agregar filtros adicionales
        if doc_type:
            base_query += " AND d.doc_type = ?"
            params.append(doc_type)
        
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            base_query += " AND d.created_at >= ?"
            params.append(cutoff_date)
        
        base_query += '''
            GROUP BY d.doc_id
            ORDER BY relevance_score DESC, d.updated_at DESC
            LIMIT ?
        '''
        params.append(limit)
        
        # Ejecutar búsqueda
        results = []
        with sqlite3.connect(self.index_file) as conn:
            cursor = conn.cursor()
            cursor.execute(base_query, params)
            
            for row in cursor.fetchall():
                doc_id, title, content, created_at, updated_at, doc_type, file_path, metadata, score = row
                
                # Calcular score mejorado basado en coincidencias exactas
                enhanced_score = score
                content_lower = content.lower()
                query_lower = query.lower()
                
                # Bonus por coincidencia exacta de la consulta
                if query_lower in content_lower:
                    enhanced_score += 50
                
                # Bonus por coincidencia en el título
                if query_lower in title.lower():
                    enhanced_score += 30
                
                # Extraer fragmentos relevantes
                relevant_snippets = self._extract_relevant_snippets(content, query, max_snippets=3)
                
                try:
                    parsed_metadata = json.loads(metadata) if metadata else {}
                except:
                    parsed_metadata = {}
                
                results.append({
                    "doc_id": doc_id,
                    "title": title,
                    "content": content,
                    "score": enhanced_score,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "doc_type": doc_type,
                    "file_path": file_path,
                    "metadata": parsed_metadata,
                    "relevant_snippets": relevant_snippets
                })
        
        # Ordenar por score mejorado
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un documento específico por ID
        
        Args:
            doc_id: ID del documento
        
        Returns:
            Documento completo o None si no existe
        """
        with sqlite3.connect(self.index_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT doc_id, title, content, created_at, updated_at,
                       doc_type, file_path, metadata
                FROM documents 
                WHERE doc_id = ?
            ''', (doc_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            doc_id, title, content, created_at, updated_at, doc_type, file_path, metadata = row
            
            try:
                parsed_metadata = json.loads(metadata) if metadata else {}
            except:
                parsed_metadata = {}
            
            return {
                "doc_id": doc_id,
                "title": title,
                "content": content,
                "created_at": created_at,
                "updated_at": updated_at,
                "doc_type": doc_type,
                "file_path": file_path,
                "metadata": parsed_metadata
            }
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Elimina un documento de la base de conocimiento
        
        Args:
            doc_id: ID del documento a eliminar
        
        Returns:
            True si se eliminó exitosamente
        """
        with sqlite3.connect(self.index_file) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        
        if deleted:
            self._update_stats()
        
        return deleted
    
    def list_documents(self, 
                      doc_type: str = None,
                      limit: int = 50,
                      days_back: int = None) -> List[Dict[str, Any]]:
        """
        Lista documentos en la base de conocimiento
        
        Args:
            doc_type: Filtrar por tipo de documento
            limit: Número máximo de documentos
            days_back: Mostrar solo documentos de los últimos N días
        
        Returns:
            Lista de documentos con información básica
        """
        base_query = '''
            SELECT doc_id, title, created_at, updated_at, doc_type, file_path,
                   LENGTH(content) as content_length
            FROM documents
            WHERE 1=1
        '''
        params = []
        
        if doc_type:
            base_query += " AND doc_type = ?"
            params.append(doc_type)
        
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            base_query += " AND created_at >= ?"
            params.append(cutoff_date)
        
        base_query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        results = []
        with sqlite3.connect(self.index_file) as conn:
            cursor = conn.cursor()
            cursor.execute(base_query, params)
            
            for row in cursor.fetchall():
                doc_id, title, created_at, updated_at, doc_type, file_path, content_length = row
                results.append({
                    "doc_id": doc_id,
                    "title": title,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "doc_type": doc_type,
                    "file_path": file_path,
                    "content_length": content_length
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la base de conocimiento
        
        Returns:
            Estadísticas completas
        """
        stats = {
            "total_documents": 0,
            "total_keywords": 0,
            "document_types": {},
            "recent_activity": {},
            "storage_info": {},
            "last_updated": datetime.now().isoformat()
        }
        
        with sqlite3.connect(self.index_file) as conn:
            cursor = conn.cursor()
            
            # Contar documentos totales
            cursor.execute("SELECT COUNT(*) FROM documents")
            stats["total_documents"] = cursor.fetchone()[0]
            
            # Contar palabras clave totales
            cursor.execute("SELECT COUNT(*) FROM keywords")
            stats["total_keywords"] = cursor.fetchone()[0]
            
            # Estadísticas por tipo de documento
            cursor.execute('''
                SELECT doc_type, COUNT(*), AVG(LENGTH(content))
                FROM documents
                GROUP BY doc_type
            ''')
            for doc_type, count, avg_length in cursor.fetchall():
                stats["document_types"][doc_type] = {
                    "count": count,
                    "avg_content_length": int(avg_length) if avg_length else 0
                }
            
            # Actividad reciente (últimos 7 días)
            cutoff_date = datetime.now() - timedelta(days=7)
            cursor.execute('''
                SELECT DATE(created_at) as date, COUNT(*)
                FROM documents
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''', (cutoff_date,))
            
            for date, count in cursor.fetchall():
                stats["recent_activity"][date] = count
        
        # Información de almacenamiento
        try:
            db_size = self.index_file.stat().st_size if self.index_file.exists() else 0
            docs_size = sum(f.stat().st_size for f in self.documents_dir.rglob("*") if f.is_file())
            
            stats["storage_info"] = {
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "documents_size_mb": round(docs_size / (1024 * 1024), 2),
                "total_size_mb": round((db_size + docs_size) / (1024 * 1024), 2)
            }
        except Exception as e:
            stats["storage_info"] = {"error": str(e)}
        
        # Guardar estadísticas en archivo
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        
        return stats
    
    def reindex_documents(self) -> Dict[str, Any]:
        """
        Reindexar todos los documentos para mejorar la búsqueda
        
        Returns:
            Resultado de la reindexación
        """
        start_time = datetime.now()
        
        with sqlite3.connect(self.index_file) as conn:
            cursor = conn.cursor()
            
            # Obtener todos los documentos
            cursor.execute("SELECT doc_id, content FROM documents")
            documents = cursor.fetchall()
            
            # Limpiar índices existentes
            cursor.execute("DELETE FROM keywords")
            
            # Reindexar cada documento
            for doc_id, content in documents:
                keywords = self._extract_keywords_advanced(content)
                
                for keyword, frequency in keywords.items():
                    cursor.execute('''
                        INSERT INTO keywords (doc_id, keyword, frequency)
                        VALUES (?, ?, ?)
                    ''', (doc_id, keyword, frequency))
            
            conn.commit()
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        return {
            "reindexed_documents": len(documents),
            "processing_time_seconds": round(processing_time, 2),
            "completed_at": end_time.isoformat()
        }
    
    def _extract_keywords_advanced(self, text: str) -> Dict[str, int]:
        """Extrae palabras clave con análisis de frecuencia avanzado"""
        # Limpiar texto
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        
        # Stop words expandida
        stop_words = {
            "el", "la", "de", "que", "y", "a", "en", "un", "es", "se", "no", "te", "lo", "le",
            "da", "su", "por", "son", "con", "para", "al", "del", "los", "las", "una", "como",
            "pero", "sus", "le", "ya", "o", "porque", "cuando", "muy", "sin", "sobre", "tambien",
            "me", "hasta", "donde", "quien", "desde", "todos", "durante", "todo", "algo", "mismo",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
            "by", "from", "up", "about", "into", "through", "during", "before", "after", "above",
            "below", "to", "from", "down", "out", "off", "over", "under", "again", "further",
            "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both",
            "each", "few", "more", "most", "other", "some", "such", "only", "own", "same", "so",
            "than", "too", "very", "can", "will", "just", "should", "now"
        }
        
        # Contar frecuencias
        word_freq = Counter()
        
        for word in words:
            # Filtrar palabras muy cortas y stop words
            if len(word) >= 3 and word not in stop_words and word.isalpha():
                word_freq[word] += 1
        
        # Filtrar palabras con frecuencia muy baja si hay muchas palabras
        if len(word_freq) > 50:
            min_frequency = 2
            word_freq = {word: freq for word, freq in word_freq.items() if freq >= min_frequency}
        
        return dict(word_freq.most_common(100))  # Top 100 palabras
    
    def _extract_relevant_snippets(self, content: str, query: str, max_snippets: int = 3) -> List[str]:
        """Extrae fragmentos relevantes del contenido"""
        query_lower = query.lower()
        content_lower = content.lower()
        snippets = []
        
        # Buscar coincidencias exactas
        sentences = content.split('.')
        for sentence in sentences:
            if query_lower in sentence.lower() and len(sentence.strip()) > 10:
                # Limpiar y truncar si es necesario
                snippet = sentence.strip()
                if len(snippet) > 200:
                    # Encontrar la posición de la consulta y mostrar contexto
                    query_pos = snippet.lower().find(query_lower)
                    start = max(0, query_pos - 50)
                    end = min(len(snippet), query_pos + len(query) + 50)
                    snippet = "..." + snippet[start:end] + "..."
                
                snippets.append(snippet)
                
                if len(snippets) >= max_snippets:
                    break
        
        return snippets
    
    def _update_stats(self):
        """Actualiza estadísticas internas (llamada automáticamente)"""
        # Las estadísticas se calculan dinámicamente en get_stats()
        # Esta función puede usarse para optimizaciones futuras
        pass