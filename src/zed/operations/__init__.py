"""
Zed Operations Module

Media operations that use the FFmpeg engine.
Provides extensible operation handlers for video editing.
"""

from .clip import VideoClipper
from .clip_model import Clip, ExportPreset, EXPORT_PRESETS, get_preset_config

__all__ = [
    'VideoClipper',
    'Clip',
    'ExportPreset',
    'EXPORT_PRESETS',
    'get_preset_config',
]
