"""
Preview Area Widget

Central panel for video playback preview.
Integrates QMediaPlayer for real-time video playback, synchronized
with PlaybackController and Timeline via signals.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QStackedLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QPalette, QColor

# QMediaPlayer for real video playback
try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    HAS_QT_MULTIMEDIA = True
except ImportError:
    HAS_QT_MULTIMEDIA = False


class PreviewAreaWidget(QWidget):
    """
    Preview Area - Central video playback display.
    
    Features:
    - Real-time video playback via QMediaPlayer (when available)
    - Placeholder display when no video loaded
    - Transport controls (play, pause, stop)
    - Timecode display
    - Timeline scrubber
    - Position/duration signals for synchronization
    
    Signals:
        play_requested: User clicked play
        pause_requested: User clicked pause
        stop_requested: User clicked stop
        seek_requested: User scrubbed to position (float 0-1)
        position_changed: Playback position updated (float seconds)
        duration_changed: Media duration changed (float seconds)
    """
    
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    seek_requested = pyqtSignal(float)
    
    # New signals for video playback synchronization
    position_changed = pyqtSignal(float)  # Current time in seconds
    duration_changed = pyqtSignal(float)  # Total duration in seconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_playing = False
        self._duration = 0.0
        self._current_video_path: str = None
        self._media_player: QMediaPlayer = None
        self._video_widget: QVideoWidget = None
        self._setup_ui()
        self._setup_media_player()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the preview area UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Preview")
        title.setObjectName("PanelTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch()
        
        # Resolution indicator (placeholder)
        resolution = QLabel("1920 × 1080")
        resolution.setObjectName("ResolutionLabel")
        header.addWidget(resolution)
        
        layout.addLayout(header)
        
        # Video display frame - uses stacked layout for video/placeholder
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("PreviewFrame")
        self.preview_frame.setFrameShape(QFrame.Shape.Box)
        self.preview_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.preview_frame.setMinimumSize(640, 360)
        
        # Stacked layout: video widget on top, placeholder label beneath
        self._stacked_layout = QStackedLayout(self.preview_frame)
        
        # Placeholder text (shown when no video)
        self.preview_label = QLabel("▶\n\nVIDEO PREVIEW\n\nImport a video to begin")
        self.preview_label.setObjectName("PreviewLabel")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stacked_layout.addWidget(self.preview_label)
        
        # QVideoWidget (for real video playback, added in _setup_media_player)
        self._video_widget_placeholder = QLabel("Loading video...")
        self._video_widget_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_widget_placeholder.setStyleSheet("color: #6a6a6a; background: #0d0d10;")
        self._stacked_layout.addWidget(self._video_widget_placeholder)
        
        layout.addWidget(self.preview_frame, stretch=1)
        
        # Timeline scrubber
        scrubber_layout = QHBoxLayout()
        self.timecode_label = QLabel("00:00:00 / 00:00:00")
        self.timecode_label.setObjectName("TimecodeLabel")
        self.timecode_label.setFixedWidth(140)
        
        self.scrubber = QSlider(Qt.Orientation.Horizontal)
        self.scrubber.setRange(0, 1000)
        self.scrubber.setValue(0)
        self.scrubber.valueChanged.connect(self._on_scrubber_change)
        
        scrubber_layout.addWidget(self.timecode_label)
        scrubber_layout.addWidget(self.scrubber, stretch=1)
        
        layout.addLayout(scrubber_layout)
        
        # Transport controls - always define buttons so other methods can reference them
        transport_layout = QHBoxLayout()
        transport_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transport_layout.setSpacing(12)
        
        # Stop button
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setObjectName("TransportButton")
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.clicked.connect(self._on_stop)
        
        # Play/Pause button
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("TransportButton")
        self.play_btn.setToolTip("Play")
        self.play_btn.clicked.connect(self._on_play_pause)
        
        # Frame navigation buttons (placeholders for future)
        self.prev_frame_btn = QPushButton("◀")
        self.prev_frame_btn.setObjectName("TransportButton")
        self.prev_frame_btn.setToolTip("Previous Frame")
        
        self.next_frame_btn = QPushButton("▶")
        self.next_frame_btn.setObjectName("TransportButton")
        self.next_frame_btn.setToolTip("Next Frame")
        
        transport_layout.addWidget(self.stop_btn)
        transport_layout.addWidget(self.prev_frame_btn)
        transport_layout.addWidget(self.play_btn)
        transport_layout.addWidget(self.next_frame_btn)
        
        layout.addLayout(transport_layout)
    
    def _setup_media_player(self):
        """Initialize QMediaPlayer for real video playback."""
        if not HAS_QT_MULTIMEDIA:
            # PyQt6 multimedia not available - fallback to placeholder only
            return
        
        # Create media player
        self._media_player = QMediaPlayer(self)
        
        # Create and set audio output (required in Qt6 for audio playback)
        self._audio_output = QAudioOutput()
        self._media_player.setAudioOutput(self._audio_output)
        
        # Create video widget and add to stacked layout
        self._video_widget = QVideoWidget()
        self._video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self._stacked_layout.insertWidget(1, self._video_widget)  # Index 1 = above placeholder
        
        # Set video output
        self._media_player.setVideoOutput(self._video_widget)
        
        # Connect signals for synchronization
        self._media_player.positionChanged.connect(self._on_media_position_changed)
        self._media_player.durationChanged.connect(self._on_media_duration_changed)
        self._media_player.playbackStateChanged.connect(self._on_media_state_changed)
        self._media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        
        # When video loaded, show video widget instead of placeholder
        self._media_player.mediaStatusChanged.connect(self._update_display_mode)
    
    def _on_media_position_changed(self, position_ms: int):
        """QMediaPlayer position changed → emit position_changed signal and update scrubber."""
        time_sec = position_ms / 1000.0
        self.position_changed.emit(time_sec)
        
        # Update timecode
        if self._duration > 0:
            current_str = self._format_time(time_sec)
            total_str = self._format_time(self._duration)
            self.timecode_label.setText(f"{current_str} / {total_str}")
            
            # Update scrubber position to follow playback (avoid feedback loop)
            # Only update if not currently scrubbing (user not dragging)
            if not self.scrubber.isSliderDown():
                scrubber_value = int((time_sec / self._duration) * 1000)
                # Block signals to avoid triggering _on_scrubber_change
                self.scrubber.blockSignals(True)
                self.scrubber.setValue(scrubber_value)
                self.scrubber.blockSignals(False)
    
    def _on_media_duration_changed(self, duration_ms: int):
        """QMediaPlayer duration changed → emit duration_changed signal."""
        self._duration = duration_ms / 1000.0
        self.duration_changed.emit(self._duration)
        
        # Update timecode display
        total_str = self._format_time(self._duration)
        self.timecode_label.setText(f"00:00:00 / {total_str}")
    
    def _on_media_state_changed(self, state):
        """QMediaPlayer state changed → update internal state and emit."""
        from PyQt6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._is_playing = True
            self.play_btn.setText("⏸")
            self.play_btn.setToolTip("Pause")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._is_playing = False
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Play")
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self._is_playing = False
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Play")
    
    def _on_media_status_changed(self, status):
        """Handle media loading status."""
        from PyQt6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            # Video loaded, set duration
            duration_ms = self._media_player.duration()
            if duration_ms > 0:
                self._duration = duration_ms / 1000.0
                self.duration_changed.emit(self._duration)
    
    def _update_display_mode(self, status):
        """Switch between placeholder and video widget based on media status."""
        from PyQt6.QtMultimedia import QMediaPlayer
        # Show video widget when media is loaded, buffered, or playing
        # Don't show for NoMedia, LoadingMedia, InvalidMedia
        show_video = (
            self._video_widget is not None and
            status in (
                QMediaPlayer.MediaStatus.LoadedMedia,
                QMediaPlayer.MediaStatus.BufferingMedia,
                QMediaPlayer.MediaStatus.BufferedMedia,
                QMediaPlayer.MediaStatus.EndOfMedia,
            )
        )
        if show_video:
            self._stacked_layout.setCurrentIndex(1)  # Video widget
        else:
            self._stacked_layout.setCurrentIndex(0)  # Placeholder
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            #PanelTitle {
                color: #e0e0e0;
            }
            #ResolutionLabel {
                color: #6a6a6a;
                font-size: 11px;
                padding: 2px 8px;
                background-color: #222226;
                border-radius: 4px;
            }
            #PreviewFrame {
                background-color: #0d0d10;
                border: 1px solid #2d2d32;
                border-radius: 8px;
            }
            #PreviewLabel {
                color: #3a3a3f;
                font-size: 14px;
                font-weight: 500;
            }
            #TimecodeLabel {
                color: #a0a0a0;
                font-family: "Consolas", monospace;
                font-size: 12px;
            }
            #TransportButton {
                background-color: #2d2d32;
                border: 1px solid #3a3a3f;
                border-radius: 20px;
                font-size: 16px;
                color: #e0e0e0;
                min-width: 40px;
                min-height: 40px;
            }
            #TransportButton:hover {
                background-color: #3a3a3f;
                border-color: #4a4a4f;
            }
        """)
    
    def _on_play_pause(self):
        """Toggle play/pause - delegates to QMediaPlayer if available."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            # Let QMediaPlayer handle it
            if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._media_player.pause()
                self.pause_requested.emit()
            else:
                self._media_player.play()
                self.play_requested.emit()
        else:
            # Fallback: just toggle state and emit signals
            self._is_playing = not self._is_playing
            if self._is_playing:
                self.play_btn.setText("⏸")
                self.play_btn.setToolTip("Pause")
                self.play_requested.emit()
            else:
                self.play_btn.setText("▶")
                self.play_btn.setToolTip("Play")
                self.pause_requested.emit()
    
    def _on_stop(self):
        """Stop playback - delegates to QMediaPlayer if available."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.stop()
            self.stop_requested.emit()
        else:
            self._is_playing = False
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Play")
            self.scrubber.setValue(0)
            self.stop_requested.emit()
    
    def _on_scrubber_change(self, value: int):
        """Handle scrubber movement - seeks QMediaPlayer if available."""
        position = value / 1000.0  # Normalize to 0-1
        self.seek_requested.emit(position)
        
        # Also seek QMediaPlayer directly
        if self._media_player and HAS_QT_MULTIMEDIA and self._duration > 0:
            seek_ms = int(position * self._duration * 1000)
            self._media_player.setPosition(seek_ms)
    
    def update_timecode(self, current: str, total: str):
        """Update timecode display."""
        self.timecode_label.setText(f"{current} / {total}")
    
    def set_playing(self, is_playing: bool):
        """Set play state from external source (e.g., PlaybackController)."""
        self._is_playing = is_playing
        self.play_btn.setText("⏸" if is_playing else "▶")
    
    def on_position_update(self, time: float):
        """
        Called by PlaybackController when position changes.
        
        Args:
            time: Current position in seconds
        """
        # Update timecode display
        # (In real app, this would also trigger frame decoding/rendering)
        if self._duration > 0:
            current_str = self._format_time(time)
            total_str = self._format_time(self._duration)
            self.timecode_label.setText(f"{current_str} / {total_str}")
        
        # Update scrubber position (0-1000 range)
        if self._duration > 0:
            frac = time / self._duration
            # Block signal to avoid re-emitting seek_requested
            self.scrubber.blockSignals(True)
            self.scrubber.setValue(int(frac * 1000))
            self.scrubber.blockSignals(False)
    
    def set_duration(self, duration: float):
        """Set the media duration (called when video is loaded)."""
        self._duration = duration
        self.update_timecode("00:00:00", self._format_time(duration))
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS or MM:SS."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    
    # ===== Public API for video loading =====
    
    def load_video(self, path: str):
        """
        Load a video file for preview.
        
        Args:
            path: Path to the video file
        """
        self._current_video_path = path
        
        if self._media_player and HAS_QT_MULTIMEDIA:
            # Load into QMediaPlayer
            url = QUrl.fromLocalFile(str(path))
            self._media_player.setSource(url)
            # Note: duration_changed signal will fire when loaded
        else:
            # No multimedia support - just store path, use placeholder
            self._duration = 30.0  # Placeholder
            self.duration_changed.emit(self._duration)
            self.set_duration(30.0)
        
        # Note: Status bar is managed by MainWindow, not PreviewAreaWidget
        # No status bar message here to avoid AttributeError
    
    def play(self):
        """Start playback - public API."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.play()
        self.play_requested.emit()
    
    def pause(self):
        """Pause playback - public API."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.pause()
        self.pause_requested.emit()
    
    def stop(self):
        """Stop playback - public API."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.stop()
        self.stop_requested.emit()
    
    def seek(self, time_seconds: float):
        """Seek to position - public API."""
        if self._media_player and HAS_QT_MULTIMEDIA:
            self._media_player.setPosition(int(time_seconds * 1000))
        self.seek_requested.emit(time_seconds / max(self._duration, 1))
