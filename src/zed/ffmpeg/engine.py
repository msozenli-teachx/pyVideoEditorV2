"""
FFmpeg Engine Module

The core engine for managing FFmpeg operations in the Zed video editor.
Provides a high-level interface for executing FFmpeg commands,
managing processes, and handling results.
"""

import uuid
import subprocess
from pathlib import Path
from typing import Optional, Callable, List, Union
from threading import Lock

from ..config import get_config, FFmpegConfig
from ..logging import get_logger
from .command import FFmpegCommand, FFmpegCommandBuilder, VideoCodec, AudioCodec
from .process import FFmpegProcess, FFmpegProcessPool, ProcessResult, ProcessStatus


class FFmpegEngine:
    """
    Core FFmpeg engine for the Zed video editor.
    
    Provides:
    - Command building and execution
    - Process management (single and concurrent)
    - Result handling and callbacks
    - Integration with configuration
    
    This is the main interface for all FFmpeg operations.
    """
    
    def __init__(self, config: Optional[FFmpegConfig] = None):
        """
        Initialize the FFmpeg engine.
        
        Args:
            config: Optional FFmpeg configuration. Uses global config if None.
        """
        self._config = config or get_config().ffmpeg
        self._logger = get_logger('ffmpeg.engine')
        
        self._ffmpeg_path = self._config.resolve_ffmpeg_path()
        self._ffprobe_path = self._config.resolve_ffprobe_path()
        
        # Get max concurrent from task config
        task_config = get_config().tasks
        max_concurrent = task_config.max_concurrent_tasks
        
        self._process_pool = FFmpegProcessPool(max_concurrent=max_concurrent)
        
        self._processes: dict[str, FFmpegProcess] = {}
        self._lock = Lock()
        
        self._logger.info(f"FFmpegEngine initialized with ffmpeg: {self._ffmpeg_path}")
    
    @property
    def ffmpeg_path(self) -> str:
        """Get the FFmpeg executable path."""
        return self._ffmpeg_path
    
    @property
    def ffprobe_path(self) -> str:
        """Get the FFprobe executable path."""
        return self._ffprobe_path
    
    def create_command(self) -> FFmpegCommandBuilder:
        """
        Create a new command builder.
        
        Returns:
            FFmpegCommandBuilder instance pre-configured with engine settings
        """
        builder = FFmpegCommandBuilder(ffmpeg_path=self._ffmpeg_path)
        
        # Apply default settings from config
        if self._config.threads > 0:
            builder.threads(self._config.threads)
        
        return builder
    
    def execute(
        self,
        command: FFmpegCommand,
        process_id: Optional[str] = None,
        timeout: Optional[int] = None,
        wait: bool = True,
        on_complete: Optional[Callable[[ProcessResult], None]] = None,
        on_error: Optional[Callable[[ProcessResult], None]] = None,
    ) -> Union[ProcessResult, FFmpegProcess]:
        """
        Execute an FFmpeg command.
        
        Args:
            command: The FFmpeg command to execute
            process_id: Optional custom process ID
            timeout: Process timeout (uses config default if None)
            wait: If True, wait for completion; if False, return process handle
            on_complete: Callback for successful completion
            on_error: Callback for errors/failures
        
        Returns:
            ProcessResult if wait=True, FFmpegProcess handle if wait=False
        """
        # Generate process ID if not provided
        if process_id is None:
            process_id = f"ffmpeg_{uuid.uuid4().hex[:8]}"
        
        # Create process
        process = FFmpegProcess(
            command=command,
            process_id=process_id,
            timeout=timeout or self._config.process_timeout,
        )
        
        # Track process
        with self._lock:
            self._processes[process_id] = process
        self._process_pool.add_process(process)
        
        if wait:
            try:
                result = process.run(on_complete=on_complete, on_error=on_error)
                return result
            finally:
                # Cleanup
                with self._lock:
                    self._processes.pop(process_id, None)
                self._process_pool.remove_process(process_id)
        else:
            # Run in background thread
            import threading
            thread = threading.Thread(
                target=process.run,
                kwargs={'on_complete': on_complete, 'on_error': on_error}
            )
            thread.daemon = True
            thread.start()
            return process
    
    def execute_multiple(
        self,
        commands: List[FFmpegCommand],
        max_concurrent: Optional[int] = None,
        on_complete: Optional[Callable[[str, ProcessResult], None]] = None,
        on_error: Optional[Callable[[str, ProcessResult], None]] = None,
    ) -> List[ProcessResult]:
        """
        Execute multiple FFmpeg commands, potentially concurrently.
        
        Args:
            commands: List of FFmpeg commands to execute
            max_concurrent: Max concurrent processes (uses pool default if None)
            on_complete: Callback for each successful completion (receives process_id, result)
            on_error: Callback for each failure (receives process_id, result)
        
        Returns:
            List of ProcessResults in order of commands
        """
        import threading
        
        results: List[Optional[ProcessResult]] = [None] * len(commands)
        threads: List[threading.Thread] = []
        
        def run_command(index: int, command: FFmpegCommand):
            process_id = f"batch_{uuid.uuid4().hex[:8]}"
            
            def handle_complete(result: ProcessResult):
                results[index] = result
                if on_complete:
                    on_complete(process_id, result)
            
            def handle_error(result: ProcessResult):
                results[index] = result
                if on_error:
                    on_error(process_id, result)
            
            process = FFmpegProcess(
                command=command,
                process_id=process_id,
                timeout=self._config.process_timeout,
            )
            
            with self._lock:
                self._processes[process_id] = process
            self._process_pool.add_process(process)
            
            try:
                process.run(on_complete=handle_complete, on_error=handle_error)
            finally:
                with self._lock:
                    self._processes.pop(process_id, None)
                self._process_pool.remove_process(process_id)
        
        # Create and start threads
        for i, cmd in enumerate(commands):
            thread = threading.Thread(target=run_command, args=(i, cmd))
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        return [r for r in results if r is not None]
    
    def cancel(self, process_id: str) -> bool:
        """
        Cancel a running process.
        
        Args:
            process_id: ID of the process to cancel
        
        Returns:
            True if cancelled, False if not found or not running
        """
        with self._lock:
            process = self._processes.get(process_id)
        
        if process:
            return process.cancel()
        return False
    
    def cancel_all(self) -> int:
        """
        Cancel all running processes.
        
        Returns:
            Number of processes cancelled
        """
        return self._process_pool.cancel_all()
    
    def get_process(self, process_id: str) -> Optional[FFmpegProcess]:
        """Get a process by ID."""
        with self._lock:
            return self._processes.get(process_id)
    
    def get_all_processes(self) -> List[FFmpegProcess]:
        """Get all tracked processes."""
        with self._lock:
            return list(self._processes.values())
    
    def wait_all(self, timeout: Optional[float] = None) -> List[ProcessResult]:
        """
        Wait for all running processes to complete.
        
        Args:
            timeout: Maximum time to wait per process
        
        Returns:
            List of completed ProcessResults
        """
        return self._process_pool.wait_all(timeout=timeout)
    
    # Convenience methods for common operations
    
    def clip_video(
        self,
        input_file: Union[str, Path],
        output_file: Union[str, Path],
        start_time: float,
        duration: Optional[float] = None,
        end_time: Optional[float] = None,
        **kwargs
    ) -> ProcessResult:
        """
        Clip a video segment.
        
        Args:
            input_file: Input video file
            output_file: Output file path
            start_time: Start time in seconds
            duration: Duration in seconds (alternative to end_time)
            end_time: End time in seconds (alternative to duration)
            **kwargs: Additional options passed to command builder
        
        Returns:
            ProcessResult of the clipping operation
        """
        builder = self.create_command()
        builder.input(input_file).output(output_file)
        builder.start_time(start_time)
        
        if duration:
            builder.duration(duration)
        elif end_time:
            builder.end_time(end_time)
        
        # Apply any extra options
        if 'video_codec' in kwargs:
            builder.video_codec(kwargs['video_codec'])
        if 'audio_codec' in kwargs:
            builder.audio_codec(kwargs['audio_codec'])
        
        builder.description(f"Clip {input_file} from {start_time}s")
        
        command = builder.build()
        return self.execute(command)
    
    def probe(self, file_path: Union[str, Path]) -> dict:
        """
        Probe a media file for information using ffprobe.
        
        Args:
            file_path: Path to media file
        
        Returns:
            Dictionary with media information
        
        Raises:
            RuntimeError: If ffprobe fails
        """
        import json
        
        cmd = [
            self._ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path),
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffprobe timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse ffprobe output: {e}")
