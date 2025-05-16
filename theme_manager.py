from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings, QObject, Signal
from PySide6.QtGui import QColor
from accessibility_utils import AccessibilityUtils

class ThemeManager(QObject):
    """
    Manages light and dark themes for the application.
    Provides signals to notify when the theme changes.
    """
    # Signal emitted when theme changes
    theme_changed = Signal(str)
    
    # Theme constants
    LIGHT_THEME = "light"
    DARK_THEME = "dark"
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("WarehousePathFinder", "PathFinder")
        self._current_theme = self.settings.value("theme", self.LIGHT_THEME)
        
        # Flag to enable/disable high contrast mode
        self._high_contrast_mode = self.settings.value("high_contrast_mode", False, type=bool)
    
    def apply_theme(self, theme=None):
        """Apply the specified theme or the current theme if none specified"""
        if theme:
            self._current_theme = theme
            
        # Save theme preference
        self.settings.setValue("theme", self._current_theme)
        
        # Get stylesheet based on theme
        if self._current_theme == self.DARK_THEME:
            stylesheet = self._get_dark_theme_stylesheet()
        else:
            stylesheet = self._get_light_theme_stylesheet()
        
        # Apply high contrast adjustments if enabled
        if self._high_contrast_mode:
            stylesheet = AccessibilityUtils.enhance_stylesheet_contrast(stylesheet)
        
        # Apply the stylesheet
        QApplication.instance().setStyleSheet(stylesheet)
            
        # Emit signal
        self.theme_changed.emit(self._current_theme)
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        if self._current_theme == self.LIGHT_THEME:
            self.apply_theme(self.DARK_THEME)
        else:
            self.apply_theme(self.LIGHT_THEME)
    
    def toggle_high_contrast(self):
        """Toggle high contrast mode"""
        self._high_contrast_mode = not self._high_contrast_mode
        self.settings.setValue("high_contrast_mode", self._high_contrast_mode)
        
        # Re-apply current theme with new contrast settings
        self.apply_theme()
        
        return self._high_contrast_mode
    
    def is_high_contrast_enabled(self):
        """Return whether high contrast mode is enabled"""
        return self._high_contrast_mode
    
    def get_current_theme(self):
        """Return the current theme"""
        return self._current_theme
    
    def is_dark_theme(self):
        """Return whether the current theme is dark"""
        return self._current_theme == self.DARK_THEME
    
    def _get_light_theme_stylesheet(self):
        """Return the light theme stylesheet with improved accessibility"""
        # Define key colors for the light theme
        bg_color = QColor("#f5f5f5")  # Main background 
        text_color = QColor("#202020") # Main text color
        disabled_text = QColor("#909090") # Disabled text
        
        # Check for sufficient contrast and adjust if needed
        if not AccessibilityUtils.is_contrast_sufficient(text_color, bg_color):
            text_color = AccessibilityUtils.adjust_color_for_contrast(text_color, bg_color)
            
        # Ensure disabled text has sufficient contrast (3:1 minimum)
        disabled_text = AccessibilityUtils.adjust_color_for_contrast(
            disabled_text, bg_color, min_ratio=3.0)
        
        # Update the stylesheet with accessibility-enhanced colors
        stylesheet = """
        /* Light Theme */
        QMainWindow, QDialog, QWidget {
            background-color: #f5f5f5;
            color: """ + text_color.name() + """;
        }
        
        QToolBar, QStatusBar, QMenuBar {
            background-color: #f0f0f0;
            color: #202020;
            border: none;
        }
        
        QMenuBar::item, QMenu::item {
            color: #202020;
        }
        
        QMenuBar::item:selected, QMenu::item:selected {
            background-color: #d0d0d0;
        }
        
        QMenu {
            background-color: #f8f8f8;
            color: #202020;
            border: 1px solid #c0c0c0;
        }
        
        QPushButton {
            background-color: #e0e0e0;
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            padding: 4px 8px;
            color: #202020;
        }
        
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: """ + disabled_text.name() + """;
            border: 1px solid #d0d0d0;
        }
        
        QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            padding: 2px;
            color: #202020;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 15px;
            border-left-width: 1px;
            border-left-color: #b0b0b0;
            border-left-style: solid;
        }
        
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #202020;
            selection-background-color: #d0d0d0;
            selection-color: #202020;
        }
        
        QLabel {
            color: #202020;
        }
        
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            padding: 2px;
            color: #202020;
        }
        
        QSplitter::handle {
            background-color: #c0c0c0;
        }
        
        QStatusBar {
            border-top: 1px solid #c0c0c0;
            background-color: #f0f0f0;
            color: #202020;
        }
        
        QProgressBar {
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            background-color: #ffffff;
            text-align: center;
            color: #202020;
        }
        
        QProgressBar::chunk {
            background-color: #05B8CC;
            border-radius: 3px;
        }
        
        QToolTip {
            background-color: #f8f8f8;
            color: #202020;
            border: 1px solid #c0c0c0;
            padding: 2px;
        }
        
        /* Scrollbars */
        QScrollBar:vertical, QScrollBar:horizontal {
            background-color: #f0f0f0;
            border: none;
        }
        
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background-color: #c0c0c0;
            border-radius: 3px;
        }
        
        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
            border: none;
        }
        
        /* PdfViewer customizations */
        PdfViewer {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            color: #202020;
        }
        
        /* WorkflowPanel customizations */
        WorkflowPanel QFrame {
            background-color: #e8e8e8;
            border-radius: 5px;
            color: #202020;
        }
        
        /* Section dividers */
        QFrame[frameShape="4"] {
            color: #c0c0c0;
        }
        
        /* Checkbox and Radio buttons */
        QCheckBox, QRadioButton {
            color: #202020;
        }
        
        QCheckBox::indicator, QRadioButton::indicator {
            width: 13px;
            height: 13px;
        }
        
        QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
            border: 1px solid #b0b0b0;
            background-color: #ffffff;
        }
        
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            border: 1px solid #b0b0b0;
            background-color: #05B8CC;
        }
        
        /* Toolbar separators */
        QToolBar::separator {
            background-color: #c0c0c0;
            width: 1px;
            height: 20px;
            margin: 0 4px;
        }
        
        /* Explicitly set action text color in toolbars and menus */
        QToolBar QToolButton {
            color: #202020;
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 3px;
            padding: 2px;
        }
        
        QToolBar QToolButton:hover {
            background-color: #e0e0e0;
            border: 1px solid #c0c0c0;
        }
        
        QToolBar QToolButton:pressed {
            background-color: #d0d0d0;
            border: 1px solid #b0b0b0;
        }
        
        QToolBar QToolButton:checked {
            background-color: #d0d0d0;
            border: 1px solid #b0b0b0;
        }
        
        QAction {
            color: #202020;
        }
        
        QToolBar QAction {
            color: #202020;
        }
        
        /* TabWidget & TabBar */
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: #f5f5f5;
        }
        
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #202020;
            padding: 4px 8px;
            border: 1px solid #c0c0c0;
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        
        QTabBar::tab:selected {
            background-color: #f5f5f5;
            border-bottom: 1px solid #f5f5f5;
        }
        
        /* GroupBox */
        QGroupBox {
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            margin-top: 1ex;
            color: #202020;
            background-color: #f5f5f5;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
            color: #202020;
        }
        """
        
        # Use the existing stylesheet but with our improved colors
        original = self._original_light_theme_stylesheet()
        return original.replace("#202020", text_color.name()).replace("#909090", disabled_text.name())
    
    def _get_dark_theme_stylesheet(self):
        """Return the dark theme stylesheet with improved accessibility"""
        # Define key colors for the dark theme
        bg_color = QColor("#2d2d2d")  # Main background 
        text_color = QColor("#e0e0e0") # Main text color
        disabled_text = QColor("#707070") # Disabled text
        
        # Check for sufficient contrast and adjust if needed
        if not AccessibilityUtils.is_contrast_sufficient(text_color, bg_color):
            text_color = AccessibilityUtils.adjust_color_for_contrast(text_color, bg_color)
            
        # Ensure disabled text has sufficient contrast (3:1 minimum)
        disabled_text = AccessibilityUtils.adjust_color_for_contrast(
            disabled_text, bg_color, min_ratio=3.0)
        
        # Update the stylesheet with accessibility-enhanced colors
        stylesheet = """
        /* Dark Theme */
        QMainWindow, QDialog, QWidget {
            background-color: #2d2d2d;
            color: """ + text_color.name() + """;
        }
        
        QToolBar, QStatusBar, QMenuBar {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: none;
        }
        
        QMenuBar::item:selected, QMenu::item:selected {
            background-color: #505050;
        }
        
        QMenu {
            background-color: #3d3d3d;
            color: #e0e0e0;
            border: 1px solid #505050;
        }
        
        QPushButton {
            background-color: #404040;
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 4px 8px;
            color: #e0e0e0;
        }
        
        QPushButton:hover {
            background-color: #505050;
        }
        
        QPushButton:pressed {
            background-color: #606060;
        }
        
        QPushButton:disabled {
            background-color: #353535;
            color: """ + disabled_text.name() + """;
            border: 1px solid #404040;
        }
        
        QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #353535;
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 2px;
            color: #e0e0e0;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QComboBox QAbstractItemView {
            background-color: #353535;
            color: #e0e0e0;
            selection-background-color: #505050;
        }
        
        QLabel {
            color: #e0e0e0;
        }
        
        QLineEdit {
            background-color: #353535;
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 2px;
            color: #e0e0e0;
        }
        
        QSplitter::handle {
            background-color: #505050;
        }
        
        QStatusBar {
            border-top: 1px solid #505050;
        }
        
        QProgressBar {
            border: 1px solid #505050;
            border-radius: 3px;
            background-color: #353535;
            text-align: center;
            color: #e0e0e0;
        }
        
        QProgressBar::chunk {
            background-color: #05B8CC;
            border-radius: 3px;
        }
        
        QToolTip {
            background-color: #353535;
            color: #e0e0e0;
            border: 1px solid #505050;
        }
        
        QScrollBar:vertical, QScrollBar:horizontal {
            background-color: #353535;
            border: none;
        }
        
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background-color: #505050;
            border-radius: 3px;
        }
        
        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
            border: none;
        }
        
        QTabWidget::pane {
            border: 1px solid #505050;
        }
        
        QTabBar::tab {
            background-color: #404040;
            color: #e0e0e0;
            padding: 4px 8px;
            border: 1px solid #505050;
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        
        QTabBar::tab:selected {
            background-color: #505050;
        }
        
        QCheckBox, QRadioButton {
            color: #e0e0e0;
            spacing: 5px;
        }
        
        /* PdfViewer customizations */
        PdfViewer {
            background-color: #353535;
            border: 1px solid #505050;
        }
        
        /* WorkflowPanel customizations */
        WorkflowPanel QFrame {
            background-color: #3d3d3d;
            border-radius: 5px;
        }
        
        /* Section dividers */
        QFrame[frameShape="4"] {
            color: #505050;
        }
        
        /* Toolbar separators */
        QToolBar::separator {
            background-color: #505050;
            width: 1px;
            height: 20px;
            margin: 0 4px;
        }
        """
        
        # Use the existing stylesheet but with our improved colors
        original = self._original_dark_theme_stylesheet()
        return original.replace("#e0e0e0", text_color.name()).replace("#707070", disabled_text.name())

    def _original_light_theme_stylesheet(self):
        """Return the original light theme stylesheet"""
        return """
        /* Light Theme */
        QMainWindow, QDialog, QWidget {
            background-color: #f5f5f5;
            color: #202020;
        }
        
        QToolBar, QStatusBar, QMenuBar {
            background-color: #f0f0f0;
            color: #202020;
            border: none;
        }
        
        QMenuBar::item, QMenu::item {
            color: #202020;
        }
        
        QMenuBar::item:selected, QMenu::item:selected {
            background-color: #d0d0d0;
        }
        
        QMenu {
            background-color: #f8f8f8;
            color: #202020;
            border: 1px solid #c0c0c0;
        }
        
        QPushButton {
            background-color: #e0e0e0;
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            padding: 4px 8px;
            color: #202020;
        }
        
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #909090;
            border: 1px solid #d0d0d0;
        }
        
        QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            padding: 2px;
            color: #202020;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 15px;
            border-left-width: 1px;
            border-left-color: #b0b0b0;
            border-left-style: solid;
        }
        
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #202020;
            selection-background-color: #d0d0d0;
            selection-color: #202020;
        }
        
        QLabel {
            color: #202020;
        }
        
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            padding: 2px;
            color: #202020;
        }
        
        QSplitter::handle {
            background-color: #c0c0c0;
        }
        
        QStatusBar {
            border-top: 1px solid #c0c0c0;
            background-color: #f0f0f0;
            color: #202020;
        }
        
        QProgressBar {
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            background-color: #ffffff;
            text-align: center;
            color: #202020;
        }
        
        QProgressBar::chunk {
            background-color: #05B8CC;
            border-radius: 3px;
        }
        
        QToolTip {
            background-color: #f8f8f8;
            color: #202020;
            border: 1px solid #c0c0c0;
            padding: 2px;
        }
        
        /* Scrollbars */
        QScrollBar:vertical, QScrollBar:horizontal {
            background-color: #f0f0f0;
            border: none;
        }
        
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background-color: #c0c0c0;
            border-radius: 3px;
        }
        
        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
            border: none;
        }
        
        /* PdfViewer customizations */
        PdfViewer {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            color: #202020;
        }
        
        /* WorkflowPanel customizations */
        WorkflowPanel QFrame {
            background-color: #e8e8e8;
            border-radius: 5px;
            color: #202020;
        }
        
        /* Section dividers */
        QFrame[frameShape="4"] {
            color: #c0c0c0;
        }
        
        /* Checkbox and Radio buttons */
        QCheckBox, QRadioButton {
            color: #202020;
        }
        
        QCheckBox::indicator, QRadioButton::indicator {
            width: 13px;
            height: 13px;
        }
        
        QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
            border: 1px solid #b0b0b0;
            background-color: #ffffff;
        }
        
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            border: 1px solid #b0b0b0;
            background-color: #05B8CC;
        }
        
        /* Toolbar separators */
        QToolBar::separator {
            background-color: #c0c0c0;
            width: 1px;
            height: 20px;
            margin: 0 4px;
        }
        
        /* Explicitly set action text color in toolbars and menus */
        QToolBar QToolButton {
            color: #202020;
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 3px;
            padding: 2px;
        }
        
        QToolBar QToolButton:hover {
            background-color: #e0e0e0;
            border: 1px solid #c0c0c0;
        }
        
        QToolBar QToolButton:pressed {
            background-color: #d0d0d0;
            border: 1px solid #b0b0b0;
        }
        
        QToolBar QToolButton:checked {
            background-color: #d0d0d0;
            border: 1px solid #b0b0b0;
        }
        
        QAction {
            color: #202020;
        }
        
        QToolBar QAction {
            color: #202020;
        }
        
        /* TabWidget & TabBar */
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: #f5f5f5;
        }
        
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #202020;
            padding: 4px 8px;
            border: 1px solid #c0c0c0;
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        
        QTabBar::tab:selected {
            background-color: #f5f5f5;
            border-bottom: 1px solid #f5f5f5;
        }
        
        /* GroupBox */
        QGroupBox {
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            margin-top: 1ex;
            color: #202020;
            background-color: #f5f5f5;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
            color: #202020;
        }
        """
    
    def _original_dark_theme_stylesheet(self):
        """Return the original dark theme stylesheet"""
        return """
        /* Dark Theme */
        QMainWindow, QDialog {
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        
        QToolBar, QStatusBar, QMenuBar {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: none;
        }
        
        QMenuBar::item:selected, QMenu::item:selected {
            background-color: #505050;
        }
        
        QMenu {
            background-color: #3d3d3d;
            color: #e0e0e0;
            border: 1px solid #505050;
        }
        
        QPushButton {
            background-color: #404040;
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 4px 8px;
            color: #e0e0e0;
        }
        
        QPushButton:hover {
            background-color: #505050;
        }
        
        QPushButton:pressed {
            background-color: #606060;
        }
        
        QPushButton:disabled {
            background-color: #353535;
            color: #707070;
            border: 1px solid #404040;
        }
        
        QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #353535;
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 2px;
            color: #e0e0e0;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QComboBox QAbstractItemView {
            background-color: #353535;
            color: #e0e0e0;
            selection-background-color: #505050;
        }
        
        QLabel {
            color: #e0e0e0;
        }
        
        QLineEdit {
            background-color: #353535;
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 2px;
            color: #e0e0e0;
        }
        
        QSplitter::handle {
            background-color: #505050;
        }
        
        QStatusBar {
            border-top: 1px solid #505050;
        }
        
        QProgressBar {
            border: 1px solid #505050;
            border-radius: 3px;
            background-color: #353535;
            text-align: center;
            color: #e0e0e0;
        }
        
        QProgressBar::chunk {
            background-color: #05B8CC;
            border-radius: 3px;
        }
        
        QToolTip {
            background-color: #353535;
            color: #e0e0e0;
            border: 1px solid #505050;
        }
        
        QScrollBar:vertical, QScrollBar:horizontal {
            background-color: #353535;
            border: none;
        }
        
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background-color: #505050;
            border-radius: 3px;
        }
        
        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
            border: none;
        }
        
        QTabWidget::pane {
            border: 1px solid #505050;
        }
        
        QTabBar::tab {
            background-color: #404040;
            color: #e0e0e0;
            padding: 4px 8px;
            border: 1px solid #505050;
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        
        QTabBar::tab:selected {
            background-color: #505050;
        }
        
        QCheckBox, QRadioButton {
            color: #e0e0e0;
            spacing: 5px;
        }
        
        /* PdfViewer customizations */
        PdfViewer {
            background-color: #353535;
            border: 1px solid #505050;
        }
        
        /* WorkflowPanel customizations */
        WorkflowPanel QFrame {
            background-color: #3d3d3d;
            border-radius: 5px;
        }
        
        /* Section dividers */
        QFrame[frameShape="4"] {
            color: #505050;
        }
        
        /* Toolbar separators */
        QToolBar::separator {
            background-color: #505050;
            width: 1px;
            height: 20px;
            margin: 0 4px;
        }
        """ 