"""
LLM Document Enhancement - Mejora de contenido de documentos via OpenAI
Genera resúmenes ejecutivos, mejora contenido y formatea automáticamente
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json

from ..document_generation.doc_generator import (
    DocumentGenerator, DocumentType, DocumentFormat, GeneratedDocument
)
from src.application.reasoning.llm_reasoner import LLMReasoner, LLMReasoningResult
# LLM reasoner functionality moved to orchestrator

logger = logging.getLogger(__name__)


@dataclass
class DocumentEnhancementRequest:
    """Request para enhancement de documento"""
    original_document: GeneratedDocument
    enhancement_type: str  # "summarize", "expand", "format", "translate"
    target_audience: str = "executive"  # "executive", "technical", "general"
    language: str = "es"
    max_length: Optional[int] = None
    custom_instructions: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte request a diccionario"""
        return {
            "enhancement_type": self.enhancement_type,
            "target_audience": self.target_audience,
            "language": self.language,
            "max_length": self.max_length,
            "custom_instructions": self.custom_instructions,
            "original_document_id": self.original_document.metadata.document_id
        }


@dataclass
class DocumentEnhancementResult:
    """Resultado del enhancement de documento"""
    enhanced_document: GeneratedDocument
    original_document: GeneratedDocument
    enhancement_request: DocumentEnhancementRequest
    llm_result: LLMReasoningResult
    enhancement_metadata: Dict[str, Any]
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte resultado a diccionario"""
        return {
            "enhanced_document": self.enhanced_document.to_dict(),
            "original_document": self.original_document.to_dict(),
            "enhancement_request": self.enhancement_request.to_dict(),
            "llm_result": self.llm_result.__dict__ if self.llm_result else {},
            "enhancement_metadata": self.enhancement_metadata,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings
        }


class LLMDocumentEnhancer:
    """
    Sistema de mejora de documentos usando LLM
    Genera resúmenes ejecutivos mejorados y contenido profesional
    """
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 model: str = "gpt-5",
                 temperature: float = 0.3):
        """
        Inicializa el enhancer de documentos
        
        Args:
            openai_api_key: API key de OpenAI
            model: Modelo a usar para enhancement
            temperature: Creatividad del modelo
        """
        # Inicializar LLM Reasoner para enhancement
        self.llm_reasoner = LLMReasoner(
            api_key=openai_api_key,
            model=model,
            temperature=temperature,
            max_tokens=1500,  # Más tokens para documentos
            timeout=20.0
        )
        
        # Document Generator para crear versiones mejoradas
        self.doc_generator = DocumentGenerator()
        
        # Templates de prompts para diferentes tipos de enhancement
        self.enhancement_prompts = self._initialize_enhancement_prompts()
        
        # Estadísticas de enhancement
        self.enhancement_stats = {
            "documents_enhanced": 0,
            "total_processing_time": 0.0,
            "enhancement_types": {},
            "success_rate": 0.0,
            "errors": []
        }
        
        logger.info(f"LLMDocumentEnhancer inicializado con modelo {model}")
    
    def _initialize_enhancement_prompts(self) -> Dict[str, str]:
        """Inicializa templates de prompts para enhancement"""
        return {
            "executive_summary": """
Eres un experto en comunicación ejecutiva y análisis financiero. Tu tarea es crear un resumen ejecutivo profesional y conciso.

DOCUMENTO ORIGINAL:
{original_content}

DATOS TÉCNICOS:
{technical_data}

INSTRUCCIONES:
1. Crea un resumen ejecutivo de máximo 3 párrafos
2. Enfócate en insights clave y recomendaciones accionables
3. Usa lenguaje claro y profesional para ejecutivos
4. Incluye métricas importantes y hallazgos críticos
5. Estructura: Situación actual → Hallazgos clave → Recomendaciones

AUDIENCIA: Ejecutivos que necesitan decisiones rápidas basadas en datos

Genera el resumen ejecutivo:
            """,
            
            "technical_expansion": """
Eres un analista técnico senior especializado en sistemas financieros. Expande y mejora el siguiente documento técnico.

DOCUMENTO ORIGINAL:
{original_content}

DATOS TÉCNICOS:
{technical_data}

INSTRUCCIONES:
1. Expande el contenido técnico con detalles profesionales
2. Agrega metodologías y consideraciones técnicas
3. Incluye interpretación de métricas y correlaciones
4. Explica implicaciones técnicas y limitaciones
5. Mantén rigor técnico pero claridad

