"""File-based implementations of financial repositories."""
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import logging
from pathlib import Path

from ...domain.entities.financial_record import FinancialRecord, Anomaly, BranchSummary
from ...domain.repositories.financial_repository import (
    FinancialRecordRepository,
    AnomalyRepository,
    BranchRepository,
    DataFileRepository
)
from ...core.file_config import FileConfig

logger = logging.getLogger(__name__)


class InMemoryFinancialRecordRepository(FinancialRecordRepository):
    """In-memory implementation of FinancialRecordRepository."""
    
    def __init__(self):
        self._records: List[FinancialRecord] = []
        self._id_counter = 0
    
    async def save(self, record: FinancialRecord) -> bool:
        """Save a financial record."""
        try:
            self._records.append(record)
            return True
        except Exception as e:
            logger.error(f"Error saving record: {e}")
            return False
    
    async def save_many(self, records: List[FinancialRecord]) -> bool:
        """Save multiple financial records."""
        try:
            self._records.extend(records)
            return True
        except Exception as e:
            logger.error(f"Error saving multiple records: {e}")
            return False
    
    async def find_by_id(self, record_id: str) -> Optional[FinancialRecord]:
        """Find a record by ID."""
        try:
            index = int(record_id.replace('record_', ''))
            if 0 <= index < len(self._records):
                return self._records[index]
            return None
        except (ValueError, IndexError):
            return None
    
    async def find_all(self) -> List[FinancialRecord]:
        """Get all financial records."""
        return self._records.copy()
    
    async def find_by_branch(self, branch_id: int) -> List[FinancialRecord]:
        """Find records by branch."""
        return [
            record for record in self._records
            if record.numero_sucursal == branch_id
        ]
    
    async def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[FinancialRecord]:
        """Find records within date range."""
        return [
            record for record in self._records
            if start_date <= record.fecha <= end_date
        ]
    
    async def find_by_transaction_type(self, transaction_type: str) -> List[FinancialRecord]:
        """Find records by transaction type."""
        return [
            record for record in self._records
            if record.tipo_transaccion.lower() == transaction_type.lower()
        ]
    
    async def count(self) -> int:
        """Get total count of records."""
        return len(self._records)
    
    async def delete_all(self) -> bool:
        """Delete all records."""
        try:
            self._records.clear()
            return True
        except Exception as e:
            logger.error(f"Error deleting all records: {e}")
            return False


class InMemoryAnomalyRepository(AnomalyRepository):
    """In-memory implementation of AnomalyRepository."""
    
    def __init__(self):
        self._anomalies: List[Anomaly] = []
    
    async def save(self, anomaly: Anomaly) -> bool:
        """Save an anomaly."""
        try:
            self._anomalies.append(anomaly)
            return True
        except Exception as e:
            logger.error(f"Error saving anomaly: {e}")
            return False
    
    async def save_many(self, anomalies: List[Anomaly]) -> bool:
        """Save multiple anomalies."""
        try:
            self._anomalies.extend(anomalies)
            return True
        except Exception as e:
            logger.error(f"Error saving multiple anomalies: {e}")
            return False
    
    async def find_all(self) -> List[Anomaly]:
        """Get all anomalies."""
        return self._anomalies.copy()
    
    async def find_by_severity(self, severity: str) -> List[Anomaly]:
        """Find anomalies by severity."""
        return [
            anomaly for anomaly in self._anomalies
            if anomaly.severity == severity
        ]
    
    async def find_by_type(self, anomaly_type: str) -> List[Anomaly]:
        """Find anomalies by type."""
        return [
            anomaly for anomaly in self._anomalies
            if anomaly.anomaly_type == anomaly_type
        ]
    
    async def count(self) -> int:
        """Get total count of anomalies."""
        return len(self._anomalies)


class InMemoryBranchRepository(BranchRepository):
    """In-memory implementation of BranchRepository."""
    
    def __init__(self):
        self._branches: Dict[int, BranchSummary] = {}
    
    async def save(self, branch_summary: BranchSummary) -> bool:
        """Save branch summary."""
        try:
            self._branches[branch_summary.numero_sucursal] = branch_summary
            return True
        except Exception as e:
            logger.error(f"Error saving branch summary: {e}")
            return False
    
    async def find_by_id(self, branch_id: int) -> Optional[BranchSummary]:
        """Find branch summary by ID."""
        return self._branches.get(branch_id)
    
    async def find_all(self) -> List[BranchSummary]:
        """Get all branch summaries."""
        return list(self._branches.values())
    
    async def generate_summary(self, records: List[FinancialRecord]) -> List[BranchSummary]:
        """Generate branch summaries from records."""
        from ...domain.services.financial_service import FinancialAnalysisService
        return FinancialAnalysisService.calculate_branch_summary(records)


