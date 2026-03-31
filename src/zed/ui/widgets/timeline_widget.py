"""
Multi-Track Timeline Widget

Bottom panel for multi-track video/audio timeline.
Manages Clip objects and supports selection, editing operations.
"""

from typing import List, Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QPushButton, QSlider, QMenu, QStackedLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QTimer
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QAction

from zed.operations import Clip
from .clip_widget import ClipWidget


class TimelineTrackWidget(QFrame):
    """Single track row in the timeline."""
    
    def __init__(self, name: str, track_type: str = "video", track_index: int = 0, parent=None):
        super().__init__(parent)
        self.name = name
        self.track_type = track_type
        self.track_index = track_index
        self._clip_widgets: Dict[str, ClipWidget] = {}
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
        
        # Track content area - this is where clips will be placed
        self.content = QFrame()
        self.content.setObjectName("TrackContent")
        self.content.setStyleSheet("""
            #TrackContent {
                background-color: #232327;
                border-bottom: 1px solid #2d2d32;
            }
        """)
        
        # Use absolute positioning for clips
        self.content_layout = QHBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(4)
        self.content_layout.addStretch()
        
        layout.addWidget(self.content, stretch=1)
    
    def add_clip_widget(self, clip_widget: ClipWidget, x_position: int):
        """Add a clip widget at the specified x position."""
        clip_widget.setParent(self.content)
        clip_widget.move(x_position, 8)  # 8px top margin
        clip_widget.show()
        self._clip_widgets[clip_widget.get_clip_id()] = clip_widget
    
    def remove_clip_widget(self, clip_id: str) -> bool:
        """Remove a clip widget by ID."""
        if clip_id in self._clip_widgets:
            widget = self._clip_widgets.pop(clip_id)
            widget.deleteLater()
            return True
        return False
    
    def clear_clips(self):
        """Remove all clip widgets."""
        for widget in self._clip_widgets.values():
            widget.deleteLater()
        self._clip_widgets.clear()
    
    def get_clip_widget(self, clip_id: str) -> Optional[ClipWidget]:
        """Get a clip widget by ID."""
        return self._clip_widgets.get(clip_id)
    
    def update_selection(self, selected_clip_id: Optional[str]):
        """Update selection state of all clip widgets."""
        for clip_id, widget in self._clip_widgets.items():
            widget.set_selected(clip_id == selected_clip_id)


