from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, 
    QHBoxLayout, QWidget, QTextBrowser
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont


class AboutDialog(QDialog):
    """Dialog to show information about the application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About PathFinder")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI elements for the about dialog."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("PathFinder Warehouse Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Version
        version_label = QLabel("Version 1.0")
        version_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(version_label)
        
        # Description
        description_browser = QTextBrowser()
        description_browser.setOpenExternalLinks(True)
        description_browser.setHtml("""
        <p>PathFinder is a warehouse management application designed to optimize pick paths 
        and analyze warehouse operations.</p>
        
        <h3>Key Features:</h3>
        <ul>
            <li>PDF floor plan import and scaling</li>
            <li>Path optimization with obstacle avoidance</li>
            <li>Picklist analysis and visualization</li>
            <li>Warehouse operation animation</li>
        </ul>
        
        <p>&copy; 2024 PathFinder Development Team. All rights reserved.</p>
        """)
        main_layout.addWidget(description_browser)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout) 