import hou
import importlib
import sys
import os
from datetime import datetime

from hutil.PySide import QtCore, QtGui, QtWidgets

class Reload(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(Reload, self).__init__(parent)
        
        self.setWindowTitle("Reload Python Modules")
        self.resize(300, 100)

        layout = QtWidgets.QVBoxLayout()

        label_layout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel("Type the name of the comma-separated Python module(s) to reload:")
        self.label.setWordWrap(True)

        self.help_button = QtWidgets.QPushButton("?")
        self.help_button.setFixedSize(20, 20)
        self.help_button.clicked.connect(self.showHelp)
        label_layout.addWidget(self.label)
        label_layout.addWidget(self.help_button)
        layout.addLayout(label_layout)

        self.input_box = QtWidgets.QLineEdit()
        self.input_box.setPlaceholderText("e.g., labutils, stickerplacer")
        layout.addWidget(self.input_box)

        self.reload_status = QtWidgets.QLabel("")
        self.reload_status.setStyleSheet("color: #aaa;")
        layout.addWidget(self.reload_status)

        self.reload_button = QtWidgets.QPushButton("Reload Script")
        self.reload_button.setDefault(True)
        layout.addWidget(self.reload_button)

        self.setLayout(layout)

        self.reload_button.clicked.connect(self.runReloader)
        self.input_box.returnPressed.connect(self.runReloader)

    def showHelp(self):
        QtWidgets.QMessageBox.information(self, "Help",
            "Enter one or more Python module names separated by commas to reload or import.\n\n"
            "The tool will search for modules in the following order:\n"
            "1. Modules already loaded in the current session\n"
            "2. Standard Python library paths, including loaded packages\n"
            "3. Recursive search of Houdini subdirectories (scripts/python, viewer_states, viewer_handles)\n\n"
            "You only need to specify the submodule name instead of the full dotted path.\n"
            "e.g., 'proxymodel' instead of 'pyper.widgets.spreadsheet.proxymodel'")

    def runReloader(self):
        module_names = self.input_box.displayText().replace(" ", "").split(",")
        status_msg = ""
        current_time = datetime.now().strftime("%H:%M:%S")

        for mod_name in module_names:

            # Will try to reload a module that has already been imported
            try:
                # The full_name variable allows for searching of the last submodule. For example, instead of "pyper.widgets.spreadsheet.proxymodel"
                # the search term can just be "proxymodel"
                full_name = mod_name if mod_name in sys.modules else next((k for k in sys.modules if k.endswith("." + mod_name)), None)

                if full_name is None:
                    raise KeyError
                
                module_references = sys.modules[full_name]
                importlib.reload(module_references)

                status_msg += '<span style="color: #66ff66;">Successfully reloaded ' + full_name + " at " + current_time + '!</span><br>'

            except:
                # If it hasn't been imported yet, it will try to import it from the standard Python library paths
                try:
                    importlib.import_module(mod_name)
                    status_msg += '<span style="color: #66ff66;">Successfully loaded ' + sys.modules[mod_name].__file__.replace("\\", "/") + " at " + current_time + '!</span><br>'

                # If we can't find the module from standard Python library paths that were loaded on startup, we search specific
                # Houdini subdirectories across all loaded packages that might not be loaded yet.
                except:
                    found = False
                    search_subdirs = ["scripts/python", "viewer_states", "viewer_handles"]

                    for subdir in search_subdirs:
                        try:
                            dirs_found = hou.findDirectories(subdir)
                        except hou.OperationFailed:
                            continue

                        for base_dir in dirs_found:
                            for root, dirs, files in os.walk(base_dir):
                                for file in files:
                                    if file == mod_name + ".py":
                                        try:
                                            rel_path = os.path.relpath(root, base_dir)
                                            if rel_path == ".":
                                                module = file.removesuffix(".py")
                                            else:
                                                module = rel_path.replace("\\", ".").replace("/", ".") + "." + file.removesuffix(".py")
                                            importlib.import_module(module)
                                            status_msg += '<span style="color: #66ff66;">Successfully loaded ' + module + " at " + current_time + '!</span><br>'
                                            found = True
                                        except Exception as e:
                                            status_msg += '<span style="color: #ff6666;">Error loading ' + mod_name + ': ' + str(e) + " at " + current_time + '</span><br>'
                                            found = True
                                        break

                    if not found:
                        status_msg += '<span style="color: #ff6666;">Could not find module ' + mod_name + " at " + current_time + '.</span><br>'

        self.reload_status.setText(status_msg)