"""
Configuration Module for Zed Video Editor

Provides centralized configuration management for the application.
Supports default settings with easy extensibility.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class FFmpegConfig:
    """Configuration for FFmpeg operations."""
    
    # Path to ffmpeg executable (auto-detected if None)
    ffmpeg_path: Optional[str] = None
    
    # Path to ffprobe executable (auto-detected if None)
    ffprobe_path: Optional[str] = None
    
    # Default output directory for processed files
    default_output_dir: Path = field(default_factory=lambda: Path.cwd() / 'output')
    
    # Timeout for FFmpeg processes (seconds), None for no timeout
    process_timeout: Optional[int] = None
    
    # Number of threads for FFmpeg operations (-threads flag)
    threads: int = 0  # 0 = auto
    
    # Default video codec for output
    default_video_codec: str = 'libx264'
    
    # Default audio codec for output
    default_audio_codec: str = 'aac'
    
    # Default video bitrate
    default_video_bitrate: str = '5M'
    
    # Default audio bitrate
    default_audio_bitrate: str = '128k'
    
    def resolve_ffmpeg_path(self) -> str:
        """Resolve FFmpeg executable path."""
        if self.ffmpeg_path:
            return self.ffmpeg_path
        # Try common locations or system PATH
        return 'ffmpeg'
    
    def resolve_ffprobe_path(self) -> str:
        """Resolve FFprobe executable path."""
        if self.ffprobe_path:
            return self.ffprobe_path
        return 'ffprobe'


@dataclass
class TaskManagerConfig:
    """Configuration for the task manager."""
    
    # Maximum number of concurrent tasks
    max_concurrent_tasks: int = 4
    
    # Default timeout for tasks (seconds)
    default_task_timeout: Optional[int] = None
    
    # Whether to wait for all tasks on shutdown
    wait_on_shutdown: bool = True
    
    # Shutdown timeout (seconds)
    shutdown_timeout: int = 30


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    
    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    level: str = 'INFO'
    
    # Enable console logging
    console_output: bool = True
    
    # Enable file logging
    file_output: bool = False
    
    # Log file path (if file_output is True)
    log_file: Optional[Path] = None
    
    # Log directory (alternative to specific file)
    log_dir: Optional[Path] = None


@dataclass
class ZedConfig:
    """Main configuration class for Zed Video Editor."""
    
    ffmpeg: FFmpegConfig = field(default_factory=FFmpegConfig)
    tasks: TaskManagerConfig = field(default_factory=TaskManagerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Application metadata
    app_name: str = 'Zed Video Editor'
    app_version: str = '0.1.0'
    
    # Base directory for the application
    base_dir: Path = field(default_factory=Path.cwd)
    
    def __post_init__(self):
        """Post-initialization setup."""
        # Ensure output directory exists
        self.ffmpeg.default_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up log file if log_dir is specified
        if self.logging.log_dir and not self.logging.log_file:
            self.logging.log_dir.mkdir(parents=True, exist_ok=True)
            self.logging.log_file = self.logging.log_dir / 'zed.log'
    
    @classmethod
    def from_env(cls) -> 'ZedConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Override from environment
        if ffmpeg_path := os.environ.get('ZED_FFMPEG_PATH'):
            config.ffmpeg.ffmpeg_path = ffmpeg_path
        if ffprobe_path := os.environ.get('ZED_FFPROBE_PATH'):
            config.ffmpeg.ffprobe_path = ffprobe_path
        if output_dir := os.environ.get('ZED_OUTPUT_DIR'):
            config.ffmpeg.default_output_dir = Path(output_dir)
        if max_tasks := os.environ.get('ZED_MAX_CONCURRENT_TASKS'):
            config.tasks.max_concurrent_tasks = int(max_tasks)
        if log_level := os.environ.get('ZED_LOG_LEVEL'):
            config.logging.level = log_level
        
        return config


# Global configuration instance
_config: Optional[ZedConfig] = None


def get_config() -> ZedConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = ZedConfig.from_env()
    return _config


def set_config(config: ZedConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
