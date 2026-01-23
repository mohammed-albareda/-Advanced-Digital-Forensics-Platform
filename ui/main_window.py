import os
import json
import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QProgressBar, QMessageBox,
                             QSystemTrayIcon, QMenu, QAction, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon
from core.scanner import scan_directory
from core.comparer import compare_scans
from core.database import Database
from core.reporter import generate_pdf_report
from core.monitor import RealTimeMonitor
from core.backup import BackupManager
from core.startup import set_run_at_startup

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Avoid os.path.abspath(".") as it depends on CWD (which is bad on startup)
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    return os.path.join(base_path, relative_path)

class ScanThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)

    def __init__(self, directory, ignore_list=None):
        super().__init__()
        self.directory = directory
        self.ignore_list = ignore_list or []

    def run(self):
        result = scan_directory(self.directory, self.ignore_list, self.progress.emit)
        self.finished.emit(result)

class ReportThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, output_path, directory, results):
        super().__init__()
        self.output_path = output_path
        self.directory = directory
        self.results = results

    def run(self):
        try:
            generate_pdf_report(self.output_path, self.directory, self.results)
            self.finished.emit(True, self.output_path)
        except Exception as e:
            self.finished.emit(False, str(e))

class InitialBackupThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, directory, file_list, backup_mgr, db):
        super().__init__()
        self.directory = directory
        self.file_list = file_list
        self.backup_mgr = backup_mgr
        self.db = db

    def run(self):
        total = len(self.file_list)
        if total == 0:
            self.finished.emit()
            return
            
        for i, rel_path in enumerate(self.file_list):
            full_path = os.path.join(self.directory, rel_path)
            backup_path = self.backup_mgr.create_backup(full_path, self.directory)
            if backup_path:
                self.db.add_backup(full_path, backup_path)
            # Update progress (less frequently to avoid overhead)
            if (i+1) % max(1, total//100) == 0 or (i+1) == total:
                self.progress.emit(int(((i + 1) / total) * 100))
        self.finished.emit()

class MainWindow(QMainWindow):
    # Signal for thread-safe cross-thread UI updates from watchdog
    realtime_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Integrity Monitor")
        self.setMinimumSize(800, 600)
        
        # 1. Ensure Application Root and Data Directory Exist
        # This is critical to avoid [WinError 5] Access Denied
        self.app_root = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.data_dir = os.path.join(self.app_root, "data")
        
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir, exist_ok=True)
            except Exception as e:
                print(f"Failed to create data directory: {e}")

        # State
        self.selected_directory = ""
        self.baseline_file = os.path.join(self.data_dir, "baseline.json")
        self.current_results = []
        self.monitor = None
        self.is_protected = False
        
        # 2. Initialize Core Components after root folders exist
        self.db = Database(os.path.join(self.data_dir, "monitor.db"))
        self.backup_mgr = BackupManager(os.path.join(self.data_dir, "backups"))

        self.init_ui()
        self.init_tray()
        self.apply_styles()
        
        # Load startup setting
        is_startup = self.db.get_setting("run_on_startup") == "1"
        set_run_at_startup(is_startup)
        
        # Connect the signal
        self.realtime_signal.connect(self.process_realtime_event)

        # AUTO-START LOGIC
        last_dir = self.db.get_setting("last_directory")
        if last_dir and os.path.exists(last_dir):
            self.selected_directory = last_dir
            self.folder_label.setText(last_dir)
            self.baseline_btn.setEnabled(True)
            self.protect_btn.setEnabled(True)
            self.scan_btn.setEnabled(os.path.exists(self.baseline_file))
            # Auto-start protection
            self.toggle_protection()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("File Integrity Monitor")
        header_label.setObjectName("headerLabel")
        
        self.protect_btn = QPushButton("Start Protection")
        self.protect_btn.setFixedWidth(150)
        self.protect_btn.setObjectName("protectBtn")
        self.protect_btn.setEnabled(False)
        self.protect_btn.clicked.connect(self.toggle_protection)

        self.alerts_btn = QPushButton("View Alerts")
        self.alerts_btn.setFixedWidth(150)
        self.alerts_btn.clicked.connect(lambda: self.view_alerts(unread_only=False))
        
        self.unread_label = QLabel("New: 0")
        self.unread_label.setStyleSheet("color: #f44747; font-weight: bold;")
        self.unread_label.setVisible(False)

        self.export_btn = QPushButton("Export Report (PDF)")
        self.export_btn.setFixedWidth(150)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_report)
        
        ignore_btn = QPushButton("Manage Ignores")
        ignore_btn.setFixedWidth(150)
        ignore_btn.clicked.connect(self.manage_ignores)
        
        settings_btn = QPushButton("Settings")
        settings_btn.setFixedWidth(100)
        settings_btn.clicked.connect(self.manage_settings)

        header_layout.addWidget(header_label, 1)
        header_layout.addWidget(self.protect_btn)
        header_layout.addWidget(self.alerts_btn)
        header_layout.addWidget(self.unread_label)
        header_layout.addWidget(self.export_btn)
        header_layout.addWidget(ignore_btn)
        header_layout.addWidget(settings_btn)
        layout.addLayout(header_layout)

        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setObjectName("folderLabel")
        select_btn = QPushButton("Select Folder")
        select_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_label, 1)
        folder_layout.addWidget(select_btn)
        layout.addLayout(folder_layout)

        # Actions
        btn_layout = QHBoxLayout()
        self.baseline_btn = QPushButton("Create Baseline")
        self.baseline_btn.setEnabled(False)
        self.baseline_btn.clicked.connect(self.create_baseline)
        
        self.scan_btn = QPushButton("Scan Files")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self.scan_files)

        self.clear_btn = QPushButton("Clear Baseline")
        self.clear_btn.clicked.connect(self.clear_baseline)
        
        btn_layout.addWidget(self.baseline_btn)
        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["File", "Status", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Status Bar
        self.status_bar = QLabel("Ready")
        self.status_bar.setObjectName("statusBar")
        layout.addWidget(self.status_bar)

        # Context menu for restoration
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)

    def show_table_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        
        row = item.row()
        file_rel = self.table.item(row, 0).text()
        full_path = os.path.join(self.selected_directory, file_rel)
        
        menu = QMenu()
        restore_action = QAction("⏪ Restore from Backup (Back-in-time)", self)
        
        # Check if backup exists
        backup_path = self.db.get_latest_backup(full_path)
        if not backup_path:
            restore_action.setEnabled(False)
            restore_action.setText(restore_action.text() + " [No Backup]")
            
        restore_action.triggered.connect(lambda: self.restore_file_logic(full_path, backup_path))
        menu.addAction(restore_action)
        menu.exec_(self.table.mapToGlobal(pos))

    def restore_file_logic(self, full_path, backup_path, row_idx=None, table=None):
        if not backup_path:
            QMessageBox.warning(self, "No Backup", "No historical snapshot found for this file.")
            return

        if self.backup_mgr.restore_file(backup_path, full_path):
            self.status_bar.setText(f"Restored file: {os.path.basename(full_path)}")
            if table is not None and row_idx is not None:
                table.removeRow(row_idx)
            else:
                QMessageBox.information(self, "Success", f"File restored successfully:\n{full_path}")
                self.scan_files() # Refresh results
        else:
            QMessageBox.critical(self, "Error", "Failed to restore file.")

    def manage_settings(self):
        from PyQt5.QtWidgets import QDialog, QCheckBox
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings / الإعدادات")
        dialog.setFixedWidth(300)
        d_layout = QVBoxLayout(dialog)
        
        startup_cb = QCheckBox("Run at Windows Startup / التشغيل التلقائي")
        startup_cb.setChecked(self.db.get_setting("run_on_startup") == "1")
        
        def save_settings():
            is_enabled = startup_cb.isChecked()
            self.db.set_setting("run_on_startup", "1" if is_enabled else "0")
            set_run_at_startup(is_enabled)
            QMessageBox.information(dialog, "Saved", "Settings updated.")
            dialog.accept()
            
        save_btn = QPushButton("Save / حفظ")
        save_btn.clicked.connect(save_settings)
        
        d_layout.addWidget(startup_cb)
        d_layout.addWidget(save_btn)
        dialog.exec_()

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fix: QSystemTrayIcon.MessageIcon is incorrect for standardIcon
            # We use a standard style icon instead (Shield or Computer)
            from PyQt5.QtWidgets import QStyle
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            
        tray_menu = QMenu()
        show_action = QAction("Open Monitor", self)
        show_action.triggered.connect(self.showNormal)
        
        quit_action = QAction("Exit Completely", self)
        quit_action.triggered.connect(self.actually_quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # KEY FEATURE: Connect notification click to open alerts
        try: self.tray_icon.messageClicked.disconnect()
        except: pass
        self.tray_icon.messageClicked.connect(lambda: self.view_alerts(unread_only=True))

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible(): self.hide()
            else: self.showNormal()

    def actually_quit(self):
        if self.monitor: self.monitor.stop()
        QApplication.quit()

    def closeEvent(self, event):
        if self.is_protected:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Integrity Monitor",
                "Program is still running in the background to protect your files.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.actually_quit()

    def toggle_protection(self):
        if not self.is_protected:
            ignore_list = [p for p, t in self.db.get_ignore_list() if t == 'directory']
            self.monitor = RealTimeMonitor(
                self.selected_directory, 
                self.realtime_signal.emit, # Emit signal directly from monitor thread
                self.db,
                ignore_list
            )
            self.monitor.start()
            self.is_protected = True
            self.protect_btn.setText("Stop Protection")
            self.protect_btn.setStyleSheet("background-color: #f44747;")
            self.status_bar.setText("🛡️ Real-time protection is ACTIVE")
        else:
            if self.monitor:
                self.monitor.stop()
                self.monitor = None
            self.is_protected = False
            self.protect_btn.setText("Start Protection")
            self.protect_btn.setStyleSheet("")
            self.status_bar.setText("Protection stopped.")

    def process_realtime_event(self, filename, status):
        # Update unread counter in UI
        unread_count = len(self.db.get_alerts(unread_only=True))
        self.unread_label.setText(f"New: {unread_count}")
        self.unread_label.setVisible(unread_count > 0)

        # Show tray notification
        self.tray_icon.showMessage(
            "Integrity Alert! 🛡️",
            f"File {status}: {filename}\nClick to view NEW alerts.",
            QSystemTrayIcon.Warning,
            5000
        )
        # Clicking notification now specifically shows unread ones
        try: self.tray_icon.messageClicked.disconnect()
        except: pass
        self.tray_icon.messageClicked.connect(lambda: self.view_alerts(unread_only=True))

    def view_alerts(self, unread_only=False):
        from PyQt5.QtWidgets import QDialog, QTableWidget, QAbstractItemView, QTableWidgetItem
        
        btn_style_allow = "background-color: #4ec9b0; font-size: 11px; padding: 5px; min-width: 80px;"
        btn_style_restore = "background-color: #ce9178; font-size: 11px; padding: 5px; min-width: 140px;"

        dialog = QDialog(self)
        title = "New Alerts / تنبيهات جديدة" if unread_only else "All Logs / كافة السجلات"
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(900, 500)
        d_layout = QVBoxLayout(dialog)
        
        if unread_only:
            header_notice = QLabel("Showing ONLY unread alerts. Viewing them marks them as read.")
            header_notice.setStyleSheet("color: #dcdcaa; font-style: italic;")
            d_layout.addWidget(header_notice)

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Time", "Status", "File", "Actor / المتسبب", "Keep Change", "Undo Change"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        alerts = self.db.get_alerts(unread_only=unread_only)
        table.setRowCount(len(alerts))
        
        for row, (ts, file, status, actor) in enumerate(alerts):
            table.setItem(row, 0, QTableWidgetItem(ts))
            table.setItem(row, 1, QTableWidgetItem(status))
            table.setItem(row, 2, QTableWidgetItem(file))
            table.setItem(row, 3, QTableWidgetItem(actor or "Unknown"))
            
            # Action Buttons
            allow_btn = QPushButton("Allow / سماح")
            allow_btn.setStyleSheet(btn_style_allow)
            
            restore_btn = QPushButton("Restore / استعادة الأصلي")
            restore_btn.setStyleSheet(btn_style_restore)
            
            # Button Logic
            full_path = os.path.join(self.selected_directory, file)
            
            def create_allow_fn(f_path, r_idx):
                return lambda: self.allow_change_logic(f_path, r_idx, table, dialog)
            
            def create_restore_fn(f_path, r_idx):
                backup_p = self.db.get_latest_backup(f_path)
                return lambda: self.restore_file_logic(f_path, backup_p, r_idx, table)

            allow_btn.clicked.connect(create_allow_fn(full_path, row))
            restore_btn.clicked.connect(create_restore_fn(full_path, row))
            
            if "Deleted" in status:
                allow_btn.setText("Acknowledge")
            
            table.setCellWidget(row, 4, allow_btn)
            table.setCellWidget(row, 5, restore_btn)
            
        d_layout.addWidget(table)
        
        bottom_box = QHBoxLayout()
        if not unread_only:
            clear_btn = QPushButton("Clear All Logs / مسح السجل بالكامل")
            clear_btn.clicked.connect(lambda: [self.db.clear_alerts(), table.setRowCount(0), self.update_unread_ui()])
            bottom_box.addWidget(clear_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        bottom_box.addStretch()
        bottom_box.addWidget(close_btn)
        d_layout.addLayout(bottom_box)
        
        # After showing unread, mark them all as read in DB
        if unread_only:
            self.db.mark_alerts_as_read()
            self.update_unread_ui()

        dialog.exec_()

    def update_unread_ui(self):
        unread_count = len(self.db.get_alerts(unread_only=True))
        self.unread_label.setText(f"New: {unread_count}")
        self.unread_label.setVisible(unread_count > 0)

    def allow_change_logic(self, full_path, row_idx, table, dialog):
        """Updates the baseline to accept the current state of the file."""
        from core.hasher import calculate_hash
        
        if not os.path.exists(self.baseline_file): return
        
        with open(self.baseline_file, 'r') as f:
            baseline = json.load(f)
            
        rel_path = os.path.relpath(full_path, self.selected_directory)
        
        if os.path.exists(full_path):
            # Update hash in baseline
            new_hash = calculate_hash(full_path)
            baseline[rel_path] = new_hash
            # Also create a NEW backup for this allowed version
            b_path = self.backup_mgr.create_backup(full_path, self.selected_directory)
            if b_path: self.db.add_backup(full_path, b_path)
        else:
            # File was deleted and we allowed it, so remove from baseline
            if rel_path in baseline:
                del baseline[rel_path]
                
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline, f)
            
        table.removeRow(row_idx)
        self.status_bar.setText(f"Accepted change for: {os.path.basename(full_path)}")

    def on_realtime_event(self, filename, status):
        # This comes from a different thread (watchdog), so we update UI carefully
        # In a real app we'd use signals, but for now we just show it in the table if visible
        # We also have the tray notification from monitor.py
        pass

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel#headerLabel { font-size: 24px; font-weight: bold; color: #ffffff; }
            QLabel { color: #d4d4d4; font-size: 14px; }
            QPushButton { background-color: #007acc; color: white; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold; min-width: 120px; }
            QPushButton:hover { background-color: #0062a3; }
            QPushButton:disabled { background-color: #3e3e42; color: #808080; }
            QTableWidget { background-color: #252526; color: #d4d4d4; border: 1px solid #3e3e42; gridline-color: #3e3e42; }
            QHeaderView::section { background-color: #333337; color: #ffffff; padding: 5px; border: none; }
            QProgressBar { border: 1px solid #3e3e42; border-radius: 4px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #007acc; }
            QLabel#statusBar { font-size: 12px; color: #808080; }
        """)

    def export_report(self):
        if not self.current_results:
            QMessageBox.warning(self, "No Data", "Perform a scan first to export a report.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Report", "", "PDF Files (*.pdf)")
        if file_path:
            self.export_btn.setEnabled(False)
            self.status_bar.setText("Generating PDF report... Please wait.")
            self.progress_bar.setRange(0, 0) # Indeterminate mode
            self.progress_bar.setVisible(True)
            
            self.report_thread = ReportThread(file_path, self.selected_directory, self.current_results)
            self.report_thread.finished.connect(self.on_report_finished)
            self.report_thread.start()

    def on_report_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100) # Reset to normal
        self.export_btn.setEnabled(True)
        
        if success:
            self.status_bar.setText(f"Report saved: {os.path.basename(message)}")
            QMessageBox.information(self, "Success", f"Report saved to:\n{message}")
        else:
            self.status_bar.setText("Export failed.")
            QMessageBox.critical(self, "Error", f"Could not save report: {message}")

    def manage_ignores(self):
        from PyQt5.QtWidgets import QDialog, QListWidget, QLineEdit, QComboBox, QFormLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Exclusions")
        dialog.setMinimumWidth(500)
        dialog_layout = QVBoxLayout(dialog)
        
        list_widget = QListWidget()
        ignores = self.db.get_ignore_list()
        for pattern, p_type in ignores:
            list_widget.addItem(f"[{p_type}] {pattern}")
        dialog_layout.addWidget(list_widget)
        
        form_layout = QFormLayout()
        pattern_layout = QHBoxLayout()
        pattern_input = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(80)
        pattern_layout.addWidget(pattern_input)
        pattern_layout.addWidget(browse_btn)
        
        type_input = QComboBox()
        type_input.addItems(["directory", "file", "extension"])
        
        form_layout.addRow("Type:", type_input)
        form_layout.addRow("Pattern:", pattern_layout)
        dialog_layout.addLayout(form_layout)
        
        btn_box = QHBoxLayout()
        add_btn = QPushButton("Add")
        rem_btn = QPushButton("Remove Selected")
        btn_box.addWidget(add_btn)
        btn_box.addWidget(rem_btn)
        dialog_layout.addLayout(btn_box)

        def browse_clicked():
            p_type = type_input.currentText()
            if p_type == "directory":
                path = QFileDialog.getExistingDirectory(dialog, "Select Directory to Ignore")
                if path:
                    pattern_input.setText(os.path.basename(path))
            elif p_type == "file":
                path, _ = QFileDialog.getOpenFileName(dialog, "Select File to Ignore")
                if path:
                    pattern_input.setText(os.path.basename(path))
            else:
                QMessageBox.information(dialog, "Note", "For extensions, please enter the pattern manually (e.g., .log)")
        
        def add_item():
            pattern = pattern_input.text().strip()
            if pattern:
                p_type = type_input.currentText()
                if self.db.add_ignore(pattern, p_type):
                    list_widget.addItem(f"[{p_type}] {pattern}")
                    pattern_input.clear()
                else:
                    QMessageBox.warning(dialog, "Error", "Pattern already exists.")
        
        def rem_item():
            current = list_widget.currentItem()
            if current:
                pattern = current.text().split("] ")[1]
                self.db.remove_ignore(pattern)
                list_widget.takeItem(list_widget.row(current))
        
        browse_btn.clicked.connect(browse_clicked)
        add_btn.clicked.connect(add_item)
        rem_btn.clicked.connect(rem_item)
        dialog.exec_()

    def select_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder to Monitor")
        if dir_path:
            self.selected_directory = dir_path
            self.db.set_setting("last_directory", dir_path) # Remember for next time
            self.folder_label.setText(dir_path)
            self.baseline_btn.setEnabled(True)
            self.protect_btn.setEnabled(True) # Enable protection
            self.scan_btn.setEnabled(os.path.exists(self.baseline_file))
            self.status_bar.setText(f"Selected: {dir_path}")

    def create_baseline(self):
        if not self.selected_directory:
            return
        
        self.baseline_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.setText("Creating Baseline...")

        ignore_list = self.db.get_ignore_list()
        self.thread = ScanThread(self.selected_directory, ignore_list)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.on_baseline_finished)
        self.thread.start()

    def on_baseline_finished(self, result):
        with open(self.baseline_file, 'w') as f:
            json.dump(result, f)
        
        # Start background backup instead of blocking loop
        self.status_bar.setText("Creating File Snapshots (Background)...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.backup_thread = InitialBackupThread(
            self.selected_directory, 
            list(result.keys()), 
            self.backup_mgr, 
            self.db
        )
        self.backup_thread.progress.connect(self.progress_bar.setValue)
        self.backup_thread.finished.connect(self.on_all_backups_finished)
        self.backup_thread.start()

    def on_all_backups_finished(self):
        self.progress_bar.setVisible(False)
        self.baseline_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.status_bar.setText("Baseline & Snapshots created.")
        QMessageBox.information(self, "Success", "Baseline created and all files backed up for restoration.")

    def scan_files(self):
        if not self.selected_directory or not os.path.exists(self.baseline_file):
            return

        self.baseline_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.setText("Scanning for changes...")

        ignore_list = self.db.get_ignore_list()
        self.thread = ScanThread(self.selected_directory, ignore_list)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.on_scan_finished)
        self.thread.start()

    def on_scan_finished(self, current_scan):
        with open(self.baseline_file, 'r') as f:
            baseline = json.load(f)

        self.current_results = compare_scans(baseline, current_scan)
        self.display_results(self.current_results)

        self.progress_bar.setVisible(False)
        self.baseline_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.export_btn.setEnabled(True) # Enable export after scan
        self.status_bar.setText(f"Scan complete. {len(self.current_results)} changes detected.")

    def display_results(self, results):
        self.table.setRowCount(0)
        if not results:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("All files are intact"))
            self.table.item(0, 0).setForeground(QColor("#4ec9b0"))
            return

        for row, res in enumerate(results):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(res["file"]))
            self.table.setItem(row, 1, QTableWidgetItem(res["status"]))
            self.table.setItem(row, 2, QTableWidgetItem(res["details"]))

            status = res["status"]
            if "Modified" in status: color = QColor("#f44747")
            elif "New" in status: color = QColor("#dcdcaa")
            elif "Deleted" in status: color = QColor("#ce9178")
            else: color = QColor("#d4d4d4")
            self.table.item(row, 1).setForeground(color)

    def clear_baseline(self):
        if os.path.exists(self.baseline_file):
            os.remove(self.baseline_file)
            self.scan_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.table.setRowCount(0)
            self.current_results = []
            self.status_bar.setText("Baseline cleared.")
            QMessageBox.information(self, "Baseline Cleared", "Baseline file has been deleted.")
