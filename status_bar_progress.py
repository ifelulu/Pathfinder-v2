#!/usr/bin/env python
"""
Status bar widget with progress indicators for long operations
"""

import sys
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QProgressBar, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor

class StatusBarProgress(QWidget):
    """Widget for status bar that can show progress bar and spinner."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(10)
        
        # Status message label
        self.message_label = QLabel()
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.message_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setHidden(True)
        layout.addWidget(self.progress_bar)
        
        # Spinner - Using a text-based spinner for simplicity
        self.spinner_label = QLabel()
        self.spinner_label.setFixedSize(16, 16)
        self.spinner_label.setHidden(True)
        layout.addWidget(self.spinner_label)
        
        # Spinner animation using text characters
        self.spinner_chars = ["|", "/", "-", "\\"]
        self.spinner_index = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self._update_spinner)
        self.spinner_timer.setInterval(100)
        
        # Add stretch to push everything to the left
        layout.addStretch(1)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(24)
        
        # Timer for clearing messages
        self.clear_timer = QTimer(self)
        self.clear_timer.timeout.connect(self.clear_message)
    
    def _update_spinner(self):
        """Update the spinner animation"""
        self.spinner_label.setText(self.spinner_chars[self.spinner_index])
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
        
    def show_message(self, message, timeout=0):
        """
        Show a message in the status bar.
        If timeout > 0, message will be cleared after timeout milliseconds.
        If timeout = 0, message will remain until another message is set.
        """
        # Check for preferences manager in parent window
        if hasattr(self.parent_window, 'preferences_manager') and timeout > 0:
            # Use timeout from preferences - only if a default timeout was provided
            # This allows longer custom timeouts passed by caller to override preferences
            if timeout == 3000:  # Default timeout often used in the app
                timeout = self.parent_window.preferences_manager.get_status_message_timeout()
        
        self.clear_timer.stop()  # Stop any previous timer
        self.message_label.setText(message)
        
        if timeout > 0:
            self.clear_timer.start(timeout)
            
    def clear_message(self):
        """Clear the status message."""
        self.message_label.clear()
        self.clear_timer.stop()
        
    def show_progress(self, visible=True, min_val=0, max_val=100):
        """Show or hide the progress bar."""
        if visible:
            self.progress_bar.setRange(min_val, max_val)
            self.progress_bar.setValue(min_val)
        
        self.progress_bar.setHidden(not visible)
            
    def update_progress(self, value):
        """Update the progress bar value."""
        self.progress_bar.setValue(value)
        
        # Ensure it's visible when updated
        if self.progress_bar.isHidden():
            self.progress_bar.setHidden(False)
            
    def show_spinner(self, visible=True):
        """Show or hide the spinner animation."""
        if visible:
            self.spinner_label.setHidden(False)
            self.spinner_timer.start()
        else:
            self.spinner_timer.stop()
            self.spinner_label.setHidden(True) 