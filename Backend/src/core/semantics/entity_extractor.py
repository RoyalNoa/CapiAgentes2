"""
Entity Extractor for Domain-Specific Entities

Extrae entidades específicas del dominio financiero/oficina
de consultas en lenguaje natural.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedEntity:
    """Entidad extraída con metadata"""
    entity_type: str
    value: str
    confidence: float
    position: Tuple[int, int]  # start, end positions in text
    raw_match: str


class EntityExtractor:
    """
    Extractor inteligente de entidades específicas del dominio

    Extrae:
    - Nombres de archivo
    - Referencias a sucursales
    - Referencias temporales
    - Acciones/operaciones
    - Formatos de archivo
    """

    def __init__(self):
        self.filename_patterns = self._initialize_filename_patterns()
        self.branch_patterns = self._initialize_branch_patterns()
        self.time_patterns = self._initialize_time_patterns()
        self.action_patterns = self._initialize_action_patterns()
        self.format_keywords = self._initialize_format_keywords()

        logger.info({"event": "entity_extractor_initialized",
                    "pattern_groups": 5})

    def extract_all_entities(self, query: str) -> Dict[str, List[ExtractedEntity]]:
        """Extrae todas las entidades de una query"""
        entities = {
            'filenames': self.extract_filenames(query),
            'branches': self.extract_branches(query),
            'time_references': self.extract_time_references(query),
            'actions': self.extract_actions(query),
            'file_formats': self.extract_file_formats(query)
        }

        # Log summary
        total_entities = sum(len(ents) for ents in entities.values())
        logger.info({"event": "entities_extracted",
                    "query": query,
                    "total_entities": total_entities,
                    "by_type": {k: len(v) for k, v in entities.items()}})

        return entities

    def extract_filenames(self, query: str) -> List[ExtractedEntity]:
        """Extrae nombres de archivo con alta precisión"""
        filenames = []

        for pattern_name, pattern in self.filename_patterns.items():
            for match in re.finditer(pattern, query, re.IGNORECASE):
                raw_filename = match.group(1).strip()
                cleaned_filename = self._clean_filename(raw_filename)

                # Special handling for with_extension pattern - remove extension
                if pattern_name == 'with_extension' and '.' in cleaned_filename:
                    cleaned_filename = cleaned_filename.split('.')[0]

                if cleaned_filename and len(cleaned_filename) > 1:
                    entity = ExtractedEntity(
                        entity_type='filename',
                        value=cleaned_filename,
                        confidence=self._calculate_filename_confidence(cleaned_filename, pattern_name),
                        position=(match.start(), match.end()),
                        raw_match=match.group(0)
                    )
                    filenames.append(entity)

        # Deduplicar por valor
        return self._deduplicate_entities(filenames)

    def extract_branches(self, query: str) -> List[ExtractedEntity]:
        """Extrae referencias a sucursales"""
        branches = []

        for pattern_name, pattern in self.branch_patterns.items():
            for match in re.finditer(pattern, query, re.IGNORECASE):
                branch_name = match.group(1).strip()

                if branch_name and len(branch_name) > 1:
                    entity = ExtractedEntity(
                        entity_type='branch',
                        value=branch_name,
                        confidence=0.9 if pattern_name == 'explicit' else 0.7,
                        position=(match.start(), match.end()),
                        raw_match=match.group(0)
                    )
                    branches.append(entity)

        return self._deduplicate_entities(branches)

    def extract_time_references(self, query: str) -> List[ExtractedEntity]:
        """Extrae referencias temporales"""
        time_refs = []

        for pattern_name, pattern in self.time_patterns.items():
            for match in re.finditer(pattern, query, re.IGNORECASE):
                time_expr = match.group(0).strip()
                parsed_time = self._parse_time_expression(time_expr)

                if parsed_time:
                    entity = ExtractedEntity(
                        entity_type='time_reference',
                        value=parsed_time,
                        confidence=0.8,
                        position=(match.start(), match.end()),
                        raw_match=time_expr
                    )
                    time_refs.append(entity)

        return time_refs

    def extract_actions(self, query: str) -> List[ExtractedEntity]:
        """Extrae acciones/operaciones"""
        actions = []

        for action_type, keywords in self.action_patterns.items():
            for keyword in keywords:
                if keyword in query.lower():
                    # Encontrar posición exacta
                    match = re.search(rf'\b{re.escape(keyword)}\b', query, re.IGNORECASE)
                    if match:
                        entity = ExtractedEntity(
                            entity_type='action',
                            value=action_type,
                            confidence=0.9,
                            position=(match.start(), match.end()),
                            raw_match=match.group(0)
                        )
                        actions.append(entity)
                        break  # Solo una acción por tipo

        return actions

    def extract_file_formats(self, query: str) -> List[ExtractedEntity]:
        """Extrae formatos de archivo"""
        formats = []

        for format_type, indicators in self.format_keywords.items():
            for indicator in indicators:
                if indicator in query.lower():
                    match = re.search(rf'\b{re.escape(indicator)}\b', query, re.IGNORECASE)
                    if match:
                        entity = ExtractedEntity(
                            entity_type='file_format',
                            value=format_type,
                            confidence=0.95,
                            position=(match.start(), match.end()),
                            raw_match=match.group(0)
                        )
                        formats.append(entity)

        return self._deduplicate_entities(formats)

    def _initialize_filename_patterns(self) -> Dict[str, str]:
        """Patrones para extracción de nombres de archivo"""
        return {
            'explicit_filename': r"(?:archivo|documento|file)\s+([^.?!\s]+(?:\s+[^.?!\s]+)*?)(?:\s+(?:del|en|que|se|está)|[.?!]|$)",
            'called_pattern': r"(?:se\s+)?llama(?:do)?\s+([^.?!\s]+(?:\s+[^.?!\s]+)*?)(?=\s+(?:que|con|del|en|para|por|tiene|contiene|dice|y|o)|[.?!]|$)",
            'with_extension': r"\b([a-zA-Z0-9_-]+\.(?:xlsx?|csv|docx?|pdf|txt))\b",
            'named_pattern': r"(?:el\s+)?(?:archivo|documento)\s+([^.?!\s]+(?:\s+[^.?!\s]+)*?)(?:\s+(?:del|en|que|se|está)|[.?!]|$)",
            'simple_called': r"llama\s+([a-zA-Z0-9_\s-]+?)(?:\s|$)",
            'excel_specific': r"excel\s+([a-zA-Z0-9_\s-]+?)(?:\s|$)",
            'word_specific': r"word\s+([a-zA-Z0-9_\s-]+?)(?:\s|$)",
            'documento_specific': r"documento\s+([a-zA-Z0-9_\s-]+?)(?:\s|$)"
        }

    def _initialize_branch_patterns(self) -> Dict[str, str]:
        """Patrones para extracción de sucursales"""
        return {
            'explicit': r"(?:sucursal|branch|oficina)\s+([^.?!\s]+(?:\s+[^.?!\s]+)*?)(?:\s|[.?!]|$)",
            'possessive': r"(?:de\s+la\s+)?sucursal\s+([^.?!\s]+)",
            'location': r"oficina\s+(?:de\s+)?([^.?!\s]+(?:\s+[^.?!\s]+)*?)(?:\s|[.?!]|$)"
        }

    def _initialize_time_patterns(self) -> Dict[str, str]:
        """Patrones para referencias temporales"""
        return {
            'relative': r"(?:último|última|pasado|pasada)\s+(?:mes|año|semana|trimestre)",
            'current': r"(?:este|esta)\s+(?:mes|año|semana|trimestre)",
            'specific_month': r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?\d{4}",
            'year': r"\b\d{4}\b",
            'quarter': r"(?:primer|segundo|tercer|cuarto)\s+trimestre"
        }

    def _initialize_action_patterns(self) -> Dict[str, List[str]]:
        """Patrones para acciones"""
        return {
            'READ_CONTENT': ['contenido', 'dentro', 'contiene', 'que tiene', 'que dice', 'que hay', 'adentro', 'mostrar'],
            'READ_FILE': ['leer', 'read', 'abrir', 'open', 'ver'],
            'WRITE_FILE': ['escribir', 'write', 'crear', 'crea', 'create', 'generar'],
            'LIST_FILES': ['listar', 'list', 'mostrar archivos', 'buscar'],
            'MODIFY_FILE': ['modificar', 'modify', 'editar', 'edit', 'actualizar'],
            'ANALYZE': ['analizar', 'analyze', 'examinar', 'revisar'],
            'SUMMARIZE': ['resumen', 'summary', 'resumir', 'totales']
        }

    def _initialize_format_keywords(self) -> Dict[str, List[str]]:
        """Keywords para formatos de archivo"""
        return {
            'excel': ['excel', 'xlsx', 'xls', 'spreadsheet', 'hoja de cálculo'],
            'word': ['word', 'docx', 'doc', 'documento'],
            'csv': ['csv', 'datos separados', 'comma separated'],
            'pdf': ['pdf', 'documento pdf'],
            'text': ['txt', 'archivo de texto', 'archivo txt', 'texto plano']
        }

    def _clean_filename(self, raw_filename: str) -> str:
        """Limpia nombre de archivo extraído"""
        # Palabras comunes a remover incluyendo tipos de archivo
        cleanup_words = {
            'que', 'esta', 'en', 'mi', 'del', 'de', 'la', 'el', 'se',
            'está', 'son', 'es', 'y', 'o', 'para', 'con', 'por',
            'escritorio', 'desktop', 'folder', 'carpeta',
            # Tipos de archivo a remover del nombre
            'excel', 'word', 'archivo', 'documento', 'file', 'doc',
            'docx', 'xlsx', 'xls', 'csv', 'pdf', 'txt',
            'decime', 'dime', 'decir', 'contame', 'mostrame', 'dame', 'haz', 'hace', 'crea', 'crear', 'generar'
        }

        normalized = raw_filename.strip()
        cut_pattern = r'\b(decime|dime|decir|contame|mostrame|dame|haz|hace|crea|crear|generar|que sepas|que digas)\b'
        match = re.search(cut_pattern, normalized.lower())
        if match:
            normalized = normalized[:match.start()].strip()

        words = normalized.split()
        cleaned_words = []

        for word in words:
            word_clean = word.strip(".,!?()[]{}'\"")
            if (word_clean.lower() not in cleanup_words and len(word_clean) >= 1
                and word_clean.replace('_', '').replace('-', '').isalnum()):
                cleaned_words.append(word_clean)

        result = ' '.join(cleaned_words) if cleaned_words else normalized.strip()

        if len(result.strip()) < 2:
            return normalized.strip() or raw_filename.strip()

        return result

    def _calculate_filename_confidence(self, filename: str, pattern_name: str) -> float:
        """Calcula confianza para nombre de archivo extraído"""
        base_confidence = {
            'with_extension': 0.95,
            'explicit_filename': 0.85,
            'called_pattern': 0.90,
            'named_pattern': 0.80
        }.get(pattern_name, 0.7)

        # Ajustes por características del filename
        if len(filename.split()) > 1:
            base_confidence += 0.05  # Nombres compuestos más confiables

        if any(char.isdigit() for char in filename):
            base_confidence += 0.02  # Números indican especificidad

        return min(0.99, base_confidence)

    def _parse_time_expression(self, time_expr: str) -> str:
        """Parsea expresión temporal a formato estándar"""
        time_expr_lower = time_expr.lower()

        # Mapeo de expresiones comunes
        time_mappings = {
            'último mes': 'last_month',
            'pasado mes': 'last_month',
            'este mes': 'current_month',
            'último año': 'last_year',
            'este año': 'current_year',
            'última semana': 'last_week',
            'esta semana': 'current_week'
        }

        for expr, standard in time_mappings.items():
            if expr in time_expr_lower:
                return standard

        # Años específicos
        year_match = re.search(r'\b(\d{4})\b', time_expr)
        if year_match:
            return f"year_{year_match.group(1)}"

        return time_expr_lower

    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Elimina entidades duplicadas, manteniendo la de mayor confianza"""
        if not entities:
            return []

        # Agrupar por valor
        value_groups = {}
        for entity in entities:
            if entity.value not in value_groups:
                value_groups[entity.value] = []
            value_groups[entity.value].append(entity)

        # Mantener la de mayor confianza por grupo
        deduplicated = []
        for value, group in value_groups.items():
            best_entity = max(group, key=lambda e: e.confidence)
            deduplicated.append(best_entity)

        return deduplicated

    def get_best_entity(self, entities: List[ExtractedEntity]) -> Optional[ExtractedEntity]:
        """Obtiene la entidad con mayor confianza"""
        if not entities:
            return None
        return max(entities, key=lambda e: e.confidence)


    def extract_primary_entities(self, query: str) -> Dict[str, Optional[str]]:
        """Extrae entidades primarias en formato simple para compatibilidad"""
        try:
            filename_entities = self.extract_filenames(query)
            branch_entities = self.extract_branches(query)
            time_entities = self.extract_time_references(query)
            action_entities = self.extract_actions(query)
            format_entities = self.extract_file_formats(query)

            filenames_detected = [entity.value for entity in filename_entities]
            actions_detected = [entity.value for entity in action_entities]
            formats_detected = [entity.value for entity in format_entities]

            filenames_detected = list(dict.fromkeys(filter(None, filenames_detected)))
            actions_detected = list(dict.fromkeys(filter(None, actions_detected)))
            formats_detected = list(dict.fromkeys(filter(None, formats_detected)))

            drop_tokens = {'que', 'se', 'llama', 'archivo', 'documento', 'file'}
            filenames_detected = [name for name in filenames_detected if name.lower() not in drop_tokens]
            cleaned_candidates = []
            for name in filenames_detected:
                lowered = name.lower()
                if any(lowered != other.lower() and lowered in other.lower() for other in filenames_detected):
                    continue
                cleaned_candidates.append(name)
            filenames_detected = cleaned_candidates or filenames_detected

            filename = self._select_primary_filename(filenames_detected, actions_detected, formats_detected)

            secondary_filename: Optional[str] = None
            if filenames_detected:
                for candidate in filenames_detected:
                    lowered = candidate.lower().strip()
                    if candidate == filename:
                        continue
                    if lowered in {'que', 'archivo', 'documento', 'file', 'archivos'}:
                        continue
                    if len(lowered) <= 2:
                        continue
                    secondary_filename = candidate
                    break

            action = self._select_primary_action(actions_detected)
            primary_format = self._select_primary_format(formats_detected)

            branch = self.get_best_entity(branch_entities)
            time_ref = self.get_best_entity(time_entities)

            return {
                'filename': filename,
                'secondary_filename': secondary_filename,
                'branch': branch.value if branch else None,
                'action': action,
                'format': primary_format,
                'time': time_ref.value if time_ref else None,
                'filenames_detected': filenames_detected,
                'actions_detected': actions_detected,
                'formats_detected': formats_detected,
            }

        except Exception as exc:
            logger.exception({"event": "entity_extraction_error", "query": query, "error": str(exc)})
            return {
                'filename': None,
                'secondary_filename': None,
                'branch': None,
                'action': None,
                'format': None,
                'time': None,
                'filenames_detected': [],
                'actions_detected': [],
                'formats_detected': [],
            }


    def _select_primary_action(self, actions_detected: List[str]) -> Optional[str]:
        """Determina la acción principal considerando combinaciones"""
        if not actions_detected:
            return None

        if 'WRITE_FILE' in actions_detected and any(a in {'READ_CONTENT', 'READ_FILE'} for a in actions_detected):
            return 'READ_WRITE'

        priority = ['WRITE_FILE', 'MODIFY_FILE', 'READ_CONTENT', 'READ_FILE', 'LIST_FILES', 'ANALYZE', 'SUMMARIZE']
        for candidate in priority:
            if candidate in actions_detected:
                return candidate

        return actions_detected[0]

    def _select_primary_format(self, formats_detected: List[str]) -> Optional[str]:
        """Selecciona el formato más relevante detectado"""
        if not formats_detected:
            return None

        priority = ['excel', 'csv', 'word', 'pdf', 'text']
        for candidate in priority:
            if candidate in formats_detected:
                return candidate

        return formats_detected[0]

    def _select_primary_filename(self, candidates: List[str], actions_detected: List[str], formats_detected: List[str]) -> Optional[str]:
        """Elige el nombre de archivo más adecuado como referencia principal"""
        if not candidates:
            return None

        filtered_candidates: List[str] = []
        for candidate in candidates:
            lowered = candidate.lower().strip()
            if lowered in {'que', 'archivo', 'documento', 'file', 'archivos'}:
                continue
            if len(lowered) <= 2:
                continue
            filtered_candidates.append(candidate)

        if filtered_candidates:
            candidates = filtered_candidates

        lowered_candidates = [candidate.lower() for candidate in candidates]

        if 'WRITE_FILE' in actions_detected and len(candidates) > 1:
            for candidate, lowered in zip(candidates, lowered_candidates):
                if any(keyword in lowered for keyword in ('resumen', 'summary', 'txt', 'texto')):
                    continue
                return candidate

        if 'text' in formats_detected and len(candidates) > 1:
            for candidate, lowered in zip(candidates, lowered_candidates):
                if any(keyword in lowered for keyword in ('resumen', 'summary', 'txt', 'texto')):
                    continue
                return candidate

        return candidates[0]
