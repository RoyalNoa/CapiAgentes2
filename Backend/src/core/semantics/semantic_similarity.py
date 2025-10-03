"""
Semantic Similarity Engine

Motor de similaridad semántica para comparación inteligente
de consultas con intents conocidos. Evoluciona desde matching
de keywords a verdadera comprensión semántica.
"""

import math
from typing import Dict, List, Tuple, Set
from collections import Counter

from src.core.logging import get_logger

logger = get_logger(__name__)


class SemanticSimilarity:
    """
    Motor de similaridad semántica

    Implementa múltiples algoritmos de similaridad:
    1. Jaccard Similarity (baseline)
    2. Cosine Similarity con TF-IDF
    3. Semantic Token Matching
    4. Future: Embeddings-based similarity
    """

    def __init__(self):
        self.stopwords = self._load_spanish_stopwords()
        self.synonym_groups = self._load_synonym_groups()
        self._token_cache: Dict[Tuple[str, bool], Set[str]] = {}
        self._concept_cache: Dict[str, List[str]] = {}

        logger.info({"event": "semantic_similarity_initialized",
                    "stopwords_count": len(self.stopwords),
                    "synonym_groups": len(self.synonym_groups)})

    def calculate_similarity(self, query: str, reference: str, method: str = "hybrid") -> float:
        """
        Calcula similaridad entre query y referencia

        Args:
            query: Consulta del usuario
            reference: Texto de referencia (signature de intent)
            method: Método de cálculo ("jaccard", "cosine", "semantic", "hybrid")

        Returns:
            Score de similaridad entre 0 y 1
        """
        if method == "jaccard":
            return self._jaccard_similarity(query, reference)
        elif method == "cosine":
            return self._cosine_similarity(query, reference)
        elif method == "semantic":
            return self._semantic_similarity(query, reference)
        elif method == "hybrid":
            return self._hybrid_similarity(query, reference)
        else:
            raise ValueError(f"Unknown similarity method: {method}")

    def _jaccard_similarity(self, query: str, reference: str) -> float:
        """Similaridad de Jaccard (intersección / unión)"""
        query_tokens = self._tokenize_and_normalize(query)
        ref_tokens = self._tokenize_and_normalize(reference)

        if not query_tokens and not ref_tokens:
            return 1.0
        if not query_tokens or not ref_tokens:
            return 0.0

        intersection = len(query_tokens.intersection(ref_tokens))
        union = len(query_tokens.union(ref_tokens))

        return intersection / union if union > 0 else 0.0

    def _cosine_similarity(self, query: str, reference: str) -> float:
        """Similaridad de coseno con TF-IDF"""
        query_tokens = self._tokenize_and_normalize(query, remove_stopwords=True)
        ref_tokens = self._tokenize_and_normalize(reference, remove_stopwords=True)

        if not query_tokens or not ref_tokens:
            return 0.0

        # Crear vectores TF
        query_tf = Counter(query_tokens)
        ref_tf = Counter(ref_tokens)

        # Obtener vocabulario común
        vocab = set(query_tokens) | set(ref_tokens)

        # Crear vectores
        query_vector = [query_tf.get(word, 0) for word in vocab]
        ref_vector = [ref_tf.get(word, 0) for word in vocab]

        # Calcular coseno
        dot_product = sum(a * b for a, b in zip(query_vector, ref_vector))
        magnitude_query = math.sqrt(sum(a * a for a in query_vector))
        magnitude_ref = math.sqrt(sum(a * a for a in ref_vector))

        if magnitude_query == 0 or magnitude_ref == 0:
            return 0.0

        return dot_product / (magnitude_query * magnitude_ref)

    def _semantic_similarity(self, query: str, reference: str) -> float:
        """Similaridad semántica usando sinónimos y expansión de conceptos"""
        query_concepts = self._extract_semantic_concepts(query)
        ref_concepts = self._extract_semantic_concepts(reference)

        # Adicionar matching directo de sinónimos
        synonym_score = self._calculate_synonym_similarity(query, reference)

        if not query_concepts or not ref_concepts:
            return synonym_score

        # Calcular matches semánticos
        semantic_matches = 0
        total_concepts = len(query_concepts)

        for query_concept in query_concepts:
            for ref_concept in ref_concepts:
                if self._concepts_are_similar(query_concept, ref_concept):
                    semantic_matches += 1
                    break  # Solo contar un match por concepto de query

        concept_score = semantic_matches / total_concepts if total_concepts > 0 else 0.0

        # Combinar scores con peso hacia sinónimos
        return max(synonym_score * 0.7 + concept_score * 0.3, synonym_score, concept_score)

    def _calculate_synonym_similarity(self, query: str, reference: str) -> float:
        """Calcula similaridad directa usando grupos de sinónimos"""
        query_tokens = self._tokenize_and_normalize(query, remove_stopwords=True)
        ref_tokens = self._tokenize_and_normalize(reference, remove_stopwords=True)

        if not query_tokens or not ref_tokens:
            return 0.0

        synonym_matches = 0
        total_tokens = len(query_tokens)

        for query_token in query_tokens:
            # Buscar match directo
            if query_token in ref_tokens:
                synonym_matches += 1
                continue

            # Buscar match con tolerancia a typos
            typo_match = self._find_typo_match(query_token, ref_tokens)
            if typo_match:
                synonym_matches += 0.9  # Score menor para typos
                continue

            # Buscar match en grupos de sinónimos
            for synonym_group in self.synonym_groups:
                if query_token in synonym_group:
                    # Ver si algún sinónimo está en la referencia
                    if any(syn in ref_tokens for syn in synonym_group):
                        synonym_matches += 1
                        break

        return synonym_matches / total_tokens if total_tokens > 0 else 0.0

    def _hybrid_similarity(self, query: str, reference: str) -> float:
        """Combina múltiples métodos para mayor robustez"""
        jaccard_score = self._jaccard_similarity(query, reference)
        cosine_score = self._cosine_similarity(query, reference)
        semantic_score = self._semantic_similarity(query, reference)

        # Pesos ajustables según el dominio - Mayor peso a semántica
        weights = {
            'jaccard': 0.2,    # Baseline para matches exactos
            'cosine': 0.3,     # TF-IDF para términos importantes
            'semantic': 0.5    # Peso mayor para sinónimos y conceptos
        }

        hybrid_score = (
            weights['jaccard'] * jaccard_score +
            weights['cosine'] * cosine_score +
            weights['semantic'] * semantic_score
        )

        return hybrid_score

    def _find_typo_match(self, token: str, candidates: Set[str]) -> bool:
        """Encuentra matches con tolerancia a errores tipográficos"""
        for candidate in candidates:
            if self._is_typo_variant(token, candidate):
                return True
        return False

    def _is_typo_variant(self, word1: str, word2: str) -> bool:
        """Determina si dos palabras son variantes tipográficas"""
        if len(word1) < 3 or len(word2) < 3:
            return False

        # Calcular distancia de Levenshtein simple
        distance = self._levenshtein_distance(word1, word2)
        max_len = max(len(word1), len(word2))

        # Permitir 1 error para palabras cortas, 2 para largas
        max_errors = 1 if max_len <= 5 else 2

        return distance <= max_errors

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calcula distancia de Levenshtein entre dos strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _tokenize_and_normalize(self, text: str, remove_stopwords: bool = False) -> Set[str]:
        """Tokeniza y normaliza texto"""
        cache_key = (text, remove_stopwords)
        if cache_key in self._token_cache:
            return self._token_cache[cache_key]

        tokens = text.lower().split()

        normalized_tokens = []
        for token in tokens:
            clean_token = ''.join(c for c in token if c.isalnum())
            if clean_token:
                normalized_tokens.append(clean_token)

        if remove_stopwords:
            normalized_tokens = [t for t in normalized_tokens if t not in self.stopwords]

        result = set(normalized_tokens)
        self._token_cache[cache_key] = result
        return result

    def _extract_semantic_concepts(self, text: str) -> List[str]:
        """Extrae conceptos semánticos del texto"""
        if text in self._concept_cache:
            return self._concept_cache[text]

        concepts = []
        text_lower = text.lower()

        # Conceptos de archivo/documento
        file_concepts = [
            "archivo", "documento", "file", "fichero",
            "excel", "csv", "word", "pdf", "texto"
        ]
        for concept in file_concepts:
            if concept in text_lower:
                concepts.append("file_operation")
                break

        # Conceptos de contenido/lectura
        content_concepts = [
            "contenido", "dentro", "contiene", "mostrar", "ver",
            "leer", "abrir", "que tiene", "que dice"
        ]
        for concept in content_concepts:
            if concept in text_lower:
                concepts.append("content_access")
                break

        # Conceptos de análisis
        analysis_concepts = [
            "analizar", "resumen", "total", "estadísticas",
            "métricas", "datos", "información"
        ]
        for concept in analysis_concepts:
            if concept in text_lower:
                concepts.append("data_analysis")
                break

        # Conceptos de sucursal/branch
        branch_concepts = [
            "sucursal", "branch", "oficina", "sede"
        ]
        for concept in branch_concepts:
            if concept in text_lower:
                concepts.append("branch_operation")
                break

        self._concept_cache[text] = concepts
        return concepts

    def _concepts_are_similar(self, concept1: str, concept2: str) -> bool:
        """Determina si dos conceptos son semánticamente similares"""
        if concept1 == concept2:
            return True

        # Grupos de conceptos similares
        concept_groups = [
            {"file_operation", "document_handling", "file_management"},
            {"content_access", "data_reading", "information_retrieval"},
            {"data_analysis", "analytics", "reporting"},
            {"branch_operation", "location_analysis", "office_management"}
        ]

        for group in concept_groups:
            if concept1 in group and concept2 in group:
                return True

        return False

    def _load_spanish_stopwords(self) -> Set[str]:
        """Carga stopwords en español"""
        return {
            'y', 'e', 'ni', 'que', 'o', 'u', 'a', 'ante', 'bajo', 'cabe',
            'con', 'contra', 'de', 'desde', 'en', 'entre', 'hacia', 'hasta',
            'para', 'por', 'según', 'sin', 'so', 'sobre', 'tras', 'durante',
            'mediante', 'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
            'aquel', 'aquella', 'aquellos', 'aquellas', 'mi', 'tu', 'su',
            'nuestro', 'vuestro', 'suyo', 'me', 'te', 'se', 'nos', 'os',
            'le', 'les', 'lo', 'la', 'los', 'las', 'mí', 'ti', 'sí',
            'yo', 'tú', 'él', 'ella', 'nosotros', 'vosotros', 'ellos', 'ellas',
            'ser', 'estar', 'haber', 'tener', 'hacer', 'decir', 'ir', 'ver',
            'dar', 'saber', 'querer', 'llegar', 'pasar', 'deber', 'poner',
            'parecer', 'quedar', 'creer', 'hablar', 'llevar', 'dejar', 'seguir',
            'encontrar', 'llamar', 'venir', 'pensar', 'salir', 'volver', 'tomar',
            'conocer', 'vivir', 'sentir', 'tratar', 'mirar', 'contar', 'empezar',
            'esperar', 'buscar', 'existir', 'entrar', 'trabajar', 'escribir',
            'perder', 'producir', 'ocurrir', 'entender', 'pedir', 'recibir'
        }

    def _load_synonym_groups(self) -> List[Set[str]]:
        """Carga grupos de sinónimos específicos del dominio"""
        return [
            # Archivo/documento
            {"archivo", "fichero", "documento", "file", "doc"},

            # Leer/ver/mostrar
            {"leer", "ver", "mostrar", "abrir", "consultar", "revisar", "read", "show", "display"},

            # Contenido/dentro
            {"contenido", "dentro", "adentro", "interior", "contiene", "tiene", "content", "inside"},

            # Análisis/resumen
            {"análisis", "resumen", "sumario", "reporte", "informe", "analysis", "summary", "report"},

            # Sucursal/oficina
            {"sucursal", "oficina", "branch", "sede", "centro", "office"},

            # Datos/información
            {"datos", "información", "data", "registros", "info", "information"},

            # Excel/spreadsheet
            {"excel", "hoja", "spreadsheet", "planilla", "xls", "xlsx", "cálculo"},

            # Total/suma
            {"total", "suma", "sumatoria", "agregado", "totales", "sum"},

            # Crear/escribir/generar
            {"crear", "escribir", "generar", "producir", "elaborar", "create", "write", "generate"},

            # Anomalías/outliers
            {"outliers", "outlier", "anomalías", "anomalía", "atípicos", "atípico", "irregular", "irregularidades"},

            # Detectar/encontrar/buscar
            {"detectar", "encontrar", "buscar", "identificar", "localizar", "detect", "find", "search", "identify"},

            # Sospechoso/raro/extraño
            {"sospechoso", "sospechosos", "raro", "raros", "extraño", "extraños", "unusual", "suspicious", "weird"}
        ]

    def find_best_matches(self, query: str, candidates: List[str],
                         top_k: int = 3, min_threshold: float = 0.4) -> List[Tuple[str, float]]:
        """
        Encuentra los mejores matches para una query

        Args:
            query: Consulta a evaluar
            candidates: Lista de candidatos
            top_k: Número máximo de resultados
            min_threshold: Threshold mínimo de similaridad

        Returns:
            Lista de (candidato, score) ordenada por score
        """
        scored_candidates = []

        for candidate in candidates:
            score = self.calculate_similarity(query, candidate, method="hybrid")
            if score >= min_threshold:
                scored_candidates.append((candidate, score))

        # Ordenar por score descendente y tomar top_k
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:top_k]

    def explain_similarity(self, query: str, reference: str) -> Dict[str, any]:
        """
        Explica por qué dos textos son similares (para debugging)

        Returns:
            Dict con métricas detalladas de similaridad
        """
        jaccard = self._jaccard_similarity(query, reference)
        cosine = self._cosine_similarity(query, reference)
        semantic = self._semantic_similarity(query, reference)
        hybrid = self._hybrid_similarity(query, reference)

        query_tokens = self._tokenize_and_normalize(query)
        ref_tokens = self._tokenize_and_normalize(reference)
        intersection = query_tokens.intersection(ref_tokens)

        query_concepts = self._extract_semantic_concepts(query)
        ref_concepts = self._extract_semantic_concepts(reference)

        return {
            "scores": {
                "jaccard": jaccard,
                "cosine": cosine,
                "semantic": semantic,
                "hybrid": hybrid
            },
            "token_analysis": {
                "query_tokens": list(query_tokens),
                "reference_tokens": list(ref_tokens),
                "common_tokens": list(intersection),
                "token_overlap_ratio": len(intersection) / len(query_tokens.union(ref_tokens)) if query_tokens.union(ref_tokens) else 0
            },
            "concept_analysis": {
                "query_concepts": query_concepts,
                "reference_concepts": ref_concepts
            }
        }