class FileDataRepository(DataFileRepository):
    """File-based implementation of DataFileRepository."""
    
    def __init__(self, file_config: Optional[FileConfig] = None):
        self.file_config = file_config or FileConfig()
    
    async def load_from_file(self, file_path: str) -> List[FinancialRecord]:
        """Load financial records from file."""
        try:
            logger.info(f"Loading data from file: {file_path}")
            
            # Read CSV file
            # Try multiple encodings to handle different file types
            df = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    logger.info(f"Successfully loaded with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                raise ValueError(f"Could not decode file {file_path} with any supported encoding")
            logger.info(f"Loaded {len(df)} rows from CSV")
            
            records = []
            for index, row in df.iterrows():
                try:
                    # Convert row to dictionary and create FinancialRecord
                    record_data = self._normalize_record_data(row.to_dict())
                    record = FinancialRecord.from_dict(record_data)
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Error processing row {index}: {e}")
                    continue
            
            logger.info(f"Successfully converted {len(records)} records")
            return records
            
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return []
    
    def _normalize_record_data(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize row data from CSV to FinancialRecord format."""
        # Handle different CSV column formats
        normalized = {}
        
        # Date handling
        if 'fecha' in row_data:
            normalized['fecha'] = row_data['fecha']
        elif 'date' in row_data:
            normalized['fecha'] = row_data['date']
        else:
            normalized['fecha'] = datetime.now().isoformat()
        
        # Amount handling
        if 'monto' in row_data:
            normalized['monto'] = row_data['monto']
        elif 'amount' in row_data:
            normalized['monto'] = row_data['amount']
        else:
            normalized['monto'] = 0
        
        # Description
        if 'descripcion' in row_data:
            normalized['descripcion'] = row_data['descripcion']
        elif 'description' in row_data:
            normalized['descripcion'] = row_data['description']
        else:
            normalized['descripcion'] = ''
        
        # Category
        if 'categoria' in row_data:
            normalized['categoria'] = row_data['categoria']
        elif 'category' in row_data:
            normalized['categoria'] = row_data['category']
        else:
            normalized['categoria'] = ''
        
        # Branch
        if 'sucursal' in row_data:
            normalized['sucursal'] = row_data['sucursal']
        elif 'branch' in row_data:
            normalized['sucursal'] = row_data['branch']
        else:
            normalized['sucursal'] = ''
        
        # Transaction type
        if 'tipo_transaccion' in row_data:
            normalized['tipo_transaccion'] = row_data['tipo_transaccion']
        elif 'transaction_type' in row_data:
            normalized['tipo_transaccion'] = row_data['transaction_type']
        else:
            normalized['tipo_transaccion'] = ''
        
        # Branch number
        if 'numero_sucursal' in row_data or 'Numero de sucursal' in row_data:
            key = 'numero_sucursal' if 'numero_sucursal' in row_data else 'Numero de sucursal'
            try:
                normalized['numero_sucursal'] = int(row_data[key]) if pd.notna(row_data[key]) else None
            except (ValueError, TypeError):
                normalized['numero_sucursal'] = None
        
        # Income/Expense
        if 'Ingresos' in row_data:
            try:
                normalized['ingresos'] = float(row_data['Ingresos']) if pd.notna(row_data['Ingresos']) else None
            except (ValueError, TypeError):
                normalized['ingresos'] = None
        
        if 'Egresos' in row_data:
            try:
                normalized['egresos'] = float(row_data['Egresos']) if pd.notna(row_data['Egresos']) else None
            except (ValueError, TypeError):
                normalized['egresos'] = None
        
        # Location
        if 'Ubicacion' in row_data:
            normalized['ubicacion'] = row_data['Ubicacion'] if pd.notna(row_data['Ubicacion']) else None
        elif 'ubicacion' in row_data:
            normalized['ubicacion'] = row_data['ubicacion'] if pd.notna(row_data['ubicacion']) else None
        
        return normalized
    
    async def save_to_file(self, records: List[FinancialRecord], file_path: str) -> bool:
        """Save records to file."""
        try:
            # Convert records to DataFrame
            data = [record.to_dict() for record in records]
            df = pd.DataFrame(data)
            
            # Save to CSV
            df.to_csv(file_path, index=False)
            logger.info(f"Saved {len(records)} records to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to file {file_path}: {e}")
            return False
    
    async def get_available_files(self) -> List[Dict[str, Any]]:
        """Get list of available data files."""
        return self.file_config.get_available_files()
    
    async def get_default_file(self) -> Optional[str]:
        """Get default data file path."""
        return self.file_config.get_default_file()
    
    async def validate_file(self, file_path: str) -> bool:
        """Validate if file exists and is readable."""
        return self.file_config.validate_file(file_path)