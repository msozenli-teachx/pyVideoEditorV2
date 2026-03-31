"""
FFmpeg Command Builder Module

Provides a flexible command builder for constructing FFmpeg commands
with support for various operations and options.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from enum import Enum


class VideoCodec(str, Enum):
    """Common video codecs."""
    H264 = 'libx264'
    H265 = 'libx265'
    VP8 = 'libvpx'
    VP9 = 'libvpx-vp9'
    PRORES = 'prores_ks'
    COPY = 'copy'


class AudioCodec(str, Enum):
    """Common audio codecs."""
    AAC = 'aac'
    MP3 = 'libmp3lame'
    OPUS = 'libopus'
    VORBIS = 'libvorbis'
    COPY = 'copy'


@dataclass
class FFmpegCommand:
    """
    Represents a built FFmpeg command.
    
    Attributes:
        args: List of command arguments
        input_files: List of input file paths
        output_file: Output file path
        description: Human-readable description of the command
    """
    
    args: List[str] = field(default_factory=list)
    input_files: List[str] = field(default_factory=list)
    output_file: Optional[str] = None
    description: str = ''
    
    def to_shell_string(self) -> str:
        """Convert command to shell-executable string."""
        return ' '.join(self.args)
    
    def __repr__(self) -> str:
        return f'FFmpegCommand({self.description or "unnamed"})'


class FFmpegCommandBuilder:
    """
    Builder class for constructing FFmpeg commands.
    
    Provides a fluent interface for building complex FFmpeg commands
    with validation and sensible defaults.
    """
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        """
        Initialize the command builder.
        
        Args:
            ffmpeg_path: Path to FFmpeg executable
        """
        self._ffmpeg_path = ffmpeg_path
        self._input_files: List[str] = []
        self._output_file: Optional[str] = None
        self._video_codec: Optional[str] = None
        self._audio_codec: Optional[str] = None
        self._video_bitrate: Optional[str] = None
        self._audio_bitrate: Optional[str] = None
        self._start_time: Optional[float] = None
        self._duration: Optional[float] = None
        self._end_time: Optional[float] = None
        self._threads: int = 0
        self._extra_args: List[str] = []
        self._global_options: List[str] = ['-y']  # Overwrite by default
        self._description: str = ''
    
    def input(self, file_path: Union[str, Path]) -> 'FFmpegCommandBuilder':
        """
        Add an input file.
        
        Args:
            file_path: Path to input file
        
        Returns:
            Self for method chaining
        """
        self._input_files.append(str(file_path))
        return self
    
    def output(self, file_path: Union[str, Path]) -> 'FFmpegCommandBuilder':
        """
        Set the output file.
        
        Args:
            file_path: Path to output file
        
        Returns:
            Self for method chaining
        """
        self._output_file = str(file_path)
        return self
    
    def video_codec(self, codec: Union[VideoCodec, str]) -> 'FFmpegCommandBuilder':
        """
        Set the video codec.
        
        Args:
            codec: Video codec name or VideoCodec enum
        
        Returns:
            Self for method chaining
        """
        self._video_codec = str(codec)
        return self
    
    def audio_codec(self, codec: Union[AudioCodec, str]) -> 'FFmpegCommandBuilder':
        """
        Set the audio codec.
        
        Args:
            codec: Audio codec name or AudioCodec enum
        
        Returns:
            Self for method chaining
        """
        self._audio_codec = str(codec)
        return self
    
    def video_bitrate(self, bitrate: str) -> 'FFmpegCommandBuilder':
        """
        Set the video bitrate.
        
        Args:
            bitrate: Bitrate string (e.g., '5M', '1000k')
        
        Returns:
            Self for method chaining
        """
        self._video_bitrate = bitrate
        return self
    
    def audio_bitrate(self, bitrate: str) -> 'FFmpegCommandBuilder':
        """
        Set the audio bitrate.
        
        Args:
            bitrate: Bitrate string (e.g., '128k', '192k')
        
        Returns:
            Self for method chaining
        """
        self._audio_bitrate = bitrate
        return self
    
    def start_time(self, seconds: float) -> 'FFmpegCommandBuilder':
        """
        Set the start time for trimming.
        
        Args:
            seconds: Start time in seconds
        
        Returns:
            Self for method chaining
        """
        self._start_time = seconds
        return self
    
    def duration(self, seconds: float) -> 'FFmpegCommandBuilder':
        """
        Set the duration of the output.
        
        Args:
            seconds: Duration in seconds
        
        Returns:
            Self for method chaining
        """
        self._duration = seconds
        return self
    
    def end_time(self, seconds: float) -> 'FFmpegCommandBuilder':
        """
        Set the end time for trimming.
        
        Args:
            seconds: End time in seconds
        
        Returns:
            Self for method chaining
        """
        self._end_time = seconds
        return self
    
    def threads(self, count: int) -> 'FFmpegCommandBuilder':
        """
        Set the number of threads.
        
        Args:
            count: Number of threads (0 for auto)
        
        Returns:
            Self for method chaining
        """
        self._threads = count
        return self
    
    def extra(self, *args: str) -> 'FFmpegCommandBuilder':
        """
        Add extra FFmpeg arguments.
        
        Args:
            *args: Additional arguments
        
        Returns:
            Self for method chaining
        """
        self._extra_args.extend(args)
        return self
    
    def description(self, desc: str) -> 'FFmpegCommandBuilder':
        """
        Set a description for the command.
        
        Args:
            desc: Human-readable description
        
        Returns:
            Self for method chaining
        """
        self._description = desc
        return self
    
    def build(self) -> FFmpegCommand:
        """
        Build the FFmpeg command.
        
        Returns:
            FFmpegCommand object with the constructed command
        
        Raises:
            ValueError: If no input or output is specified
        """
        if not self._input_files:
            raise ValueError("At least one input file is required")
        if not self._output_file:
            raise ValueError("Output file is required")
        
        args = [self._ffmpeg_path]
        
        # Add global options
        args.extend(self._global_options)
        
        # Add threads
        if self._threads > 0:
            args.extend(['-threads', str(self._threads)])
        
        # Add input files
        for input_file in self._input_files:
            args.extend(['-i', input_file])
        
        # Add trim options
        if self._start_time is not None:
            args.extend(['-ss', str(self._start_time)])
        
        if self._duration is not None:
            args.extend(['-t', str(self._duration)])
        elif self._end_time is not None and self._start_time is not None:
            duration = self._end_time - self._start_time
            if duration > 0:
                args.extend(['-t', str(duration)])
        elif self._end_time is not None:
            # If only end_time specified, use -to
            args.extend(['-to', str(self._end_time)])
        
        # Add codecs
        if self._video_codec:
            args.extend(['-c:v', self._video_codec])
        if self._audio_codec:
            args.extend(['-c:a', self._audio_codec])
        
        # Add bitrates
        if self._video_bitrate:
            args.extend(['-b:v', self._video_bitrate])
        if self._audio_bitrate:
            args.extend(['-b:a', self._audio_bitrate])
        
        # Add extra arguments
        if self._extra_args:
            args.extend(self._extra_args)
        
        # Add output file
        args.append(self._output_file)
        
        return FFmpegCommand(
            args=args,
            input_files=self._input_files,
            output_file=self._output_file,
            description=self._description,
        )
