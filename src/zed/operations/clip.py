"""
Video Clipping Operation

Provides video clipping/trimming functionality using the FFmpeg engine.
This is an example operation demonstrating the extensible architecture.
"""

from pathlib import Path
from typing import Optional, Union

from ..ffmpeg import FFmpegEngine, ProcessResult, VideoCodec, AudioCodec
from ..logging import get_logger
from ..config import get_config


class VideoClipper:
    """
    Video clipping operation handler.
    
    Provides methods for trimming video segments with various options.
    This operation uses the FFmpeg engine internally.
    """
    
    def __init__(self, engine: Optional[FFmpegEngine] = None):
        """
        Initialize the video clipper.
        
        Args:
            engine: Optional FFmpeg engine instance. Creates new one if None.
        """
        self._engine = engine or FFmpegEngine()
        self._logger = get_logger('operations.clip')
        self._config = get_config()
    
    @property
    def engine(self) -> FFmpegEngine:
        """Get the underlying FFmpeg engine."""
        return self._engine
    
    def clip(
        self,
        input_file: Union[str, Path],
        output_file: Union[str, Path],
        start_time: float,
        duration: Optional[float] = None,
        end_time: Optional[float] = None,
        video_codec: Optional[Union[VideoCodec, str]] = None,
        audio_codec: Optional[Union[AudioCodec, str]] = None,
        copy_codec: bool = False,
    ) -> ProcessResult:
        """
        Clip a video segment.
        
        Args:
            input_file: Path to input video file
            output_file: Path to output file
            start_time: Start time in seconds
            duration: Duration in seconds (alternative to end_time)
            end_time: End time in seconds (alternative to duration)
            video_codec: Video codec to use (default from config)
            audio_codec: Audio codec to use (default from config)
            copy_codec: If True, copy streams without re-encoding (fastest)
        
        Returns:
            ProcessResult of the clipping operation
        
        Example:
            >>> clipper = VideoClipper()
            >>> result = clipper.clip(
            ...     'input.mp4',
            ...     'output.mp4',
            ...     start_time=10.0,
            ...     duration=30.0
            ... )
            >>> if result.success:
            ...     print(f"Clipped to {result.output_file}")
        """
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        self._logger.info(
            f"Clipping {input_path.name}: {start_time}s -> "
            f"{end_time or (start_time + duration) if duration else 'end'}"
        )
        
        # Build command
        builder = self._engine.create_command()
        builder.input(input_path).output(output_path)
        builder.start_time(start_time)
        
        if duration:
            builder.duration(duration)
        elif end_time:
            builder.end_time(end_time)
        
        # Set codecs
        if copy_codec:
            builder.video_codec(VideoCodec.COPY)
            builder.audio_codec(AudioCodec.COPY)
        else:
            builder.video_codec(
                video_codec or self._config.ffmpeg.default_video_codec
            )
            builder.audio_codec(
                audio_codec or self._config.ffmpeg.default_audio_codec
            )
        
        builder.description(f"Clip {input_path.name} from {start_time}s")
        
        command = builder.build()
        result = self._engine.execute(command)
        
        if result.success:
            self._logger.info(f"Clip completed: {output_path}")
        else:
            self._logger.error(f"Clip failed: {result.error_message}")
        
        return result
    
    def clip_multiple(
        self,
        clips: list[dict],
        max_concurrent: Optional[int] = None,
    ) -> list[ProcessResult]:
        """
        Clip multiple video segments, potentially concurrently.
        
        Args:
            clips: List of clip specifications, each containing:
                - input_file: Path to input
                - output_file: Path to output
                - start_time: Start time
                - duration or end_time: Length
                - (optional) video_codec, audio_codec, copy_codec
            max_concurrent: Max concurrent operations
        
        Returns:
            List of ProcessResults
        
        Example:
            >>> clips = [
            ...     {'input_file': 'video.mp4', 'output_file': 'clip1.mp4',
            ...      'start_time': 0, 'duration': 10},
            ...     {'input_file': 'video.mp4', 'output_file': 'clip2.mp4',
            ...      'start_time': 20, 'duration': 10},
            ... ]
            >>> results = clipper.clip_multiple(clips)
        """
        commands = []
        
        for clip_spec in clips:
            builder = self._engine.create_command()
            builder.input(clip_spec['input_file'])
            builder.output(clip_spec['output_file'])
            builder.start_time(clip_spec['start_time'])
            
            if 'duration' in clip_spec:
                builder.duration(clip_spec['duration'])
            elif 'end_time' in clip_spec:
                builder.end_time(clip_spec['end_time'])
            
            if clip_spec.get('copy_codec'):
                builder.video_codec(VideoCodec.COPY)
                builder.audio_codec(AudioCodec.COPY)
            else:
                builder.video_codec(
                    clip_spec.get('video_codec', self._config.ffmpeg.default_video_codec)
                )
                builder.audio_codec(
                    clip_spec.get('audio_codec', self._config.ffmpeg.default_audio_codec)
                )
            
            builder.description(f"Batch clip: {clip_spec['output_file']}")
            commands.append(builder.build())
        
        results = self._engine.execute_multiple(
            commands,
            max_concurrent=max_concurrent,
        )
        
        successful = sum(1 for r in results if r.success)
        self._logger.info(f"Batch clipping complete: {successful}/{len(results)} successful")
        
        return results
    
    def quick_trim(
        self,
        input_file: Union[str, Path],
        output_file: Union[str, Path],
        start_time: float,
        end_time: float,
    ) -> ProcessResult:
        """
        Quick trim using stream copy (no re-encoding).
        
        Fastest clipping method but may not be frame-accurate.
        
        Args:
            input_file: Input video file
            output_file: Output file
            start_time: Start time in seconds
            end_time: End time in seconds
        
        Returns:
            ProcessResult
        """
        return self.clip(
            input_file=input_file,
            output_file=output_file,
            start_time=start_time,
            end_time=end_time,
            copy_codec=True,
        )
