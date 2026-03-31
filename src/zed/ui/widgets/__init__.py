"""
Zed UI Widgets

Reusable widget components for the video editor interface.
"""

from .media_pool import MediaPoolWidget
from .preview_area import PreviewAreaWidget
from .timeline_widget import TimelineWidget
from .controls_panel import ControlsPanelWidget
from .clip_widget import ClipWidget

__all__ = [
    'MediaPoolWidget',
    'PreviewAreaWidget',
    'TimelineWidget',
    'ControlsPanelWidget',
    'ClipWidget',
]
