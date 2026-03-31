"""
Zed UI Module

Provides the graphical user interface for Zed Video Editor.
Separated from backend logic - widgets communicate via signals.

Components:
- MainWindow: Primary application window
- Widgets: Reusable UI components (MediaPool, Preview, Timeline, Controls)
- Styles: Dark theme QSS stylesheet

Usage:
    from zed.ui import MainWindow
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
"""

from .main_window import MainWindow
from .widgets import (
    MediaPoolWidget,
    PreviewAreaWidget,
    TimelineWidget,
    ControlsPanelWidget,
)

__all__ = [
    'MainWindow',
    'MediaPoolWidget',
    'PreviewAreaWidget',
    'TimelineWidget',
    'ControlsPanelWidget',
]
