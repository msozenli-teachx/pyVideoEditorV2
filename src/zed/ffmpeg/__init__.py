"""
Zed FFmpeg Module

Core FFmpeg management engine for video editing operations.
Provides command building, process management, and execution.
"""

from .engine import FFmpegEngine
from .command import (
    FFmpegCommand,
    FFmpegCommandBuilder,
    VideoCodec,
    AudioCodec,
)
from .process import (
    FFmpegProcess,
    FFmpegProcessPool,
    ProcessResult,
    ProcessStatus,
    ProcessInfo,
)

__all__ = [
    'FFmpegEngine',
    'FFmpegCommand',
    'FFmpegCommandBuilder',
    'VideoCodec',
    'AudioCodec',
    'FFmpegProcess',
    'FFmpegProcessPool',
    'ProcessResult',
    'ProcessStatus',
    'ProcessInfo',
]
