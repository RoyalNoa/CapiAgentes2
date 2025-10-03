"""
Financial Analyzer - Motor de análisis financiero con capacidades ML
Procesa datos reales y genera insights accionables con observabilidad completa
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from pathlib import Path

# ML and statistical libraries
try:
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.cluster import KMeans
    from sklearn.ensemble import IsolationForest
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from scipy import stats
    from scipy.stats import zscore, jarque_bera, normaltest
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class FinancialMetrics:
    """Métricas financieras calculadas"""
    total_records: int
    total_value: float
    mean_value: float
    median_value: float
    std_deviation: float
    min_value: float
    max_value: float
    value_range: float
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    percentile_25: Optional[float] = None
    percentile_75: Optional[float] = None
    iqr: Optional[float] = None
    coefficient_of_variation: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte métricas a diccionario"""
        return {
            "total_records": self.total_records,
            "total_value": self.total_value,
            "mean_value": self.mean_value,
            "median_value": self.median_value,
            "std_deviation": self.std_deviation,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "value_range": self.value_range,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
            "percentile_25": self.percentile_25,
            "percentile_75": self.percentile_75,
            "iqr": self.iqr,
            "coefficient_of_variation": self.coefficient_of_variation
        }


@dataclass
class CorrelationAnalysis:
    """Análisis de correlaciones entre variables"""
    correlation_matrix: Dict[str, Dict[str, float]]
    strong_correlations: List[Tuple[str, str, float]]  # (var1, var2, correlation)
    weak_correlations: List[Tuple[str, str, float]]
    correlation_summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte análisis a diccionario"""
        return {
            "correlation_matrix": self.correlation_matrix,
            "strong_correlations": self.strong_correlations,
            "weak_correlations": self.weak_correlations,
            "correlation_summary": self.correlation_summary
        }


@dataclass
class PatternAnalysis:
    """Análisis de patrones en los datos"""
    trend_analysis: Dict[str, str]  # variable -> trend (increasing, decreasing, stable)
    seasonal_patterns: Dict[str, Any]
    outlier_detection: Dict[str, List[int]]  # variable -> list of outlier indices
    cluster_analysis: Optional[Dict[str, Any]] = None
    anomaly_scores: Optional[Dict[str, List[float]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte análisis a diccionario"""
        return {
            "trend_analysis": self.trend_analysis,
            "seasonal_patterns": self.seasonal_patterns,
            "outlier_detection": self.outlier_detection,
            "cluster_analysis": self.cluster_analysis,
            "anomaly_scores": self.anomaly_scores
        }