class TimelineRulerWidget(QFrame):
    """Time ruler at top of timeline with draggable playhead."""
    
    playhead_moved = pyqtSignal(float)  # Emits time in seconds when moved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelineRuler")
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._duration = 60.0  # Default 60 seconds
        self._position = 0.0   # Current playhead position
        self._scale = 10.0     # Pixels per second
        self._is_dragging = False
        self.setMouseTracking(True)
    
    def set_duration(self, duration: float):
        """Set the total duration."""
        self._duration = max(0.0, duration)
        self.update()
    
    def set_position(self, position: float):
        """Set the playhead position."""
        self._position = max(0.0, min(position, self._duration))
        self.update()
    
    def set_scale(self, scale: float):
        """Set the zoom scale (pixels per second)."""
        self._scale = max(1.0, scale)
        self.update()
    
    def _time_to_x(self, time: float) -> int:
        """Convert time to x coordinate."""
        return int(time * self._scale) + 128  # 128 = header width offset
    
    def _x_to_time(self, x: int) -> float:
        """Convert x coordinate to time."""
        return max(0.0, (x - 128) / self._scale)
    
    def _is_over_playhead(self, pos) -> bool:
        """Check if mouse is over the playhead handle."""
        playhead_x = self._time_to_x(self._position)
        return abs(pos.x() - playhead_x) < 10  # 10px tolerance
    
    def paintEvent(self, event):
        """Draw time markers and playhead."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw background
        painter.fillRect(self.rect(), QColor("#222226"))
        
        # Draw time markers
        painter.setPen(QPen(QColor("#6a6a6a"), 1))
        
        # Calculate marker spacing based on scale
        if self._scale >= 50:
            marker_interval = 1  # Every second
        elif self._scale >= 20:
            marker_interval = 5  # Every 5 seconds
        elif self._scale >= 10:
            marker_interval = 10  # Every 10 seconds
        else:
            marker_interval = 30  # Every 30 seconds
        
        header_offset = 128  # Width of track header
        
        for t in range(0, int(self._duration) + marker_interval, marker_interval):
            x = int(t * self._scale) + header_offset
            if x > width:
                break
            
            # Draw tick mark
            painter.drawLine(x, 18, x, 24)
            
            # Draw time label
            time_str = self._format_time(t)
            painter.drawText(x + 4, 16, time_str)
        
        # Draw playhead (red line)
        playhead_x = self._time_to_x(self._position)
        if header_offset <= playhead_x <= width:
            painter.setPen(QPen(QColor("#ff4444"), 2))
            painter.drawLine(playhead_x, 0, playhead_x, height)
            
            # Draw playhead handle (triangle at top)
            painter.setBrush(QColor("#ff4444"))
            painter.drawPolygon([
                QPoint(playhead_x, 0),
                QPoint(playhead_x - 6, 8),
                QPoint(playhead_x + 6, 8),
            ])
            
            # Draw playhead handle (circle at bottom for dragging)
            painter.drawEllipse(playhead_x - 4, height - 8, 8, 8)
        
        # Bottom border
        painter.setPen(QPen(QColor("#3a3a3f"), 1))
        painter.drawLine(0, height - 1, width, height - 1)
    
    def mousePressEvent(self, event):
        """Handle mouse press - start dragging if over playhead."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            time = self._x_to_time(event.pos().x())
            self.set_position(time)
            self.playhead_moved.emit(time)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move - drag playhead if dragging."""
        if self._is_dragging:
            time = self._x_to_time(event.pos().x())
            self.set_position(time)
            self.playhead_moved.emit(time)
        else:
            # Update cursor based on position
            if self._is_over_playhead(event.pos()):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
        super().mouseReleaseEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave - reset cursor."""
        self._is_dragging = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().leaveEvent(event)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS."""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"


class TimelineWidget(QWidget):
    """
    Multi-Track Timeline - Bottom panel for video editing.
    
    Features:
    - Multiple tracks (Video, Audio, Effects)
    - Scrollable timeline
    - Time ruler with playhead
    - Real clip management (add, remove, select)
    - Zoom control
    - Visual clip representation
    
    Signals:
        position_changed: Playhead moved (float 0-1)
        clip_selected: A clip was selected (str clip_id)
        clip_added: A new clip was added (Clip)
        clip_removed: A clip was removed (str clip_id)
        clip_updated: A clip was modified (Clip)
        time_selected: User clicked on timeline at specific time (float seconds)
    """
    
    position_changed = pyqtSignal(float)
    clip_selected = pyqtSignal(str)  # emits clip_id
    clip_added = pyqtSignal(object)  # emits Clip
    clip_removed = pyqtSignal(str)   # emits clip_id
    clip_updated = pyqtSignal(object)  # emits Clip
    time_selected = pyqtSignal(float)  # emits time in seconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 60.0
        self._position = 0.0
        self._scale = 10.0  # pixels per second (zoom level)
        self._clips: List[Clip] = []
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
        
        # Zoom slider
        zoom_label = QLabel("Zoom:")
        zoom_label.setObjectName("HintLabel")
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setObjectName("ZoomSlider")
        self.zoom_slider.setRange(5, 100)  # 5 to 100 pixels per second
        self.zoom_slider.setValue(int(self._scale))
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(zoom_label)
        header.addWidget(self.zoom_slider)
        
        layout.addLayout(header)
        
        # Ruler with playhead
        self.ruler = TimelineRulerWidget()
        self.ruler.set_scale(self._scale)
        self.ruler.playhead_moved.connect(self._on_ruler_clicked)
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
        tracks_container.setObjectName("TracksContainer")
        tracks_layout = QVBoxLayout(tracks_container)
        tracks_layout.setContentsMargins(0, 0, 0, 0)
        tracks_layout.setSpacing(0)
        
        # Create tracks
        self.video_track = TimelineTrackWidget("Video 1", "video", 0)
        self.audio_track = TimelineTrackWidget("Audio 1", "audio", 1)
        self.effects_track = TimelineTrackWidget("Effects", "effects", 2)
        
        tracks_layout.addWidget(self.video_track)
        tracks_layout.addWidget(self.audio_track)
        tracks_layout.addWidget(self.effects_track)
        tracks_layout.addStretch()
        
        scroll.setWidget(tracks_container)
        layout.addWidget(scroll, stretch=1)
        
        # Connect track clip signals
        self.video_track.content.mousePressEvent = self._on_track_clicked
        
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
            #ZoomSlider::groove:horizontal {
                background-color: #3a3a3f;
                height: 4px;
                border-radius: 2px;
            }
            #ZoomSlider::handle:horizontal {
                background-color: #6a6a6a;
                width: 12px;
                height: 12px;
                border-radius: 6px;
            }
            #ZoomSlider::sub-page:horizontal {
                background-color: #4a6fa5;
                border-radius: 2px;
            }
        """)
    
    def _on_zoom_changed(self, value: int):
        """Handle zoom slider change."""
        self._scale = float(value)
        self.ruler.set_scale(self._scale)
        self._refresh_tracks()
    
    def _on_ruler_clicked(self, time: float):
        """Handle ruler click - seek to time."""
        self._position = time
        self.ruler.set_position(time)
        self.time_selected.emit(time)
        self.position_changed.emit(time / max(self._duration, 1.0))
        self.update_position(self._format_time(time))
    
    def _on_track_clicked(self, event):
        """Handle click on track background - deselect clips."""
        # Deselect all clips
        self._selected_clip_id = None
        self._update_selection_state()
        self.clip_selected.emit("")
    
    def _get_track_for_clip(self, clip: Clip) -> TimelineTrackWidget:
        """Get the appropriate track widget for a clip."""
        if clip.track == 0:
            return self.video_track
        elif clip.track == 1:
            return self.audio_track
        else:
            return self.effects_track
    
    def _time_to_x(self, time: float) -> int:
        """Convert timeline time to x coordinate."""
        return int(time * self._scale)
    
    def update_position(self, time_str: str):
        """Update position display."""
        self.position_label.setText(time_str)
    
    def on_position_update(self, time: float):
        """
        Called by PlaybackController when position changes.
        
        Args:
            time: Current position in seconds
        """
        self._position = time
        self.ruler.set_position(time)
        self.update_position(self._format_time(time))
    
    def set_duration(self, duration: float):
        """Set the media duration (called when video is loaded)."""
        self._duration = max(0.0, duration)
        self.ruler.set_duration(self._duration)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    
    # ===== Clip Management =====
    
    def add_clip(self, clip: Clip) -> Clip:
        """
        Add a clip to the timeline.
        
        Args:
            clip: Clip object to add
            
        Returns:
            The added Clip
        """
        self._clips.append(clip)
        self._refresh_tracks()
        self.clip_added.emit(clip)
        return clip
    
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
            end_time: End time in source (seconds). If None, use default duration.
            name: Display name. If None, derived from filename.
            
        Returns:
            The created Clip
        """
        # If end_time not provided, use a default duration
        if end_time is None:
            end_time = start_time + 10.0  # Default 10s clip
        
        from pathlib import Path
        clip_name = name or Path(source_file).stem
        
        # Calculate timeline position - place after last clip on track 0
        existing_clips = [c for c in self._clips if c.track == 0]
        if existing_clips:
            last_end = max(c.timeline_end_time for c in existing_clips)
            timeline_start = last_end
        else:
            timeline_start = 0.0
        
        source_duration = end_time - start_time
        timeline_end = timeline_start + source_duration
        
        clip = Clip(
            source_file=source_file,
            name=clip_name,
            source_start_time=start_time,
            source_end_time=end_time,
            timeline_start_time=timeline_start,
            timeline_end_time=timeline_end,
            track=0,
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
                
                # Remove from track
                track = self._get_track_for_clip(removed)
                track.remove_clip_widget(clip_id)
                
                if self._selected_clip_id == clip_id:
                    self._selected_clip_id = None
                
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
            self._update_selection_state()
            self.clip_selected.emit(clip_id)
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
        # Find and update the clip in our list
        for i, c in enumerate(self._clips):
            if c.id == clip.id:
                self._clips[i] = clip
                break
        
        self._refresh_tracks()
        self.clip_updated.emit(clip)
    
    def _update_selection_state(self):
        """Update visual selection state on all tracks."""
        self.video_track.update_selection(self._selected_clip_id)
        self.audio_track.update_selection(self._selected_clip_id)
        self.effects_track.update_selection(self._selected_clip_id)
    
    def _on_clip_clicked(self, clip_id: str):
        """Handle clip widget click."""
        self.select_clip(clip_id)
    
    def _refresh_tracks(self) -> None:
        """Refresh the visual representation of tracks."""
        # Clear all tracks
        self.video_track.clear_clips()
        self.audio_track.clear_clips()
        self.effects_track.clear_clips()
        
        # Re-add all clips to their respective tracks
        for clip in self._clips:
            track = self._get_track_for_clip(clip)
            
            # Create clip widget
            clip_widget = ClipWidget(clip, scale=self._scale)
            clip_widget.clicked.connect(self._on_clip_clicked)
            
            # Calculate x position based on timeline_start_time
            x_position = self._time_to_x(clip.timeline_start_time)
            
            # Add to track
            track.add_clip_widget(clip_widget, x_position)
            
            # Set selection state
            clip_widget.set_selected(clip.id == self._selected_clip_id)


__all__ = ['TimelineWidget', 'TimelineTrackWidget', 'TimelineRulerWidget']