AUDIENCIA: Profesionales técnicos y analistas especializados

Genera el documento técnico expandido:
            """,
            
            "professional_formatting": """
Eres un especialista en documentación profesional. Mejora el formato y estructura del siguiente documento.

DOCUMENTO ORIGINAL:
{original_content}

DATOS TÉCNICOS:
{technical_data}

INSTRUCCIONES:
1. Mejora la estructura y organización del contenido
2. Agrega títulos, subtítulos y organización clara
3. Incluye bullet points y numeración donde sea apropiado
4. Mejora la claridad del lenguaje sin cambiar el contenido técnico
5. Asegura consistencia en terminología

AUDIENCIA: {target_audience}

Genera el documento con formato mejorado:
            """,
            
            "insight_generation": """
Eres un consultor financiero senior con experiencia en análisis de datos. Genera insights valiosos del siguiente análisis.

DOCUMENTO ORIGINAL:
{original_content}

DATOS TÉCNICOS:
{technical_data}

INSTRUCCIONES:
1. Identifica patrones y tendencias importantes
2. Genera recomendaciones específicas y accionables
3. Explica implicaciones de correlaciones y métricas
4. Identifica riesgos y oportunidades
5. Proporciona contexto de mercado cuando sea relevante

AUDIENCIA: Tomadores de decisiones financieras

Genera insights y recomendaciones detalladas:
            """,
            
            "quality_improvement": """
Eres un editor técnico especializado en documentos financieros. Mejora la calidad del siguiente documento.

DOCUMENTO ORIGINAL:
{original_content}

DATOS TÉCNICOS:
{technical_data}

INSTRUCCIONES:
1. Mejora la claridad y precisión del lenguaje
2. Elimina redundancias y mejora la concisión
3. Asegura coherencia en terminología técnica
4. Mejora transiciones entre secciones
5. Mantén toda la información técnica importante

AUDIENCIA: {target_audience}

