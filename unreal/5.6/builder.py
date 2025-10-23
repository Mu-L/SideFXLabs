import os
import platform
import re
import shutil
import subprocess
import sys

from hutil.PySide.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QFileDialog,
    QGroupBox, QFormLayout, QMessageBox, QProgressBar, QSizePolicy
)
from hutil.PySide.QtCore import Qt, QThread, Signal
from hutil.PySide.QtGui import QFont


class WorkerThread(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, build_command, build_path, plugin_path):
        super().__init__()
        self.build_command = build_command
        self.build_path = build_path
        self.plugin_path = plugin_path

    def run(self):
        try:
            self.progress.emit("Executing build command...")

            proc = subprocess.Popen(
                self.build_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            for line in iter(proc.stdout.readline, ""):
                if line:
                    self.progress.emit(line.rstrip("\r\n"))
                if proc.poll() is not None and not line:
                    break

            proc.stdout.close()
            rc = proc.wait()

            if rc != 0:
                self.finished.emit(False, f"Build failed with exit code {rc}")
                return

            self.progress.emit("Build completed successfully!")

            intermediate_dir = os.path.join(self.build_path, "Intermediate")
            if os.path.exists(intermediate_dir):
                shutil.rmtree(intermediate_dir)
                self.progress.emit("Intermediate directory deleted successfully!")
            else:
                self.progress.emit("No intermediate directory to clean up.")

            plugin_dir = os.path.dirname(self.plugin_path)
            python_source = os.path.join(plugin_dir, "Python")
            python_dest = os.path.join(self.build_path, "Python")
            
            if os.path.exists(python_source):
                if os.path.exists(python_dest):
                    shutil.rmtree(python_dest)
                    self.progress.emit("Existing Python directory removed from build path.")
                
                shutil.copytree(python_source, python_dest)
                self.progress.emit("Python directory copied to build path successfully!")
            else:
                self.progress.emit("No Python directory found in plugin directory.")

            self.finished.emit(True, "Build completed successfully!")
        except subprocess.CalledProcessError as e:
            self.finished.emit(False, f"Build failed: {str(e)}")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class LogTextEdit(QTextEdit):
    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        clear_action = menu.addAction("Clear")
        clear_action.triggered.connect(self.clear)
        menu.exec_(event.globalPos())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.build_worker = None
        self.initUI()

    def getPlatform(self):
        system = platform.system()
        if system == "Windows":
            return "Win64"
        elif system == "Darwin":
            return "Mac"
        elif system == "Linux":
            return "Linux"
        else:
            return "Win64"

    def logMessage(self, message):
        self.output_text.append(message)

    def selectBuildScript(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Unreal Build Script",
            "",
            "Scripts (*.bat *.sh);;All Files (*)"
        )
        if file_path:
            self.build_script_input.setText(file_path.replace("\\", "/"))
            self.logMessage(f"Build script selected: {file_path}")

    def selectUplugin(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select .uplugin File",
            "",
            "Plugin Files (*.uplugin);;All Files (*)"
        )
        if file_path:
            self.uplugin_input.setText(file_path.replace("\\", "/"))
            self.logMessage(f"Plugin file selected: {file_path}")

    def selectBuildPath(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Build Directory")
        if dir_path:
            dir_path = dir_path.replace("\\", "/")
            
            '''
            if dir_path.endswith("/Build"):
                sidefx_folder = os.path.join(dir_path, "SideFX_Labs").replace("\\", "/")
            else:
                build_folder = os.path.join(dir_path, "Build").replace("\\", "/")
                sidefx_folder = os.path.join(build_folder, "SideFX_Labs").replace("\\", "/")
                os.makedirs(build_folder, exist_ok=True)
            '''

            sidefx_folder = os.path.join(dir_path, "SideFX_Labs").replace("\\", "/")
            
            os.makedirs(sidefx_folder, exist_ok=True)
            self.build_path_input.setText(sidefx_folder)
            self.logMessage(f"Build path set to: {sidefx_folder}")

    def updateUpluginFile(self, plugin_path, selected_platform):
        try:
            with open(plugin_path, "r", encoding="utf-8") as file:
                content = file.read()

            def replace_platform_list(match):
                return f'"{match.group(1)}": ["{selected_platform}"]'

            new_content, count = re.subn(
                r'"(PlatformAllowList)"\s*:\s*\[.*?\]',
                replace_platform_list,
                content,
                flags=re.DOTALL
            )

            if count > 0:
                with open(plugin_path, "w", encoding="utf-8") as file:
                    file.write(new_content)
                self.logMessage(".uplugin file updated successfully!")
                return True
            else:
                self.logMessage("⚠ Warning: No PlatformAllowList found in .uplugin file")
                return True

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update .uplugin file:\n{str(e)}")
            return False

    def buildFinished(self, success, message):
        self.build_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.logMessage(f"\n{message}")

        if success:
            QMessageBox.information(self, "Success", "Build completed successfully!")
        else:
            QMessageBox.critical(self, "Build Failed", message)

    def startBuild(self):
        build_script = self.build_script_input.text()
        plugin_path = self.uplugin_input.text()
        build_path = self.build_path_input.text()
        selected_platform = self.platform_combo.currentText()

        if not build_script:
            QMessageBox.warning(self, "Missing Input", "Please select an Unreal build script.")
            return

        if not plugin_path:
            QMessageBox.warning(self, "Missing Input", "Please select a .uplugin file.")
            return

        if not build_path:
            QMessageBox.warning(self, "Missing Input", "Please select a build path.")
            return

        if not os.path.exists(plugin_path):
            QMessageBox.critical(self, "Error", "Selected .uplugin file does not exist.")
            return

        if not os.path.exists(build_script):
            QMessageBox.critical(self, "Error", "Selected build script does not exist.")
            return

        self.logMessage(f"\n{'='*60}")
        self.logMessage(f"Starting build for platform: {selected_platform}")
        self.logMessage(f"{'='*60}\n")

        if not self.updateUpluginFile(plugin_path, selected_platform):
            return

        build_command = f'"{build_script}" BuildPlugin -Plugin="{plugin_path}" -TargetPlatforms={selected_platform} -Package="{build_path}"'
        self.logMessage(f"\nGenerated command:\n{build_command}\n")

        self.build_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.build_worker = WorkerThread(build_command, build_path, plugin_path)
        self.build_worker.progress.connect(self.logMessage)
        self.build_worker.finished.connect(self.buildFinished)
        self.build_worker.start()

    def initUI(self):
        self.setWindowTitle("Unreal Engine Build Tool")
        self.setGeometry(100, 100, 800, 600)

        self.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #d0d0d0;
        }
        QLabel {
            color: #d0d0d0;
            background: transparent;
        }
        QGroupBox {
            border: 1px solid #444444;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
            color: #ff6600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #ff6600;
            background: transparent;
        }
        QLineEdit {
            background-color: #1e1e1e; /* Dark color for text boxes */
            border: 1px solid #444444;
            border-radius: 3px;
            padding: 5px;
            color: #d0d0d0;
            selection-background-color: #ff6600;
            selection-color: #111111;
        }
        QLineEdit:focus {
            border: 1px solid #ff6600;
        }
        QComboBox {
            background-color: #1e1e1e;
            border: 1px solid #444444;
            border-radius: 3px;
            padding: 5px;
            color: #d0d0d0;
        }
        QComboBox:focus {
            border: 1px solid #ff6600;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox QAbstractItemView {
            background-color: #1e1e1e;
            border: 1px solid #444444;
            selection-background-color: #ff6600;
            color: #d0d0d0;
            outline: none;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #ff6600;
            color: #111111;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #ff6600;
            color: #111111;
        }
        QPushButton {
            /* Updated to match QLineEdit background-color */
            background-color: #1e1e1e;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 8px 15px;
            color: #d0d0d0;
        }
        QPushButton:hover {
            /* Slightly lighter hover color */
            background-color: #2a2a2a; 
            border: 1px solid #ff6600;
        }
        QPushButton:pressed {
            /* Slightly darker pressed color */
            background-color: #111111;
        }
        QPushButton:disabled {
            background-color: #555555;
            color: #888888;
            border: 1px solid #555555;
        }
        QToolButton {
            /* Updated to match QLineEdit background-color */
            background-color: #1e1e1e;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 6px 10px;
            color: #d0d0d0;
        }
        QToolButton:hover {
            /* Slightly lighter hover color */
            background-color: #2a2a2a;
            border: 1px solid #ff6600;
        }
        QToolButton:pressed {
            /* Slightly darker pressed color */
            background-color: #111111;
        }

        /* Assuming the log box is a QTextEdit or QPlainTextEdit */
        QTextEdit, QPlainTextEdit {
            background-color: #1e1e1e; /* Dark color for log box */
            border: 1px solid #444444;
            border-radius: 3px;
            padding: 5px;
            color: #d0d0d0;
            selection-background-color: #ff6600; /* Orange selection color */
            selection-color: #111111;
        }

        QProgressBar {
            border: 1px solid #444444;
            border-radius: 3px;
            background-color: #1e1e1e;
            text-align: center;
            color: #d0d0d0;
            height: 16px;
        }
        QProgressBar::chunk {
            background-color: #ff6600;
        }
        """)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Configuration Group
        config_group = QGroupBox("Build Configuration")
        config_layout = QFormLayout()
        config_group.setLayout(config_layout)

        # Platform selection
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Win64", "Mac", "Linux"])
        self.platform_combo.setCurrentText(self.getPlatform())
        config_layout.addRow("Build Platform:", self.platform_combo)

        main_layout.addWidget(config_group)

        # File Selection Group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        file_group.setLayout(file_layout)

        # Build Script
        build_script_layout = QHBoxLayout()
        self.build_script_input = QLineEdit()
        self.build_script_input.setPlaceholderText("Select Unreal build script (.bat or .sh)")
        build_script_btn = QPushButton("Browse...")
        build_script_btn.clicked.connect(self.selectBuildScript)
        build_script_layout.addWidget(QLabel("Build Script:"))
        build_script_layout.addWidget(self.build_script_input)
        build_script_layout.addWidget(build_script_btn)
        file_layout.addLayout(build_script_layout)

        # Plugin File
        uplugin_layout = QHBoxLayout()
        self.uplugin_input = QLineEdit()
        self.uplugin_input.setPlaceholderText("Select .uplugin file")
        uplugin_btn = QPushButton("Browse...")
        uplugin_btn.clicked.connect(self.selectUplugin)
        uplugin_layout.addWidget(QLabel("Plugin File:"))
        uplugin_layout.addWidget(self.uplugin_input)
        uplugin_layout.addWidget(uplugin_btn)
        file_layout.addLayout(uplugin_layout)

        # Build Path
        build_path_layout = QHBoxLayout()
        self.build_path_input = QLineEdit()
        self.build_path_input.setPlaceholderText("Select output build directory")
        build_path_btn = QPushButton("Browse...")
        build_path_btn.clicked.connect(self.selectBuildPath)
        build_path_layout.addWidget(QLabel("Build Path:"))
        build_path_layout.addWidget(self.build_path_input)
        build_path_layout.addWidget(build_path_btn)
        file_layout.addLayout(build_path_layout)

        main_layout.addWidget(file_group)

        # Build Button
        self.build_btn = QPushButton("Start Build")
        self.build_btn.clicked.connect(self.startBuild)
        main_layout.addWidget(self.build_btn)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Output Log
        output_group = QGroupBox("Build Log")
        output_layout = QVBoxLayout()
        output_group.setLayout(output_layout)

        #self.output_text = QTextEdit()
        self.output_text = LogTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier", 11))
        self.output_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        output_layout.addWidget(self.output_text, 1)

        main_layout.addWidget(output_group)
        main_layout.setStretch(main_layout.indexOf(output_group), 1)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
