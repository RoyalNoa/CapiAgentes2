"""Financial record entity for the domain."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, Dict
from decimal import Decimal


@dataclass
class FinancialRecord:
    """Core financial record entity."""
    
    fecha: datetime
    monto: Decimal
    descripcion: str
    categoria: str
    sucursal: str
    tipo_transaccion: str
    numero_sucursal: Optional[int] = None
    ingresos: Optional[Decimal] = None
    egresos: Optional[Decimal] = None
    ubicacion: Optional[str] = None
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        if self.monto == 0:
            raise ValueError("Monto cannot be zero")
        
        if not self.descripcion.strip():
            raise ValueError("Descripcion cannot be empty")
            
        # Normalize transaction type
        self.tipo_transaccion = self.tipo_transaccion.lower().strip()
    
    @property
    def is_income(self) -> bool:
        """Check if this is an income transaction."""
        return self.tipo_transaccion in ['deposito', 'transferencia', 'ingreso', 'pago_prestamo']
    
    @property
    def is_expense(self) -> bool:
        """Check if this is an expense transaction."""
        return self.tipo_transaccion in ['retiro', 'pago', 'prestamo', 'comision']
    
    @property
    def net_amount(self) -> Decimal:
        """Get net amount considering transaction type."""
        return self.monto if self.is_income else -self.monto
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'fecha': self.fecha.isoformat(),
            'monto': float(self.monto),
            'descripcion': self.descripcion,
            'categoria': self.categoria,
            'sucursal': self.sucursal,
            'tipo_transaccion': self.tipo_transaccion,
            'numero_sucursal': self.numero_sucursal,
            'ingresos': float(self.ingresos) if self.ingresos else None,
            'egresos': float(self.egresos) if self.egresos else None,
            'ubicacion': self.ubicacion,
            'is_income': self.is_income,
            'is_expense': self.is_expense,
            'net_amount': float(self.net_amount)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialRecord':
        """Create instance from dictionary."""
        # Handle date conversion
        fecha = data.get('fecha')
        if isinstance(fecha, str):
            fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
        elif not isinstance(fecha, datetime):
            fecha = datetime.now()
        
        # Convert numeric values
        monto = Decimal(str(data.get('monto', 0)))
        ingresos = Decimal(str(data.get('ingresos', 0))) if data.get('ingresos') else None
        egresos = Decimal(str(data.get('egresos', 0))) if data.get('egresos') else None
        
        return cls(
            fecha=fecha,
            monto=monto,
            descripcion=str(data.get('descripcion', '')),
            categoria=str(data.get('categoria', '')),
            sucursal=str(data.get('sucursal', '')),
            tipo_transaccion=str(data.get('tipo_transaccion', '')),
            numero_sucursal=data.get('numero_sucursal'),
            ingresos=ingresos,
            egresos=egresos,
            ubicacion=data.get('ubicacion')
        )


@dataclass
class Anomaly:
    """Anomaly detection result entity."""
    
    record_id: str
    anomaly_type: str
    severity: str  # 'low', 'medium', 'high'
    description: str
    detected_at: datetime
    confidence_score: float
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate anomaly data."""
        if self.confidence_score < 0 or self.confidence_score > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        
        if self.severity not in ['low', 'medium', 'high']:
            raise ValueError("Severity must be 'low', 'medium', or 'high'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'record_id': self.record_id,
            'anomaly_type': self.anomaly_type,
            'severity': self.severity,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'confidence_score': self.confidence_score,
            'metadata': self.metadata
        }


@dataclass
class BranchSummary:
    """Branch financial summary entity."""
    
    numero_sucursal: int
    nombre_sucursal: str
    total_ingresos: Decimal
    total_egresos: Decimal
    total_transacciones: int
    ubicacion: Optional[str] = None
    
    @property
    def saldo_neto(self) -> Decimal:
        """Calculate net balance."""
        return self.total_ingresos - self.total_egresos
    
    @property
    def rentabilidad(self) -> str:
        """Get profitability status."""
        return "Positiva" if self.saldo_neto > 0 else "Negativa" if self.saldo_neto < 0 else "Neutral"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'numero_sucursal': self.numero_sucursal,
            'nombre_sucursal': self.nombre_sucursal,
            'total_ingresos': float(self.total_ingresos),
            'total_egresos': float(self.total_egresos),
            'saldo_neto': float(self.saldo_neto),
            'total_transacciones': self.total_transacciones,
            'rentabilidad': self.rentabilidad,
            'ubicacion': self.ubicacion
        }