Genera la versión mejorada del documento:
            """
        }
    
    async def enhance_document(self,
                             document: GeneratedDocument,
                             enhancement_type: str = "executive_summary",
                             target_audience: str = "executive",
                             language: str = "es",
                             max_length: Optional[int] = None,
                             custom_instructions: Optional[str] = None,
                             trace_id: Optional[str] = None) -> DocumentEnhancementResult:
        """
        Mejora un documento usando LLM
        
        Args:
            document: Documento original a mejorar
            enhancement_type: Tipo de mejora a aplicar
            target_audience: Audiencia objetivo
            language: Idioma del documento
            max_length: Longitud máxima del contenido mejorado
            custom_instructions: Instrucciones personalizadas
            trace_id: ID de trazabilidad
            
        Returns:
            Resultado del enhancement
        """
        start_time = datetime.now()
        
        # Crear request
        enhancement_request = DocumentEnhancementRequest(
            original_document=document,
            enhancement_type=enhancement_type,
            target_audience=target_audience,
            language=language,
            max_length=max_length,
            custom_instructions=custom_instructions
        )
        
        logger.info(f"[{trace_id}] Iniciando enhancement de documento: {document.metadata.document_id} "
                   f"({enhancement_type})")
        
        try:
            # Preparar contexto para LLM
            llm_context = self._prepare_llm_context(document, enhancement_request)
            
            # Ejecutar enhancement via LLM
            llm_result = await self.llm_reasoner.reason(
                query=llm_context["prompt"],
                context_data=llm_context["context"],
                trace_id=trace_id
            )
            
            if llm_result.success:
                # Crear documento mejorado
                enhanced_document = self._create_enhanced_document(
                    original_document=document,
                    enhanced_content=llm_result.response,
                    enhancement_request=enhancement_request,
                    llm_result=llm_result
                )
                
                # Metadata del enhancement
                enhancement_metadata = {
                    "enhancement_type": enhancement_type,
                    "llm_model": self.llm_reasoner.model,
                    "llm_processing_time": llm_result.processing_time,
                    "llm_confidence": llm_result.confidence_score,
                    "llm_tokens_used": llm_result.token_usage,
                    "original_length": len(document.content),
                    "enhanced_length": len(enhanced_document.content),
                    "length_improvement": len(enhanced_document.content) / len(document.content) if len(document.content) > 0 else 0,
                    "enhancement_timestamp": start_time.isoformat()
                }
                
                # Crear resultado exitoso
                result = DocumentEnhancementResult(
                    enhanced_document=enhanced_document,
                    original_document=document,
                    enhancement_request=enhancement_request,
                    llm_result=llm_result,
                    enhancement_metadata=enhancement_metadata,
                    success=True
                )
                
                # Actualizar estadísticas
                self._update_enhancement_stats(enhancement_type, start_time, True)
                
                logger.info(f"[{trace_id}] Enhancement exitoso - "
                           f"original: {len(document.content)} chars → "
                           f"mejorado: {len(enhanced_document.content)} chars "
                           f"({llm_result.processing_time:.2f}s)")
                
                return result
            
            else:
                # LLM falló, crear resultado con error
                error_msg = f"LLM enhancement falló: {llm_result.error}"
                logger.warning(f"[{trace_id}] {error_msg}")
                
                result = DocumentEnhancementResult(
                    enhanced_document=document,  # Usar documento original
                    original_document=document,
                    enhancement_request=enhancement_request,
                    llm_result=llm_result,
                    enhancement_metadata={"error": error_msg},
                    success=False,
                    errors=[error_msg]
                )
                
                self._update_enhancement_stats(enhancement_type, start_time, False)
                return result
        
        except Exception as e:
            error_msg = f"Error en document enhancement: {str(e)}"
            logger.error(f"[{trace_id}] {error_msg}")
            
            result = DocumentEnhancementResult(
                enhanced_document=document,
                original_document=document,
                enhancement_request=enhancement_request,
                llm_result=None,
                enhancement_metadata={"error": error_msg},
                success=False,
                errors=[error_msg]
            )
            
            self._update_enhancement_stats(enhancement_type, start_time, False)
            return result
    
    def _prepare_llm_context(self, 
                           document: GeneratedDocument, 
                           request: DocumentEnhancementRequest) -> Dict[str, Any]:
        """Prepara contexto para el LLM"""
        
        # Seleccionar prompt template
        prompt_template = self.enhancement_prompts.get(
            request.enhancement_type, 
            self.enhancement_prompts["quality_improvement"]
        )
        
        # Preparar datos técnicos
        technical_data = {
            "document_metadata": document.metadata.to_dict(),
            "document_type": document.metadata.document_type.value,
            "document_format": document.metadata.format.value,
            "raw_data_summary": self._summarize_raw_data(document.raw_data),
            "enhancement_request": request.to_dict()
        }
        
        # Crear prompt personalizado
        prompt = prompt_template.format(
            original_content=document.content[:3000],  # Limitar contenido para tokens
            technical_data=json.dumps(technical_data, indent=2),
            target_audience=request.target_audience
        )
        
        # Agregar instrucciones personalizadas
        if request.custom_instructions:
            prompt += f"\n\nINSTRUCCIONES ADICIONALES:\n{request.custom_instructions}"
        
        # Agregar restricciones de longitud
        if request.max_length:
            prompt += f"\n\nLIMITE DE LONGITUD: Máximo {request.max_length} caracteres."
        
        return {
            "prompt": prompt,
            "context": {
                "document_enhancement": True,
                "enhancement_type": request.enhancement_type,
                "target_audience": request.target_audience,
                "original_document_id": document.metadata.document_id
            }
        }
    
    def _summarize_raw_data(self, raw_data: Dict[str, Any]) -> str:
        """Crea resumen de datos raw para contexto LLM"""
        if not raw_data:
            return "No hay datos técnicos disponibles"
        
        summary_parts = []
        
        # Resumen de insights
        if "insights" in raw_data and raw_data["insights"]:
            insights_count = len(raw_data["insights"])
            summary_parts.append(f"Insights generados: {insights_count}")
        
        # Resumen de análisis financiero
        if "financial_analysis" in raw_data:
            fa = raw_data["financial_analysis"]
            if "basic_metrics" in fa:
                metrics_count = len(fa["basic_metrics"])
                summary_parts.append(f"Métricas financieras: {metrics_count} columnas")
            
            if "correlation_analysis" in fa and "strong_correlations" in fa["correlation_analysis"]:
                corr_count = len(fa["correlation_analysis"]["strong_correlations"])
                summary_parts.append(f"Correlaciones fuertes: {corr_count}")
        
        # Resumen de contexto de procesamiento
        if "processing_context" in raw_data:
            pc = raw_data["processing_context"]
            if "performance_summary" in pc:
                ps = pc["performance_summary"]
                duration = ps.get("total_duration", 0)
                summary_parts.append(f"Tiempo de procesamiento: {duration:.3f}s")
        
        return "; ".join(summary_parts) if summary_parts else "Datos técnicos disponibles"
    
    def _create_enhanced_document(self,
                                original_document: GeneratedDocument,
                                enhanced_content: str,
                                enhancement_request: DocumentEnhancementRequest,
                                llm_result: LLMReasoningResult) -> GeneratedDocument:
        """Crea nuevo documento con contenido mejorado"""
        
        # Crear nueva metadata basada en la original
        enhanced_metadata = original_document.metadata
        enhanced_metadata.title = f"{enhanced_metadata.title} (Enhanced)"
        enhanced_metadata.version = f"{enhanced_metadata.version}-enhanced"
        enhanced_metadata.created_at = datetime.now()
        enhanced_metadata.tags.extend(["llm_enhanced", enhancement_request.enhancement_type])
        
        # Crear documento mejorado
        enhanced_document = GeneratedDocument(
            content=enhanced_content,
            metadata=enhanced_metadata,
            raw_data={
                **original_document.raw_data,
                "enhancement_metadata": {
                    "enhancement_type": enhancement_request.enhancement_type,
                    "llm_confidence": llm_result.confidence_score,
                    "llm_tokens": llm_result.token_usage,
                    "original_document_id": original_document.metadata.document_id
                }
            },
            template_used=f"{original_document.template_used}_enhanced",
            success=True
        )
        
        return enhanced_document
    
    def _update_enhancement_stats(self, enhancement_type: str, start_time: datetime, success: bool):
        """Actualiza estadísticas de enhancement"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        self.enhancement_stats["documents_enhanced"] += 1
        self.enhancement_stats["total_processing_time"] += processing_time
        
        if enhancement_type not in self.enhancement_stats["enhancement_types"]:
            self.enhancement_stats["enhancement_types"][enhancement_type] = {"count": 0, "success": 0}
        
        self.enhancement_stats["enhancement_types"][enhancement_type]["count"] += 1
        if success:
            self.enhancement_stats["enhancement_types"][enhancement_type]["success"] += 1
        
        # Calcular success rate general
        total_docs = self.enhancement_stats["documents_enhanced"]
        total_success = sum(
            et["success"] for et in self.enhancement_stats["enhancement_types"].values()
        )
        self.enhancement_stats["success_rate"] = (total_success / total_docs) * 100 if total_docs > 0 else 0
    
    def get_enhancement_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de enhancement"""
        return self.enhancement_stats.copy()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Retorna capacidades del enhancer"""
        return {
            "llm_model": self.llm_reasoner.model,
            "enhancement_types": list(self.enhancement_prompts.keys()),
            "supported_audiences": ["executive", "technical", "general"],
            "max_tokens": self.llm_reasoner.max_tokens,
            "timeout": self.llm_reasoner.timeout,
            "temperature": self.llm_reasoner.temperature
        }


