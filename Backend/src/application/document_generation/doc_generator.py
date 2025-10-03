"""
Document Generator Engine - Sistema de generación automática de documentación
Produce reportes profesionales en múltiples formatos con templates inteligentes
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import io

# Template engine (optional)
try:
    from jinja2 import Environment, DictLoader, Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

# Optional imports for different document formats
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

logger = logging.getLogger(__name__)


class DocumentFormat(Enum):
    """Formatos de documento soportados"""
    JSON = "json"
    HTML = "html"
    MARKDOWN = "md"
    PDF = "pdf"
    TXT = "txt"


class DocumentType(Enum):
    """Tipos de documento disponibles"""
    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL_REPORT = "technical_report"
    FINANCIAL_ANALYSIS = "financial_analysis"
    API_DOCUMENTATION = "api_documentation"
    PROCESSING_LOG = "processing_log"
    INSIGHT_REPORT = "insight_report"
    PERFORMANCE_REPORT = "performance_report"


@dataclass
class DocumentMetadata:
    """Metadata del documento generado"""
    document_id: str
    document_type: DocumentType
    format: DocumentFormat
    title: str
    created_at: datetime
    author: str = "CapiAgentes System"
    version: str = "1.0"
    template_version: str = "1.0"
    processing_time: float = 0.0
    file_size: int = 0
    language: str = "es"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte metadata a diccionario"""
        return {
            "document_id": self.document_id,
            "document_type": self.document_type.value,
            "format": self.format.value,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "author": self.author,
            "version": self.version,
            "template_version": self.template_version,
            "processing_time": self.processing_time,
            "file_size": self.file_size,
            "language": self.language,
            "tags": self.tags
        }


@dataclass
class GeneratedDocument:
    """Documento generado con contenido y metadata"""
    content: str
    metadata: DocumentMetadata
    raw_data: Dict[str, Any]
    template_used: str
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def save_to_file(self, file_path: Union[str, Path]) -> bool:
        """Guarda documento a archivo"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.content)
            
            # Update file size in metadata
            self.metadata.file_size = file_path.stat().st_size
            return True
            
        except Exception as e:
            self.errors.append(f"Error saving to file: {str(e)}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte documento a diccionario"""
        return {
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "raw_data": self.raw_data,
            "template_used": self.template_used,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings
        }


class SimpleTemplateEngine:
    """Template engine simple sin dependencias externas"""
    
    @staticmethod
    def render(template: str, context: Dict[str, Any]) -> str:
        """Renderiza template simple con substituciones básicas"""
        rendered = template
        
        # Simple variable substitution
        for key, value in context.items():
            if isinstance(value, dict):
                # Handle nested dictionaries
                for nested_key, nested_value in value.items():
                    placeholder = f"{{{{ {key}.{nested_key} }}}}"
                    rendered = rendered.replace(placeholder, str(nested_value))
            else:
                placeholder = f"{{{{ {key} }}}}"
                rendered = rendered.replace(placeholder, str(value))
        
        # Handle conditionals and loops (basic)
        rendered = SimpleTemplateEngine._process_conditionals(rendered, context)
        rendered = SimpleTemplateEngine._process_loops(rendered, context)
        
        return rendered
    
    @staticmethod
    def _process_conditionals(template: str, context: Dict[str, Any]) -> str:
        """Procesa condicionales básicos"""
        import re
        
        # Simple if statements: {% if condition %}...{% endif %}
        if_pattern = r'{%\s*if\s+([^%]+)\s*%}(.*?){%\s*endif\s*%}'
        
        def replace_if(match):
            condition = match.group(1).strip()
            content = match.group(2)
            
            # Evaluate simple conditions
            if condition in context and context[condition]:
                return content
            elif '.' in condition:
                # Handle nested conditions like "data.insights"
                parts = condition.split('.')
                value = context
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                if value:
                    return content
            
            return ""
        
        return re.sub(if_pattern, replace_if, template, flags=re.DOTALL)
    
    @staticmethod
    def _process_loops(template: str, context: Dict[str, Any]) -> str:
        """Procesa loops básicos"""
        import re
        
        # Simple for loops: {% for item in items %}...{% endfor %}
        for_pattern = r'{%\s*for\s+(\w+)\s+in\s+([^%]+)\s*%}(.*?){%\s*endfor\s*%}'
        
        def replace_for(match):
            var_name = match.group(1).strip()
            collection_name = match.group(2).strip()
            content = match.group(3)
            
            # Get collection from context
            collection = context
            for part in collection_name.split('.'):
                if isinstance(collection, dict) and part in collection:
                    collection = collection[part]
                else:
                    collection = []
                    break
            
            if not isinstance(collection, (list, tuple)):
                return ""
            
            result = ""
            for item in collection:
                item_content = content
                # Replace loop variable
                item_content = item_content.replace(f"{{{{ {var_name}.title }}}}", str(item.get('title', '') if isinstance(item, dict) else ''))
                item_content = item_content.replace(f"{{{{ {var_name}.message }}}}", str(item.get('message', '') if isinstance(item, dict) else ''))
                item_content = item_content.replace(f"{{{{ {var_name}.priority }}}}", str(item.get('priority', '') if isinstance(item, dict) else ''))
                item_content = item_content.replace(f"{{{{ {var_name} }}}}", str(item))
                result += item_content
            
            return result
        
        return re.sub(for_pattern, replace_for, template, flags=re.DOTALL)


