"""
Results Window for DLT Viewer - Shows only search results
"""
from PyQt5.QtWidgets import (QMainWindow, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QAction, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QFont, QKeyEvent
from typing import List, Tuple
import re


class ResultsWindow(QMainWindow):
    """Window displaying only search results"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.search_patterns = []
        self.init_ui()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events"""
        if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self.copy_selected_rows()
        else:
            super().keyPressEvent(event)
    
    def copy_selected_rows(self):
        """Copy selected rows to clipboard with all columns"""
        from PyQt5.QtWidgets import QMessageBox, QProgressDialog
        from PyQt5.QtGui import QClipboard
        
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
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Search Results - DLT Viewer")
        self.setGeometry(150, 150, 1400, 600)
        
        # Create menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        
        close_action = QAction('&Close', self)
        close_action.setShortcut('Ctrl+W')
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        
        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            'Index', 'Timestamp', 'ECU ID', 'App ID', 
            'Context ID', 'Type', 'Payload', 'Source'
        ])
        
        # Set smaller font and reduce row height
        table_font = QFont()
        table_font.setPointSize(9)  # Readable font size
        self.table.setFont(table_font)
        self.table.verticalHeader().setDefaultSectionSize(22)  # Adjusted row height
        
        # Set table properties
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        
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
        self.table.setColumnWidth(6, 1040)  # Payload
        self.table.setColumnWidth(7, 80)  # Source
        # Make last column stretch to fill remaining space
        header.setStretchLastSection(True)
        
        self.setCentralWidget(self.table)
        
        # Create status bar
        self.statusBar().showMessage("Ready")
    
    def display_results(self, messages: List, search_patterns: List[Tuple[str, bool, str]]):
        """
        Display search results
        
        Args:
            messages: List of DLTMessage objects to display
            search_patterns: List of (pattern, is_regex, color) tuples
        """
        self.messages = messages
        self.search_patterns = search_patterns
        
        self.table.setRowCount(len(messages))
        
        for row, message in enumerate(messages):
            self.table.setItem(row, 0, QTableWidgetItem(str(message.index)))
            self.table.setItem(row, 1, QTableWidgetItem(message.timestamp))
            self.table.setItem(row, 2, QTableWidgetItem(message.ecu_id))
            self.table.setItem(row, 3, QTableWidgetItem(message.app_id))
            self.table.setItem(row, 4, QTableWidgetItem(message.context_id))
            self.table.setItem(row, 5, QTableWidgetItem(message.message_type))
            self.table.setItem(row, 6, QTableWidgetItem(message.payload))
            self.table.setItem(row, 7, QTableWidgetItem(message.source_file))
        
        # Apply color highlighting
        self.apply_highlighting()
        
        # Update status bar
        self.statusBar().showMessage(f"Showing {len(messages)} matching message(s)")
    
    def apply_highlighting(self):
        """Apply color highlighting based on search patterns"""
        for row in range(self.table.rowCount()):
            if row >= len(self.messages):
                continue
            
            message = self.messages[row]
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