# Helper functions for easy enhancement
async def enhance_executive_summary(document: GeneratedDocument,
                                  openai_api_key: Optional[str] = None,
                                  trace_id: Optional[str] = None) -> DocumentEnhancementResult:
    """Helper para mejorar resumen ejecutivo"""
    enhancer = LLMDocumentEnhancer(openai_api_key=openai_api_key)
    return await enhancer.enhance_document(
        document=document,
        enhancement_type="executive_summary",
        target_audience="executive",
        trace_id=trace_id
    )


async def enhance_technical_report(document: GeneratedDocument,
                                 openai_api_key: Optional[str] = None,
                                 trace_id: Optional[str] = None) -> DocumentEnhancementResult:
    """Helper para mejorar reporte técnico"""
    enhancer = LLMDocumentEnhancer(openai_api_key=openai_api_key)
    return await enhancer.enhance_document(
        document=document,
        enhancement_type="technical_expansion",
        target_audience="technical",
        trace_id=trace_id
    )


async def generate_insights_report(document: GeneratedDocument,
                                 openai_api_key: Optional[str] = None,
                                 trace_id: Optional[str] = None) -> DocumentEnhancementResult:
    """Helper para generar reporte de insights"""
    enhancer = LLMDocumentEnhancer(openai_api_key=openai_api_key)
    return await enhancer.enhance_document(
        document=document,
        enhancement_type="insight_generation",
        target_audience="executive",
        trace_id=trace_id
    )
