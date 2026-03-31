"""
Multi-Track Timeline Widget

Bottom panel for multi-track video/audio timeline.
Manages Clip objects and supports selection, editing operations.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QPushButton, QSlider, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QAction

from zed.operations import Clip


class TimelineTrackWidget(QFrame):
    """Single track row in the timeline."""
    
    def __init__(self, name: str, track_type: str = "video", parent=None):
        super().__init__(parent)
        self.name = name
        self.track_type = track_type
        self._setup_ui()
    
    def _setup_ui(self):
        self.setObjectName("TimelineTrack")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(60)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Track header (name)
        header = QFrame()
        header.setObjectName("TimelineTrackHeader")
        header.setFixedWidth(120)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(8, 8, 8, 8)
        
        label = QLabel(self.name)
        label.setObjectName("TrackLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        type_label = QLabel(self.track_type.upper())
        type_label.setObjectName("TrackTypeLabel")
        type_label.setStyleSheet("color: #6a6a6a; font-size: 9px;")
        
        header_layout.addWidget(label)
        header_layout.addWidget(type_label)
        
        layout.addWidget(header)
        
        # Track content area (empty by default - clips added programmatically)
        content = QFrame()
        content.setObjectName("TrackContent")
        content.setStyleSheet("""
            #TrackContent {
                background-color: #232327;
                border-bottom: 1px solid #2d2d32;
            }
        """)
        
        # Empty content layout - no static demo clips
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.addStretch()
        
        layout.addWidget(content, stretch=1)


class TimelineRulerWidget(QFrame):
    """Time ruler at top of timeline."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelineRuler")
        self.setFixedHeight(24)
    
    def paintEvent(self, event):
        """Draw time markers."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor("#222226"))
        
        # Draw time markers
        painter.setPen(QPen(QColor("#6a6a6a"), 1))
        width = self.width()
        
        # Simple markers every 100px (representing time)
        for x in range(0, width, 100):
            painter.drawLine(x, 18, x, 24)
            # Time label
            seconds = x / 100 * 5  # Assume 5s per 100px
            painter.drawText(x + 4, 16, f"{int(seconds)}s")
        
        # Bottom border
        painter.setPen(QPen(QColor("#3a3a3f"), 1))
        painter.drawLine(0, self.height() - 1, width, self.height() - 1)


class TimelineWidget(QWidget):
    """
    Multi-Track Timeline - Bottom panel for video editing.
    
    Features:
    - Multiple tracks (Video, Audio, Effects)
    - Scrollable timeline
    - Time ruler
    - Real clip management (add, remove, select)
    - Zoom control (future)
    
    Signals:
        position_changed: Playhead moved (float 0-1)
        clip_selected: A clip was selected (str clip_id)
        clip_added: A new clip was added (Clip)
        clip_removed: A clip was removed (str clip_id)
        clip_updated: A clip was modified (Clip)
    """
    
    position_changed = pyqtSignal(float)
    clip_selected = pyqtSignal(str)  # emits clip_id
    clip_added = pyqtSignal(object)  # emits Clip
    clip_removed = pyqtSignal(str)   # emits clip_id
    clip_updated = pyqtSignal(object)  # emits Clip
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 0.0
        self._clips: List[Clip] = []  # All clips across tracks
        self._selected_clip_id: Optional[str] = None
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the timeline UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Timeline")
        title.setObjectName("PanelTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        
        # Zoom slider (placeholder)
        zoom_label = QLabel("Zoom:")
        zoom_label.setObjectName("HintLabel")
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(zoom_label)
        header.addWidget(self.zoom_slider)
        
        layout.addLayout(header)
        
        # Ruler
        self.ruler = TimelineRulerWidget()
        layout.addWidget(self.ruler)
        
        # Scroll area for tracks
        scroll = QScrollArea()
        scroll.setObjectName("TimelineScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Tracks container
        tracks_container = QWidget()
        tracks_layout = QVBoxLayout(tracks_container)
        tracks_layout.setContentsMargins(0, 0, 0, 0)
        tracks_layout.setSpacing(0)
        
        # Create tracks
        self.video_track = TimelineTrackWidget("Video 1", "video")
        self.audio_track = TimelineTrackWidget("Audio 1", "audio")
        self.effects_track = TimelineTrackWidget("Effects", "effects")
        
        tracks_layout.addWidget(self.video_track)
        tracks_layout.addWidget(self.audio_track)
        tracks_layout.addWidget(self.effects_track)
        tracks_layout.addStretch()
        
        scroll.setWidget(tracks_container)
        layout.addWidget(scroll, stretch=1)
        
        # Playhead position (bottom controls)
        pos_layout = QHBoxLayout()
        pos_label = QLabel("Position:")
        pos_label.setObjectName("HintLabel")
        self.position_label = QLabel("00:00:00")
        self.position_label.setObjectName("PositionLabel")
        
        pos_layout.addWidget(pos_label)
        pos_layout.addWidget(self.position_label)
        pos_layout.addStretch()
        
        layout.addLayout(pos_layout)
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            #PanelTitle {
                color: #e0e0e0;
            }
            #HintLabel {
                color: #6a6a6a;
                font-size: 11px;
            }
            #PositionLabel {
                color: #a0a0a0;
                font-family: "Consolas", monospace;
                font-size: 12px;
            }
            #TimelineScroll {
                background-color: #1e1e22;
                border: 1px solid #2d2d32;
                border-radius: 6px;
            }
            #TimelineTrack {
                background-color: #232327;
                border-bottom: 1px solid #2d2d32;
            }
            #TimelineTrackHeader {
                background-color: #222226;
                border-right: 1px solid #2d2d32;
            }
            #TrackLabel {
                color: #a0a0a0;
                font-size: 11px;
                font-weight: 500;
            }
            #TimelineRuler {
                background-color: #222226;
                border-bottom: 1px solid #3a3a3f;
            }
        """)
    
    def update_position(self, time_str: str):
        """Update position display."""
        self.position_label.setText(time_str)
    
    def on_position_update(self, time: float):
        """
        Called by PlaybackController when position changes.
        
        Args:
            time: Current position in seconds
        """
        # Update position label
        self.update_position(self._format_time(time))
        # Future: Move playhead graphic to time position
        # Future: Scroll timeline to keep playhead visible
    
    def set_duration(self, duration: float):
        """Set the media duration (called when video is loaded)."""
        self._duration = duration
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    
    # ===== Clip Management =====
    
    def add_clip(self, clip: Clip) -> None:
        """
        Add a clip to the timeline.
        
        Args:
            clip: Clip object to add
        """
        self._clips.append(clip)
        self._refresh_tracks()
        self.clip_added.emit(clip)
    
    def add_clip_from_source(
        self,
        source_file: str,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        name: Optional[str] = None
    ) -> Clip:
        """
        Convenience method to create and add a clip from a source file.
        
        Args:
            source_file: Path to media file
            start_time: Start time in source (seconds)
            end_time: End time in source (seconds). If None, use video duration.
            name: Display name. If None, derived from filename.
        
        Returns:
            The created Clip
        """
        # If end_time not provided, we don't know duration yet - use a default
        if end_time is None:
            end_time = start_time + 10.0  # Default 10s clip
        
        clip = Clip(
            source_file=source_file,
            name=name,
            start_time=start_time,
            end_time=end_time,
        )
        self.add_clip(clip)
        return clip
    
    def remove_clip(self, clip_id: str) -> bool:
        """
        Remove a clip by ID.
        
        Args:
            clip_id: ID of clip to remove
        
        Returns:
            True if removed, False if not found
        """
        for i, clip in enumerate(self._clips):
            if clip.id == clip_id:
                removed = self._clips.pop(i)
                if self._selected_clip_id == clip_id:
                    self._selected_clip_id = None
                self._refresh_tracks()
                self.clip_removed.emit(clip_id)
                return True
        return False
    
    def get_clip(self, clip_id: str) -> Optional[Clip]:
        """Get a clip by ID."""
        for clip in self._clips:
            if clip.id == clip_id:
                return clip
        return None
    
    def get_all_clips(self) -> List[Clip]:
        """Get all clips."""
        return list(self._clips)
    
    def get_clips_by_track(self, track: int) -> List[Clip]:
        """Get clips on a specific track."""
        return [c for c in self._clips if c.track == track]
    
    def select_clip(self, clip_id: str) -> Optional[Clip]:
        """
        Select a clip by ID.
        
        Args:
            clip_id: ID of clip to select
        
        Returns:
            The selected Clip, or None if not found
        """
        clip = self.get_clip(clip_id)
        if clip:
            self._selected_clip_id = clip_id
            self.clip_selected.emit(clip_id)
            self._refresh_tracks()  # Refresh to show selection highlight
        return clip
    
    def get_selected_clip(self) -> Optional[Clip]:
        """Get the currently selected clip."""
        if self._selected_clip_id:
            return self.get_clip(self._selected_clip_id)
        return None
    
    def clear_clips(self) -> None:
        """Remove all clips from the timeline."""
        self._clips.clear()
        self._selected_clip_id = None
        self._refresh_tracks()
    
    def update_clip(self, clip: Clip) -> None:
        """
        Notify that a clip has been updated externally.
        Triggers refresh and clip_updated signal.
        """
        self._refresh_tracks()
        self.clip_updated.emit(clip)
    
    def _refresh_tracks(self) -> None:
        """Refresh the visual representation of tracks."""
        # For Phase 1, we just update the video track's content area
        # with clips from track 0
        # This is a simplified version - full visual rendering can be added later
        
        video_clips = self.get_clips_by_track(0)
        
        # Clear existing content in video track
        # (The TimelineTrackWidget has a content frame we can repopulate)
        # For now, we'll leave visual rendering simple and rely on signals
        # A full implementation would create ClipWidget items here
        
        # Future: Create visual clip widgets based on timing
        pass
