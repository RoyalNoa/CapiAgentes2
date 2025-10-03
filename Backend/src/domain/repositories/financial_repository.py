"""Repository interfaces for financial data."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..entities.financial_record import FinancialRecord, Anomaly, BranchSummary


class FinancialRecordRepository(ABC):
    """Abstract repository for financial records."""
    
    @abstractmethod
    async def save(self, record: FinancialRecord) -> bool:
        """Save a financial record."""
        pass
    
    @abstractmethod
    async def save_many(self, records: List[FinancialRecord]) -> bool:
        """Save multiple financial records."""
        pass
    
    @abstractmethod
    async def find_by_id(self, record_id: str) -> Optional[FinancialRecord]:
        """Find a record by ID."""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[FinancialRecord]:
        """Get all financial records."""
        pass
    
    @abstractmethod
    async def find_by_branch(self, branch_id: int) -> List[FinancialRecord]:
        """Find records by branch."""
        pass
    
    @abstractmethod
    async def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[FinancialRecord]:
        """Find records within date range."""
        pass
    
    @abstractmethod
    async def find_by_transaction_type(self, transaction_type: str) -> List[FinancialRecord]:
        """Find records by transaction type."""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get total count of records."""
        pass
    
    @abstractmethod
    async def delete_all(self) -> bool:
        """Delete all records."""
        pass


class AnomalyRepository(ABC):
    """Abstract repository for anomalies."""
    
    @abstractmethod
    async def save(self, anomaly: Anomaly) -> bool:
        """Save an anomaly."""
        pass
    
    @abstractmethod
    async def save_many(self, anomalies: List[Anomaly]) -> bool:
        """Save multiple anomalies."""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[Anomaly]:
        """Get all anomalies."""
        pass
    
    @abstractmethod
    async def find_by_severity(self, severity: str) -> List[Anomaly]:
        """Find anomalies by severity."""
        pass
    
    @abstractmethod
    async def find_by_type(self, anomaly_type: str) -> List[Anomaly]:
        """Find anomalies by type."""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get total count of anomalies."""
        pass


class BranchRepository(ABC):
    """Abstract repository for branch summaries."""
    
    @abstractmethod
    async def save(self, branch_summary: BranchSummary) -> bool:
        """Save branch summary."""
        pass
    
    @abstractmethod
    async def find_by_id(self, branch_id: int) -> Optional[BranchSummary]:
        """Find branch summary by ID."""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[BranchSummary]:
        """Get all branch summaries."""
        pass
    
    @abstractmethod
    async def generate_summary(self, records: List[FinancialRecord]) -> List[BranchSummary]:
        """Generate branch summaries from records."""
        pass


class DataFileRepository(ABC):
    """Abstract repository for data file operations."""
    
    @abstractmethod
    async def load_from_file(self, file_path: str) -> List[FinancialRecord]:
        """Load financial records from file."""
        pass
    
    @abstractmethod
    async def save_to_file(self, records: List[FinancialRecord], file_path: str) -> bool:
        """Save records to file."""
        pass
    
    @abstractmethod
    async def get_available_files(self) -> List[Dict[str, Any]]:
        """Get list of available data files."""
        pass
    
    @abstractmethod
    async def get_default_file(self) -> Optional[str]:
        """Get default data file path."""
        pass
    
    @abstractmethod
    async def validate_file(self, file_path: str) -> bool:
        """Validate if file exists and is readable."""
        pass