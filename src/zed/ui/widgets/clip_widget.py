"""
Clip Widget

Visual representation of a clip on the timeline track.
Handles display, selection, and basic interactions.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QMouseEvent

from zed.operations import Clip


class ClipWidget(QFrame):
    """
    Visual widget representing a clip on a timeline track.
    
    Features:
    - Visual display with clip name and duration
    - Selection state (highlighted when selected)
    - Color coding by track type
    - Handles mouse events for selection
    
    Signals:
        clicked: Emitted when clip is clicked (str clip_id)
        double_clicked: Emitted on double click (str clip_id)
    """
    
    clicked = pyqtSignal(str)  # clip_id
    double_clicked = pyqtSignal(str)  # clip_id
    
    # Color schemes for different states
    COLORS = {
        'video': {
            'normal': {'bg': '#3a5a8a', 'border': '#4a7ab5', 'text': '#ffffff'},
            'selected': {'bg': '#5a8aca', 'border': '#7aaae5', 'text': '#ffffff'},
            'hover': {'bg': '#4a6a9a', 'border': '#5a8aca', 'text': '#ffffff'},
        },
        'audio': {
            'normal': {'bg': '#3a7a4a', 'border': '#4a9a5a', 'text': '#ffffff'},
            'selected': {'bg': '#5a9a6a', 'border': '#6aba7a', 'text': '#ffffff'},
            'hover': {'bg': '#4a8a5a', 'border': '#5a9a6a', 'text': '#ffffff'},
        },
        'effects': {
            'normal': {'bg': '#7a4a8a', 'border': '#9a5aaa', 'text': '#ffffff'},
            'selected': {'bg': '#9a6aaa', 'border': '#ba8aca', 'text': '#ffffff'},
            'hover': {'bg': '#8a5a9a', 'border': '#9a6aaa', 'text': '#ffffff'},
        },
    }
    
    def __init__(self, clip: Clip, parent=None, scale: float = 10.0):
        """
        Initialize the clip widget.
        
        Args:
            clip: The Clip data model
            parent: Parent widget
            scale: Pixels per second for width calculation
        """
        super().__init__(parent)
        self._clip = clip
        self._scale = scale  # pixels per second
        self._is_selected = False
        self._is_hovered = False
        self._track_type = self._get_track_type(clip.track)
        
        self.setObjectName("ClipWidget")
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Calculate size based on timeline duration
        self._update_size()
        
        self._setup_ui()
        self._apply_styles()
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
    
    def _get_track_type(self, track_index: int) -> str:
        """Determine track type from index."""
        if track_index == 0:
            return 'video'
        elif track_index == 1:
            return 'audio'
        else:
            return 'effects'
    
    def _update_size(self):
        """Update widget size based on clip duration and scale."""
        duration = self._clip.timeline_duration
        width = max(60, int(duration * self._scale))  # Minimum 60px width
        self.setFixedWidth(width)
        self.setFixedHeight(44)  # Slightly smaller than track height (60)
    
    def _setup_ui(self):
        """Build the clip widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        
        # Clip name label
        self.name_label = QLabel(self._clip.name or "Untitled")
        self.name_label.setObjectName("ClipNameLabel")
        self.name_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.name_label.setStyleSheet("color: #ffffff; background: transparent;")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.name_label.setWordWrap(False)
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # Duration label
        duration_text = f"{self._clip.timeline_duration:.1f}s"
        self.duration_label = QLabel(duration_text)
        self.duration_label.setObjectName("ClipDurationLabel")
        self.duration_label.setFont(QFont("Consolas", 8))
        self.duration_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); background: transparent;")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(self.name_label, stretch=1)
        layout.addWidget(self.duration_label)
        
        layout.addStretch()
    
    def _apply_styles(self):
        """Apply styles based on current state."""
        colors = self.COLORS[self._track_type]
        
        if self._is_selected:
            scheme = colors['selected']
        elif self._is_hovered:
            scheme = colors['hover']
        else:
            scheme = colors['normal']
        
        self.setStyleSheet(f"""
            ClipWidget {{
                background-color: {scheme['bg']};
                border: 2px solid {scheme['border']};
                border-radius: 6px;
            }}
            ClipWidget:hover {{
                background-color: {colors['hover']['bg']};
                border-color: {colors['hover']['border']};
            }}
        """)
    
    def set_selected(self, selected: bool):
        """Set the selection state."""
        if self._is_selected != selected:
            self._is_selected = selected
            self._apply_styles()
            # Raise to front when selected
            if selected:
                self.raise_()
    
    def is_selected(self) -> bool:
        """Get selection state."""
        return self._is_selected
    
    def get_clip_id(self) -> str:
        """Get the clip ID."""
        return self._clip.id
    
    def get_clip(self) -> Clip:
        """Get the clip data model."""
        return self._clip
    
    def set_scale(self, scale: float):
        """Update the scale and resize."""
        self._scale = scale
        self._update_size()
    
    def update_clip_data(self, clip: Clip):
        """Update the clip data and refresh display."""
        self._clip = clip
        self.name_label.setText(clip.name or "Untitled")
        self.duration_label.setText(f"{clip.timeline_duration:.1f}s")
        self._update_size()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press - emit clicked signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._clip.id)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double click - emit double_clicked signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self._clip.id)
        super().mouseDoubleClickEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter - hover effect."""
        self._is_hovered = True
        self._apply_styles()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave - remove hover effect."""
        self._is_hovered = False
        self._apply_styles()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        """Custom paint for rounded corners and effects."""
        super().paintEvent(event)
        
        # Add a subtle gradient effect or indicators
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw fade indicators if applicable
        if self._clip.fade_in > 0 or self._clip.fade_out > 0:
            width = self.width()
            height = self.height()
            
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
            
            if self._clip.fade_in > 0:
                # Draw fade in indicator (left side)
                fade_width = min(int(self._clip.fade_in * self._scale), width // 4)
                for i in range(fade_width):
                    alpha = int(100 * (1 - i / fade_width))
                    painter.setPen(QPen(QColor(255, 255, 255, alpha), 1))
                    painter.drawLine(i, 2, i, height - 2)
            
            if self._clip.fade_out > 0:
                # Draw fade out indicator (right side)
                fade_width = min(int(self._clip.fade_out * self._scale), width // 4)
                for i in range(fade_width):
                    alpha = int(100 * (1 - i / fade_width))
                    painter.setPen(QPen(QColor(255, 255, 255, alpha), 1))
                    painter.drawLine(width - i - 1, 2, width - i - 1, height - 2)


__all__ = ['ClipWidget']
