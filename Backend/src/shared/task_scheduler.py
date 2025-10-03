"""
Task Scheduler - Sistema de programación de tareas para la IA
"""

import os
import json
import uuid
import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
import time
from collections import defaultdict
import logging


class TaskStatus(Enum):
    """Estados posibles de una tarea"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class TaskPriority(Enum):
    """Prioridades de tarea"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class Task:
    """Representa una tarea individual"""
    
    def __init__(self, 
                 task_id: str,
                 name: str,
                 function: Callable,
                 args: tuple = (),
                 kwargs: dict = None,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 scheduled_time: datetime = None,
                 max_retries: int = 3,
                 timeout: int = 300,
                 metadata: Dict[str, Any] = None):
        
        self.task_id = task_id
        self.name = name
        self.function = function
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.scheduled_time = scheduled_time or datetime.now()
        self.max_retries = max_retries
        self.timeout = timeout
        self.metadata = metadata or {}
        
        # Estado de ejecución
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.result = None
        self.retry_count = 0
        self.execution_time = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la tarea a diccionario para serialización"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "priority": self.priority.value,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


class TaskScheduler:
    """
    Programador de tareas que puede ejecutar funciones de forma asíncrona
    """
    
    def __init__(self, workspace_root: Path, max_concurrent_tasks: int = 5):
        self.workspace_root = Path(workspace_root)
        self.tasks_dir = self.workspace_root / "tasks"
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # Cola de tareas y estado
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        
        # Control de ejecución
        self.is_running = False
        self.scheduler_thread = None
        self.lock = threading.Lock()
        
        # Configurar logging
        self.logger = logging.getLogger(__name__)
        
        # Crear directorios necesarios
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar tareas persistentes
        self._load_persistent_tasks()
    
    def schedule_task(self, 
                     name: str,
                     function: Callable,
                     args: tuple = (),
                     kwargs: dict = None,
                     priority: TaskPriority = TaskPriority.NORMAL,
                     scheduled_time: datetime = None,
                     max_retries: int = 3,
                     timeout: int = 300,
                     persist: bool = False,
                     metadata: Dict[str, Any] = None) -> str:
        """
        Programa una nueva tarea
        
        Args:
            name: Nombre de la tarea
            function: Función a ejecutar
            args: Argumentos posicionales
            kwargs: Argumentos con nombre
            priority: Prioridad de la tarea
            scheduled_time: Tiempo programado (por defecto: ahora)
            max_retries: Máximo número de reintentos
            timeout: Timeout en segundos
            persist: Si guardar la tarea en disco
            metadata: Metadata adicional
        
        Returns:
            ID de la tarea programada
        """
        task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            name=name,
            function=function,
            args=args,
            kwargs=kwargs,
            priority=priority,
            scheduled_time=scheduled_time,
            max_retries=max_retries,
            timeout=timeout,
            metadata=metadata
        )
        
        with self.lock:
            self.tasks[task_id] = task
            
            if persist:
                self._save_task_to_disk(task)
        
        self.logger.info(f"Tarea programada: {name} (ID: {task_id})")
        return task_id
    
    def schedule_recurring_task(self,
                              name: str,
                              function: Callable,
                              interval_minutes: int,
                              args: tuple = (),
                              kwargs: dict = None,
                              max_executions: int = None,
                              start_time: datetime = None) -> str:
        """
        Programa una tarea recurrente
        
        Args:
            name: Nombre de la tarea
            function: Función a ejecutar
            interval_minutes: Intervalo en minutos entre ejecuciones
            args: Argumentos posicionales
            kwargs: Argumentos con nombre
            max_executions: Máximo número de ejecuciones (None = infinito)
            start_time: Tiempo de inicio (por defecto: ahora)
        
        Returns:
            ID de la tarea recurrente base
        """
        if not start_time:
            start_time = datetime.now()
        
        def recurring_wrapper(*wrapper_args, **wrapper_kwargs):
            """Wrapper que re-programa la tarea"""
            try:
                result = function(*wrapper_args, **wrapper_kwargs)
                
                # Re-programar siguiente ejecución si no se ha alcanzado el límite
                executions = wrapper_kwargs.get('_execution_count', 1)
                if not max_executions or executions < max_executions:
                    next_time = datetime.now() + timedelta(minutes=interval_minutes)
                    next_kwargs = wrapper_kwargs.copy()
                    next_kwargs['_execution_count'] = executions + 1
                    
                    self.schedule_task(
                        name=f"{name} (ejecución {executions + 1})",
                        function=recurring_wrapper,
                        args=wrapper_args,
                        kwargs=next_kwargs,
                        scheduled_time=next_time,
                        metadata={"recurring": True, "execution": executions + 1}
                    )
                
                return result
            except Exception as e:
                self.logger.error(f"Error en tarea recurrente {name}: {e}")
                raise
        
        # Programar primera ejecución
        initial_kwargs = (kwargs or {}).copy()
        initial_kwargs['_execution_count'] = 1
        
        return self.schedule_task(
            name=f"{name} (ejecución 1)",
            function=recurring_wrapper,
            args=args,
            kwargs=initial_kwargs,
            scheduled_time=start_time,
            metadata={"recurring": True, "execution": 1, "interval_minutes": interval_minutes}
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancela una tarea
        
        Args:
            task_id: ID de la tarea a cancelar
        
        Returns:
            True si se canceló exitosamente
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status == TaskStatus.RUNNING:
                # Intentar detener thread si está ejecutándose
                if task_id in self.running_tasks:
                    # Note: threading.Thread no tiene un método kill() seguro
                    # Marcar como cancelada y esperar que termine naturalmente
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now()
                    return True
            elif task.status in [TaskStatus.PENDING, TaskStatus.SCHEDULED]:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de una tarea
        
        Args:
            task_id: ID de la tarea
        
        Returns:
            Estado de la tarea o None si no existe
        """
        with self.lock:
            task = self.tasks.get(task_id)
            return task.to_dict() if task else None
    
    def list_tasks(self, 
                  status_filter: TaskStatus = None,
                  limit: int = 50) -> List[Dict[str, Any]]:
        """
        Lista las tareas programadas
        
        Args:
            status_filter: Filtrar por estado
            limit: Límite de resultados
        
        Returns:
            Lista de tareas
        """
        with self.lock:
            tasks = list(self.tasks.values())
            
            if status_filter:
                tasks = [task for task in tasks if task.status == status_filter]
            
            # Ordenar por prioridad y tiempo programado
            tasks.sort(key=lambda t: (-t.priority.value, t.scheduled_time))
            
            return [task.to_dict() for task in tasks[:limit]]
    
    def start_scheduler(self):
        """Inicia el scheduler de tareas"""
        if self.is_running:
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Task scheduler iniciado")
    
    def stop_scheduler(self):
        """Detiene el scheduler de tareas"""
        self.is_running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        # Esperar que terminen las tareas en ejecución
        for task_id, thread in list(self.running_tasks.items()):
            if thread.is_alive():
                thread.join(timeout=2)
        
        self.logger.info("Task scheduler detenido")
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del scheduler
        
        Returns:
            Estadísticas completas
        """
        with self.lock:
            stats = {
                "total_tasks": len(self.tasks),
                "running_tasks": len(self.running_tasks),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "is_running": self.is_running,
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "status_breakdown": defaultdict(int),
                "priority_breakdown": defaultdict(int),
                "recent_executions": [],
                "average_execution_time": 0
            }
            
            # Analizar tareas por estado y prioridad
            execution_times = []
            recent_tasks = []
            
            for task in self.tasks.values():
                stats["status_breakdown"][task.status.value] += 1
                stats["priority_breakdown"][task.priority.name] += 1
                
                if task.execution_time:
                    execution_times.append(task.execution_time)
                
                if task.completed_at:
                    completed_delta = datetime.now() - task.completed_at
                    if completed_delta.days < 1:  # Tareas del último día
                        recent_tasks.append({
                            "task_id": task.task_id,
                            "name": task.name,
                            "status": task.status.value,
                            "execution_time": task.execution_time,
                            "completed_at": task.completed_at.isoformat()
                        })
            
            # Calcular tiempo promedio de ejecución
            if execution_times:
                stats["average_execution_time"] = round(sum(execution_times) / len(execution_times), 2)
            
            # Tareas recientes ordenadas por tiempo de completado
            recent_tasks.sort(key=lambda x: x["completed_at"], reverse=True)
            stats["recent_executions"] = recent_tasks[:10]
            
            # Convertir defaultdict a dict normal
            stats["status_breakdown"] = dict(stats["status_breakdown"])
            stats["priority_breakdown"] = dict(stats["priority_breakdown"])
            
            return stats
    
    def _scheduler_loop(self):
        """Loop principal del scheduler"""
        while self.is_running:
            try:
                self._process_scheduled_tasks()
                self._cleanup_completed_tasks()
                time.sleep(1)  # Verificar cada segundo
            except Exception as e:
                self.logger.error(f"Error en scheduler loop: {e}")
                time.sleep(5)
    
    def _process_scheduled_tasks(self):
        """Procesa tareas programadas que estén listas para ejecutar"""
        now = datetime.now()
        
        with self.lock:
            # Encontrar tareas listas para ejecutar
            ready_tasks = [
                task for task in self.tasks.values()
                if (task.status in [TaskStatus.PENDING, TaskStatus.SCHEDULED] and 
                    task.scheduled_time <= now and
                    len(self.running_tasks) < self.max_concurrent_tasks)
            ]
            
            # Ordenar por prioridad
            ready_tasks.sort(key=lambda t: -t.priority.value)
            
            # Ejecutar tareas disponibles
            for task in ready_tasks:
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    break
                
                self._execute_task(task)
    
    def _execute_task(self, task: Task):
        """Ejecuta una tarea en un hilo separado"""
        def task_executor():
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            try:
                # Ejecutar función con timeout
                result = self._execute_with_timeout(
                    task.function, 
                    task.args, 
                    task.kwargs, 
                    task.timeout
                )
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.execution_time = (task.completed_at - task.started_at).total_seconds()
                
                with self.lock:
                    self.completed_tasks.append(task.task_id)
                
                self.logger.info(f"Tarea completada: {task.name} (ID: {task.task_id})")
                
            except Exception as e:
                task.error_message = str(e)
                task.completed_at = datetime.now()
                
                # Verificar si se debe reintentar
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    task.scheduled_time = datetime.now() + timedelta(minutes=2 ** task.retry_count)
                    self.logger.warning(f"Tarea falló, reintentando ({task.retry_count}/{task.max_retries}): {task.name}")
                else:
                    task.status = TaskStatus.FAILED
                    with self.lock:
                        self.failed_tasks.append(task.task_id)
                    self.logger.error(f"Tarea falló definitivamente: {task.name} - {e}")
            
            finally:
                with self.lock:
                    if task.task_id in self.running_tasks:
                        del self.running_tasks[task.task_id]
        
        # Iniciar hilo de ejecución
        thread = threading.Thread(target=task_executor, daemon=True)
        self.running_tasks[task.task_id] = thread
        thread.start()
    
    def _execute_with_timeout(self, function: Callable, args: tuple, kwargs: dict, timeout: int):
        """Ejecuta una función con timeout"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Tarea excedió el timeout de {timeout} segundos")
        
        # Configurar timeout (solo funciona en sistemas Unix)
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            result = function(*args, **kwargs)
            signal.alarm(0)  # Cancelar alarma
            return result
        except AttributeError:
            # En Windows, ejecutar sin timeout
            return function(*args, **kwargs)
    
    def _cleanup_completed_tasks(self):
        """Limpia tareas completadas antiguas"""
        cutoff_date = datetime.now() - timedelta(hours=24)
        
        with self.lock:
            tasks_to_remove = [
                task_id for task_id, task in self.tasks.items()
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and
                    task.completed_at and task.completed_at < cutoff_date)
            ]
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
                if task_id in self.completed_tasks:
                    self.completed_tasks.remove(task_id)
                if task_id in self.failed_tasks:
                    self.failed_tasks.remove(task_id)
    
    def _save_task_to_disk(self, task: Task):
        """Guarda una tarea en disco para persistencia"""
        task_file = self.tasks_dir / f"task_{task.task_id}.json"
        
        # No podemos serializar funciones, solo metadata
        task_data = {
            "task_id": task.task_id,
            "name": task.name,
            "priority": task.priority.value,
            "scheduled_time": task.scheduled_time.isoformat(),
            "max_retries": task.max_retries,
            "timeout": task.timeout,
            "metadata": task.metadata,
            "created_at": task.created_at.isoformat(),
            "persistent": True
        }
        
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
    
    def _load_persistent_tasks(self):
        """Carga tareas persistentes desde disco"""
        if not self.tasks_dir.exists():
            return
        
        for task_file in self.tasks_dir.glob("task_*.json"):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                
                # Solo cargar metadata, las funciones no se pueden restaurar
                self.logger.info(f"Tarea persistente encontrada: {task_data['name']} (no ejecutable tras reinicio)")
                
            except Exception as e:
                self.logger.error(f"Error cargando tarea persistente {task_file}: {e}")
                continue