"""
Centralized Task Manager Module

Manages concurrent media operations across the application.
Provides task queuing, execution, monitoring, and lifecycle management.
"""

import uuid
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from datetime import datetime

from ..logging import get_logger
from ..config import get_config, TaskManagerConfig
from ..ffmpeg import FFmpegEngine, ProcessResult


class TaskStatus(str, Enum):
    """Status of a managed task."""
    PENDING = 'pending'
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class TaskResult:
    """Result of a completed task."""
    
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class Task:
    """
    Represents a managed task in the system.
    
    Tasks are units of work that can be queued, executed,
    monitored, and cancelled.
    """
    
    task_id: str
    name: str
    func: Callable[..., Any]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    result: Optional[TaskResult] = None
    future: Optional[Future] = field(default=None, repr=False)
    
    # Callbacks
    on_complete: Optional[Callable[['Task'], None]] = field(default=None, repr=False)
    on_error: Optional[Callable[['Task', Exception], None]] = field(default=None, repr=False)
    on_progress: Optional[Callable[['Task', float], None]] = field(default=None, repr=False)
    
    @property
    def duration(self) -> float:
        """Get task duration in seconds."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()
    
    def __lt__(self, other: 'Task') -> bool:
        """Compare tasks by priority for sorting."""
        return self.priority.value > other.priority.value  # Higher priority first


class TaskManager:
    """
    Centralized manager for concurrent media operations.
    
    Features:
    - Thread pool based execution
    - Priority-based task queuing
    - Task monitoring and status tracking
    - Cancellation support
    - Callbacks for lifecycle events
    - Integration with FFmpeg engine
    
    This is the main coordinator for all background operations.
    """
    
    def __init__(self, config: Optional[TaskManagerConfig] = None):
        """
        Initialize the task manager.
        
        Args:
            config: Optional task manager configuration
        """
        self._config = config or get_config().tasks
        self._logger = get_logger('tasks.manager')
        
        self._executor = ThreadPoolExecutor(
            max_workers=self._config.max_concurrent_tasks,
            thread_name_prefix='zed_task_'
        )
        
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()
        
        # FFmpeg engine for media operations
        self._ffmpeg_engine: Optional[FFmpegEngine] = None
        
        self._logger.info(
            f"TaskManager initialized with {self._config.max_concurrent_tasks} workers"
        )
    
    @property
    def ffmpeg(self) -> FFmpegEngine:
        """Get or create the FFmpeg engine."""
        if self._ffmpeg_engine is None:
            self._ffmpeg_engine = FFmpegEngine()
        return self._ffmpeg_engine
    
    def submit(
        self,
        func: Callable[..., Any],
        *args,
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        on_complete: Optional[Callable[[Task], None]] = None,
        on_error: Optional[Callable[[Task, Exception], None]] = None,
        **kwargs
    ) -> str:
        """
        Submit a task for execution.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            name: Optional task name
            priority: Task priority
            on_complete: Callback on successful completion
            on_error: Callback on error
            **kwargs: Keyword arguments for the function
        
        Returns:
            Task ID
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task_name = name or f"Task {task_id}"
        
        task = Task(
            task_id=task_id,
            name=task_name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            on_complete=on_complete,
            on_error=on_error,
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        # Submit to executor
        future = self._executor.submit(self._run_task, task)
        task.future = future
        task.status = TaskStatus.QUEUED
        
        self._logger.debug(f"Task submitted: {task_id} ({task_name})")
        
        return task_id
    
    def submit_media_operation(
        self,
        operation_func: Callable[..., ProcessResult],
        *args,
        name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Submit a media operation (FFmpeg-based task).
        
        Args:
            operation_func: Media operation function
            *args: Arguments for the operation
            name: Optional task name
            **kwargs: Keyword arguments
        
        Returns:
            Task ID
        """
        return self.submit(
            operation_func,
            *args,
            name=name or "Media Operation",
            priority=TaskPriority.NORMAL,
            **kwargs
        )
    
    def _run_task(self, task: Task) -> Any:
        """Internal method to run a task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        self._logger.info(f"Task started: {task.task_id} ({task.name})")
        
        try:
            result = task.func(*task.args, **task.kwargs)
            
            task.result = TaskResult(
                success=True,
                data=result,
                duration=task.duration,
            )
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            self._logger.info(
                f"Task completed: {task.task_id} in {task.duration:.2f}s"
            )
            
            if task.on_complete:
                try:
                    task.on_complete(task)
                except Exception as e:
                    self._logger.error(f"on_complete callback error: {e}")
            
            return result
            
        except Exception as e:
            task.result = TaskResult(
                success=False,
                error=str(e),
                duration=task.duration,
            )
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            self._logger.error(f"Task failed: {task.task_id} - {e}")
            
            if task.on_error:
                try:
                    task.on_error(task, e)
                except Exception as cb_error:
                    self._logger.error(f"on_error callback error: {cb_error}")
            
            raise
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        with self._lock:
            return list(self._tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks filtered by status."""
        with self._lock:
            return [t for t in self._tasks.values() if t.status == status]
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
        
        Returns:
            True if cancelled, False otherwise
        """
        with self._lock:
            task = self._tasks.get(task_id)
        
        if task is None:
            return False
        
        if task.future and not task.future.done():
            cancelled = task.future.cancel()
            if cancelled:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                self._logger.info(f"Task cancelled: {task_id}")
                return True
        
        return False
    
    def cancel_all(self) -> int:
        """
        Cancel all pending/queued tasks.
        
        Returns:
            Number of tasks cancelled
        """
        count = 0
        for task in self.get_tasks_by_status(TaskStatus.PENDING):
            if self.cancel(task.task_id):
                count += 1
        for task in self.get_tasks_by_status(TaskStatus.QUEUED):
            if self.cancel(task.task_id):
                count += 1
        return count
    
    def wait(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """
        Wait for a specific task to complete.
        
        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait
        
        Returns:
            TaskResult if completed, None if timeout
        """
        with self._lock:
            task = self._tasks.get(task_id)
        
        if task is None or task.future is None:
            return None
        
        try:
            task.future.result(timeout=timeout)
            return task.result
        except Exception:
            return task.result
    
    def wait_all(self, timeout: Optional[float] = None) -> List[TaskResult]:
        """
        Wait for all tasks to complete.
        
        Args:
            timeout: Maximum time to wait per task
        
        Returns:
            List of TaskResults
        """
        results = []
        for task in self.get_all_tasks():
            if task.future:
                try:
                    task.future.result(timeout=timeout)
                except Exception:
                    pass
                if task.result:
                    results.append(task.result)
        return results
    
    def shutdown(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        """
        Shutdown the task manager.
        
        Args:
            wait: Whether to wait for running tasks
            timeout: Maximum time to wait
        """
        self._logger.info("Shutting down TaskManager...")
        
        if wait:
            self.wait_all(timeout=timeout)
        
        self._executor.shutdown(wait=wait)
        self._logger.info("TaskManager shutdown complete")
    
    def get_stats(self) -> Dict[str, int]:
        """Get task statistics."""
        with self._lock:
            stats = {
                'total': len(self._tasks),
                'pending': 0,
                'queued': 0,
                'running': 0,
                'completed': 0,
                'failed': 0,
                'cancelled': 0,
            }
            for task in self._tasks.values():
                if task.status.value in stats:
                    stats[task.status.value] += 1
            return stats
