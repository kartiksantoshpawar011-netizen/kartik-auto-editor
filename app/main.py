"""Main GUI window for Kartik Auto Editor."""
import os
import sys
from pathlib import Path

from PySide6.QtCore import QThread, QObject, Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.pipeline import VideoEditPipeline


class ProcessingWorker(QObject):
    """Worker thread for video processing."""
    progress = Signal(int, str)
    log = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, video_path: str, model_name: str, output_dir: str):
        super().__init__()
        self.video_path = video_path
        self.model_name = model_name
        self.output_dir = output_dir

    def run(self):
        """Execute the video processing pipeline."""
        try:
            pipeline = VideoEditPipeline(
                output_dir=self.output_dir,
                progress_callback=lambda value, text: self.progress.emit(value, text),
                log_callback=lambda msg: self.log.emit(msg),
            )
            result = pipeline.process(self.video_path, model_name=self.model_name)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kartik Auto Editor 🚀")
        self.resize(1000, 750)

        # Dark modern theme
        self.setStyleSheet(
            """
            QMainWindow { background: #0d1117; }
            QWidget { background: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; font-size: 11px; }
            QLabel { color: #c9d1d9; }
            QPushButton {
                background: #1f6feb; color: white; border: none; border-radius: 6px;
                font-weight: 600; padding: 10px 16px; font-size: 12px;
            }
            QPushButton:hover { background: #388bfd; }
            QPushButton:pressed { background: #1a5bd9; }
            QPushButton:disabled { background: #30363d; color: #6e7681; }
            QComboBox, QTextEdit, QProgressBar, QLineEdit {
                background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 8px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { background: none; }
            QTextEdit { padding: 10px; font-family: 'Courier New', monospace; font-size: 10px; }
            QProgressBar {
                text-align: center; color: white; border-radius: 6px;
            }
            QProgressBar::chunk { background: #1f6feb; }
            """
        )

        self.video_path = ""
        self.output_dir = str(Path.cwd() / "exports")
        self.thread = None
        self.worker = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Kartik Auto Editor 🚀")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: #f0f6fc; margin-bottom: 4px;")
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Local AI-powered short-form video editor for Reels and Shorts")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet("color: #8b949e; margin-bottom: 16px;")
        layout.addWidget(subtitle)

        # Form
        form = QFormLayout()
        form.setSpacing(12)

        # Video selection
        self.video_label = QLabel("No file selected")
        self.video_label.setStyleSheet(
            "background: #161b22; padding: 12px; border: 1px solid #30363d; border-radius: 6px; color: #8b949e;"
        )
        self.video_button = QPushButton("Browse")
        self.video_button.clicked.connect(self.select_video)
        self.video_button.setMaximumWidth(100)

        video_row = QWidget()
        video_row_layout = QHBoxLayout(video_row)
        video_row_layout.setContentsMargins(0, 0, 0, 0)
        video_row_layout.setSpacing(8)
        video_row_layout.addWidget(self.video_label)
        video_row_layout.addWidget(self.video_button)
        form.addRow("Source video:", video_row)

        # Model selection
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small"])
        self.model_combo.setCurrentText("base")
        self.model_combo.setMaximumWidth(150)
        form.addRow("Whisper model:", self.model_combo)

        # Output folder
        self.output_label = QLabel(self.output_dir)
        self.output_label.setStyleSheet(
            "background: #161b22; padding: 12px; border: 1px solid #30363d; border-radius: 6px; color: #8b949e;"
        )
        self.output_label.setWordWrap(True)
        form.addRow("Output folder:", self.output_label)

        layout.addLayout(form)

        # Start button
        self.start_button = QPushButton("Start processing")
        self.start_button.setMinimumHeight(44)
        self.start_button.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.start_button.clicked.connect(self.start_processing)
        layout.addWidget(self.start_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(28)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #58a6ff; font-weight: 600;")
        layout.addWidget(self.status_label)

        # Log box
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(300)
        self.log_box.setPlainText("Kartik Auto Editor v1.0.0\n" + "="*50 + "\n\nWaiting for input...\n")
        layout.addWidget(self.log_box)

    def select_video(self):
        """Open file dialog to select a video."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select video file",
            str(Path.cwd()),
            "Video Files (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv *.flv)",
        )
        if not path:
            return

        self.video_path = path
        filename = Path(path).name
        self.video_label.setText(filename)
        self.video_label.setStyleSheet(
            "background: #161b22; padding: 12px; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9;"
        )
        self.status_label.setText(f"Selected: {filename}")
        self.log_box.append(f"[INFO] Selected video: {path}")

    def start_processing(self):
        """Start the video processing pipeline."""
        if not self.video_path:
            QMessageBox.warning(self, "No video selected", "Please select a video file first.")
            return

        if not os.path.exists(self.video_path):
            QMessageBox.critical(self, "File not found", f"Video file does not exist: {self.video_path}")
            self.video_path = ""
            self.video_label.setText("No file selected")
            return

        model_name = self.model_combo.currentText().strip().lower()
        self.start_button.setEnabled(False)
        self.model_combo.setEnabled(False)
        self.video_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing...")
        self.log_box.append(f"\n[START] Processing with model: {model_name}\n")

        self.thread = QThread()
        self.worker = ProcessingWorker(self.video_path, model_name, self.output_dir)
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.processing_finished)
        self.worker.error.connect(self.processing_failed)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def update_progress(self, value: int, text: str):
        """Update progress bar and status."""
        self.progress_bar.setValue(value)
        if text:
            self.status_label.setText(text)

    def append_log(self, message: str):
        """Append message to log box."""
        self.log_box.append(message)

    def processing_finished(self, result: str):
        """Handle successful processing completion."""
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()

        self.start_button.setEnabled(True)
        self.model_combo.setEnabled(True)
        self.video_button.setEnabled(True)
        self.status_label.setText("✓ Completed")
        self.log_box.append(f"\n[SUCCESS] Video exported to:\n{result}\n")

        QMessageBox.information(
            self,
            "Processing Complete",
            f"Your video has been successfully processed and saved to:\n\n{result}",
        )

    def processing_failed(self, error_message: str):
        """Handle processing errors."""
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()

        self.start_button.setEnabled(True)
        self.model_combo.setEnabled(True)
        self.video_button.setEnabled(True)
        self.status_label.setText("✗ Error")
        self.log_box.append(f"\n[ERROR] {error_message}\n")

        QMessageBox.critical(self, "Processing Failed", error_message)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Kartik Auto Editor")
    app.setApplicationVersion("1.0.0")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