class DocumentTemplates:
    """Gestor de templates para diferentes tipos de documento"""
    
    @staticmethod
    def get_templates() -> Dict[str, str]:
        """Retorna todos los templates disponibles"""
        return {
            # Executive Summary Template (Simple version)
            "executive_summary_html": """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ metadata.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
        .header { border-bottom: 3px solid #2c5aa0; padding-bottom: 20px; margin-bottom: 30px; }
        h1 { color: #2c5aa0; margin: 0; }
        .metadata { font-size: 14px; color: #666; margin-top: 10px; }
        .summary-box { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .metric { display: inline-block; margin: 10px 20px 10px 0; }
        .metric-value { font-size: 24px; font-weight: bold; color: #2c5aa0; }
        .metric-label { font-size: 12px; color: #666; }
        .insights { margin: 30px 0; }
        .insight { margin: 15px 0; padding: 15px; border-left: 4px solid #28a745; background: #f8fff9; }
        .insight.warning { border-left-color: #ffc107; background: #fffdf5; }
        .insight.critical { border-left-color: #dc3545; background: #fff5f5; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ metadata.title }}</h1>
        <div class="metadata">
            Generado: {{ metadata.created_at }} | 
            Tipo: {{ metadata.document_type }} | 
            Versión: {{ metadata.version }}
        </div>
    </div>

    <div class="summary-box">
        <h2>Resumen Ejecutivo</h2>
        <p>{{ data.executive_summary }}</p>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{{ data.total_records }}</div>
                <div class="metric-label">Registros Procesados</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ data.processing_time }}</div>
                <div class="metric-label">Tiempo de Procesamiento</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ data.success_rate }}</div>
                <div class="metric-label">Tasa de Éxito</div>
            </div>
        </div>
    </div>

    <div class="insights">
        <h2>Insights Principales</h2>
        <div class="insight info">
            <strong>Análisis Completado</strong><br>
            {{ data.summary_message }}
        </div>
        {% if data.insights %}
        {% for insight in data.insights %}
        <div class="insight {{ insight.priority }}">
            <strong>{{ insight.title }}</strong><br>
            {{ insight.message }}
        </div>
        {% endfor %}
        {% endif %}
    </div>

    <div class="recommendations">
        <h2>Resultados</h2>
        <p>{{ data.results_summary }}</p>
    </div>

    <div class="footer">
        <p>Documento generado por CapiAgentes System v{{ metadata.version }}</p>
        <p>Tiempo de procesamiento: {{ metadata.processing_time }}s</p>
    </div>
</body>
</html>
            """,
            
            # Technical Report Template
            "technical_report_md": """
# {{ metadata.title }}

**Documento**: {{ metadata.document_type }}  
**Generado**: {{ metadata.created_at }}  
**Versión**: {{ metadata.version }}  
**Autor**: {{ metadata.author }}

---

## Resumen Técnico

{{ data.technical_summary | default("Análisis técnico completo del sistema.") }}

## Métricas de Procesamiento

{% if data.processing_context %}
- **Trace ID**: {{ data.processing_context.trace_id }}
- **Duración Total**: {{ data.processing_context.performance_summary.total_duration }}s
- **Etapas Procesadas**: {{ data.processing_context.performance_summary.stage_count }}
- **Uso de Memoria**: {{ data.processing_context.performance_summary.memory_usage.delta_mb }}MB
{% endif %}

## Análisis Detallado

{% if data.financial_analysis %}
### Análisis Financiero

{% if data.financial_analysis.basic_metrics %}
#### Métricas Básicas
{% for column, metrics in data.financial_analysis.basic_metrics.items() %}
- **{{ column }}**:
  - Media: {{ "%.2f" | format(metrics.mean_value) }}
  - Desviación Estándar: {{ "%.2f" | format(metrics.std_deviation) }}
  - Rango: {{ "%.2f" | format(metrics.value_range) }}
{% endfor %}
{% endif %}

{% if data.financial_analysis.correlation_analysis.strong_correlations %}
#### Correlaciones Significativas
{% for corr in data.financial_analysis.correlation_analysis.strong_correlations %}
- {{ corr[0] }} ↔ {{ corr[1] }}: {{ "%.3f" | format(corr[2]) }}
{% endfor %}
{% endif %}
{% endif %}

## Insights y Recomendaciones

{% if data.insights %}
{% for insight in data.insights %}
### {{ insight.title }}
**Prioridad**: {{ insight.priority }}

{{ insight.message }}

{% if insight.data %}
**Datos técnicos**: {{ insight.data | tojson }}
{% endif %}

---
{% endfor %}
{% endif %}

## Información Técnica

- **Tiempo de Procesamiento**: {{ metadata.processing_time }}s
- **Tamaño del Documento**: {{ metadata.file_size }} bytes
- **Template**: {{ template_used }}
- **Tags**: {{ metadata.tags | join(", ") }}

---

*Generado automáticamente por CapiAgentes System*
            """,
            
            # Financial Analysis Report
            "financial_analysis_json": """
{
    "metadata": {{ metadata | tojson }},
    "executive_summary": {
        "total_records": {{ data.dataset_info.total_records | default(0) }},
        "processing_time": {{ data.analysis_metadata.processing_time_seconds | default(0) }},
        "success": {{ data.success | default(false) | tojson }},
        "key_findings": {{ data.key_findings | default([]) | tojson }}
    },
    "financial_metrics": {{ data.financial_analysis.basic_metrics | default({}) | tojson }},
    "correlations": {{ data.financial_analysis.correlation_analysis | default({}) | tojson }},
    "patterns": {{ data.financial_analysis.pattern_analysis | default({}) | tojson }},
    "insights": {{ data.insights | default([]) | tojson }},
    "processing_details": {{ data.processing_context | default({}) | tojson }},
    "generated_at": "{{ metadata.created_at }}",
    "document_info": {
        "format": "{{ metadata.format }}",
        "type": "{{ metadata.document_type }}",
        "version": "{{ metadata.version }}"
    }
}
            """,
            
            # Performance Report
            "performance_report_txt": """
REPORTE DE PERFORMANCE - {{ metadata.title }}
{{ "=" * 60 }}

Generado: {{ metadata.created_at }}
Versión: {{ metadata.version }}

RESUMEN DE PERFORMANCE:
{{ "-" * 25 }}
{% if data.processing_context %}
Trace ID: {{ data.processing_context.trace_id }}
Duración Total: {{ data.processing_context.performance_summary.total_duration }}s
Etapas Procesadas: {{ data.processing_context.performance_summary.stage_count }}
Errores: {{ data.processing_context.performance_summary.error_count }}
{% endif %}

MÉTRICAS DETALLADAS:
{{ "-" * 25 }}
{% if data.processing_context and data.processing_context.performance_summary.stage_durations %}
{% for stage, duration in data.processing_context.performance_summary.stage_durations.items() %}
{{ stage }}: {{ "%.3f" | format(duration) }}s
{% endfor %}
{% endif %}

MÉTRICAS DE MEMORIA:
{{ "-" * 25 }}
{% if data.processing_context and data.processing_context.performance_summary.memory_usage %}
Inicial: {{ data.processing_context.performance_summary.memory_usage.initial_mb }}MB
Final: {{ data.processing_context.performance_summary.memory_usage.current_mb }}MB
Pico: {{ data.processing_context.performance_summary.memory_usage.peak_mb }}MB
Delta: {{ data.processing_context.performance_summary.memory_usage.delta_mb }}MB
{% endif %}

API METRICS:
{{ "-" * 25 }}
{% if data.processing_context and data.processing_context.performance_summary.api_metrics %}
Llamadas API: {{ data.processing_context.performance_summary.api_metrics.api_calls }}
Tokens Usados: {{ data.processing_context.performance_summary.api_metrics.token_usage }}
{% endif %}

{{ "=" * 60 }}
Generado por CapiAgentes System
            """
        }


