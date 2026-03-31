"""
Clip Data Model

Represents a clip on the timeline with its source, timing, and effects.
This is the core data structure for video editing operations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from enum import Enum
import uuid


class ExportPreset(str, Enum):
    """Predefined export presets for common use cases."""
    H264_HIGH = "h264_high"       # H.264, high quality (1080p, 8M)
    H264_MEDIUM = "h264_medium"   # H.264, medium quality (720p, 5M)
    H264_LOW = "h264_low"         # H.264, low quality (480p, 2M)
    WEBM_VP9 = "webm_vp9"         # WebM VP9 for web
    PRORES = "prores"             # ProRes for editing/mastering
    COPY = "copy"                 # Stream copy (fast, no re-encode)


@dataclass
class Clip:
    """
    Represents a single clip on the timeline.
    
    A clip references a source media file and defines a segment
    with optional speed and fade effects.
    
    Timing Model:
        - source_start_time / source_end_time: Define the segment within the source media file
        - timeline_start_time / timeline_end_time: Define where the clip appears on the timeline
        
    For a simple clip (no speed change), timeline duration equals source duration.
    With speed changes, timeline duration = source_duration / speed.
    
    Attributes:
        id: Unique identifier for this clip instance
        source_file: Path to the source media file
        name: Display name (defaults to filename)
        source_start_time: Start time in source file (seconds)
        source_end_time: End time in source file (seconds)
        timeline_start_time: Start position on timeline (seconds)
        timeline_end_time: End position on timeline (seconds)
        speed: Playback speed multiplier (1.0 = normal)
        fade_in: Fade in duration (seconds, 0 = none)
        fade_out: Fade out duration (seconds, 0 = none)
        track: Track index this clip belongs to (0 = video, 1 = audio, etc.)
    """
    
    id: str = field(default_factory=lambda: f"clip_{uuid.uuid4().hex[:8]}")
    source_file: str = ""
    name: str = ""
    # Source timing (what portion of the source file to use)
    source_start_time: float = 0.0
    source_end_time: float = 10.0
    # Timeline timing (where the clip appears on the track)
    timeline_start_time: float = 0.0
    timeline_end_time: float = 10.0
    speed: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    track: int = 0  # 0 = video track, 1 = audio, etc.
    
    def __post_init__(self):
        """Set default name from source file and ensure timeline timing is initialized."""
        if not self.name and self.source_file:
            self.name = Path(self.source_file).stem
        # Ensure timeline timing matches source timing by default
        if self.timeline_end_time <= self.timeline_start_time:
            self.timeline_end_time = self.timeline_start_time + self.source_duration
    
    # Backward compatibility properties
    @property
    def start_time(self) -> float:
        """Backward compatibility - returns source_start_time."""
        return self.source_start_time
    
    @start_time.setter
    def start_time(self, value: float):
        """Backward compatibility - sets source_start_time."""
        self.source_start_time = value
    
    @property
    def end_time(self) -> float:
        """Backward compatibility - returns source_end_time."""
        return self.source_end_time
    
    @end_time.setter
    def end_time(self, value: float):
        """Backward compatibility - sets source_end_time."""
        self.source_end_time = value
    
    @property
    def source_duration(self) -> float:
        """Duration of the clip in source time (seconds)."""
        return max(0.0, self.source_end_time - self.source_start_time)
    
    @property
    def timeline_duration(self) -> float:
        """Duration of the clip on the timeline (seconds), accounting for speed."""
        if self.speed <= 0:
            return 0.0
        return self.source_duration / self.speed
    
    @property
    def duration(self) -> float:
        """Backward compatibility - returns source_duration."""
        return self.source_duration
    
    @property
    def output_duration(self) -> float:
        """Backward compatibility - returns timeline_duration."""
        return self.timeline_duration
    
    def to_dict(self) -> dict:
        """Serialize to dictionary with new timeline fields."""
        return {
            'id': self.id,
            'source_file': self.source_file,
            'name': self.name,
            # New explicit timing fields
            'source_start_time': self.source_start_time,
            'source_end_time': self.source_end_time,
            'timeline_start_time': self.timeline_start_time,
            'timeline_end_time': self.timeline_end_time,
            # Backward compatibility
            'start_time': self.start_time,
            'end_time': self.end_time,
            'speed': self.speed,
            'fade_in': self.fade_in,
            'fade_out': self.fade_out,
            'track': self.track,
        }
    
    def __init__(self, **kwargs):
        """Initialize with backward compatibility for start_time/end_time."""
        # Handle backward compatibility: start_time -> source_start_time
        if 'start_time' in kwargs and 'source_start_time' not in kwargs:
            kwargs['source_start_time'] = kwargs.pop('start_time')
        if 'end_time' in kwargs and 'source_end_time' not in kwargs:
            kwargs['source_end_time'] = kwargs.pop('end_time')
        
        # Set defaults for new timeline fields if not provided
        if 'timeline_start_time' not in kwargs:
            kwargs['timeline_start_time'] = kwargs.get('source_start_time', 0.0)
        if 'timeline_end_time' not in kwargs:
            source_end = kwargs.get('source_end_time', 10.0)
            source_start = kwargs.get('source_start_time', 0.0)
            kwargs['timeline_end_time'] = kwargs['timeline_start_time'] + (source_end - source_start)
        
        # Set defaults for all fields
        defaults = {
            'id': f"clip_{uuid.uuid4().hex[:8]}",
            'source_file': '',
            'name': '',
            'source_start_time': 0.0,
            'source_end_time': 10.0,
            'timeline_start_time': 0.0,
            'timeline_end_time': 10.0,
            'speed': 1.0,
            'fade_in': 0.0,
            'fade_out': 0.0,
            'track': 0,
        }
        
        # Merge defaults with provided kwargs
        for key, default_val in defaults.items():
            if key not in kwargs:
                kwargs[key] = default_val
        
        # Set all attributes
        for key, value in kwargs.items():
            if key in self.__dataclass_fields__:
                object.__setattr__(self, key, value)
        
        # Run post-init
        self.__post_init__()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Clip':
        """Deserialize from dictionary with backward compatibility."""
        # Handle old format (start_time/end_time) -> new format
        kwargs = {
            'id': data.get('id', ''),
            'source_file': data.get('source_file', ''),
            'name': data.get('name', ''),
            'speed': data.get('speed', 1.0),
            'fade_in': data.get('fade_in', 0.0),
            'fade_out': data.get('fade_out', 0.0),
            'track': data.get('track', 0),
        }
        
        # Handle timing fields
        if 'source_start_time' in data:
            kwargs['source_start_time'] = data['source_start_time']
        elif 'start_time' in data:
            kwargs['source_start_time'] = data['start_time']
        else:
            kwargs['source_start_time'] = 0.0
        
        if 'source_end_time' in data:
            kwargs['source_end_time'] = data['source_end_time']
        elif 'end_time' in data:
            kwargs['source_end_time'] = data['end_time']
        else:
            kwargs['source_end_time'] = 10.0
        
        if 'timeline_start_time' in data:
            kwargs['timeline_start_time'] = data['timeline_start_time']
        else:
            kwargs['timeline_start_time'] = kwargs['source_start_time']
        
        if 'timeline_end_time' in data:
            kwargs['timeline_end_time'] = data['timeline_end_time']
        else:
            kwargs['timeline_end_time'] = kwargs['timeline_start_time'] + (kwargs['source_end_time'] - kwargs['source_start_time'])
        
        return cls(**kwargs)
    
    def copy(self, new_id: bool = True) -> 'Clip':
        """Create a copy of this clip. Optionally generate new ID."""
        return Clip(
            id=f"clip_{uuid.uuid4().hex[:8]}" if new_id else self.id,
            source_file=self.source_file,
            name=f"{self.name} (copy)" if new_id else self.name,
            source_start_time=self.source_start_time,
            source_end_time=self.source_end_time,
            timeline_start_time=self.timeline_start_time,
            timeline_end_time=self.timeline_end_time,
            speed=self.speed,
            fade_in=self.fade_in,
            fade_out=self.fade_out,
            track=self.track,
        )


# Preset configurations for export
EXPORT_PRESETS = {
    ExportPreset.H264_HIGH: {
        'name': 'H.264 High (1080p)',
        'video_codec': 'libx264',
        'audio_codec': 'aac',
        'video_bitrate': '8M',
        'audio_bitrate': '192k',
        'scale': '1920:1080',
        'description': 'High quality H.264, suitable for archiving',
    },
    ExportPreset.H264_MEDIUM: {
        'name': 'H.264 Medium (720p)',
        'video_codec': 'libx264',
        'audio_codec': 'aac',
        'video_bitrate': '5M',
        'audio_bitrate': '128k',
        'scale': '1280:720',
        'description': 'Medium quality, good for web sharing',
    },
    ExportPreset.H264_LOW: {
        'name': 'H.264 Low (480p)',
        'video_codec': 'libx264',
        'audio_codec': 'aac',
        'video_bitrate': '2M',
        'audio_bitrate': '96k',
        'scale': '854:480',
        'description': 'Lower quality, smaller files',
    },
    ExportPreset.WEBM_VP9: {
        'name': 'WebM VP9',
        'video_codec': 'libvpx-vp9',
        'audio_codec': 'libopus',
        'video_bitrate': '4M',
        'audio_bitrate': '128k',
        'scale': None,  # Keep original
        'description': 'Web-optimized VP9',
    },
    ExportPreset.PRORES: {
        'name': 'ProRes (Editing)',
        'video_codec': 'prores_ks',
        'audio_codec': 'pcm_s16le',
        'video_bitrate': None,  # ProRes is quality-based
        'audio_bitrate': None,
        'scale': None,
        'description': 'High quality for further editing',
    },
    ExportPreset.COPY: {
        'name': 'Stream Copy (Fast)',
        'video_codec': 'copy',
        'audio_codec': 'copy',
        'video_bitrate': None,
        'audio_bitrate': None,
        'scale': None,
        'description': 'Fastest export, no re-encoding',
    },
}


def get_preset_config(preset: ExportPreset) -> dict:
    """Get configuration dict for an export preset."""
    return EXPORT_PRESETS.get(preset, EXPORT_PRESETS[ExportPreset.H264_MEDIUM])


__all__ = ['Clip', 'ExportPreset', 'EXPORT_PRESETS', 'get_preset_config']
