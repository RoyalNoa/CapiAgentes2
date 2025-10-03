"""Domain services for financial business logic."""
from typing import List, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal

from ..entities.financial_record import FinancialRecord, Anomaly, BranchSummary


class FinancialAnalysisService:
    """Domain service for financial analysis business rules."""
    
    @staticmethod
    def calculate_branch_summary(records: List[FinancialRecord]) -> List[BranchSummary]:
        """Calculate branch summaries from financial records."""
        branch_data: Dict[int, Dict[str, Any]] = {}
        
        for record in records:
            if not record.numero_sucursal:
                continue
                
            branch_id = record.numero_sucursal
            if branch_id not in branch_data:
                branch_data[branch_id] = {
                    'nombre_sucursal': record.sucursal,
                    'total_ingresos': Decimal('0'),
                    'total_egresos': Decimal('0'),
                    'total_transacciones': 0,
                    'ubicacion': record.ubicacion
                }
            
            branch_info = branch_data[branch_id]
            branch_info['total_transacciones'] += 1
            
            if record.is_income:
                branch_info['total_ingresos'] += record.monto
            elif record.is_expense:
                branch_info['total_egresos'] += record.monto
        
        return [
            BranchSummary(
                numero_sucursal=branch_id,
                nombre_sucursal=data['nombre_sucursal'],
                total_ingresos=data['total_ingresos'],
                total_egresos=data['total_egresos'],
                total_transacciones=data['total_transacciones'],
                ubicacion=data['ubicacion']
            )
            for branch_id, data in branch_data.items()
        ]
    
    @staticmethod
    def calculate_financial_metrics(records: List[FinancialRecord]) -> Dict[str, Any]:
        """Calculate overall financial metrics."""
        total_ingresos = Decimal('0')
        total_egresos = Decimal('0')
        branches = set()
        transaction_types = {}
        
        for record in records:
            if record.is_income:
                total_ingresos += record.monto
            elif record.is_expense:
                total_egresos += record.monto
            
            if record.numero_sucursal:
                branches.add(record.numero_sucursal)
            
            tx_type = record.tipo_transaccion
            transaction_types[tx_type] = transaction_types.get(tx_type, 0) + 1
        
        saldo_neto = total_ingresos - total_egresos
        
        return {
            'total_ingresos': float(total_ingresos),
            'total_egresos': float(total_egresos),
            'saldo_neto': float(saldo_neto),
            'total_sucursales': len(branches),
            'total_transacciones': len(records),
            'rentabilidad': 'Positiva' if saldo_neto > 0 else 'Negativa' if saldo_neto < 0 else 'Neutral',
            'promedio_por_sucursal': float(total_ingresos / len(branches)) if branches else 0,
            'tipos_transacciones': transaction_types
        }
    
    @staticmethod
    def detect_anomalies(records: List[FinancialRecord]) -> List[Anomaly]:
        """Detect financial anomalies using business rules."""
        anomalies = []
        
        if not records:
            return anomalies
        
        # Calculate statistics for anomaly detection
        amounts = [record.monto for record in records]
        avg_amount = sum(amounts) / len(amounts)
        max_amount = max(amounts)
        min_amount = min(amounts)
        
        # Threshold for unusual amounts (3x average)
        high_threshold = avg_amount * 3
        
        # Detect unusual amounts
        for i, record in enumerate(records):
            record_id = f"record_{i}"
            detected_at = datetime.now()
            
            # High amount anomaly
            if record.monto > high_threshold:
                anomalies.append(Anomaly(
                    record_id=record_id,
                    anomaly_type="high_amount",
                    severity="high" if record.monto > high_threshold * 2 else "medium",
                    description=f"Monto inusualmente alto: ${record.monto} (promedio: ${avg_amount:.2f})",
                    detected_at=detected_at,
                    confidence_score=min(0.9, float(record.monto / high_threshold / 2)),
                    metadata={
                        'amount': float(record.monto),
                        'average': float(avg_amount),
                        'threshold': float(high_threshold),
                        'branch': record.numero_sucursal,
                        'transaction_type': record.tipo_transaccion
                    }
                ))
            
            # Duplicate transaction detection (same amount, branch, and type)
            duplicates = [
                r for r in records 
                if r.monto == record.monto 
                and r.numero_sucursal == record.numero_sucursal
                and r.tipo_transaccion == record.tipo_transaccion
                and r != record
            ]
            
            if duplicates:
                anomalies.append(Anomaly(
                    record_id=record_id,
                    anomaly_type="duplicate_transaction",
                    severity="medium",
                    description=f"Transacción posiblemente duplicada: ${record.monto} en sucursal {record.numero_sucursal}",
                    detected_at=detected_at,
                    confidence_score=0.7,
                    metadata={
                        'duplicate_count': len(duplicates),
                        'amount': float(record.monto),
                        'branch': record.numero_sucursal,
                        'transaction_type': record.tipo_transaccion
                    }
                ))
        
        return anomalies
    
    @staticmethod
    def validate_financial_record(record: FinancialRecord) -> Tuple[bool, List[str]]:
        """Validate a financial record according to business rules."""
        errors = []
        
        # Basic validations
        if record.monto <= 0:
            errors.append("El monto debe ser mayor que cero")
        
        if not record.descripcion.strip():
            errors.append("La descripción no puede estar vacía")
        
        if not record.sucursal.strip():
            errors.append("La sucursal es requerida")
        
        # Business rule validations
        valid_transaction_types = [
            'deposito', 'retiro', 'transferencia', 'pago', 
            'prestamo', 'comision', 'pago_prestamo'
        ]
        
        if record.tipo_transaccion not in valid_transaction_types:
            errors.append(f"Tipo de transacción inválido: {record.tipo_transaccion}")
        
        # Maximum amount validation (business rule)
        max_allowed_amount = Decimal('1000000')  # 1 million
        if record.monto > max_allowed_amount:
            errors.append(f"El monto excede el límite permitido: ${max_allowed_amount}")
        
        # Date validation
        if record.fecha > datetime.now():
            errors.append("La fecha no puede ser futura")
        
        return len(errors) == 0, errors


class AnomalyAnalysisService:
    """Domain service for anomaly analysis."""
    
    @staticmethod
    def categorize_anomalies(anomalies: List[Anomaly]) -> Dict[str, List[Anomaly]]:
        """Categorize anomalies by type."""
        categories = {}
        
        for anomaly in anomalies:
            anomaly_type = anomaly.anomaly_type
            if anomaly_type not in categories:
                categories[anomaly_type] = []
            categories[anomaly_type].append(anomaly)
        
        return categories
    
    @staticmethod
    def get_anomaly_summary(anomalies: List[Anomaly]) -> Dict[str, Any]:
        """Get summary statistics for anomalies."""
        if not anomalies:
            return {
                'total': 0,
                'by_severity': {},
                'by_type': {},
                'average_confidence': 0
            }
        
        by_severity = {}
        by_type = {}
        total_confidence = 0
        
        for anomaly in anomalies:
            # Count by severity
            severity = anomaly.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Count by type
            anomaly_type = anomaly.anomaly_type
            by_type[anomaly_type] = by_type.get(anomaly_type, 0) + 1
            
            total_confidence += anomaly.confidence_score
        
        return {
            'total': len(anomalies),
            'by_severity': by_severity,
            'by_type': by_type,
            'average_confidence': total_confidence / len(anomalies)
        }