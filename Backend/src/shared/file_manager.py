"""
File Manager - Gestiona archivos del workspace de la IA
"""

import os
import json
import yaml
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union


class WorkspaceFileManager:
    """
    Gestiona la creación, lectura y organización de archivos en el workspace
    """
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.supported_formats = {
            'json': self._save_json,
            'yaml': self._save_yaml,
            'yml': self._save_yaml,
            'csv': self._save_csv,
            'txt': self._save_text,
            'md': self._save_text,
            'py': self._save_text,
            'js': self._save_text,
            'ts': self._save_text
        }
        
        # Crear directorio raíz si no existe
        self.workspace_root.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, 
                  content: Any, 
                  filename: str, 
                  directory: str = "generated") -> Path:
        """
        Guarda un archivo en el workspace
        
        Args:
            content: Contenido a guardar
            filename: Nombre del archivo
            directory: Subdirectorio dentro del workspace
        
        Returns:
            Path del archivo guardado
        """
        # Crear directorio si no existe
        target_dir = self.workspace_root / directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = target_dir / filename
        file_extension = filename.split('.')[-1].lower() if '.' in filename else 'txt'
        
        # Determinar el método de guardado basado en la extensión
        save_method = self.supported_formats.get(file_extension, self._save_text)
        
        try:
            save_method(content, file_path)
            
            # Crear metadata del archivo
            self._create_file_metadata(file_path, content, file_extension)
            
            return file_path
        except Exception as e:
            raise Exception(f"Error guardando archivo {filename}: {str(e)}")
    
    def read_file(self, file_path: Union[str, Path]) -> Any:
        """
        Lee un archivo del workspace
        
        Args:
            file_path: Ruta del archivo a leer
        
        Returns:
            Contenido del archivo
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        file_extension = file_path.suffix.lower().lstrip('.')
        
        try:
            if file_extension == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif file_extension in ['yaml', 'yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            elif file_extension == 'csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return list(csv.DictReader(f))
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            raise Exception(f"Error leyendo archivo {file_path}: {str(e)}")
    
    def list_files(self, 
                   directory: str = None, 
                   file_type: str = None,
                   include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Lista archivos en el workspace
        
        Args:
            directory: Subdirectorio específico (opcional)
            file_type: Filtrar por tipo de archivo (opcional)
            include_metadata: Incluir metadata de archivos
        
        Returns:
            Lista de archivos con información
        """
        search_path = self.workspace_root
        if directory:
            search_path = search_path / directory
            
        if not search_path.exists():
            return []
        
        files = []
        for file_path in search_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                
                # Filtrar por tipo si se especifica
                if file_type:
                    if not file_path.suffix.lower().lstrip('.') == file_type.lower():
                        continue
                
                file_info = {
                    "name": file_path.name,
                    "path": str(file_path.relative_to(self.workspace_root)),
                    "full_path": str(file_path),
                    "size": file_path.stat().st_size,
                    "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "extension": file_path.suffix.lower().lstrip('.')
                }
                
                # Incluir metadata si está disponible y se solicita
                if include_metadata:
                    metadata_path = file_path.with_suffix(f"{file_path.suffix}.meta")
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                file_info["metadata"] = json.load(f)
                        except Exception:
                            pass
                
                files.append(file_info)
        
        return sorted(files, key=lambda x: x["modified"], reverse=True)
    
    def delete_file(self, file_path: Union[str, Path]) -> bool:
        """
        Elimina un archivo del workspace
        
        Args:
            file_path: Ruta del archivo a eliminar
        
        Returns:
            True si se eliminó exitosamente
        """
        file_path = Path(file_path)
        
        try:
            if file_path.exists():
                file_path.unlink()
                
                # Eliminar metadata asociada
                metadata_path = file_path.with_suffix(f"{file_path.suffix}.meta")
                if metadata_path.exists():
                    metadata_path.unlink()
                
                return True
            return False
        except Exception as e:
            raise Exception(f"Error eliminando archivo {file_path}: {str(e)}")
    
    def get_workspace_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del workspace
        
        Returns:
            Estadísticas del workspace
        """
        stats = {
            "total_files": 0,
            "total_size": 0,
            "directories": {},
            "file_types": {},
            "last_activity": None
        }
        
        if not self.workspace_root.exists():
            return stats
        
        latest_modification = 0
        
        for file_path in self.workspace_root.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                file_size = file_path.stat().st_size
                file_ext = file_path.suffix.lower().lstrip('.')
                dir_name = file_path.parent.name
                mod_time = file_path.stat().st_mtime
                
                stats["total_files"] += 1
                stats["total_size"] += file_size
                
                # Actualizar última actividad
                if mod_time > latest_modification:
                    latest_modification = mod_time
                
                # Estadísticas por directorio
                if dir_name not in stats["directories"]:
                    stats["directories"][dir_name] = {"count": 0, "size": 0}
                stats["directories"][dir_name]["count"] += 1
                stats["directories"][dir_name]["size"] += file_size
                
                # Estadísticas por tipo de archivo
                if file_ext not in stats["file_types"]:
                    stats["file_types"][file_ext] = {"count": 0, "size": 0}
                stats["file_types"][file_ext]["count"] += 1
                stats["file_types"][file_ext]["size"] += file_size
        
        if latest_modification > 0:
            stats["last_activity"] = datetime.fromtimestamp(latest_modification).isoformat()
        
        # Convertir tamaños a formato legible
        stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
        
        return stats
    
    def _save_json(self, content: Any, file_path: Path):
        """Guarda contenido como JSON"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False, default=str)
    
    def _save_yaml(self, content: Any, file_path: Path):
        """Guarda contenido como YAML"""
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
    
    def _save_csv(self, content: Any, file_path: Path):
        """Guarda contenido como CSV"""
        if isinstance(content, list) and len(content) > 0:
            fieldnames = content[0].keys() if isinstance(content[0], dict) else range(len(content[0]))
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(content)
        else:
            raise ValueError("Contenido CSV debe ser una lista no vacía")
    
    def _save_text(self, content: Any, file_path: Path):
        """Guarda contenido como texto"""
        text_content = content if isinstance(content, str) else str(content)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
    
    def _create_file_metadata(self, file_path: Path, content: Any, file_extension: str):
        """Crea metadata para un archivo"""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "file_hash": self._calculate_file_hash(file_path),
            "content_type": file_extension,
            "size": file_path.stat().st_size,
            "encoding": "utf-8"
        }
        
        # Agregar información específica del contenido
        if isinstance(content, dict) and "metadata" in content:
            metadata.update(content["metadata"])
        
        metadata_path = file_path.with_suffix(f"{file_path.suffix}.meta")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcula hash MD5 del archivo"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()