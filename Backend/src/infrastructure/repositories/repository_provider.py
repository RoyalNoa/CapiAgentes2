"""
Repository Provider - Singleton para gestión de repositorios
"""

from typing import Optional
from threading import Lock

from src.domain.repositories.financial_repository import (
    FinancialRecordRepository,
    AnomalyRepository,
    BranchRepository,
    DataFileRepository
)
from src.infrastructure.repositories.file_financial_repository import (
    InMemoryFinancialRecordRepository,
    InMemoryAnomalyRepository,
    InMemoryBranchRepository,
    FileDataRepository
)


class RepositoryProvider:
    """
    Singleton provider para repositorios
    Gestiona instancias únicas de repositorios
    """
    
    _instance: Optional['RepositoryProvider'] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> 'RepositoryProvider':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize_repositories()
        return cls._instance
    
    def _initialize_repositories(self) -> None:
        """Inicializa los repositorios"""
        self._financial_repo: Optional[FinancialRecordRepository] = None
        self._anomaly_repo: Optional[AnomalyRepository] = None
        self._branch_repo: Optional[BranchRepository] = None
        self._data_file_repo: Optional[DataFileRepository] = None
    
    def get_financial_repository(self) -> FinancialRecordRepository:
        """
        Obtiene el repositorio de registros financieros
        
        Returns:
            Instancia de FinancialRecordRepository
        """
        if self._financial_repo is None:
            self._financial_repo = InMemoryFinancialRecordRepository()
        return self._financial_repo
    
    def get_anomaly_repository(self) -> AnomalyRepository:
        """
        Obtiene el repositorio de anomalías
        
        Returns:
            Instancia de AnomalyRepository
        """
        if self._anomaly_repo is None:
            self._anomaly_repo = InMemoryAnomalyRepository()
        return self._anomaly_repo
    
    def get_branch_repository(self) -> BranchRepository:
        """
        Obtiene el repositorio de sucursales
        
        Returns:
            Instancia de BranchRepository
        """
        if self._branch_repo is None:
            self._branch_repo = InMemoryBranchRepository()
        return self._branch_repo
    
    def get_data_file_repository(self) -> DataFileRepository:
        """
        Obtiene el repositorio de archivos de datos
        
        Returns:
            Instancia de DataFileRepository
        """
        if self._data_file_repo is None:
            self._data_file_repo = FileDataRepository()
        return self._data_file_repo
    
    def clear_all(self) -> None:
        """Limpia todas las instancias de repositorios"""
        self._financial_repo = None
        self._anomaly_repo = None
        self._branch_repo = None
        self._data_file_repo = None