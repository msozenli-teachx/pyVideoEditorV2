#!/usr/bin/env python3
"""
Zed Video Editor - Main Entry Point

This is the main entry point for the Zed video editing application.

Usage:
    python main.py              # Run core foundation demo
    python main.py --gui        # Launch the GUI (requires PyQt6)

The GUI is a dark theme dashboard with:
- Media Pool (left) - manage imported files
- Preview Area (center) - video playback
- Properties Panel (right) - future editing controls
- Multi-track Timeline (bottom)
- Controls with start/end inputs and process button

UI is separated from backend - all widgets communicate via signals.
"""

import sys
import argparse
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from zed import (
    ZedApp,
    ZedConfig,
    FFmpegEngine,
    TaskManager,
    VideoClipper,
    get_logger,
    configure_logging,
    logging,
)


def demo_logging():
    """Demonstrate the logging system."""
    print("\n" + "="*60)
    print("DEMO: Logging System")
    print("="*60)
    
    # Configure logging
    configure_logging(
        level=logging.DEBUG,
        console_output=True,
        file_output=False,
    )
    
    logger = get_logger('demo')
    logger.info("Logging system initialized")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message (for demonstration)")
    
    print("✓ Logging system working correctly")


def demo_config():
    """Demonstrate the configuration system."""
    print("\n" + "="*60)
    print("DEMO: Configuration System")
    print("="*60)
    
    config = ZedConfig()
    
    print(f"App Name: {config.app_name}")
    print(f"App Version: {config.app_version}")
    print(f"FFmpeg Path: {config.ffmpeg.resolve_ffmpeg_path()}")
    print(f"Default Video Codec: {config.ffmpeg.default_video_codec}")
    print(f"Max Concurrent Tasks: {config.tasks.max_concurrent_tasks}")
    print(f"Output Directory: {config.ffmpeg.default_output_dir}")
    
    print("✓ Configuration system working correctly")


def demo_ffmpeg_engine():
    """Demonstrate the FFmpeg engine (command building)."""
    print("\n" + "="*60)
    print("DEMO: FFmpeg Engine - Command Building")
    print("="*60)
    
    engine = FFmpegEngine()
    
    # Build a clipping command
    command = (
        engine.create_command()
        .input('input_video.mp4')
        .output('output_clip.mp4')
        .start_time(10.0)
        .duration(30.0)
        .video_codec('libx264')
        .audio_codec('aac')
        .description('Example video clip')
        .build()
    )
    
    print(f"Command Description: {command.description}")
    print(f"Input Files: {command.input_files}")
    print(f"Output File: {command.output_file}")
    print(f"Shell Command: {command.to_shell_string()}")
    
    print("✓ FFmpeg command builder working correctly")


def demo_task_manager():
    """Demonstrate the task manager."""
    print("\n" + "="*60)
    print("DEMO: Task Manager")
    print("="*60)
    
    task_manager = TaskManager()
    
    # Submit some example tasks
    def sample_task(x):
        import time
        time.sleep(0.1)
        return x * 2
    
    task1_id = task_manager.submit(sample_task, 5, name="Double 5")
    task2_id = task_manager.submit(sample_task, 10, name="Double 10")
    task3_id = task_manager.submit(sample_task, 15, name="Double 15")
    
    print(f"Submitted tasks: {task1_id}, {task2_id}, {task3_id}")
    
    # Wait for all to complete
    results = task_manager.wait_all(timeout=5.0)
    
    print(f"Completed {len(results)} tasks")
    for i, result in enumerate(results):
        print(f"  Task {i+1}: success={result.success}, data={result.data}")
    
    # Show stats
    stats = task_manager.get_stats()
    print(f"Task Stats: {stats}")
    
    task_manager.shutdown(wait=True)
    print("✓ Task manager working correctly")


def demo_video_clipper():
    """Demonstrate the video clipper operation."""
    print("\n" + "="*60)
    print("DEMO: Video Clipper Operation")
    print("="*60)
    
    clipper = VideoClipper()
    
    # Show how clipping would work (won't actually run without files)
    print("VideoClipper initialized")
    print(f"  Engine: {clipper.engine}")
    print(f"  Methods available:")
    print(f"    - clip(input, output, start_time, duration/end_time)")
    print(f"    - clip_multiple(list_of_clips)")
    print(f"    - quick_trim(input, output, start_time, end_time)")
    
    print("✓ Video clipper operation ready")


def demo_zed_app():
    """Demonstrate the main ZedApp class."""
    print("\n" + "="*60)
    print("DEMO: ZedApp - Main Application Class")
    print("="*60)
    
    # Create the application
    app = ZedApp()
    
    print(f"Application: {app.config.app_name} v{app.config.app_version}")
    print(f"Components initialized:")
    print(f"  - FFmpeg Engine: {app.ffmpeg}")
    print(f"  - Task Manager: {app.tasks}")
    print(f"  - Video Clipper: {app.clipper}")
    
    # Show stats
    stats = app.get_stats()
    print(f"\nApplication Stats:")
    print(f"  {stats}")
    
    # Shutdown
    app.shutdown()
    print("✓ ZedApp working correctly")


def launch_gui():
    """Launch the GUI dashboard."""
    try:
        from PyQt6.QtWidgets import QApplication
        from zed.ui import MainWindow
    except ImportError as e:
        print("Error: PyQt6 is required for the GUI.")
        print("Install with: pip install PyQt6")
        print(f"Details: {e}")
        return 1
    
    app = QApplication(sys.argv)
    app.setApplicationName("Zed Video Editor")
    
    window = MainWindow()
    window.show()
    
    print("Zed Video Editor GUI launched.")
    print("Close the window to exit.")
    
    return app.exec()


def main():
    """Main entry point - runs demo or GUI based on args."""
    parser = argparse.ArgumentParser(
        description="Zed Video Editor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py         Run core foundation demo
  python main.py --gui   Launch the dark theme GUI
        """
    )
    parser.add_argument(
        '--gui', '-g',
        action='store_true',
        help='Launch the GUI (requires PyQt6)'
    )
    args = parser.parse_args()
    
    if args.gui:
        return launch_gui()
    
    # Run demo
    print("\n" + "#"*60)
    print("#  Zed Video Editor - Foundation Demo")
    print("#"*60)
    
    try:
        demo_logging()
        demo_config()
        demo_ffmpeg_engine()
        demo_task_manager()
        demo_video_clipper()
        demo_zed_app()
        
        print("\n" + "="*60)
        print("All demos completed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Install FFmpeg on your system")
        print("  2. Install PyQt6: pip install PyQt6")
        print("  3. Launch GUI: python main.py --gui")
        print("  4. Add real video editing features")
        print()
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
