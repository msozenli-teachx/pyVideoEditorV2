"""
FFmpeg Process Manager Module

Handles execution and management of FFmpeg subprocesses,
including concurrent process handling and result collection.
"""

import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Any, List
from enum import Enum
import time

from ..logging import get_logger
from .command import FFmpegCommand


class ProcessStatus(str, Enum):
    """Status of an FFmpeg process."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'


@dataclass
class ProcessResult:
    """
    Result of an FFmpeg process execution.
    
    Attributes:
        status: Final status of the process
        return_code: Process exit code
        stdout: Captured stdout
        stderr: Captured stderr (often contains FFmpeg progress/info)
        duration: Execution duration in seconds
        output_file: Path to output file if successful
        error_message: Error message if failed
    """
    
    status: ProcessStatus
    return_code: int = 0
    stdout: str = ''
    stderr: str = ''
    duration: float = 0.0
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if the process completed successfully."""
        return self.status == ProcessStatus.COMPLETED and self.return_code == 0


@dataclass
class ProcessInfo:
    """Information about a running or completed process."""
    
    process_id: str
    command: FFmpegCommand
    status: ProcessStatus = ProcessStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    pid: Optional[int] = None
    result: Optional[ProcessResult] = None
    
    @property
    def duration(self) -> float:
        """Get current or final duration."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time


class FFmpegProcess:
    """
    Manages a single FFmpeg subprocess.
    
    Provides control over process execution, cancellation,
    and result retrieval.
    """
    
    def __init__(
        self,
        command: FFmpegCommand,
        process_id: str,
        timeout: Optional[int] = None,
    ):
        """
        Initialize the FFmpeg process.
        
        Args:
            command: The FFmpeg command to execute
            process_id: Unique identifier for this process
            timeout: Process timeout in seconds
        """
        self.command = command
        self.process_id = process_id
        self.timeout = timeout
        
        self._logger = get_logger('ffmpeg.process')
        self._process: Optional[subprocess.Popen] = None
        self._info = ProcessInfo(
            process_id=process_id,
            command=command,
        )
        self._lock = threading.Lock()
        self._cancelled = False
    
    @property
    def info(self) -> ProcessInfo:
        """Get current process information."""
        with self._lock:
            return self._info
    
    def run(
        self,
        on_complete: Optional[Callable[[ProcessResult], None]] = None,
        on_error: Optional[Callable[[ProcessResult], None]] = None,
    ) -> ProcessResult:
        """
        Execute the FFmpeg command.
        
        Args:
            on_complete: Callback when process completes successfully
            on_error: Callback when process fails
        
        Returns:
            ProcessResult with execution details
        """
        with self._lock:
            if self._info.status != ProcessStatus.PENDING:
                return self._info.result or ProcessResult(
                    status=self._info.status,
                    error_message="Process already executed"
                )
            
            self._info.status = ProcessStatus.RUNNING
            self._info.start_time = time.time()
        
        self._logger.info(f"Starting FFmpeg process [{self.process_id}]: {self.command.description}")
        
        try:
            # Execute the command
            self._process = subprocess.Popen(
                self.command.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            
            with self._lock:
                self._info.pid = self._process.pid
            
            self._logger.debug(f"Process [{self.process_id}] started with PID {self._process.pid}")
            
            # Wait for completion with optional timeout
            try:
                stdout, stderr = self._process.communicate(timeout=self.timeout)
                return_code = self._process.returncode
                
                with self._lock:
                    self._info.end_time = time.time()
                
                if self._cancelled:
                    status = ProcessStatus.CANCELLED
                    error_message = "Process was cancelled"
                elif return_code == 0:
                    status = ProcessStatus.COMPLETED
                    error_message = None
                else:
                    status = ProcessStatus.FAILED
                    error_message = f"FFmpeg exited with code {return_code}"
                
                result = ProcessResult(
                    status=status,
                    return_code=return_code,
                    stdout=stdout,
                    stderr=stderr,
                    duration=self._info.duration,
                    output_file=self.command.output_file,
                    error_message=error_message,
                )
                
                with self._lock:
                    self._info.status = status
                    self._info.result = result
                
                if status == ProcessStatus.COMPLETED:
                    self._logger.info(
                        f"Process [{self.process_id}] completed in {result.duration:.2f}s"
                    )
                    if on_complete:
                        on_complete(result)
                else:
                    self._logger.error(
                        f"Process [{self.process_id}] failed: {error_message}"
                    )
                    self._logger.debug(f"FFmpeg stderr: {stderr}")
                    if on_error:
                        on_error(result)
                
                return result
                
            except subprocess.TimeoutExpired:
                self._logger.warning(f"Process [{self.process_id}] timed out")
                self._cancel()
                
                result = ProcessResult(
                    status=ProcessStatus.TIMEOUT,
                    return_code=-1,
                    duration=self._info.duration,
                    output_file=self.command.output_file,
                    error_message=f"Process timed out after {self.timeout}s",
                )
                
                with self._lock:
                    self._info.status = ProcessStatus.TIMEOUT
                    self._info.result = result
                    self._info.end_time = time.time()
                
                if on_error:
                    on_error(result)
                
                return result
                
        except Exception as e:
            self._logger.error(f"Process [{self.process_id}] error: {e}")
            
            result = ProcessResult(
                status=ProcessStatus.FAILED,
                return_code=-1,
                duration=self._info.duration,
                output_file=self.command.output_file,
                error_message=str(e),
            )
            
            with self._lock:
                self._info.status = ProcessStatus.FAILED
                self._info.result = result
                self._info.end_time = time.time()
            
            if on_error:
                on_error(result)
            
            return result
    
    def _cancel(self) -> None:
        """Cancel the running process."""
        self._cancelled = True
        if self._process and self._process.poll() is None:
            self._logger.debug(f"Terminating process [{self.process_id}]")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
    
    def cancel(self) -> bool:
        """
        Cancel the process if running.
        
        Returns:
            True if process was cancelled, False otherwise
        """
        with self._lock:
            if self._info.status != ProcessStatus.RUNNING:
                return False
            
            self._cancel()
            self._info.status = ProcessStatus.CANCELLED
            self._info.end_time = time.time()
            
            result = ProcessResult(
                status=ProcessStatus.CANCELLED,
                return_code=-1,
                duration=self._info.duration,
                error_message="Process was cancelled",
            )
            self._info.result = result
        
        self._logger.info(f"Process [{self.process_id}] cancelled")
        return True
    
    def wait(self, timeout: Optional[float] = None) -> Optional[ProcessResult]:
        """
        Wait for the process to complete.
        
        Args:
            timeout: Maximum time to wait
        
        Returns:
            ProcessResult if completed, None if still running
        """
        if self._process is None:
            return None
        
        try:
            self._process.wait(timeout=timeout)
            return self._info.result
        except subprocess.TimeoutExpired:
            return None


class FFmpegProcessPool:
    """
    Manages a pool of FFmpeg processes for concurrent execution.
    
    Provides thread-safe management of multiple concurrent
    FFmpeg processes with a configurable limit.
    """
    
    def __init__(self, max_concurrent: int = 4):
        """
        Initialize the process pool.
        
        Args:
            max_concurrent: Maximum number of concurrent processes
        """
        self.max_concurrent = max_concurrent
        self._logger = get_logger('ffmpeg.pool')
        self._processes: dict[str, FFmpegProcess] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_concurrent)
    
    def add_process(self, process: FFmpegProcess) -> None:
        """Add a process to the pool."""
        with self._lock:
            self._processes[process.process_id] = process
    
    def remove_process(self, process_id: str) -> Optional[FFmpegProcess]:
        """Remove and return a process from the pool."""
        with self._lock:
            return self._processes.pop(process_id, None)
    
    def get_process(self, process_id: str) -> Optional[FFmpegProcess]:
        """Get a process by ID."""
        with self._lock:
            return self._processes.get(process_id)
    
    def get_all_processes(self) -> List[FFmpegProcess]:
        """Get all processes."""
        with self._lock:
            return list(self._processes.values())
    
    def cancel_all(self) -> int:
        """
        Cancel all running processes.
        
        Returns:
            Number of processes cancelled
        """
        count = 0
        for process in self.get_all_processes():
            if process.cancel():
                count += 1
        return count
    
    def wait_all(self, timeout: Optional[float] = None) -> List[ProcessResult]:
        """
        Wait for all processes to complete.
        
        Args:
            timeout: Maximum time to wait for each process
        
        Returns:
            List of ProcessResults
        """
        results = []
        for process in self.get_all_processes():
            result = process.wait(timeout=timeout)
            if result:
                results.append(result)
        return results
    
    def acquire_slot(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a slot for running a new process.
        
        Args:
            timeout: Maximum time to wait for a slot
        
        Returns:
            True if slot acquired, False otherwise
        """
        return self._semaphore.acquire(timeout=timeout)
    
    def release_slot(self) -> None:
        """Release a process slot."""
        self._semaphore.release()