class DocumentGenerator:
    """
    Sistema de generación automática de documentación
    Produce reportes profesionales en múltiples formatos
    """
    
    def __init__(self, 
                 output_dir: Optional[Union[str, Path]] = None,
                 enable_pdf: bool = True):
        """
        Inicializa el generador de documentos
        
        Args:
            output_dir: Directorio base para output
            enable_pdf: Habilitar generación PDF
        """
        self.output_dir = Path(output_dir) if output_dir else Path("generated_docs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.enable_pdf = enable_pdf and (PDFKIT_AVAILABLE or WEASYPRINT_AVAILABLE)
        
        # Configurar template engine
        self.templates = DocumentTemplates.get_templates()
        
        if JINJA2_AVAILABLE:
            # Usar Jinja2 si está disponible
            self.template_env = Environment(
                loader=DictLoader(self.templates),
                autoescape=True
            )
            self.use_jinja2 = True
        else:
            # Usar template engine simple
            self.template_env = None
            self.use_jinja2 = False
        
        # Métricas de generación
        self.generation_stats = {
            "documents_generated": 0,
            "total_processing_time": 0.0,
            "formats_generated": {},
            "errors": []
        }
        
        logger.info(f"DocumentGenerator inicializado - PDF: {self.enable_pdf}, "
                   f"Templates: {len(self.templates)}, Engine: {'Jinja2' if self.use_jinja2 else 'Simple'}, "
                   f"Output: {self.output_dir}")
    
    def generate_document(self,
                         document_type: DocumentType,
                         format: DocumentFormat,
                         data: Dict[str, Any],
                         title: Optional[str] = None,
                         document_id: Optional[str] = None,
                         save_to_file: bool = True) -> GeneratedDocument:
        """
        Genera un documento del tipo y formato especificado
        
        Args:
            document_type: Tipo de documento a generar
            format: Formato de salida
            data: Datos para el documento
            title: Título personalizado
            document_id: ID personalizado del documento
            save_to_file: Si guardar automáticamente a archivo
            
        Returns:
            Documento generado
        """
        start_time = datetime.now(timezone.utc)
        
        # Crear metadata
        metadata = DocumentMetadata(
            document_id=document_id or f"{document_type}_{int(start_time.timestamp())}",
            document_type=document_type,
            format=format,
            title=title or self._generate_title(document_type),
            created_at=start_time
        )
        
        logger.info(f"Generando documento: {metadata.document_id} "
                   f"({document_type}.{format})")
        
        try:
            # Seleccionar template
            template_name = self._select_template(document_type, format)
            
            # Preparar contexto para template
            template_context = {
                "metadata": metadata,
                "data": data,
                "template_used": template_name,
                "generation_time": start_time.isoformat()
            }
            
            # Renderizar documento
            if self.use_jinja2:
                template = self.template_env.get_template(template_name)
                content = template.render(**template_context)
            else:
                # Usar simple template engine
                template_content = self.templates.get(template_name, "")
                content = SimpleTemplateEngine.render(template_content, template_context)
            
            # Post-procesar según formato
            if format == DocumentFormat.JSON:
                content = self._format_json(content)
            elif format == DocumentFormat.PDF and self.enable_pdf:
                content = self._generate_pdf(content)
            
            # Calcular tiempo de procesamiento
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            metadata.processing_time = processing_time
            
            # Crear documento
            document = GeneratedDocument(
                content=content,
                metadata=metadata,
                raw_data=data,
                template_used=template_name
            )
            
            # Guardar a archivo si se solicita
            if save_to_file:
                file_path = self._get_output_path(metadata)
                if document.save_to_file(file_path):
                    logger.info(f"Documento guardado: {file_path}")
                else:
                    logger.warning(f"Error guardando documento: {file_path}")
            
            # Actualizar estadísticas
            self._update_stats(document_type, format, processing_time)
            
            logger.info(f"Documento generado exitosamente: {metadata.document_id} "
                       f"({processing_time:.3f}s)")
            
            return document
            
        except Exception as e:
            error_msg = f"Error generando documento: {str(e)}"
            logger.error(f"[{metadata.document_id}] {error_msg}")
            
            self.generation_stats["errors"].append({
                "document_id": metadata.document_id,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return GeneratedDocument(
                content="",
                metadata=metadata,
                raw_data=data,
                template_used="",
                success=False,
                errors=[error_msg]
            )
    
    def _select_template(self, document_type: DocumentType, format: DocumentFormat) -> str:
        """Selecciona el template apropiado"""
        template_name = f"{document_type}_{format}"
        
        # Fallbacks para templates no disponibles
        fallback_map = {
            DocumentType.EXECUTIVE_SUMMARY: {
                DocumentFormat.HTML: "executive_summary_html",
                DocumentFormat.MARKDOWN: "technical_report_md",
                DocumentFormat.JSON: "financial_analysis_json",
                DocumentFormat.TXT: "performance_report_txt"
            },
            DocumentType.TECHNICAL_REPORT: {
                DocumentFormat.MARKDOWN: "technical_report_md",
                DocumentFormat.HTML: "executive_summary_html",
                DocumentFormat.JSON: "financial_analysis_json"
            },
            DocumentType.FINANCIAL_ANALYSIS: {
                DocumentFormat.JSON: "financial_analysis_json",
                DocumentFormat.HTML: "executive_summary_html",
                DocumentFormat.MARKDOWN: "technical_report_md"
            },
            DocumentType.PERFORMANCE_REPORT: {
                DocumentFormat.TXT: "performance_report_txt",
                DocumentFormat.MARKDOWN: "technical_report_md"
            }
        }
        
        # Intentar template específico primero
        if self.use_jinja2 and template_name in self.template_env.list_templates():
            return template_name
        elif not self.use_jinja2 and template_name in self.templates:
            return template_name
        
        # Usar fallback
        if document_type in fallback_map and format in fallback_map[document_type]:
            return fallback_map[document_type][format]
        
        # Fallback final
        return "technical_report_md"
    
    def _generate_title(self, document_type: DocumentType) -> str:
        """Genera título automático"""
        titles = {
            DocumentType.EXECUTIVE_SUMMARY: "Resumen Ejecutivo - Análisis Financiero",
            DocumentType.TECHNICAL_REPORT: "Reporte Técnico Detallado",
            DocumentType.FINANCIAL_ANALYSIS: "Análisis Financiero Completo",
            DocumentType.API_DOCUMENTATION: "Documentación de API",
            DocumentType.PROCESSING_LOG: "Log de Procesamiento",
            DocumentType.INSIGHT_REPORT: "Reporte de Insights",
            DocumentType.PERFORMANCE_REPORT: "Reporte de Performance"
        }
        return titles.get(document_type, "Documento Generado")
    
    def _format_json(self, content: str) -> str:
        """Formatea y valida contenido JSON"""
        try:
            # Parse y re-format para asegurar JSON válido
            parsed = json.loads(content)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # Si no es JSON válido, wrap en estructura básica
            return json.dumps({"content": content, "error": "Invalid JSON template"}, indent=2)
    
    def _generate_pdf(self, html_content: str) -> str:
        """Genera PDF desde HTML (placeholder)"""
        if WEASYPRINT_AVAILABLE:
            try:
                # Usar WeasyPrint si está disponible
                pdf_buffer = io.BytesIO()
                HTML(string=html_content).write_pdf(pdf_buffer)
                return pdf_buffer.getvalue().decode('latin1')  # Encoding for binary content
            except Exception as e:
                logger.warning(f"Error generando PDF con WeasyPrint: {e}")
        
        # Fallback: retornar HTML con nota
        return f"<!-- PDF generation not available -->\n{html_content}"
    
    def _get_output_path(self, metadata: DocumentMetadata) -> Path:
        """Genera path de output para documento"""
        filename = f"{metadata.document_id}.{metadata.format}"
        return self.output_dir / str(metadata.document_type) / filename
    
    def _update_stats(self, document_type: DocumentType, format: DocumentFormat, processing_time: float):
        """Actualiza estadísticas de generación"""
        self.generation_stats["documents_generated"] += 1
        self.generation_stats["total_processing_time"] += processing_time
        
        format_key = f"{document_type}.{format}"
        if format_key not in self.generation_stats["formats_generated"]:
            self.generation_stats["formats_generated"][format_key] = 0
        self.generation_stats["formats_generated"][format_key] += 1
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Retorna capacidades del generador"""
        return {
            "pdf_generation": self.enable_pdf,
            "weasyprint_available": WEASYPRINT_AVAILABLE,
            "pdfkit_available": PDFKIT_AVAILABLE,
            "jinja2_available": JINJA2_AVAILABLE,
            "template_engine": "Jinja2" if self.use_jinja2 else "Simple",
            "supported_formats": [f.value for f in DocumentFormat],
            "supported_types": [t.value for t in DocumentType],
            "templates_available": len(self.templates),
            "output_directory": str(self.output_dir)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de generación"""
        return self.generation_stats.copy()


# Helper functions for easy document generation
def generate_executive_summary(data: Dict[str, Any], 
                             title: Optional[str] = None,
                             format: DocumentFormat = DocumentFormat.HTML) -> GeneratedDocument:
    """Helper para generar resumen ejecutivo"""
    generator = DocumentGenerator()
    return generator.generate_document(
        DocumentType.EXECUTIVE_SUMMARY,
        format,
        data,
        title
    )


def generate_technical_report(data: Dict[str, Any],
                            title: Optional[str] = None,
                            format: DocumentFormat = DocumentFormat.MARKDOWN) -> GeneratedDocument:
    """Helper para generar reporte técnico"""
    generator = DocumentGenerator()
    return generator.generate_document(
        DocumentType.TECHNICAL_REPORT,
        format,
        data,
        title
    )


def generate_financial_analysis_doc(data: Dict[str, Any],
                                  format: DocumentFormat = DocumentFormat.JSON) -> GeneratedDocument:
    """Helper para generar documento de análisis financiero"""
    generator = DocumentGenerator()
    return generator.generate_document(
        DocumentType.FINANCIAL_ANALYSIS,
        format,
        data
    )