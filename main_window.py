"""
Main Window for DLT Viewer
"""
from PyQt5.QtWidgets import (QMainWindow, QTableWidget, QTableWidgetItem, 
                             QFileDialog, QMessageBox, QProgressDialog, 
                             QHeaderView, QApplication, QAction, QMenu, QLabel)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QKeyEvent, QClipboard
from dlt_parser import DLTParser, DLTMessage
from search_dialog import SearchDialog
from typing import List
import os
import psutil


class LoadingThread(QThread):
    """Thread for loading DLT files in background"""
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)  # messages
    error = pyqtSignal(str)  # error message
    
    def __init__(self, file_paths: List[str]):
        super().__init__()
        self.file_paths = file_paths
        
    def run(self):
        try:
            parser = DLTParser()
            all_messages = []
            total_files = len(self.file_paths)
            
            # Sort files by index
            sorted_files = DLTParser.sort_files_by_index(self.file_paths)
            
            global_index = 0
            for i, file_path in enumerate(sorted_files):
                self.progress.emit(i + 1, total_files)
                messages = parser.parse_file(file_path, global_index)
                all_messages.extend(messages)
                global_index += len(messages)
            
            self.finished.emit(all_messages)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.messages: List[DLTMessage] = []
        self.filtered_indices: List[int] = []  # Indices of messages matching search
        self.search_patterns = []  # List of (pattern, is_regex, color) tuples
        self.current_files = []
        self.results_window = None  # Reference to results window
        
        self.init_ui()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events"""
        if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self.copy_selected_rows()
        else:
            super().keyPressEvent(event)
    
    def copy_selected_rows(self):
        """Copy selected rows to clipboard with all columns"""
        from PyQt5.QtWidgets import QProgressDialog
        
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        # Sort rows
        sorted_rows = sorted(selected_rows)
        row_count = len(sorted_rows)
        
        # Show progress dialog for large selections
        progress = None
        if row_count > 100:
            progress = QProgressDialog("Copying rows to clipboard...", "Cancel", 0, row_count, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
        
        # Build text with all columns
        lines = []
        total_chars = 0
        max_clipboard_size = 50 * 1024 * 1024  # 50 MB limit
        
        for idx, row in enumerate(sorted_rows):
            # Update progress
            if progress and idx % 50 == 0:
                progress.setValue(idx)
                QApplication.processEvents()
                if progress.wasCanceled():
                    self.statusBar().showMessage("Copy cancelled", 2000)
                    return
            
            columns = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    columns.append(item.text())
                else:
                    columns.append("")
            
            line = "  ".join(columns)
            lines.append(line)
            total_chars += len(line) + 1  # +1 for newline
            
            # Check size limit
            if total_chars > max_clipboard_size:
                if progress:
                    progress.close()
                response = QMessageBox.warning(
                    self, 
                    "Data Too Large", 
                    f"Selected data exceeds clipboard size limit ({idx + 1} rows, ~{total_chars // (1024*1024)} MB).\n\n"
                    f"Only the first {idx} rows will be copied.\n\nContinue?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if response == QMessageBox.No:
                    self.statusBar().showMessage("Copy cancelled", 2000)
                    return
                break
        
        if progress:
            progress.setValue(row_count)
        
        # Copy to clipboard with error handling
        try:
            clipboard = QApplication.clipboard()
            clipboard.clear()
            text = "\n".join(lines)
            
            # Try to set clipboard with timeout handling
            clipboard.setText(text, QClipboard.Clipboard)
            
            # Also set to selection clipboard on Linux
            if clipboard.supportsSelection():
                clipboard.setText(text, QClipboard.Selection)
            
            if progress:
                progress.close()
            
            data_size = len(text)
            if data_size > 1024 * 1024:
                size_str = f"{data_size / (1024 * 1024):.1f} MB"
            elif data_size > 1024:
                size_str = f"{data_size / 1024:.1f} KB"
            else:
                size_str = f"{data_size} bytes"
            
            self.statusBar().showMessage(
                f"Copied {len(lines)} row(s) to clipboard ({size_str})", 
                3000
            )
        except Exception as e:
            if progress:
                progress.close()
            QMessageBox.warning(
                self, 
                "Copy Error", 
                f"Failed to copy to clipboard:\n{str(e)}\n\n"
                f"Try selecting fewer rows or saving to a file instead."
            )
        
    def show_context_menu(self, position):
        """Show context menu for table"""
        menu = QMenu()
        
        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_selected_rows)
        menu.addAction(copy_action)
        
        # Show menu at cursor position
        menu.exec_(self.table.viewport().mapToGlobal(position))
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("DLT Viewer - SoC DLT parser")
        self.setGeometry(100, 100, 1400, 800)
        
        # Create menu bar
        self.create_menus()
        
        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            'Index', 'Timestamp', 'ECU ID', 'App ID', 
            'Context ID', 'Type', 'Payload', 'Source'
        ])
        
        # Set smaller font and reduce row height
        from PyQt5.QtGui import QFont
        table_font = QFont()
        table_font.setPointSize(9)  # Readable font size
        self.table.setFont(table_font)
        self.table.verticalHeader().setDefaultSectionSize(22)  # Adjusted row height
        
        # Set table properties
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)  # Enable multi-row selection
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setWordWrap(True)  # Enable word wrapping for long text
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)  # Auto-adjust row height
        
        # Set column widths - all interactive for manual adjustment
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        # Set initial widths
        self.table.setColumnWidth(0, 60)   # Index
        self.table.setColumnWidth(1, 180)  # Timestamp
        self.table.setColumnWidth(2, 60)   # ECU ID
        self.table.setColumnWidth(3, 60)   # App ID
        self.table.setColumnWidth(4, 80)   # Context ID
        self.table.setColumnWidth(5, 60)   # Type
        self.table.setColumnWidth(6, 1000)  # Payload
        self.table.setColumnWidth(7, 120)  # Source
        # Make last column stretch to fill remaining space
        header.setStretchLastSection(True)
        
        self.setCentralWidget(self.table)
        
        # Create status bar with permanent widgets
        self.statusBar().showMessage("Ready")
        
        # Add memory usage as permanent widget
        self.memory_label = QLabel()
        self.memory_label.setStyleSheet("QLabel { padding: 0 5px; }")
        self.update_memory_usage()
        self.statusBar().addPermanentWidget(self.memory_label)
        
        # Add version info as permanent widget on the right
        self.version_label = QLabel(" v0.11 ")
        self.version_label.setStyleSheet("QLabel { padding: 0 5px; }")
        self.statusBar().addPermanentWidget(self.version_label)
        
    def create_menus(self):
        """Create application menus"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        open_action = QAction('&Open DLT Files...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.setStatusTip('Open DLT files')
        open_action.triggered.connect(self.open_files)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Search menu
        search_menu = menubar.addMenu('&Search')
        
        search_action = QAction('&Find...', self)
        search_action.setShortcut('Ctrl+F')
        search_action.setStatusTip('Search in messages')
        search_action.triggered.connect(self.open_search_dialog)
        search_menu.addAction(search_action)
        
        clear_search_action = QAction('&Clear Search', self)
        clear_search_action.setShortcut('Ctrl+Shift+F')
        clear_search_action.setStatusTip('Clear search highlighting')
        clear_search_action.triggered.connect(self.clear_search)
        search_menu.addAction(clear_search_action)
        
        search_menu.addSeparator()
        
        show_results_action = QAction('Show &Results Window', self)
        show_results_action.setShortcut('Ctrl+R')
        show_results_action.setStatusTip('Show search results in separate window')
        show_results_action.triggered.connect(self.show_results_window)
        search_menu.addAction(show_results_action)
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        about_action = QAction('&About', self)
        about_action.setStatusTip('About DLT Viewer')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def open_files(self):
        """Open file dialog to select DLT files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select DLT Files",
            "",
            "DLT Files (*.dlt);;All Files (*.*)"
        )
        
        if file_paths:
            self.load_files(file_paths)
    
    def load_files(self, file_paths: List[str]):
        """Load DLT files"""
        self.current_files = file_paths
        
        # Create progress dialog
        progress = QProgressDialog("Loading DLT files...", "Cancel", 0, len(file_paths), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        # Create loading thread
        self.loading_thread = LoadingThread(file_paths)
        self.loading_thread.progress.connect(lambda curr, total: progress.setValue(curr))
        self.loading_thread.finished.connect(lambda msgs: self.on_files_loaded(msgs, progress))
        self.loading_thread.error.connect(lambda err: self.on_loading_error(err, progress))
        
        # Start loading
        self.loading_thread.start()
    
    def on_files_loaded(self, messages: List[DLTMessage], progress: QProgressDialog):
        """Callback when files are loaded"""
        progress.close()
        self.messages = messages
        self.display_messages()
        
        file_count = len(self.current_files)
        msg_count = len(messages)
        self.statusBar().showMessage(
            f"Loaded {msg_count} messages from {file_count} file(s)"
        )
        self.update_memory_usage()
    
    def on_loading_error(self, error: str, progress: QProgressDialog):
        """Callback when loading error occurs"""
        progress.close()
        QMessageBox.critical(self, "Loading Error", f"Error loading files:\n{error}")
    
    def display_messages(self, message_indices: List[int] = None):
        """
        Display messages in the table
        
        Args:
            message_indices: If provided, only display messages at these indices
        """
        if message_indices is None:
            messages_to_display = self.messages
        else:
            messages_to_display = [self.messages[i] for i in message_indices]
        
        total_messages = len(messages_to_display)
        
        # Show progress dialog for large datasets
        progress = None
        if total_messages > 1000:
            progress = QProgressDialog("Displaying messages...", None, 0, total_messages, self)
            progress.setWindowTitle("Loading Display")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
        
        self.table.setRowCount(total_messages)
        
        # Disable sorting during population for better performance
        self.table.setSortingEnabled(False)
        
        for row, message in enumerate(messages_to_display):
            # Update progress every 500 rows
            if progress and row % 500 == 0:
                progress.setValue(row)
                QApplication.processEvents()
            
            self.table.setItem(row, 0, QTableWidgetItem(str(message.index)))
            self.table.setItem(row, 1, QTableWidgetItem(message.timestamp))
            self.table.setItem(row, 2, QTableWidgetItem(message.ecu_id))
            self.table.setItem(row, 3, QTableWidgetItem(message.app_id))
            self.table.setItem(row, 4, QTableWidgetItem(message.context_id))
            self.table.setItem(row, 5, QTableWidgetItem(message.message_type))
            self.table.setItem(row, 6, QTableWidgetItem(message.payload))
            self.table.setItem(row, 7, QTableWidgetItem(message.source_file))
        
        # Re-enable sorting
        self.table.setSortingEnabled(True)
        
        if progress:
            progress.setValue(total_messages)
            progress.close()
        
        # Apply search highlighting if active
        if self.search_patterns:
            self.apply_search_highlighting()
    
    def open_search_dialog(self):
        """Open the search dialog"""
        if not self.messages:
            QMessageBox.information(self, "No Data", "Please load DLT files first.")
            return
        
        dialog = SearchDialog(self)
        if dialog.exec_():
            patterns = dialog.get_search_patterns()
            if patterns:
                self.search_patterns = patterns
                self.perform_search()
    
    def perform_search(self):
        """Perform search based on current search patterns"""
        if not self.search_patterns:
            return
        
        import re
        
        matching_indices = []
        total_messages = len(self.messages)
        
        # Create progress dialog
        progress = QProgressDialog("Searching messages...", "Cancel", 0, total_messages, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setWindowTitle("Search Progress")
        progress.setValue(0)
        
        for idx, message in enumerate(self.messages):
            # Update progress every 100 messages or at the end
            if idx % 100 == 0 or idx == total_messages - 1:
                progress.setValue(idx + 1)
                progress.setLabelText(f"Searching messages... {idx + 1}/{total_messages}")
                QApplication.processEvents()  # Keep UI responsive
                
                # Check if user cancelled
                if progress.wasCanceled():
                    self.statusBar().showMessage("Search cancelled")
                    progress.close()
                    return
            
            # Search in all text fields
            search_text = f"{message.ecu_id} {message.app_id} {message.context_id} {message.payload}"
            
            for pattern, is_regex, color in self.search_patterns:
                try:
                    if is_regex:
                        if re.search(pattern, search_text, re.IGNORECASE):
                            matching_indices.append(idx)
                            break
                    else:
                        if pattern.lower() in search_text.lower():
                            matching_indices.append(idx)
                            break
                except re.error:
                    continue
        
        progress.close()
        
        # Store filtered indices for results window
        self.filtered_indices = matching_indices
        
        # Apply highlighting
        self.apply_search_highlighting()
        
        self.statusBar().showMessage(
            f"Found {len(matching_indices)} matching messages"
        )
        self.update_memory_usage()
    
    def apply_search_highlighting(self):
        """Apply color highlighting to matching rows"""
        import re
        
        for row in range(self.table.rowCount()):
            # Get message index for this row
            index_item = self.table.item(row, 0)
            if not index_item:
                continue
            
            message_idx = int(index_item.text())
            if message_idx >= len(self.messages):
                continue
                
            message = self.messages[message_idx]
            search_text = f"{message.ecu_id} {message.app_id} {message.context_id} {message.payload}"
            
            # Check each pattern and use the first match's color
            for pattern, is_regex, color in self.search_patterns:
                matched = False
                try:
                    if is_regex:
                        matched = bool(re.search(pattern, search_text, re.IGNORECASE))
                    else:
                        matched = pattern.lower() in search_text.lower()
                except re.error:
                    continue
                
                if matched:
                    # Apply color to entire row
                    brush = QBrush(QColor(color))
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(brush)
                    break
    
    def clear_search(self):
        """Clear search highlighting"""
        self.search_patterns = []
        self.filtered_indices = []
        
        # Remove all background colors
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QBrush(Qt.white))
        
        # Close results window if open
        if self.results_window:
            self.results_window.close()
            self.results_window = None
        
        self.statusBar().showMessage("Search cleared")
    
    def show_results_window(self):
        """Show search results in a separate window"""
        if not self.search_patterns:
            QMessageBox.information(self, "No Search", "Please perform a search first.")
            return
        
        if not self.filtered_indices:
            QMessageBox.information(self, "No Results", "No matching messages found.")
            return
        
        # Create or update results window
        from results_window import ResultsWindow
        if self.results_window is None or not self.results_window.isVisible():
            self.results_window = ResultsWindow(self)
        
        # Update results
        filtered_messages = [self.messages[i] for i in self.filtered_indices]
        self.results_window.display_results(filtered_messages, self.search_patterns)
        self.results_window.show()
        self.results_window.raise_()
        self.results_window.activateWindow()
    
    def show_about(self):
        """Show about dialog"""
        about_text = """<h2>DLT Viewer - SoC DLT parser</h2>
        <p><b>Version:</b> 0.11</p>
        <p><b>Location:</b> Novi, MI</p>
        <br>
        <p><b>Requirements and Testing:</b><br>
        Huang Weiliang</p>
        <p><b>Implementation:</b><br>
        GitHub Copilot</p>
        <br>
        <p>A lightweight DLT (Diagnostic Log and Trace) file viewer<br>
        with advanced search capabilities.</p>
        <br>
        <p><b>Copyright © 2025</b><br>
        All rights reserved.</p>
        <p style="font-size: 9px; color: #666;">
        This software is provided "as is" without warranty of any kind.<br>
        For internal use only. Not for redistribution.</p>
        """
        QMessageBox.about(self, "About DLT Viewer", about_text)
    
    def update_memory_usage(self):
        """Update memory usage display in status bar"""
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024  # Convert bytes to MB
            
            if mem_mb < 1024:
                mem_text = f" Memory: {mem_mb:.1f} MB "
            else:
                mem_gb = mem_mb / 1024
                mem_text = f" Memory: {mem_gb:.2f} GB "
            
            self.memory_label.setText(mem_text)
        except Exception:
            self.memory_label.setText(" Memory: N/A ")
