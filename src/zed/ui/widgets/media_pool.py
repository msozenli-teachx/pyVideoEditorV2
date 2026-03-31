"""
Media Pool Widget

Left panel for managing media files (import, browse, organize).
Separated from backend - just UI presentation for now.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QFont


class MediaPoolWidget(QWidget):
    """
    Media Pool Panel - Manages imported media files.
    
    Features:
    - Import button for adding media
    - List view of media files
    - Drag & drop ready (placeholder for future)
    - Context menu ready (placeholder for future)
    
    Signals:
        import_requested: Emitted when user wants to import files
        media_selected: Emitted when a media item is selected (str path)
    """
    
    import_requested = pyqtSignal()
    media_selected = pyqtSignal(str)
    add_to_timeline_requested = pyqtSignal(str)  # Emits path of selected item to add to timeline
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the media pool UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Media Pool")
        title.setObjectName("PanelTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        
        # Import button
        self.import_btn = QPushButton("+ Import")
        self.import_btn.setObjectName("ImportButton")
        self.import_btn.setFixedHeight(28)
        self.import_btn.clicked.connect(self.import_requested)
        
        # Add to Timeline button
        self.add_timeline_btn = QPushButton("→ Timeline")
        self.add_timeline_btn.setObjectName("AddTimelineButton")
        self.add_timeline_btn.setFixedHeight(28)
        self.add_timeline_btn.clicked.connect(self._on_add_to_timeline)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.import_btn)
        header_layout.addWidget(self.add_timeline_btn)
        
        layout.addLayout(header_layout)
        
        # Media list (empty by default - populated via import)
        self.media_list = QListWidget()
        self.media_list.setObjectName("MediaList")
        self.media_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.media_list.itemClicked.connect(self._on_item_clicked)
        
        # No static demo items - user imports media via Import button
        
        layout.addWidget(self.media_list, stretch=1)
        
        # Info label
        info = QLabel("No media imported. Click + Import to add files.")
        info.setObjectName("HintLabel")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
    
    def _apply_styles(self):
        """Apply inline styles specific to this widget."""
        self.setStyleSheet("""
            #PanelTitle {
                color: #e0e0e0;
            }
            #MediaList {
                background-color: #1e1e22;
                border: 1px solid #2d2d32;
                border-radius: 6px;
                padding: 4px;
            }
            #MediaList::item {
                padding: 10px 12px;
                border-radius: 4px;
                margin: 2px;
            }
            #MediaList::item:hover {
                background-color: #3a3a3f;
            }
            #MediaList::item:selected {
                background-color: #4a6fa5;
                color: #ffffff;
            }
            #ImportButton {
                background-color: #4a6fa5;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                font-weight: 500;
                padding: 0 12px;
            }
            #ImportButton:hover {
                background-color: #5a7fb5;
            }
            #AddTimelineButton {
                background-color: #3a7a4a;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                font-weight: 500;
                padding: 0 12px;
            }
            #AddTimelineButton:hover {
                background-color: #4a8a5a;
            }
            #HintLabel {
                color: #6a6a6a;
                font-size: 11px;
                padding: 4px;
            }
        """)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle media selection - extract clean path and emit."""
        raw_path = item.data(Qt.ItemDataRole.UserRole)
        if raw_path:
            # Strip emoji prefix if present (demo items have "📹 " or "📄 " prefix)
            # Also handle cases where the full path might be stored
            clean_path = self._extract_clean_path(raw_path)
            self.media_selected.emit(clean_path)
    
    def _on_add_to_timeline(self):
        """Handle Add to Timeline button - emit selected item's path."""
        current_item = self.media_list.currentItem()
        if current_item:
            raw_path = current_item.data(Qt.ItemDataRole.UserRole)
            if raw_path:
                clean_path = self._extract_clean_path(raw_path)
                self.add_to_timeline_requested.emit(clean_path)
        else:
            # No selection - try to use the first item if any
            if self.media_list.count() > 0:
                first = self.media_list.item(0)
                raw_path = first.data(Qt.ItemDataRole.UserRole)
                if raw_path:
                    clean_path = self._extract_clean_path(raw_path)
                    self.add_to_timeline_requested.emit(clean_path)
    
    def _extract_clean_path(self, raw: str) -> str:
        """Extract a clean file path from potentially emoji-prefixed or demo string."""
        if not raw:
            return raw
        # If it looks like a real file path (exists or has path separators), use as-is
        if "/" in raw or "\\" in raw:
            return raw
        # Strip leading emoji and space (e.g., "📹 sample.mp4" -> "sample.mp4")
        # Common emoji prefixes: 📹, 📄, 🎵, 🖼️
        import re
        # Remove leading emoji + optional space
        cleaned = re.sub(r'^[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]+\s*', '', raw)
        return cleaned if cleaned else raw
    
    def add_media(self, path: str, display_name: str = None):
        """Add a media file to the pool."""
        # Check if already exists
        for i in range(self.media_list.count()):
            existing_item = self.media_list.item(i)
            existing_path = existing_item.data(Qt.ItemDataRole.UserRole)
            if existing_path == path:
                # Already exists, select it and return
                self.media_list.setCurrentItem(existing_item)
                return
        
        display = display_name or path.split("/")[-1]
        item = QListWidgetItem(f"📄 {display}")
        item.setData(Qt.ItemDataRole.UserRole, path)
        self.media_list.addItem(item)
        # Select the newly added item
        self.media_list.setCurrentItem(item)
    
    def clear_media(self):
        """Clear all media items."""
        self.media_list.clear()
