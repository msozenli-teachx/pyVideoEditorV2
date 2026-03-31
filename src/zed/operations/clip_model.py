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
    
    Attributes:
        id: Unique identifier for this clip instance
        source_file: Path to the source media file
        name: Display name (defaults to filename)
        start_time: Start time in source file (seconds)
        end_time: End time in source file (seconds)
        speed: Playback speed multiplier (1.0 = normal)
        fade_in: Fade in duration (seconds, 0 = none)
        fade_out: Fade out duration (seconds, 0 = none)
        track: Track index this clip belongs to (0 = video, 1 = audio, etc.)
    """
    
    id: str = field(default_factory=lambda: f"clip_{uuid.uuid4().hex[:8]}")
    source_file: str = ""
    name: str = ""
    start_time: float = 0.0
    end_time: float = 10.0
    speed: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    track: int = 0  # 0 = video track, 1 = audio, etc.
    
    def __post_init__(self):
        """Set default name from source file if not provided."""
        if not self.name and self.source_file:
            self.name = Path(self.source_file).stem
    
    @property
    def duration(self) -> float:
        """Duration of the clip in seconds (in source time)."""
        return max(0.0, self.end_time - self.start_time)
    
    @property
    def output_duration(self) -> float:
        """Duration after speed adjustment (output time)."""
        if self.speed <= 0:
            return 0.0
        return self.duration / self.speed
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'source_file': self.source_file,
            'name': self.name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'speed': self.speed,
            'fade_in': self.fade_in,
            'fade_out': self.fade_out,
            'track': self.track,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Clip':
        """Deserialize from dictionary."""
        return cls(
            id=data.get('id', ''),
            source_file=data.get('source_file', ''),
            name=data.get('name', ''),
            start_time=data.get('start_time', 0.0),
            end_time=data.get('end_time', 10.0),
            speed=data.get('speed', 1.0),
            fade_in=data.get('fade_in', 0.0),
            fade_out=data.get('fade_out', 0.0),
            track=data.get('track', 0),
        )
    
    def copy(self, new_id: bool = True) -> 'Clip':
        """Create a copy of this clip. Optionally generate new ID."""
        return Clip(
            id=f"clip_{uuid.uuid4().hex[:8]}" if new_id else self.id,
            source_file=self.source_file,
            name=f"{self.name} (copy)" if new_id else self.name,
            start_time=self.start_time,
            end_time=self.end_time,
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