@dataclass
class FinancialAnalysisResult:
    """Resultado completo del análisis financiero"""
    dataset_info: Dict[str, Any]
    basic_metrics: Dict[str, FinancialMetrics]
    correlation_analysis: CorrelationAnalysis
    pattern_analysis: PatternAnalysis
    quality_assessment: Dict[str, Any]
    feature_engineering: Dict[str, Any]
    analysis_metadata: Dict[str, Any]
    processing_time: float
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte resultado completo a diccionario"""
        return {
            "dataset_info": self.dataset_info,
            "basic_metrics": {k: v.to_dict() for k, v in self.basic_metrics.items()},
            "correlation_analysis": self.correlation_analysis.to_dict(),
            "pattern_analysis": self.pattern_analysis.to_dict(),
            "quality_assessment": self.quality_assessment,
            "feature_engineering": self.feature_engineering,
            "analysis_metadata": self.analysis_metadata,
            "processing_time": self.processing_time,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    def to_json(self) -> str:
        """Convierte a JSON para serialización"""
        return json.dumps(self.to_dict(), default=str, indent=2)


class FinancialAnalyzer:
    """
    Motor de análisis financiero con capacidades ML
    Procesa datos CSV y genera insights profesionales
    """
    
    def __init__(self,
                 enable_ml: bool = True,
                 outlier_threshold: float = 3.0,
                 correlation_threshold: float = 0.5,
                 min_records_for_analysis: int = 10):
        """
        Inicializa el analizador financiero
        
        Args:
            enable_ml: Habilitar análisis ML avanzado
            outlier_threshold: Threshold Z-score para outliers
            correlation_threshold: Threshold para correlaciones fuertes
            min_records_for_analysis: Mínimo registros requeridos
        """
        self.enable_ml = enable_ml and SKLEARN_AVAILABLE
        self.outlier_threshold = outlier_threshold
        self.correlation_threshold = correlation_threshold
        self.min_records_for_analysis = min_records_for_analysis
        
        # Configurar capacidades disponibles
        self.capabilities = {
            "sklearn_available": SKLEARN_AVAILABLE,
            "scipy_available": SCIPY_AVAILABLE,
            "ml_analysis": self.enable_ml,
            "basic_statistics": True,
            "correlation_analysis": True,
            "pattern_detection": True
        }
        
        logger.info(f"FinancialAnalyzer inicializado - ML: {self.enable_ml}, "
                   f"sklearn: {SKLEARN_AVAILABLE}, scipy: {SCIPY_AVAILABLE}")
    
    def analyze_dataset(self, 
                       data: Union[pd.DataFrame, List[Dict[str, Any]], str, Path],
                       trace_id: Optional[str] = None) -> FinancialAnalysisResult:
        """
        Analiza dataset financiero completo
        
        Args:
            data: DataFrame, lista de dict, ruta CSV o Path
            trace_id: ID de trazabilidad
            
        Returns:
            Resultado completo del análisis
        """
        start_time = pd.Timestamp.now()
        logger.info(f"[{trace_id}] Iniciando análisis financiero de dataset")
        
        try:
            # Cargar y validar datos
            df = self._load_and_validate_data(data)
            
            if len(df) < self.min_records_for_analysis:
                raise ValueError(f"Dataset muy pequeño: {len(df)} registros < {self.min_records_for_analysis} mínimo")
            
            # Información del dataset
            dataset_info = self._analyze_dataset_info(df)
            logger.info(f"[{trace_id}] Dataset cargado: {dataset_info['total_records']} registros, "
                       f"{dataset_info['total_columns']} columnas")
            
            # Métricas básicas por columna numérica
            basic_metrics = self._calculate_basic_metrics(df)
            logger.info(f"[{trace_id}] Métricas básicas calculadas para {len(basic_metrics)} columnas")
            
            # Análisis de correlaciones
            correlation_analysis = self._analyze_correlations(df)
            logger.info(f"[{trace_id}] Análisis de correlaciones: {len(correlation_analysis.strong_correlations)} fuertes")
            
            # Análisis de patrones
            pattern_analysis = self._analyze_patterns(df)
            logger.info(f"[{trace_id}] Análisis de patrones: tendencias y outliers detectados")
            
            # Evaluación de calidad de datos
            quality_assessment = self._assess_data_quality(df)
            
            # Feature engineering
            feature_engineering = self._engineer_features(df)
            
            # Metadata del análisis
            processing_time = (pd.Timestamp.now() - start_time).total_seconds()
            analysis_metadata = {
                "analysis_timestamp": start_time.isoformat(),
                "processing_time_seconds": processing_time,
                "analyzer_version": "1.0.0",
                "capabilities_used": self.capabilities,
                "trace_id": trace_id
            }
            
            result = FinancialAnalysisResult(
                dataset_info=dataset_info,
                basic_metrics=basic_metrics,
                correlation_analysis=correlation_analysis,
                pattern_analysis=pattern_analysis,
                quality_assessment=quality_assessment,
                feature_engineering=feature_engineering,
                analysis_metadata=analysis_metadata,
                processing_time=processing_time,
                success=True
            )
            
            logger.info(f"[{trace_id}] Análisis financiero completado exitosamente en {processing_time:.3f}s")
            return result
            
        except Exception as e:
            processing_time = (pd.Timestamp.now() - start_time).total_seconds()
            logger.error(f"[{trace_id}] Error en análisis financiero: {e}")
            
            return FinancialAnalysisResult(
                dataset_info={},
                basic_metrics={},
                correlation_analysis=CorrelationAnalysis({}, [], [], {}),
                pattern_analysis=PatternAnalysis({}, {}, {}),
                quality_assessment={},
                feature_engineering={},
                analysis_metadata={"error": str(e), "trace_id": trace_id},
                processing_time=processing_time,
                success=False,
                errors=[str(e)]
            )
    
    def _load_and_validate_data(self, data: Union[pd.DataFrame, List[Dict], str, Path]) -> pd.DataFrame:
        """Carga y valida datos de entrada"""
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, (str, Path)):
            # Cargar desde archivo CSV
            df = pd.read_csv(data)
        else:
            raise ValueError(f"Tipo de datos no soportado: {type(data)}")
        
        if df.empty:
            raise ValueError("Dataset vacío")
        
        # Limpiar nombres de columnas
        df.columns = df.columns.str.strip().str.lower()
        
        return df
    
    def _analyze_dataset_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza información general del dataset"""
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        datetime_columns = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        return {
            "total_records": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "datetime_columns": datetime_columns,
            "column_types": df.dtypes.to_dict(),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "null_counts": df.isnull().sum().to_dict(),
            "duplicate_rows": df.duplicated().sum()
        }
    
    def _calculate_basic_metrics(self, df: pd.DataFrame) -> Dict[str, FinancialMetrics]:
        """Calcula métricas básicas para columnas numéricas"""
        metrics = {}
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            series = df[column].dropna()
            
            if len(series) == 0:
                continue
            
            # Métricas básicas
            basic_stats = {
                'total_records': len(series),
                'total_value': float(series.sum()),
                'mean_value': float(series.mean()),
                'median_value': float(series.median()),
                'std_deviation': float(series.std()),
                'min_value': float(series.min()),
                'max_value': float(series.max()),
                'value_range': float(series.max() - series.min())
            }
            
            # Métricas avanzadas si scipy disponible
            if SCIPY_AVAILABLE and len(series) > 3:
                try:
                    basic_stats.update({
                        'skewness': float(stats.skew(series)),
                        'kurtosis': float(stats.kurtosis(series)),
                        'percentile_25': float(series.quantile(0.25)),
                        'percentile_75': float(series.quantile(0.75)),
                        'iqr': float(series.quantile(0.75) - series.quantile(0.25)),
                        'coefficient_of_variation': float(series.std() / series.mean()) if series.mean() != 0 else None
                    })
                except Exception as e:
                    logger.warning(f"Error calculando métricas avanzadas para {column}: {e}")
            
            metrics[column] = FinancialMetrics(**basic_stats)
        
        return metrics
    
    def _analyze_correlations(self, df: pd.DataFrame) -> CorrelationAnalysis:
        """Analiza correlaciones entre variables numéricas"""
        numeric_df = df.select_dtypes(include=[np.number])
        
        if len(numeric_df.columns) < 2:
            return CorrelationAnalysis({}, [], [], {"message": "Insuficientes columnas numéricas para correlación"})
        
        # Calcular matriz de correlación
        corr_matrix = numeric_df.corr()
        
        # Convertir a diccionario anidado
        correlation_matrix = {}
        for col1 in corr_matrix.columns:
            correlation_matrix[col1] = {}
            for col2 in corr_matrix.columns:
                correlation_matrix[col1][col2] = float(corr_matrix.loc[col1, col2]) if not pd.isna(corr_matrix.loc[col1, col2]) else 0.0
        
        # Identificar correlaciones fuertes y débiles
        strong_correlations = []
        weak_correlations = []
        
        for i, col1 in enumerate(corr_matrix.columns):
            for j, col2 in enumerate(corr_matrix.columns):
                if i < j:  # Evitar duplicados
                    corr_value = corr_matrix.loc[col1, col2]
                    if not pd.isna(corr_value):
                        abs_corr = abs(corr_value)
                        if abs_corr >= self.correlation_threshold:
                            strong_correlations.append((col1, col2, float(corr_value)))
                        elif abs_corr >= 0.1:  # Correlaciones débiles pero detectables
                            weak_correlations.append((col1, col2, float(corr_value)))
        
        # Resumen de correlaciones
        correlation_summary = {
            "total_pairs": len(numeric_df.columns) * (len(numeric_df.columns) - 1) // 2,
            "strong_correlations_count": len(strong_correlations),
            "weak_correlations_count": len(weak_correlations),
            "max_correlation": max([abs(corr[2]) for corr in strong_correlations + weak_correlations], default=0),
            "mean_abs_correlation": np.mean([abs(corr[2]) for corr in strong_correlations + weak_correlations]) if strong_correlations or weak_correlations else 0
        }
        
        return CorrelationAnalysis(
            correlation_matrix=correlation_matrix,
            strong_correlations=strong_correlations,
            weak_correlations=weak_correlations,
            correlation_summary=correlation_summary
        )
    
    def _analyze_patterns(self, df: pd.DataFrame) -> PatternAnalysis:
        """Analiza patrones y tendencias en los datos"""
        numeric_df = df.select_dtypes(include=[np.number])
        
        # Análisis de tendencias
        trend_analysis = {}
        for column in numeric_df.columns:
            series = numeric_df[column].dropna()
            if len(series) > 10:
                # Regresión lineal simple para detectar tendencia
                x = np.arange(len(series))
                slope = np.polyfit(x, series, 1)[0]
                
                if abs(slope) < series.std() * 0.01:  # Threshold adaptativo
                    trend_analysis[column] = "stable"
                elif slope > 0:
                    trend_analysis[column] = "increasing"
                else:
                    trend_analysis[column] = "decreasing"
            else:
                trend_analysis[column] = "insufficient_data"
        
        # Detección de outliers usando Z-score
        outlier_detection = {}
        for column in numeric_df.columns:
            series = numeric_df[column].dropna()
            if len(series) > 3:
                if SCIPY_AVAILABLE:
                    z_scores = np.abs(zscore(series))
                    outliers = np.where(z_scores > self.outlier_threshold)[0].tolist()
                else:
                    # Método alternativo sin scipy
                    mean = series.mean()
                    std = series.std()
                    outliers = series[(series < mean - self.outlier_threshold * std) | 
                                    (series > mean + self.outlier_threshold * std)].index.tolist()
                
                outlier_detection[column] = outliers
        
        # Análisis de patrones estacionales (básico)
        seasonal_patterns = {}
        if 'fecha' in df.columns or 'date' in df.columns:
            date_column = 'fecha' if 'fecha' in df.columns else 'date'
            try:
                df[date_column] = pd.to_datetime(df[date_column])
                df['month'] = df[date_column].dt.month
                df['day_of_week'] = df[date_column].dt.dayofweek
                
                for column in numeric_df.columns:
                    monthly_avg = df.groupby('month')[column].mean()
                    weekly_avg = df.groupby('day_of_week')[column].mean()
                    
                    seasonal_patterns[column] = {
                        "monthly_pattern": monthly_avg.to_dict(),
                        "weekly_pattern": weekly_avg.to_dict(),
                        "has_monthly_seasonality": monthly_avg.std() > monthly_avg.mean() * 0.1,
                        "has_weekly_seasonality": weekly_avg.std() > weekly_avg.mean() * 0.1
                    }
            except Exception as e:
                logger.warning(f"Error en análisis estacional: {e}")
                seasonal_patterns = {"error": "Could not parse date column"}
        
        # Análisis de clustering si ML disponible
        cluster_analysis = None
        anomaly_scores = None
        
        if self.enable_ml and len(numeric_df.columns) >= 2 and len(numeric_df) > 10:
            try:
                # Preparar datos para clustering
                scaler = StandardScaler()
                scaled_data = scaler.fit_transform(numeric_df.fillna(numeric_df.mean()))
                
                # K-means clustering
                optimal_clusters = min(5, len(numeric_df) // 10)  # Heurística simple
                if optimal_clusters >= 2:
                    kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
                    cluster_labels = kmeans.fit_predict(scaled_data)
                    
                    silhouette_avg = silhouette_score(scaled_data, cluster_labels)
                    
                    cluster_analysis = {
                        "n_clusters": optimal_clusters,
                        "cluster_labels": cluster_labels.tolist(),
                        "cluster_centers": kmeans.cluster_centers_.tolist(),
                        "silhouette_score": float(silhouette_avg),
                        "cluster_sizes": {str(i): int(np.sum(cluster_labels == i)) for i in range(optimal_clusters)}
                    }
                
                # Detección de anomalías con Isolation Forest
                isolation_forest = IsolationForest(contamination=0.1, random_state=42)
                anomaly_labels = isolation_forest.fit_predict(scaled_data)
                anomaly_scores_values = isolation_forest.score_samples(scaled_data)
                
                anomaly_scores = {
                    "anomaly_labels": anomaly_labels.tolist(),
                    "anomaly_scores": anomaly_scores_values.tolist(),
                    "anomaly_count": int(np.sum(anomaly_labels == -1)),
                    "normal_count": int(np.sum(anomaly_labels == 1))
                }
                
            except Exception as e:
                logger.warning(f"Error en análisis ML: {e}")
        
        return PatternAnalysis(
            trend_analysis=trend_analysis,
            seasonal_patterns=seasonal_patterns,
            outlier_detection=outlier_detection,
            cluster_analysis=cluster_analysis,
            anomaly_scores=anomaly_scores
        )
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Evalúa la calidad de los datos"""
        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        
        return {
            "completeness_score": 1.0 - (null_cells / total_cells),
            "null_percentage": (null_cells / total_cells) * 100,
            "duplicate_percentage": (df.duplicated().sum() / len(df)) * 100,
            "columns_with_nulls": df.columns[df.isnull().any()].tolist(),
            "columns_with_high_nulls": df.columns[df.isnull().sum() > len(df) * 0.5].tolist(),
            "data_types_consistent": all(df[col].dtype != 'object' for col in df.select_dtypes(include=[np.number]).columns),
            "recommendations": self._generate_quality_recommendations(df)
        }
    
    def _engineer_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Realiza feature engineering básico"""
        numeric_df = df.select_dtypes(include=[np.number])
        features = {}
        
        if len(numeric_df.columns) > 0:
            # Estadísticas agregadas
            features["aggregate_stats"] = {
                "row_means": numeric_df.mean(axis=1).tolist(),
                "row_sums": numeric_df.sum(axis=1).tolist(),
                "row_std": numeric_df.std(axis=1).tolist(),
                "row_min": numeric_df.min(axis=1).tolist(),
                "row_max": numeric_df.max(axis=1).tolist()
            }
            
            # Ratios financieros simples (si aplicable)
            if len(numeric_df.columns) >= 2:
                col1, col2 = numeric_df.columns[0], numeric_df.columns[1]
                safe_col2 = numeric_df[col2].replace(0, np.nan)
                ratio = numeric_df[col1] / safe_col2
                features["financial_ratios"] = {
                    f"{col1}_to_{col2}_ratio": ratio.fillna(0).tolist()
                }
            
            # Moving averages si hay suficientes datos
            if len(numeric_df) > 10:
                features["moving_averages"] = {}
                for column in numeric_df.columns:
                    ma_5 = numeric_df[column].rolling(window=5, min_periods=1).mean()
                    features["moving_averages"][f"{column}_ma5"] = ma_5.tolist()
        
        return features
    
    def _generate_quality_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Genera recomendaciones para mejorar calidad de datos"""
        recommendations = []
        
        null_percentage = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
        if null_percentage > 20:
            recommendations.append("High null percentage detected - consider data cleaning")
        
        if df.duplicated().sum() > len(df) * 0.1:
            recommendations.append("High duplicate percentage - consider deduplication")
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) < len(df.columns) * 0.5:
            recommendations.append("Low ratio of numeric columns - consider data type conversion")
        
        return recommendations
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Retorna capacidades del analizador"""
        return self.capabilities.copy()