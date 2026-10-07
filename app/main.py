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
    model_status = Signal(str)

    def __init__(self, video_path: str, model_name: str, output_dir: str):
        super().__init__()
        self.video_path = video_path
        self.model_name = model_name
        self.output_dir = output_dir
        self.cancel_requested = False
        self.pipeline = None

    def request_cancel(self):
        """Request cancellation of processing."""
        self.cancel_requested = True
        if self.pipeline is not None:
            self.pipeline.request_cancel()

    def run(self):
        """Execute the video processing pipeline."""
        try:
            self.pipeline = VideoEditPipeline(
                output_dir=self.output_dir,
                progress_callback=lambda value, text: self.progress.emit(value, text),
                log_callback=lambda msg: self.log.emit(msg),
                model_status_callback=lambda status: self.model_status.emit(status),
                cancel_callback=lambda: self.cancel_requested,
            )
            result = self.pipeline.process(self.video_path, model_name=self.model_name)
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Processing was cancelled.")
        except Exception as exc:
            if not self.cancel_requested:
                self.error.emit(str(exc))
            else:
                self.error.emit("Processing was cancelled.")


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kartik Auto Editor 🚀")
        self.resize(1000, 850)

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
        self.processing = False

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

        # Output folder selection
        self.output_label = QLabel(self.output_dir)
        self.output_label.setStyleSheet(
            "background: #161b22; padding: 12px; border: 1px solid #30363d; border-radius: 6px; color: #8b949e;"
        )
        self.output_label.setWordWrap(True)
        self.output_button = QPushButton("Choose Folder")
        self.output_button.clicked.connect(self.select_output_folder)
        self.output_button.setMaximumWidth(120)

        output_row = QWidget()
        output_row_layout = QHBoxLayout(output_row)
        output_row_layout.setContentsMargins(0, 0, 0, 0)
        output_row_layout.setSpacing(8)
        output_row_layout.addWidget(self.output_label)
        output_row_layout.addWidget(self.output_button)
        form.addRow("Output folder:", output_row)

        layout.addLayout(form)

        # Model status indicator
        self.model_status_label = QLabel("Model: Ready")
        self.model_status_label.setStyleSheet("color: #58a6ff; font-weight: 600; font-size: 11px;")
        layout.addWidget(self.model_status_label)

        # Control buttons row
        controls_row = QWidget()
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        # Start button
        self.start_button = QPushButton("Start Processing")
        self.start_button.setMinimumHeight(44)
        self.start_button.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.start_button.clicked.connect(self.start_processing)
        controls_layout.addWidget(self.start_button)

        # Cancel button (initially disabled)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(44)
        self.cancel_button.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet(
            """
            QPushButton {
                background: #da3633; color: white; border: none; border-radius: 6px;
                font-weight: 600; padding: 10px 16px; font-size: 12px;
            }
            QPushButton:hover { background: #f85149; }
            QPushButton:disabled { background: #30363d; color: #6e7681; }
            """
        )
        controls_layout.addWidget(self.cancel_button)

        layout.addWidget(controls_row)

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
        self.log_box.setMinimumHeight(280)
        self.log_box.setPlainText("Kartik Auto Editor v1.0.0\n" + "="*50 + "\n\nWaiting for input...\n")
        layout.addWidget(self.log_box)

        # Log control buttons
        log_controls = QWidget()
        log_controls_layout = QHBoxLayout(log_controls)
        log_controls_layout.setContentsMargins(0, 0, 0, 0)
        log_controls_layout.setSpacing(8)

        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        self.clear_log_button.setMaximumWidth(120)
        log_controls_layout.addWidget(self.clear_log_button)
        log_controls_layout.addStretch()

        layout.addWidget(log_controls)

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

    def select_output_folder(self):
        """Open folder dialog to select output directory."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select output folder",
            self.output_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return

        self.output_dir = folder
        self.output_label.setText(folder)
        self.output_label.setStyleSheet(
            "background: #161b22; padding: 12px; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9;"
        )
        self.log_box.append(f"[INFO] Output folder set to: {folder}")

    def clear_log(self):
        """Clear the log text box."""
        self.log_box.clear()
        self.log_box.append("Log cleared at " + str(Path.cwd()) + "\n")

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
        self.cancel_button.setEnabled(True)
        self.model_combo.setEnabled(False)
        self.video_button.setEnabled(False)
        self.output_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing...")
        self.log_box.append(f"\n[START] Processing with model: {model_name}\n")
        self.processing = True

        self.thread = QThread()
        self.worker = ProcessingWorker(self.video_path, model_name, self.output_dir)
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.model_status.connect(self.update_model_status)
        self.worker.finished.connect(self.processing_finished)
        self.worker.error.connect(self.processing_failed)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def cancel_processing(self):
        """Cancel the currently running processing job."""
        if self.worker is not None:
            self.worker.request_cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling...")
            self.log_box.append("\n[INFO] Cancellation requested. Please wait...\n")

    def update_progress(self, value: int, text: str):
        """Update progress bar and status."""
        self.progress_bar.setValue(value)
        if text:
            self.status_label.setText(text)

    def update_model_status(self, status: str):
        """Update model download/loading status."""
        self.model_status_label.setText(f"Model: {status}")
        self.log_box.append(f"[MODEL] {status}")

    def append_log(self, message: str):
        """Append message to log box."""
        self.log_box.append(message)

    def processing_finished(self, result: str):
        """Handle successful processing completion."""
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()

        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.model_combo.setEnabled(True)
        self.video_button.setEnabled(True)
        self.output_button.setEnabled(True)
        self.processing = False
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
        self.cancel_button.setEnabled(False)
        self.model_combo.setEnabled(True)
        self.video_button.setEnabled(True)
        self.output_button.setEnabled(True)
        self.processing = False
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
