"""
Main Window

The primary application window for Zed Video Editor.
Integrates all UI components with a dark theme dashboard layout.

Layout Structure (following Composite pattern for extensibility):
    ┌─────────────────────────────────────────────────────────┐
    │  Menu Bar                                               │
    ├───────────────┬───────────────────────┬─────────────────┤
    │               │                       │                 │
    │   Media       │      Preview          │   Properties    │
    │   Pool        │      Area             │   (Future)      │
    │   (Left)      │      (Center)         │   (Right)       │
    │               │                       │                 │
    ├───────────────┴───────────────────────┴─────────────────┤
    │                                                         │
    │         Multi-Track Timeline (Bottom)                   │
    │                                                         │
    ├─────────────────────────────────────────────────────────┤
    │  [Start: ___] [End: ___]              [▶ Process]      │
    └─────────────────────────────────────────────────────────┘

UI Layer is separated from backend:
- All backend calls go through signals
- No direct FFmpeg/TaskManager calls here
- Future: Connect signals to backend controllers
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QStatusBar, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QFont

from .widgets import (
    MediaPoolWidget,
    PreviewAreaWidget,
    TimelineWidget,
    ControlsPanelWidget,
)
from .controllers import PlaybackController

# Backend imports (UI remains separate, only called here for actions)
from zed.ffmpeg import FFmpegEngine, ProcessResult
from zed.config import get_config
from zed.operations import VideoClipper, Clip, ExportPreset, get_preset_config


class MainWindow(QMainWindow):
    """
    Main Application Window for Zed Video Editor.
    
    Features:
    - Dark theme dashboard
    - Three-panel main area (Media Pool | Preview | Properties)
    - Multi-track timeline at bottom
    - Controls panel with time inputs and process button
    - Menu bar and status bar
    - UI separated from backend logic (signals only)
    
    Signals from child widgets can be connected to backend controllers:
    - media_pool.import_requested → backend file dialog
    - preview.play_requested → backend playback
    - timeline.position_changed → backend seek
    - controls.process_requested → backend video processing
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Zed Video Editor")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)
        
        # Backend (created lazily, only when needed for processing)
        self._ffmpeg_engine: FFmpegEngine = None
        self._current_video_path: str = None
        
        # Playback synchronization controller
        self._playback_controller: PlaybackController = None
        
        self._setup_ui()
        self._apply_styles()
        self._create_menus()
        self._connect_signals()
        self._wire_playback_controller()
    
    def _setup_ui(self):
        """Build the main window layout."""
        # Central widget
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main splitter (horizontal: left | center | right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setObjectName("MainSplitter")
        main_splitter.setHandleWidth(2)
        
        # Left: Media Pool
        self.media_pool = MediaPoolWidget()
        self.media_pool.setObjectName("MediaPoolPanel")
        self.media_pool.setMinimumWidth(200)
        self.media_pool.setMaximumWidth(350)
        
        # Center: Preview Area (expands)
        self.preview = PreviewAreaWidget()
        self.preview.setObjectName("PreviewPanel")
        
        # Right: Properties Panel (placeholder for future)
        self.properties_panel = QWidget()
        self.properties_panel.setObjectName("PropertiesPanel")
        self.properties_panel.setMinimumWidth(180)
        self.properties_panel.setMaximumWidth(280)
        
        props_layout = QVBoxLayout(self.properties_panel)
        props_layout.setContentsMargins(8, 8, 8, 8)
        
        props_title = QLabel("Properties")
        props_title.setObjectName("PanelTitle")
        props_title_font = QFont()
        props_title_font.setBold(True)
        props_title_font.setPointSize(12)
        props_title.setFont(props_title_font)
        
        props_hint = QLabel("Select a clip or effect\non the timeline to edit")
        props_hint.setObjectName("HintLabel")
        props_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        props_hint.setWordWrap(True)
        
        props_layout.addWidget(props_title)
        props_layout.addWidget(props_hint)
        props_layout.addStretch()
        
        # Add to main splitter
        main_splitter.addWidget(self.media_pool)
        main_splitter.addWidget(self.preview)
        main_splitter.addWidget(self.properties_panel)
        
        # Set splitter sizes (left | center | right)
        main_splitter.setSizes([220, 800, 200])
        
        main_layout.addWidget(main_splitter, stretch=1)
        
        # Bottom: Timeline
        self.timeline = TimelineWidget()
        self.timeline.setObjectName("TimelinePanel")
        self.timeline.setMinimumHeight(200)
        self.timeline.setMaximumHeight(300)
        
        main_layout.addWidget(self.timeline)
        
        # Bottom: Controls Panel
        self.controls = ControlsPanelWidget()
        self.controls.setObjectName("ControlsPanel")
        self.controls.setFixedHeight(60)
        
        main_layout.addWidget(self.controls)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.setObjectName("StatusBar")
        
        status_label = QLabel("Ready — Import media to begin")
        self.status_bar.addWidget(status_label)
        
        version_label = QLabel("Zed v0.1.0")
        version_label.setObjectName("VersionLabel")
        self.status_bar.addPermanentWidget(version_label)
    
    def _apply_styles(self):
        """Apply dark theme QSS stylesheet."""
        # Load external QSS file
        qss_path = os.path.join(os.path.dirname(__file__), "styles", "dark_theme.qss")
        
        try:
            with open(qss_path, 'r') as f:
                qss = f.read()
            self.setStyleSheet(qss)
        except FileNotFoundError:
            # Fallback inline styles if QSS not found
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1a1a1e;
                    color: #e0e0e0;
                    font-family: "Segoe UI", sans-serif;
                }
                #PanelTitle {
                    color: #e0e0e0;
                    font-weight: bold;
                }
                #HintLabel {
                    color: #6a6a6a;
                    font-size: 11px;
                }
                #StatusBar {
                    background-color: #222226;
                    color: #a0a0a0;
                }
            """)
        
        # Additional inline adjustments
        self.setStyleSheet(self.styleSheet() + """
            #CentralWidget {
                background-color: #1a1a1e;
            }
            #MainSplitter::handle {
                background-color: #2d2d32;
                width: 2px;
            }
            #MediaPoolPanel, #PreviewPanel, #PropertiesPanel, #TimelinePanel {
                background-color: #1a1a1e;
            }
            #VersionLabel {
                color: #6a6a6a;
                font-size: 11px;
                padding-right: 8px;
            }
        """)
    
    def _create_menus(self):
        """Create menu bar."""
        menubar = self.menuBar()
        menubar.setObjectName("MenuBar")
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        import_action = QAction("Import Media...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.media_pool.import_requested)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("Export...", self)
        export_action.setShortcut("Ctrl+E")
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        # Split clip at current playhead position
        split_action = QAction("Split Clip", self)
        split_action.setShortcut("Ctrl+Shift+S")
        split_action.triggered.connect(self._on_split_clip)
        edit_menu.addAction(split_action)
        
        # Duplicate selected clip
        duplicate_action = QAction("Duplicate Clip", self)
        duplicate_action.setShortcut("Ctrl+D")
        duplicate_action.triggered.connect(self._on_duplicate_clip)
        edit_menu.addAction(duplicate_action)
        
        edit_menu.addSeparator()
        
        # Delete selected clip
        delete_action = QAction("Delete Clip", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self._on_delete_clip)
        edit_menu.addAction(delete_action)
        
        edit_menu.addSeparator()
        
        # Undo/Redo (placeholders for future)
        edit_menu.addAction("Undo", lambda: None)
        edit_menu.addAction("Redo", lambda: None)
        
        # View menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Toggle Media Pool", lambda: None)
        view_menu.addAction("Toggle Timeline", lambda: None)
        view_menu.addAction("Toggle Properties", lambda: None)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About Zed", lambda: None)
    
    def _connect_signals(self):
        """Connect internal widget signals."""
        # Controls: update duration when start/end changes
        self.controls.start_changed.connect(self.controls.on_start_changed)
        self.controls.end_changed.connect(self.controls.on_end_changed)
        
        # Process button → backend processing with all parameters
        self.controls.process_requested.connect(self._on_process_requested)
        
        # Media pool import
        self.media_pool.import_requested.connect(self._on_import_requested)
        self.media_pool.media_selected.connect(self._on_media_selected)
        self.media_pool.add_to_timeline_requested.connect(self._on_add_to_timeline)
        
        # Timeline: clip selection syncs with controls panel
        self.timeline.clip_selected.connect(self._on_timeline_clip_selected)
    
    def _wire_playback_controller(self):
        """Create and wire the PlaybackController to all UI components."""
        self._playback_controller = PlaybackController()
        
        # Controller → Preview (for state coordination)
        self._playback_controller.position_changed.connect(self.preview.on_position_update)
        self._playback_controller.playing_changed.connect(self.preview.set_playing)
        self._playback_controller.duration_changed.connect(self.preview.set_duration)
        
        # Controller → Timeline
        self._playback_controller.position_changed.connect(self.timeline.on_position_update)
        self._playback_controller.duration_changed.connect(self.timeline.set_duration)
        
        # Preview → Controller (transport controls)
        self.preview.play_requested.connect(self._playback_controller.play)
        self.preview.pause_requested.connect(self._playback_controller.pause)
        self.preview.stop_requested.connect(self._playback_controller.stop)
        self.preview.seek_requested.connect(
            lambda frac: self._playback_controller.seek_normalized(frac)
        )
        
        # Preview → Timeline (direct sync from QMediaPlayer for real video)
        self.preview.position_changed.connect(self.timeline.on_position_update)
        self.preview.duration_changed.connect(self.timeline.set_duration)
        
        # Timeline → Controller (playhead/scrubbing)
        self.timeline.position_changed.connect(
            lambda frac: self._playback_controller.seek_normalized(frac)
        )
        
        # Controls → Controller (if duration changes via process panel)
        # (Optional: could sync controls with controller if needed)
    
    def _on_process_requested(
        self,
        start: float,
        end: float,
        speed: float = 1.0,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
        preset: str = "h264_medium"
    ):
        """Handle Process button: clip video with speed, fade, and export preset."""
        if not self._current_video_path:
            self.status_bar.showMessage("Please import a video first.", 3000)
            QMessageBox.warning(self, "No Video", "Please import a video before processing.")
            return
        
        if end <= start:
            self.status_bar.showMessage("End time must be greater than start time.", 3000)
            return
        
        preset_name = get_preset_config(ExportPreset(preset))['name']
        self.status_bar.showMessage(
            f"Processing: {start:.2f}s → {end:.2f}s @ {speed}x, fade {fade_in}/{fade_out}s, {preset_name}...", 
            0
        )
        
        try:
            engine = self._get_ffmpeg_engine()
            
            # Generate output path
            input_path = Path(self._current_video_path)
            output_dir = get_config().ffmpeg.default_output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{input_path.stem}_clip{input_path.suffix}"
            
            # Build command with all effects
            builder = engine.create_command()
            builder.input(input_path).output(output_file)
            builder.start_time(start)
            builder.end_time(end)
            
            # Get preset config
            preset_config = get_preset_config(ExportPreset(preset))
            if preset_config['video_codec']:
                builder.video_codec(preset_config['video_codec'])
            if preset_config['audio_codec']:
                builder.audio_codec(preset_config['audio_codec'])
            if preset_config['video_bitrate']:
                builder.video_bitrate(preset_config['video_bitrate'])
            if preset_config['audio_bitrate']:
                builder.audio_bitrate(preset_config['audio_bitrate'])
            
            # Speed adjustment via setpts filter
            vf_filters = []
            if speed != 1.0:
                # setpts=PTS/{speed} for video, atempo for audio (limited to 0.5-2.0 range)
                vf_filters.append(f"setpts=PTS/{speed}")
            
            # Fade filters
            if fade_in > 0:
                vf_filters.append(f"fade=t=in:st=0:d={fade_in}")
            if fade_out > 0:
                # Fade out starts at (duration - fade_out) in output time
                output_duration = (end - start) / speed
                fade_start = max(0, output_duration - fade_out)
                vf_filters.append(f"fade=t=out:st={fade_start}:d={fade_out}")
            
            if vf_filters:
                builder.extra("-vf", ",".join(vf_filters))
            
            # Audio tempo for speed (only if 0.5 <= speed <= 2.0)
            if speed != 1.0 and 0.5 <= speed <= 2.0:
                builder.extra("-af", f"atempo={speed}")
            
            builder.description(f"Clip {input_path.name} with effects")
            command = builder.build()
            
            result: ProcessResult = engine.execute(command)
            
            if result.success:
                self.status_bar.showMessage(f"✓ Exported: {output_file}", 5000)
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Processed video saved to:\n{output_file}"
                )
            else:
                self.status_bar.showMessage(f"✗ Export failed: {result.error_message}", 5000)
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to process video:\n{result.error_message}"
                )
        
        except Exception as e:
            self.status_bar.showMessage(f"✗ Error: {e}", 5000)
            QMessageBox.critical(self, "Error", str(e))
    
    def _on_timeline_clip_selected(self, clip_id: str):
        """Handle timeline clip selection - sync controls panel."""
        clip = self.timeline.get_clip(clip_id)
        if clip:
            # Update controls panel with clip properties
            self.controls.set_time_range(clip.start_time, clip.end_time)
            self.controls.set_speed(clip.speed)
            self.controls.set_fade_in(clip.fade_in)
            self.controls.set_fade_out(clip.fade_out)
    
    # ===== Clip Editing Operations =====
    
    def _on_split_clip(self):
        """Split the selected clip at the current playhead position."""
        clip = self.timeline.get_selected_clip()
        if not clip:
            self.status_bar.showMessage("No clip selected to split.", 3000)
            return
        
        # Get current playhead position from playback controller
        playhead = self._playback_controller.position if self._playback_controller else 0.0
        
        # Playhead position is absolute; clip times are relative to source
        # For simplicity, split if playhead is within the clip's source range
        if not (clip.start_time < playhead < clip.end_time):
            self.status_bar.showMessage("Playhead must be within the selected clip to split.", 3000)
            return
        
        # Create two clips: [start → playhead] and [playhead → end]
        clip1 = clip.copy(new_id=True)
        clip1.end_time = playhead
        clip1.name = f"{clip.name} (part 1)"
        
        clip2 = clip.copy(new_id=True)
        clip2.start_time = playhead
        clip2.name = f"{clip.name} (part 2)"
        
        # Remove original, add the two parts
        self.timeline.remove_clip(clip.id)
        self.timeline.add_clip(clip1)
        self.timeline.add_clip(clip2)
        self.timeline.select_clip(clip2.id)  # Select the second part
        
        self.status_bar.showMessage(f"Split clip at {playhead:.2f}s", 3000)
    
    def _on_duplicate_clip(self):
        """Duplicate the selected clip."""
        clip = self.timeline.get_selected_clip()
        if not clip:
            self.status_bar.showMessage("No clip selected to duplicate.", 3000)
            return
        
        new_clip = clip.copy(new_id=True)
        new_clip.name = f"{clip.name} (copy)"
        # Offset slightly so copies don't overlap exactly
        new_clip.start_time += 1.0
        new_clip.end_time += 1.0
        
        self.timeline.add_clip(new_clip)
        self.timeline.select_clip(new_clip.id)
        
        self.status_bar.showMessage(f"Duplicated: {clip.name}", 3000)
    
    def _on_delete_clip(self):
        """Delete the selected clip from the timeline."""
        clip = self.timeline.get_selected_clip()
        if not clip:
            self.status_bar.showMessage("No clip selected to delete.", 3000)
            return
        
        clip_name = clip.name
        self.timeline.remove_clip(clip.id)
        
        self.status_bar.showMessage(f"Deleted: {clip_name}", 3000)
    
    def _on_import_requested(self):
        """Open file dialog to import a video."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Video",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)"
        )
        
        if path:
            self._load_video_path(path)
    
    def _on_media_selected(self, path: str):
        """Handle media pool selection - load video for preview."""
        # Extract actual path (strip emoji prefix if present)
        if path and Path(path).exists():
            self._load_video_path(path)
        else:
            # Try to find the file (demo items have emoji prefix)
            # For demo, just use the path as-is
            self._load_video_path(path)
    
    def _on_add_to_timeline(self, path: str):
        """Handle Add to Timeline button - add selected media pool item to timeline."""
        if not path:
            self.status_bar.showMessage("No media selected to add to timeline.", 3000)
            return
        if not Path(path).exists():
            self.status_bar.showMessage(f"File not found: {path}", 3000)
            return
        
        # Add as a new clip to timeline
        clip = self.timeline.add_clip_from_source(
            source_file=path,
            start_time=0.0,
            end_time=60.0,
            name=Path(path).stem
        )
        self.timeline.select_clip(clip.id)
        self.status_bar.showMessage(f"Added to timeline: {Path(path).name}", 3000)
    
    def _load_video_path(self, path: str):
        """Common handler to load a video path."""
        self._current_video_path = path
        self.preview.load_video(path)
        self.status_bar.showMessage(f"Loaded: {Path(path).name}", 3000)
        
        # Add to media pool so user can see/manage imported files
        self.media_pool.add_media(path)
        
        # Add to timeline as a clip (track 0 = video)
        # For now, use default timing - full video assumed
        # In future, we could probe the file to get actual duration
        clip = self.timeline.add_clip_from_source(
            source_file=path,
            start_time=0.0,
            end_time=60.0,  # Default 60s - will be overridden by user
            name=Path(path).stem
        )
        # Auto-select this new clip
        self.timeline.select_clip(clip.id)
    
    def _get_ffmpeg_engine(self) -> FFmpegEngine:
        """Lazy-create the FFmpeg engine."""
        if self._ffmpeg_engine is None:
            self._ffmpeg_engine = FFmpegEngine()
        return self._ffmpeg_engine
    
    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        # Future: Adjust layouts dynamically if needed
