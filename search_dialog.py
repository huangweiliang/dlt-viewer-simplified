"""
Search Dialog for DLT Viewer
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QListWidget,
                             QListWidgetItem, QColorDialog, QMessageBox, QComboBox, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from typing import List, Tuple
import json
import os
import os


class SearchPatternItem(QListWidgetItem):
    """Custom list item for search patterns"""
    def __init__(self, pattern: str, is_regex: bool, color: str):
        super().__init__()
        self.pattern = pattern
        self.is_regex = is_regex
        self.color = color
        self.update_text()
    
    def update_text(self):
        """Update the display text"""
        regex_marker = "[REGEX] " if self.is_regex else ""
        self.setText(f"{regex_marker}{self.pattern}")
        self.setBackground(QColor(self.color))


class SearchDialog(QDialog):
    """Dialog for searching messages"""
    
    HISTORY_FILE = "search_history.json"
    MAX_HISTORY = 50
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_patterns: List[Tuple[str, bool, str]] = []
        self.search_history: List[str] = []
        self.load_search_history()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Search Messages")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Make the dialog independent from parent window minimize/maximize
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        
        layout = QVBoxLayout()
        
        # Search input section
        input_layout = QVBoxLayout()
        
        input_layout.addWidget(QLabel("Search Pattern:"))
        
        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setInsertPolicy(QComboBox.NoInsert)
        self.search_input.lineEdit().setPlaceholderText("Enter search text or regular expression...")
        self.search_input.setMaxCount(self.MAX_HISTORY)
        
        # Populate with history
        if self.search_history:
            self.search_input.addItems(self.search_history)
        
        input_layout.addWidget(self.search_input)
        
        # Regex checkbox
        self.regex_checkbox = QCheckBox("Use Regular Expression")
        input_layout.addWidget(self.regex_checkbox)
        
        # Color selection
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Highlight Color:"))
        
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self.select_color)
        self.selected_color = "#FFFF99"  # Default light yellow
        self.update_color_button()
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        
        input_layout.addLayout(color_layout)
        
        # Add pattern button
        add_button = QPushButton("Add Pattern")
        add_button.clicked.connect(self.add_pattern)
        input_layout.addWidget(add_button)
        
        layout.addLayout(input_layout)
        
        # Pattern list section
        layout.addWidget(QLabel("Search Patterns:"))
        
        self.pattern_list = QListWidget()
        layout.addWidget(self.pattern_list)
        
        # Remove pattern button
        remove_button = QPushButton("Remove Selected Pattern")
        remove_button.clicked.connect(self.remove_pattern)
        layout.addWidget(remove_button)
        
        # Save/Load pattern buttons
        pattern_file_layout = QHBoxLayout()
        
        save_button = QPushButton("Save Patterns to File...")
        save_button.clicked.connect(self.save_patterns_to_file)
        pattern_file_layout.addWidget(save_button)
        
        load_button = QPushButton("Load Patterns from File...")
        load_button.clicked.connect(self.load_patterns_from_file)
        pattern_file_layout.addWidget(load_button)
        
        layout.addLayout(pattern_file_layout)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.accept)
        search_button.setDefault(True)
        button_layout.addWidget(search_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def select_color(self):
        """Open color picker dialog"""
        color = QColorDialog.getColor(QColor(self.selected_color), self, "Select Highlight Color")
        if color.isValid():
            self.selected_color = color.name()
            self.update_color_button()
    
    def update_color_button(self):
        """Update the color button appearance"""
        self.color_button.setStyleSheet(
            f"background-color: {self.selected_color}; "
            f"border: 1px solid #000000; "
            f"padding: 5px;"
        )
    
    def add_pattern(self):
        """Add a search pattern to the list"""
        pattern = self.search_input.currentText().strip()
        
        if not pattern:
            QMessageBox.warning(self, "Empty Pattern", "Please enter a search pattern.")
            return
        
        is_regex = self.regex_checkbox.isChecked()
        
        # Validate regex if enabled
        if is_regex:
            import re
            try:
                re.compile(pattern)
            except re.error as e:
                QMessageBox.warning(
                    self, 
                    "Invalid Regular Expression", 
                    f"The regular expression is invalid:\n{str(e)}"
                )
                return
            
            # Check if pattern contains OR operator (|)
            if '|' in pattern:
                response = QMessageBox.question(
                    self,
                    "Multiple Patterns Detected",
                    f"This regex contains OR operator (|).\n\n"
                    f"Do you want to split '{pattern}' into separate patterns with different colors?\n\n"
                    f"Yes: Each alternative gets its own color\n"
                    f"No: Entire pattern uses one color",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if response == QMessageBox.Yes:
                    # Split by | and add each as separate pattern
                    sub_patterns = [p.strip() for p in pattern.split('|') if p.strip()]
                    for sub_pattern in sub_patterns:
                        item = SearchPatternItem(sub_pattern, True, self.selected_color)
                        self.pattern_list.addItem(item)
                        self.search_patterns.append((sub_pattern, True, self.selected_color))
                        self.cycle_color()
                    
                    # Add to history and save
                    self.add_to_history(pattern)
                    self.search_input.clearEditText()
                    return
        
        # Add to list
        item = SearchPatternItem(pattern, is_regex, self.selected_color)
        self.pattern_list.addItem(item)
        self.search_patterns.append((pattern, is_regex, self.selected_color))
        
        # Add to history and save
        self.add_to_history(pattern)
        
        # Clear input
        self.search_input.clearEditText()
        
        # Change color for next pattern
        self.cycle_color()
    
    def remove_pattern(self):
        """Remove selected pattern from the list"""
        current_row = self.pattern_list.currentRow()
        if current_row >= 0:
            self.pattern_list.takeItem(current_row)
            self.search_patterns.pop(current_row)
    
    def cycle_color(self):
        """Cycle to next default color"""
        default_colors = [
            "#FFFF99",  # Light Yellow
            "#99FF99",  # Light Green
            "#99FFFF",  # Light Cyan
            "#FFB3FF",  # Light Magenta
            "#FFCC99",  # Light Orange
            "#B3D9FF",  # Light Blue
            "#E6B3FF",  # Light Purple
            "#FFFFB3",  # Cream
            "#B3FFB3",  # Pale Green
            "#FFD9B3",  # Peach
            "#D9B3FF",  # Lavender
        ]
        
        current_index = default_colors.index(self.selected_color) if self.selected_color in default_colors else -1
        next_index = (current_index + 1) % len(default_colors)
        self.selected_color = default_colors[next_index]
        self.update_color_button()
    
    def get_search_patterns(self) -> List[Tuple[str, bool, str]]:
        """Get the list of search patterns"""
        return self.search_patterns
    
    def load_search_history(self):
        """Load search history from file"""
        try:
            if os.path.exists(self.HISTORY_FILE):
                with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.search_history = json.load(f)
                    # Ensure it's a list and limit size
                    if isinstance(self.search_history, list):
                        self.search_history = self.search_history[:self.MAX_HISTORY]
                    else:
                        self.search_history = []
            else:
                self.search_history = []
        except Exception as e:
            print(f"Error loading search history: {e}")
            self.search_history = []
    
    def save_search_history(self):
        """Save search history to file"""
        try:
            with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.search_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving search history: {e}")
    
    def add_to_history(self, pattern: str):
        """Add a pattern to search history"""
        if not pattern:
            return
        
        # Remove if already exists (move to top)
        if pattern in self.search_history:
            self.search_history.remove(pattern)
        
        # Add to beginning
        self.search_history.insert(0, pattern)
        
        # Limit size
        self.search_history = self.search_history[:self.MAX_HISTORY]
        
        # Update combobox
        self.search_input.clear()
        self.search_input.addItems(self.search_history)
        
        # Save to file
        self.save_search_history()
    
    def save_patterns_to_file(self):
        """Save current search patterns to a JSON file"""
        if not self.search_patterns:
            QMessageBox.information(self, "No Patterns", 
                                  "No patterns to save. Add some patterns first.")
            return
        
        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Search Patterns", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # Prepare pattern data
            patterns_data = []
            for pattern, is_regex, color in self.search_patterns:
                patterns_data.append({
                    'pattern': pattern,
                    'is_regex': is_regex,
                    'color': color  # Color is already a string
                })
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(patterns_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", 
                                  f"Patterns saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to save patterns:\n{str(e)}")
    
    def load_patterns_from_file(self):
        """Load search patterns from a JSON file"""
        # Get file path from user
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Search Patterns", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # Load from file
            with open(file_path, 'r', encoding='utf-8') as f:
                patterns_data = json.load(f)
            
            if not isinstance(patterns_data, list):
                QMessageBox.warning(self, "Invalid Format", 
                                  "File does not contain a valid pattern list.")
                return
            
            # Ask user whether to replace or append
            if self.search_patterns:
                reply = QMessageBox.question(
                    self, "Load Patterns",
                    "Do you want to replace existing patterns?\n\n"
                    "Yes: Replace all patterns\n"
                    "No: Append to existing patterns",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Cancel:
                    return
                elif reply == QMessageBox.Yes:
                    self.search_patterns.clear()
                    self.pattern_list.clear()
            
            # Load patterns
            loaded_count = 0
            for item in patterns_data:
                if not isinstance(item, dict):
                    continue
                
                pattern = item.get('pattern', '')
                is_regex = item.get('is_regex', False)
                color_str = item.get('color', '#ffff00')
                
                if not pattern:
                    continue
                
                # Add pattern
                self.search_patterns.append((pattern, is_regex, color_str))
                
                # Add to list widget
                list_item = SearchPatternItem(pattern, is_regex, color_str)
                self.pattern_list.addItem(list_item)
                
                loaded_count += 1
            
            if loaded_count > 0:
                QMessageBox.information(self, "Success", 
                                      f"Loaded {loaded_count} pattern(s) from:\n{file_path}")
            else:
                QMessageBox.warning(self, "No Patterns", 
                                  "No valid patterns found in file.")
        
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", 
                               "Invalid JSON file format.")
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to load patterns:\n{str(e)}")
