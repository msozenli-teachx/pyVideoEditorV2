"""
Controls Panel Widget

Bottom bar with start/end time inputs, speed, fade, and export presets.
Separated from backend - emits signals for processing.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QDoubleSpinBox,
    QGroupBox, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from zed.operations import ExportPreset, EXPORT_PRESETS


class ControlsPanelWidget(QWidget):
    """
    Controls Panel - Bottom bar for processing operations.
    
    Features:
    - Start time input (seconds)
    - End time input (seconds)
    - Speed control (0.25x - 4.0x)
    - Fade in/out duration (seconds)
    - Export preset dropdown
    - Process button (triggers operation)
    - Duration display
    
    Signals:
        process_requested: User clicked Process (start, end, speed, fade_in, fade_out, preset)
        start_changed: Start time value changed (float)
        end_changed: End time value changed (float)
        speed_changed: Speed value changed (float)
        fade_in_changed: Fade in duration changed (float)
        fade_out_changed: Fade out duration changed (float)
        preset_changed: Export preset changed (str preset value)
    """
    
    process_requested = pyqtSignal(float, float, float, float, float, str)  # start, end, speed, fade_in, fade_out, preset
    start_changed = pyqtSignal(float)
    end_changed = pyqtSignal(float)
    speed_changed = pyqtSignal(float)
    fade_in_changed = pyqtSignal(float)
    fade_out_changed = pyqtSignal(float)
    preset_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the controls panel UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)
        
        # ===== Time inputs group =====
        time_frame = QFrame()
        time_frame.setObjectName("TimeInputsFrame")
        time_layout = QHBoxLayout(time_frame)
        time_layout.setContentsMargins(12, 8, 12, 8)
        time_layout.setSpacing(12)
        
        # Start time
        start_label = QLabel("Start:")
        start_label.setObjectName("FieldLabel")
        
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setObjectName("TimeSpinBox")
        self.start_spin.setRange(0.0, 99999.0)
        self.start_spin.setDecimals(2)
        self.start_spin.setSuffix(" s")
        self.start_spin.setValue(0.0)
        self.start_spin.setFixedWidth(100)
        self.start_spin.valueChanged.connect(self.start_changed)
        
        # End time
        end_label = QLabel("End:")
        end_label.setObjectName("FieldLabel")
        
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setObjectName("TimeSpinBox")
        self.end_spin.setRange(0.0, 99999.0)
        self.end_spin.setDecimals(2)
        self.end_spin.setSuffix(" s")
        self.end_spin.setValue(10.0)
        self.end_spin.setFixedWidth(100)
        self.end_spin.valueChanged.connect(self.end_changed)
        
        # Duration display
        self.duration_label = QLabel("Duration: 10.00 s")
        self.duration_label.setObjectName("DurationLabel")
        
        time_layout.addWidget(start_label)
        time_layout.addWidget(self.start_spin)
        time_layout.addSpacing(8)
        time_layout.addWidget(end_label)
        time_layout.addWidget(self.end_spin)
        time_layout.addSpacing(16)
        time_layout.addWidget(self.duration_label)
        time_layout.addStretch()
        
        layout.addWidget(time_frame)
        
        # ===== Speed control =====
        speed_frame = QFrame()
        speed_frame.setObjectName("SpeedFrame")
        speed_layout = QHBoxLayout(speed_frame)
        speed_layout.setContentsMargins(12, 8, 12, 8)
        speed_layout.setSpacing(8)
        
        speed_label = QLabel("Speed:")
        speed_label.setObjectName("FieldLabel")
        
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setObjectName("TimeSpinBox")
        self.speed_spin.setRange(0.25, 4.0)
        self.speed_spin.setDecimals(2)
        self.speed_spin.setSingleStep(0.25)
        self.speed_spin.setSuffix("x")
        self.speed_spin.setValue(1.0)
        self.speed_spin.setFixedWidth(80)
        self.speed_spin.valueChanged.connect(self.speed_changed)
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_spin)
        
        layout.addWidget(speed_frame)
        
        # ===== Fade controls =====
        fade_frame = QFrame()
        fade_frame.setObjectName("FadeFrame")
        fade_layout = QHBoxLayout(fade_frame)
        fade_layout.setContentsMargins(12, 8, 12, 8)
        fade_layout.setSpacing(8)
        
        fade_in_label = QLabel("Fade In:")
        fade_in_label.setObjectName("FieldLabel")
        
        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setObjectName("TimeSpinBox")
        self.fade_in_spin.setRange(0.0, 10.0)
        self.fade_in_spin.setDecimals(2)
        self.fade_in_spin.setSuffix(" s")
        self.fade_in_spin.setValue(0.0)
        self.fade_in_spin.setFixedWidth(80)
        self.fade_in_spin.valueChanged.connect(self.fade_in_changed)
        
        fade_out_label = QLabel("Fade Out:")
        fade_out_label.setObjectName("FieldLabel")
        
        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setObjectName("TimeSpinBox")
        self.fade_out_spin.setRange(0.0, 10.0)
        self.fade_out_spin.setDecimals(2)
        self.fade_out_spin.setSuffix(" s")
        self.fade_out_spin.setValue(0.0)
        self.fade_out_spin.setFixedWidth(80)
        self.fade_out_spin.valueChanged.connect(self.fade_out_changed)
        
        fade_layout.addWidget(fade_in_label)
        fade_layout.addWidget(self.fade_in_spin)
        fade_layout.addSpacing(8)
        fade_layout.addWidget(fade_out_label)
        fade_layout.addWidget(self.fade_out_spin)
        
        layout.addWidget(fade_frame)
        
        # ===== Export preset dropdown =====
        preset_frame = QFrame()
        preset_frame.setObjectName("PresetFrame")
        preset_layout = QHBoxLayout(preset_frame)
        preset_layout.setContentsMargins(12, 8, 12, 8)
        preset_layout.setSpacing(8)
        
        preset_label = QLabel("Preset:")
        preset_label.setObjectName("FieldLabel")
        
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("PresetCombo")
        self.preset_combo.setFixedWidth(180)
        
        # Populate presets
        for preset in ExportPreset:
            config = EXPORT_PRESETS[preset]
            self.preset_combo.addItem(config['name'], preset.value)
        
        # Default to H264 Medium
        self.preset_combo.setCurrentIndex(1)  # H264_MEDIUM
        
        # Use currentIndexChanged since currentDataChanged doesn't exist in PyQt6 QComboBox
        # When index changes, emit the preset value via currentData()
        def on_preset_changed(index):
            data = self.preset_combo.currentData()
            if data:
                self.preset_changed.emit(data)
        
        self.preset_combo.currentIndexChanged.connect(on_preset_changed)
        
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.preset_combo)
        
        layout.addWidget(preset_frame)
        
        # Add stretch to push process button to the right
        layout.addStretch()
        
        # ===== Process button =====
        self.process_btn = QPushButton("▶ Process")
        self.process_btn.setObjectName("ProcessButton")
        self.process_btn.setFixedHeight(40)
        self.process_btn.setFixedWidth(140)
        self.process_btn.clicked.connect(self._on_process)
        
        layout.addWidget(self.process_btn)
    
    def _apply_styles(self):
        """Apply inline styles."""
        self.setStyleSheet("""
            #TimeInputsFrame, #SpeedFrame, #FadeFrame, #PresetFrame {
                background-color: #222226;
                border: 1px solid #2d2d32;
                border-radius: 8px;
            }
            #FieldLabel {
                color: #a0a0a0;
                font-size: 12px;
                font-weight: 500;
            }
            #TimeSpinBox {
                background-color: #1e1e22;
                border: 1px solid #3a3a3f;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e0e0e0;
                font-family: "Consolas", monospace;
            }
            #TimeSpinBox:focus {
                border-color: #4a6fa5;
            }
            #DurationLabel {
                color: #6a6a6a;
                font-size: 11px;
                font-family: "Consolas", monospace;
            }
            #PresetCombo {
                background-color: #1e1e22;
                border: 1px solid #3a3a3f;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e0e0e0;
                font-size: 11px;
            }
            #PresetCombo:focus {
                border-color: #4a6fa5;
            }
            #PresetCombo::drop-down {
                border: none;
            }
            #ProcessButton {
                background-color: #4a6fa5;
                border: none;
                border-radius: 8px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
            #ProcessButton:hover {
                background-color: #5a7fb5;
            }
            #ProcessButton:pressed {
                background-color: #3a5f95;
            }
        """)
    
    def _on_process(self):
        """Handle process button click - emit all current settings."""
        start = self.start_spin.value()
        end = self.end_spin.value()
        speed = self.speed_spin.value()
        fade_in = self.fade_in_spin.value()
        fade_out = self.fade_out_spin.value()
        preset = self.preset_combo.currentData() or ExportPreset.H264_MEDIUM.value
        self.process_requested.emit(start, end, speed, fade_in, fade_out, preset)
    
    def get_time_range(self) -> tuple:
        """Get current start and end times."""
        return (self.start_spin.value(), self.end_spin.value())
    
    def set_time_range(self, start: float, end: float):
        """Set start and end times."""
        self.start_spin.setValue(start)
        self.end_spin.setValue(end)
        self._update_duration()
    
    def get_speed(self) -> float:
        """Get current speed multiplier."""
        return self.speed_spin.value()
    
    def set_speed(self, speed: float):
        """Set speed multiplier."""
        self.speed_spin.setValue(speed)
    
    def get_fade_in(self) -> float:
        """Get fade in duration in seconds."""
        return self.fade_in_spin.value()
    
    def set_fade_in(self, duration: float):
        """Set fade in duration."""
        self.fade_in_spin.setValue(duration)
    
    def get_fade_out(self) -> float:
        """Get fade out duration in seconds."""
        return self.fade_out_spin.value()
    
    def set_fade_out(self, duration: float):
        """Set fade out duration."""
        self.fade_out_spin.setValue(duration)
    
    def get_preset(self) -> str:
        """Get current export preset value."""
        return self.preset_combo.currentData() or ExportPreset.H264_MEDIUM.value
    
    def set_preset(self, preset_value: str):
        """Set export preset by value."""
        index = self.preset_combo.findData(preset_value)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
    
    def _update_duration(self):
        """Update duration label."""
        duration = self.end_spin.value() - self.start_spin.value()
        self.duration_label.setText(f"Duration: {duration:.2f} s")
    
    def on_start_changed(self, value: float):
        """Called when start changes."""
        self._update_duration()
    
    def on_end_changed(self, value: float):
        """Called when end changes."""
        self._update_duration()
