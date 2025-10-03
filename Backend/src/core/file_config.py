"""
Configuración centralizada para manejo de archivos de datos.
Proporciona gestión automática de rutas y selección inteligente de archivos.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FileConfig:
    """Configuración centralizada para archivos de datos."""
    
    def __init__(self, base_data_dir: Optional[str] = None):
        """
        Inicializa la configuración de archivos.
        
        Args:
            base_data_dir: Directorio base para datos. Si es None, usa ./data
        """
        if base_data_dir:
            self.data_dir = Path(base_data_dir)
        else:
            # Directorio de datos en Backend/ia_workspace/data
            # Desde Backend/src/core/file_config.py subimos 2 niveles a Backend/
            backend_root = Path(__file__).resolve().parents[2]
            self.data_dir = Path(os.environ.get("CAPI_DATA_DIR", "/tmp/capi_data"))
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Patrones de archivos soportados (más flexibles para detectar variaciones)
        self.supported_patterns = {
            "atm": ["atm", "ATM"],  # Detecta ATM-DENOM, ATM_, etc.
            "tesoro": ["tesoro", "TESORO"],  # Detecta TESORO-DENOM, etc.
            "cateodar": ["cateodar", "CATEODAR"],  # Detecta cateodar-D, etc.
            "processed": ["processed", "PROCESSED"],
            "movimientos": ["movimientos", "MOVIMIENTOS"]
        }
        
        # Prioridades por tipo (mayor número = mayor prioridad)
        self.type_priority = {
            "atm": 5,
            "tesoro": 4,
            "cateodar": 3,
            "processed": 2,
            "movimientos": 1
        }
        
    def get_available_files(self) -> List[Dict[str, any]]:
        """
        Obtiene lista de archivos CSV disponibles con metadatos.
        
        Returns:
            Lista de diccionarios con información de archivos
        """
        files = []
        
        # Buscar archivos CSV y CSV.BAK
        csv_patterns = ["*.csv", "*.csv.bak"]
        for pattern in csv_patterns:
            for csv_file in self.data_dir.glob(pattern):
                    try:
                        stat = csv_file.stat()
                        file_info = {
                            "name": csv_file.name,
                            "path": str(csv_file),
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime),
                            "modified_timestamp": stat.st_mtime,
                            "type": self._classify_file(csv_file.name),
                            "priority": self._get_file_priority(csv_file.name)
                        }
                        files.append(file_info)
                    except Exception as e:
                        logger.warning(f"Error al procesar archivo {csv_file}: {e}")
                
        # Ordenar por prioridad y fecha de modificación
        files.sort(key=lambda x: (x["priority"], x["modified_timestamp"]), reverse=True)
        return files
        
    def get_default_file(self) -> Optional[str]:
        """
        Obtiene el archivo por defecto para procesamiento.
        
        Returns:
            Ruta del archivo por defecto o None si no hay archivos
        """
        available = self.get_available_files()
        if available:
            return available[0]["path"]
        return None
        
    def get_file_by_type(self, file_type: str) -> Optional[str]:
        """
        Obtiene archivo por tipo específico.
        
        Args:
            file_type: Tipo de archivo (atm, tesoro, etc.)
            
        Returns:
            Ruta del archivo del tipo especificado o None
        """
        available = self.get_available_files()
        for file_info in available:
            if file_info["type"] == file_type.lower():
                return file_info["path"]
        return None
        
    def get_most_recent(self) -> Optional[str]:
        """
        Obtiene el archivo más recientemente modificado.
        
        Returns:
            Ruta del archivo más reciente o None
        """
        csv_files = list(self.data_dir.glob("*.csv"))
        if not csv_files:
            return None
            
        most_recent = max(csv_files, key=lambda p: p.stat().st_mtime)
        return str(most_recent)
        
    def _classify_file(self, filename: str) -> str:
        """
        Clasifica un archivo según su nombre.
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Tipo clasificado del archivo
        """
        # Remover .bak del final para clasificación correcta
        filename_for_classification = filename.lower()
        if filename_for_classification.endswith('.bak'):
            filename_for_classification = filename_for_classification[:-4]  # Remover ".bak"
        
        for file_type, patterns in self.supported_patterns.items():
            for pattern in patterns:
                # Buscar patrón en el nombre del archivo
                if pattern.lower() in filename_for_classification:
                    return file_type
                    
        return "unknown"
        
    def _get_file_priority(self, filename: str) -> int:
        """
        Obtiene la prioridad de un archivo según su tipo.
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Prioridad numérica del archivo
        """
        file_type = self._classify_file(filename)
        return self.type_priority.get(file_type, 0)
        
    def validate_file(self, file_path: str) -> bool:
        """
        Valida que un archivo existe y es accesible.
        
        Args:
            file_path: Ruta del archivo a validar
            
        Returns:
            True si el archivo es válido
        """
        try:
            path = Path(file_path)
            return path.exists() and path.is_file() and path.suffix.lower() == ".csv"
        except Exception:
            return False


# Instancia global de configuración
file_config = FileConfig()


def get_default_data_file() -> Optional[str]:
    """Función de conveniencia para obtener archivo por defecto."""
    return file_config.get_default_file()


def get_available_data_files() -> List[Dict[str, any]]:
    """Función de conveniencia para obtener archivos disponibles."""
    return file_config.get_available_files()


def get_data_file_by_type(file_type: str) -> Optional[str]:
    """Función de conveniencia para obtener archivo por tipo."""
    return file_config.get_file_by_type(file_type)