"""
Playback Controller

Central controller for synchronized playback state across the UI.
Follows Observer (Pub-Sub) pattern using PyQt signals/slots.

This is the single source of truth for:
- Playback position (current time in seconds)
- Playing state (playing/paused/stopped)
- Media duration

All UI components (Preview, Timeline, Transport) react to this controller's signals.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from typing import Optional


class PlaybackController(QObject):
    """
    Central controller for video playback synchronization.
    
    State:
        position: Current playback position in seconds
        duration: Total media duration in seconds
        is_playing: True if currently playing
    
    Signals:
        position_changed(float): Emitted when position updates (every frame during play)
        playing_changed(bool): Emitted when play/pause state changes
        duration_changed(float): Emitted when media duration is set
    
    Usage:
        controller = PlaybackController()
        
        # Connect widgets
        controller.position_changed.connect(timeline.on_position_update)
        controller.position_changed.connect(preview.on_position_update)
        controller.playing_changed.connect(preview.set_playing)
        
        # Widget signals → controller methods
        preview.play_requested.connect(controller.play)
        preview.pause_requested.connect(controller.pause)
        preview.seek_requested.connect(lambda frac: controller.seek(frac * controller.duration))
        
        # Start playback
        controller.set_duration(60.0)  # 60 second video
        controller.play()
    """
    
    # Outgoing signals (broadcast state changes to all connected widgets)
    position_changed = pyqtSignal(float)    # Current time in seconds
    playing_changed = pyqtSignal(bool)      # True = playing, False = paused/stopped
    duration_changed = pyqtSignal(float)    # Total duration in seconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._position = 0.0
        self._duration = 0.0
        self._is_playing = False
        
        # Frame timer (drives position updates during playback)
        # ~60fps = 16ms per frame
        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(16)
        self._frame_timer.timeout.connect(self._on_frame_tick)
        
        # Playback rate (1.0 = normal speed)
        self._playback_rate = 1.0
    
    # ===== Properties =====
    
    @property
    def position(self) -> float:
        """Current playback position in seconds."""
        return self._position
    
    @property
    def duration(self) -> float:
        """Total media duration in seconds."""
        return self._duration
    
    @property
    def is_playing(self) -> bool:
        """True if playback is active."""
        return self._is_playing
    
    @property
    def playback_rate(self) -> float:
        """Playback speed (1.0 = normal)."""
        return self._playback_rate
    
    # ===== Public Methods =====
    
    def set_duration(self, duration: float):
        """Set the total media duration."""
        if duration != self._duration:
            self._duration = max(0.0, duration)
            self.duration_changed.emit(self._duration)
    
    def set_playback_rate(self, rate: float):
        """Set playback speed."""
        self._playback_rate = max(0.1, rate)
    
    def play(self):
        """Start or resume playback."""
        if not self._is_playing and self._duration > 0:
            self._is_playing = True
            self._frame_timer.start()
            self.playing_changed.emit(True)
    
    def pause(self):
        """Pause playback (position preserved)."""
        if self._is_playing:
            self._is_playing = False
            self._frame_timer.stop()
            self.playing_changed.emit(False)
    
    def stop(self):
        """Stop playback and reset position to 0."""
        was_playing = self._is_playing
        self._frame_timer.stop()
        self._is_playing = False
        self._position = 0.0
        
        if was_playing:
            self.playing_changed.emit(False)
        
        self.position_changed.emit(0.0)
    
    def seek(self, time: float):
        """
        Jump to a specific time position.
        
        Args:
            time: Target position in seconds
        """
        new_pos = max(0.0, min(time, self._duration))
        if new_pos != self._position:
            self._position = new_pos
            self.position_changed.emit(self._position)
    
    def seek_normalized(self, fraction: float):
        """
        Seek to a position given as a fraction of total duration.
        
        Args:
            fraction: 0.0 to 1.0
        """
        self.seek(fraction * self._duration)
    
    def toggle_play_pause(self):
        """Toggle between play and pause."""
        if self._is_playing:
            self.pause()
        else:
            self.play()
    
    # ===== Private Methods =====
    
    def _on_frame_tick(self):
        """
        Called every frame (~16ms) during playback.
        Advances position and emits updates.
        """
        # Advance position based on playback rate
        # 16ms = 0.016s per tick
        delta = 0.016 * self._playback_rate
        new_pos = self._position + delta
        
        if new_pos >= self._duration:
            # Reached end of media
            self._position = self._duration
            self.position_changed.emit(self._position)
            self.stop()
        else:
            self._position = new_pos
            self.position_changed.emit(self._position)
    
    # ===== Utility =====
    
    def reset(self):
        """Reset controller to initial state."""
        self.stop()
        self._duration = 0.0
        self._position = 0.0
        self.duration_changed.emit(0.0)
