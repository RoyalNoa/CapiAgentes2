"""
Observable Financial Analyzer - Integración con ProcessingContext
Análisis financiero con observabilidad completa para demo técnica
"""
import logging
from typing import Dict, Any, List, Optional, Union
import pandas as pd
from pathlib import Path

from .financial_analyzer import FinancialAnalyzer, FinancialAnalysisResult
# Processing context functionality moved to orchestrator

logger = logging.getLogger(__name__)


class ObservableFinancialAnalyzer:
    """
    Financial Analyzer con observabilidad completa
    Integra FinancialAnalyzer con ProcessingContext para visibilidad técnica total
    """
    
    def __init__(self, 
                 enable_ml: bool = True,
                 outlier_threshold: float = 3.0,
                 correlation_threshold: float = 0.5):
        """
        Inicializa el analizador observable
        
        Args:
            enable_ml: Habilitar análisis ML avanzado
            outlier_threshold: Threshold para detección de outliers
            correlation_threshold: Threshold para correlaciones fuertes
        """
        self.analyzer = FinancialAnalyzer(
            enable_ml=enable_ml,
            outlier_threshold=outlier_threshold,
            correlation_threshold=correlation_threshold
        )
        
        logger.info(f"ObservableFinancialAnalyzer inicializado - ML: {enable_ml}")
    
    def analyze_with_context(self,
                           data: Union[pd.DataFrame, List[Dict[str, Any]], str, Path],
                           query: str,
                           trace_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Ejecuta análisis financiero con contexto observable completo
        
        Args:
            data: Datos a analizar
            query: Query original del usuario
            trace_id: ID de trazabilidad
            user_id: ID del usuario
            session_id: ID de sesión
            
        Returns:
            Diccionario con análisis y contexto observable
        """
        # Crear contexto de procesamiento
        context = create_processing_context(
            query=query,
            trace_id=trace_id,
            user_id=user_id,
            session_id=session_id
        )
        
        logger.info(f"[{context.trace_id}] Iniciando análisis financiero observable")
        
        try:
            # ETAPA 1: Inicializar procesamiento
            context.start_processing()
            context.start_stage(ProcessingStage.DATA_ANALYSIS, component="ObservableFinancialAnalyzer")
            
            # ETAPA 2: Validación y carga de datos
            context.start_stage(ProcessingStage.QUERY_RECEIVED, data_type=type(data).__name__)
            context.add_input_data("original_query", query)
            context.add_input_data("data_source_type", self._identify_data_source(data))
            context.complete_stage(success=True)
            
            # ETAPA 3: Análisis principal
            context.start_stage(ProcessingStage.DATA_ANALYSIS, analyzer="FinancialAnalyzer")
            
            # Ejecutar análisis principal
            analysis_result = self.analyzer.analyze_dataset(data, trace_id=context.trace_id)
            
            # Registrar métricas del análisis
            if analysis_result.success:
                context.add_intermediate_result("financial_analysis", analysis_result.to_dict())
                context.add_metric("analysis_processing_time", analysis_result.processing_time)
                context.add_metric("records_processed", analysis_result.dataset_info.get("total_records", 0))
                context.add_metric("columns_analyzed", analysis_result.dataset_info.get("total_columns", 0))
                context.add_metric("correlations_found", len(analysis_result.correlation_analysis.strong_correlations))
                context.complete_stage(success=True, metrics_calculated=len(analysis_result.basic_metrics))
            else:
                context.add_error("Financial analysis failed", stage=ProcessingStage.DATA_ANALYSIS)
                context.complete_stage(success=False, error=analysis_result.errors[0] if analysis_result.errors else "Unknown error")
            
            # ETAPA 4: Feature Engineering
            if analysis_result.success and analysis_result.feature_engineering:
                context.start_stage(ProcessingStage.DATA_ANALYSIS, sub_stage="feature_engineering")
                context.add_intermediate_result("features", analysis_result.feature_engineering)
                features_count = len(analysis_result.feature_engineering)
                context.add_metric("features_engineered", features_count)
                context.complete_stage(success=True, features_generated=features_count)
            
            # ETAPA 5: Evaluación de calidad
            context.start_stage(ProcessingStage.DATA_ANALYSIS, sub_stage="quality_assessment")
            if analysis_result.success:
                quality_score = analysis_result.quality_assessment.get("completeness_score", 0)
                context.add_metric("data_quality_score", quality_score)
                context.add_intermediate_result("quality_assessment", analysis_result.quality_assessment)
                context.complete_stage(success=True, quality_score=quality_score)
                
                # Agregar alertas si hay problemas de calidad
                if quality_score < 0.8:
                    context.add_warning("Low data quality detected", stage=ProcessingStage.DATA_ANALYSIS)
            else:
                context.complete_stage(success=False)
            
            # ETAPA 6: Construcción de insights
            context.start_stage(ProcessingStage.DATA_ANALYSIS, sub_stage="insights_generation")
            insights = self._generate_insights(analysis_result, context)
            context.add_intermediate_result("insights", insights)
            context.complete_stage(success=True, insights_generated=len(insights))
            
            # ETAPA 7: Finalización
            context.complete_processing(success=analysis_result.success)
            
            # Construir resultado completo
            result = {
                "financial_analysis": analysis_result.to_dict(),
                "processing_context": context.to_dict(),
                "insights": insights,
                "demo_status": context.get_demo_status(),
                "performance_summary": context.get_performance_summary(),
                "success": analysis_result.success,
                "trace_id": context.trace_id
            }
            
            logger.info(f"[{context.trace_id}] Análisis financiero observable completado - "
                       f"éxito: {analysis_result.success}, "
                       f"duración total: {context.get_total_duration():.3f}s")
            
            return result
            
        except Exception as e:
            context.add_error(str(e), stage=ProcessingStage.DATA_ANALYSIS)
            context.complete_processing(success=False)
            
            logger.error(f"[{context.trace_id}] Error en análisis observable: {e}")
            
            return {
                "financial_analysis": {},
                "processing_context": context.to_dict(),
                "insights": [],
                "demo_status": context.get_demo_status(),
                "performance_summary": context.get_performance_summary(),
                "success": False,
                "error": str(e),
                "trace_id": context.trace_id
            }
    
    def _identify_data_source(self, data: Union[pd.DataFrame, List[Dict], str, Path]) -> str:
        """Identifica el tipo de fuente de datos"""
        if isinstance(data, pd.DataFrame):
            return f"DataFrame({len(data)}x{len(data.columns)})"
        elif isinstance(data, list):
            return f"List[Dict]({len(data)} records)"
        elif isinstance(data, (str, Path)):
            return f"File({Path(data).suffix})"
        else:
            return f"Unknown({type(data).__name__})"
    
    def _generate_insights(self, analysis_result: FinancialAnalysisResult, context: ProcessingContext) -> List[Dict[str, Any]]:
        """Genera insights accionables del análisis"""
        insights = []
        
        if not analysis_result.success:
            return insights
        
        try:
            # Insight 1: Dataset overview
            dataset_info = analysis_result.dataset_info
            insights.append({
                "type": "dataset_overview",
                "title": "Dataset Overview",
                "message": f"Analyzed {dataset_info.get('total_records', 0)} financial records with {dataset_info.get('total_columns', 0)} variables",
                "priority": "info",
                "data": {
                    "records": dataset_info.get('total_records', 0),
                    "columns": dataset_info.get('total_columns', 0),
                    "numeric_columns": len(dataset_info.get('numeric_columns', [])),
                    "memory_usage": dataset_info.get('memory_usage_mb', 0)
                }
            })
            
            # Insight 2: Strong correlations
            strong_corrs = analysis_result.correlation_analysis.strong_correlations
            if strong_corrs:
                top_corr = max(strong_corrs, key=lambda x: abs(x[2]))
                insights.append({
                    "type": "correlation_insight",
                    "title": "Strong Financial Correlation Detected",
                    "message": f"Strong correlation between {top_corr[0]} and {top_corr[1]} (r={top_corr[2]:.3f})",
                    "priority": "high",
                    "data": {
                        "variable_1": top_corr[0],
                        "variable_2": top_corr[1], 
                        "correlation": top_corr[2],
                        "total_strong_correlations": len(strong_corrs)
                    }
                })
            
            # Insight 3: Data quality assessment
            quality = analysis_result.quality_assessment
            completeness = quality.get('completeness_score', 1.0)
            if completeness < 0.9:
                insights.append({
                    "type": "data_quality_warning",
                    "title": "Data Quality Issue",
                    "message": f"Dataset completeness is {completeness*100:.1f}% - consider data cleaning",
                    "priority": "medium",
                    "data": {
                        "completeness_score": completeness,
                        "null_percentage": quality.get('null_percentage', 0),
                        "recommendations": quality.get('recommendations', [])
                    }
                })
            else:
                insights.append({
                    "type": "data_quality_good",
                    "title": "High Data Quality",
                    "message": f"Dataset has excellent completeness ({completeness*100:.1f}%)",
                    "priority": "info",
                    "data": {"completeness_score": completeness}
                })
            
            # Insight 4: Outlier detection
            outliers = analysis_result.pattern_analysis.outlier_detection
            total_outliers = sum(len(outlier_list) for outlier_list in outliers.values())
            if total_outliers > 0:
                insights.append({
                    "type": "outliers_detected",
                    "title": "Financial Outliers Detected",
                    "message": f"Found {total_outliers} outliers across financial variables",
                    "priority": "medium",
                    "data": {
                        "total_outliers": total_outliers,
                        "outliers_by_variable": {k: len(v) for k, v in outliers.items()}
                    }
                })
            
            # Insight 5: Trend analysis
            trends = analysis_result.pattern_analysis.trend_analysis
            increasing_vars = [var for var, trend in trends.items() if trend == "increasing"]
            decreasing_vars = [var for var, trend in trends.items() if trend == "decreasing"]
            
            if increasing_vars:
                insights.append({
                    "type": "trend_increasing",
                    "title": "Increasing Trends Detected", 
                    "message": f"Variables showing upward trends: {', '.join(increasing_vars)}",
                    "priority": "info",
                    "data": {"increasing_variables": increasing_vars}
                })
            
            if decreasing_vars:
                insights.append({
                    "type": "trend_decreasing",
                    "title": "Decreasing Trends Detected",
                    "message": f"Variables showing downward trends: {', '.join(decreasing_vars)}",
                    "priority": "info", 
                    "data": {"decreasing_variables": decreasing_vars}
                })
            
            # Insight 6: Performance metrics
            perf_summary = context.get_performance_summary()
            insights.append({
                "type": "performance_metrics",
                "title": "Analysis Performance",
                "message": f"Analysis completed in {perf_summary.get('total_duration', 0):.3f}s with {perf_summary.get('stage_count', 0)} processing stages",
                "priority": "info",
                "data": perf_summary
            })
            
            # Insight 7: ML analysis results (si disponible)
            if analysis_result.pattern_analysis.cluster_analysis:
                cluster_info = analysis_result.pattern_analysis.cluster_analysis
                insights.append({
                    "type": "cluster_analysis",
                    "title": "Data Clustering Results",
                    "message": f"Identified {cluster_info['n_clusters']} distinct data clusters (silhouette score: {cluster_info['silhouette_score']:.3f})",
                    "priority": "info",
                    "data": cluster_info
                })
            
            if analysis_result.pattern_analysis.anomaly_scores:
                anomaly_info = analysis_result.pattern_analysis.anomaly_scores
                insights.append({
                    "type": "anomaly_detection",
                    "title": "ML Anomaly Detection",
                    "message": f"ML model detected {anomaly_info['anomaly_count']} potential anomalies",
                    "priority": "medium",
                    "data": anomaly_info
                })
            
        except Exception as e:
            logger.warning(f"Error generating insights: {e}")
            insights.append({
                "type": "insight_generation_error",
                "title": "Insight Generation Warning",
                "message": f"Some insights could not be generated: {str(e)}",
                "priority": "low",
                "data": {"error": str(e)}
            })
        
        return insights
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Retorna capacidades del analizador observable"""
        base_capabilities = self.analyzer.get_capabilities()
        
        return {
            **base_capabilities,
            "observable_processing": True,
            "context_tracking": True,
            "stage_visibility": True,
            "performance_monitoring": True,
            "insight_generation": True,
            "demo_ready": True
        }


# Función helper para análisis rápido
def analyze_financial_data_observable(data: Union[pd.DataFrame, List[Dict], str, Path],
                                    query: str = "Análisis financiero completo",
                                    trace_id: Optional[str] = None,
                                    enable_ml: bool = True) -> Dict[str, Any]:
    """
    Función helper para análisis financiero observable rápido
    
    Args:
        data: Datos a analizar
        query: Descripción del análisis
        trace_id: ID de trazabilidad opcional
        enable_ml: Habilitar análisis ML
        
    Returns:
        Resultado completo con análisis y contexto
    """
    analyzer = ObservableFinancialAnalyzer(enable_ml=enable_ml)
    return analyzer.analyze_with_context(data, query, trace_id)