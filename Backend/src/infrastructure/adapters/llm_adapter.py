"""LLM integration adapter for the hexagonal architecture."""
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ...application.use_cases.financial_analysis_use_cases import (
    GetFinancialSummaryUseCase,
    GetBranchAnalysisUseCase,
    GetAnomalyAnalysisUseCase,
    QueryFinancialDataUseCase
)

logger = logging.getLogger(__name__)


class LLMQueryProcessor:
    """Processes natural language queries and maps them to use cases."""
    
    def __init__(
        self,
        summary_use_case: GetFinancialSummaryUseCase,
        branch_analysis_use_case: GetBranchAnalysisUseCase,
        anomaly_analysis_use_case: GetAnomalyAnalysisUseCase,
        query_use_case: QueryFinancialDataUseCase
    ):
        self.summary_use_case = summary_use_case
        self.branch_analysis_use_case = branch_analysis_use_case
        self.anomaly_analysis_use_case = anomaly_analysis_use_case
        self.query_use_case = query_use_case
        
        # Query patterns for intent recognition
        self.query_patterns = {
            'summary': [
                'resumen', 'general', 'overview', 'estadistic', 'total',
                'cuanto', 'suma', 'balance', 'saldo'
            ],
            'branch': [
                'sucursal', 'branch', 'oficina', 'sede'
            ],
            'anomaly': [
                'anomal', 'problema', 'error', 'irregular', 'sospech',
                'alerta', 'raro', 'extraño', 'inusual'
            ],
            'transaction_type': [
                'deposito', 'retiro', 'transferencia', 'pago', 'prestamo', 'comision'
            ],
            'date_range': [
                'fecha', 'periodo', 'mes', 'año', 'dia', 'desde', 'hasta'
            ]
        }
    
    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process natural language query and return results."""
        try:
            query_lower = query.lower()
            intent = self._classify_query_intent(query_lower)
            
            logger.info(f"Processing query with intent: {intent}")
            
            if intent == 'summary':
                return await self._handle_summary_query(query_lower, context)
            elif intent == 'branch':
                return await self._handle_branch_query(query_lower, context)
            elif intent == 'anomaly':
                return await self._handle_anomaly_query(query_lower, context)
            elif intent == 'transaction_type':
                return await self._handle_transaction_query(query_lower, context)
            else:
                return await self._handle_general_query(query_lower, context)
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'success': False,
                'message': f'Error procesando consulta: {str(e)}',
                'data': {},
                'response': 'Lo siento, hubo un error procesando tu consulta. Por favor intenta reformularla.'
            }
    
    def _classify_query_intent(self, query_lower: str) -> str:
        """Classify query intent based on keywords."""
        intent_scores = {}
        
        for intent, patterns in self.query_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return 'general'
        
        # Return intent with highest score
        return max(intent_scores.items(), key=lambda x: x[1])[0]
    
    async def _handle_summary_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle summary queries."""
        result = await self.summary_use_case.execute()
        
        if result['success']:
            data = result['data']
            metrics = data.get('metrics', {})
            
            response = self._generate_summary_response(metrics, data)
            
            return {
                'success': True,
                'message': result['message'],
                'data': data,
                'response': response,
                'source': 'hexagonal_architecture'
            }
        else:
            return {
                'success': False,
                'message': result['message'],
                'data': {},
                'response': 'No hay datos disponibles para generar un resumen.'
            }
    
    async def _handle_branch_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle branch-related queries."""
        # Try to extract branch number from query
        branch_id = self._extract_branch_id(query)
        
        result = await self.branch_analysis_use_case.execute(branch_id)
        
        if result['success']:
            data = result['data']
            response = self._generate_branch_response(data, branch_id)
            
            return {
                'success': True,
                'message': result['message'],
                'data': data,
                'response': response,
                'source': 'hexagonal_architecture'
            }
        else:
            return {
                'success': False,
                'message': result['message'],
                'data': {},
                'response': f'No se encontraron datos para la sucursal{"" if not branch_id else f" {branch_id}"}.'
            }
    
    async def _handle_anomaly_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle anomaly-related queries."""
        # Extract severity or type filters
        severity_filter = self._extract_severity(query)
        type_filter = self._extract_anomaly_type(query)
        
        result = await self.anomaly_analysis_use_case.execute(severity_filter, type_filter)
        
        if result['success']:
            data = result['data']
            response = self._generate_anomaly_response(data)
            
            return {
                'success': True,
                'message': result['message'],
                'data': data,
                'response': response,
                'source': 'hexagonal_architecture'
            }
        else:
            return {
                'success': False,
                'message': result['message'],
                'data': {},
                'response': 'No se encontraron anomalías en los datos.'
            }
    
    async def _handle_transaction_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transaction type queries."""
        transaction_type = self._extract_transaction_type(query)
        
        if not transaction_type:
            # Default to all transactions
            result = await self.query_use_case.execute('all')
        else:
            result = await self.query_use_case.execute(
                'by_transaction_type',
                {'transaction_type': transaction_type}
            )
        
        if result['success']:
            data = result['data']
            response = self._generate_transaction_response(data, transaction_type)
            
            return {
                'success': True,
                'message': result['message'],
                'data': data,
                'response': response,
                'source': 'hexagonal_architecture'
            }
        else:
            return {
                'success': False,
                'message': result['message'],
                'data': {},
                'response': f'No se encontraron transacciones{"" if not transaction_type else f" de tipo {transaction_type}"}.'
            }
    
    async def _handle_general_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general queries."""
        # Default to summary for general queries
        return await self._handle_summary_query(query, context)
    
    def _generate_summary_response(self, metrics: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Generate human-readable summary response."""
        total_ingresos = metrics.get('total_ingresos', 0)
        total_egresos = metrics.get('total_egresos', 0)
        saldo_neto = metrics.get('saldo_neto', 0)
        total_sucursales = metrics.get('total_sucursales', 0)
        total_transacciones = metrics.get('total_transacciones', 0)
        rentabilidad = metrics.get('rentabilidad', 'Neutral')
        
        response = f"""📊 **Resumen Ejecutivo Financiero**

## 💰 Métricas Principales
- **Total Ingresos**: ${total_ingresos:,.2f}
- **Total Egresos**: ${total_egresos:,.2f}
- **Saldo Neto**: ${saldo_neto:,.2f}
- **Sucursales Activas**: {total_sucursales}
- **Transacciones Procesadas**: {total_transacciones:,}

## 🎯 Estado Financiero
- **Rentabilidad**: {'✅ ' + rentabilidad if rentabilidad == 'Positiva' else '⚠️ ' + rentabilidad}"""

        if total_sucursales > 0:
            promedio_sucursal = total_ingresos / total_sucursales
            response += f"\n- **Promedio por Sucursal**: ${promedio_sucursal:,.2f}"
        
        anomalies_count = len(data.get('anomalies_summary', {}).get('by_severity', {}))
        if anomalies_count > 0:
            response += f"\n- **Anomalías Detectadas**: {anomalies_count}"
        
        response += "\n\n💡 **¿Necesitas información específica de alguna sucursal o tipo de transacción?**"
        
        return response
    
    def _generate_branch_response(self, data: Dict[str, Any], branch_id: Optional[int]) -> str:
        """Generate branch analysis response."""
        if branch_id:
            # Specific branch response
            branch_summary = data.get('branch_summary', {})
            metrics = data.get('metrics', {})
            
            if not branch_summary:
                return f"No se encontró información para la sucursal {branch_id}."
            
            return f"""🏦 **Análisis de Sucursal #{branch_id}**

## 💰 Rendimiento Financiero
- **Total Ingresos**: ${branch_summary.get('total_ingresos', 0):,.2f}
- **Total Egresos**: ${branch_summary.get('total_egresos', 0):,.2f}
- **Saldo Neto**: ${branch_summary.get('saldo_neto', 0):,.2f}
- **Transacciones**: {branch_summary.get('total_transacciones', 0):,}
- **Estado**: {branch_summary.get('rentabilidad', 'N/A')}

📍 **Ubicación**: {branch_summary.get('ubicacion', 'No especificada')}

💡 *¿Quieres comparar con otras sucursales?*"""
        else:
            # All branches summary
            total_branches = data.get('total_branches', 0)
            top_performing = data.get('top_performing', [])
            
            response = f"""🏦 **Análisis de Red de Sucursales**

📊 **Resumen General**
- **Total de Sucursales**: {total_branches}

## 🏆 **Top 5 Sucursales por Rendimiento**"""
            
            for i, branch in enumerate(top_performing[:5], 1):
                response += f"\n{i}. **Sucursal #{branch.get('numero_sucursal')}**: ${branch.get('saldo_neto', 0):,.2f}"
            
            response += "\n\n💡 *¿Quieres analizar una sucursal específica?*"
            
            return response
    
    def _generate_anomaly_response(self, data: Dict[str, Any]) -> str:
        """Generate anomaly analysis response."""
        total_anomalies = data.get('total_anomalies', 0)
        summary = data.get('summary', {})
        
        if total_anomalies == 0:
            return "✅ **Excelente!** No se detectaron anomalías en los datos financieros."
        
        by_severity = summary.get('by_severity', {})
        by_type = summary.get('by_type', {})
        
        response = f"""🚨 **Análisis de Anomalías Detectadas**

## 📊 **Resumen**
- **Total de Anomalías**: {total_anomalies}

## ⚠️ **Por Severidad**"""
        
        for severity, count in by_severity.items():
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
            response += f"\n- {severity_icon} **{severity.capitalize()}**: {count}"
        
        response += "\n\n## 🔍 **Por Tipo**"
        for anomaly_type, count in by_type.items():
            response += f"\n- **{anomaly_type.replace('_', ' ').title()}**: {count}"
        
        response += "\n\n💡 *¿Quieres revisar las anomalías de alta severidad?*"
        
        return response
    
    def _generate_transaction_response(self, data: Dict[str, Any], transaction_type: Optional[str]) -> str:
        """Generate transaction analysis response."""
        records_count = data.get('records_count', 0)
        metrics = data.get('metrics', {})
        
        if records_count == 0:
            return f"No se encontraron transacciones{'.' if not transaction_type else f' de tipo {transaction_type}.'}"
        
        total_ingresos = metrics.get('total_ingresos', 0)
        total_egresos = metrics.get('total_egresos', 0)
        
        type_text = f" de {transaction_type}" if transaction_type else ""
        
        return f"""💳 **Análisis de Transacciones{type_text.title()}**

## 📊 **Resumen**
- **Total de Transacciones**: {records_count:,}
- **Monto Total en Ingresos**: ${total_ingresos:,.2f}
- **Monto Total en Egresos**: ${total_egresos:,.2f}
- **Balance Neto**: ${total_ingresos - total_egresos:,.2f}

💡 *¿Quieres ver el detalle por sucursal?*"""
    
    # Helper methods for extracting information from queries
    def _extract_branch_id(self, query: str) -> Optional[int]:
        """Extract branch ID from query."""
        import re
        match = re.search(r'sucursal\s*#?(\d+)', query)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_severity(self, query: str) -> Optional[str]:
        """Extract severity filter from query."""
        if any(word in query for word in ['alta', 'high', 'critica', 'grave']):
            return 'high'
        elif any(word in query for word in ['media', 'medium', 'moderada']):
            return 'medium'
        elif any(word in query for word in ['baja', 'low', 'menor']):
            return 'low'
        return None
    
    def _extract_anomaly_type(self, query: str) -> Optional[str]:
        """Extract anomaly type from query."""
        if 'monto' in query or 'cantidad' in query:
            return 'high_amount'
        elif 'duplicad' in query:
            return 'duplicate_transaction'
        return None
    
    def _extract_transaction_type(self, query: str) -> Optional[str]:
        """Extract transaction type from query."""
        types = ['deposito', 'retiro', 'transferencia', 'pago', 'prestamo', 'comision']
        for tx_type in types:
            if tx_type in query:
                return tx_type
        return None