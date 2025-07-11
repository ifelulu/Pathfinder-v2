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
            padding: 2px 4px; /* Adjusted padding for spinbox text */
            color: #202020;
            min-height: 20px; /* Ensure a decent height */
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 18px; /* Slightly wider drop-down */
            border-left-width: 1px;
            border-left-color: #b0b0b0;
            border-left-style: solid;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }
        QComboBox::down-arrow {
            /* image: url(:/qt-project.org/styles/commonstyle/images/down_arrow.png); */
            /* Using a simple border to create an arrow for now if no image */
            border: solid #555555;
            border-width: 0 2px 2px 0;            
            padding: 2px;
            margin: 0 0 2px 2px; /* Adjust position */
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #202020;
            selection-background-color: #d0d0d0;
            selection-color: #202020;
            border: 1px solid #b0b0b0;
        }

        /* SpinBox Up/Down Buttons */
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 16px;
            height: 10px; /* Half of min-height roughly */
            background-color: #e0e0e0;
            border-left: 1px solid #b0b0b0;
            border-bottom: 1px solid #b0b0b0; /* Add separator */
            border-top-right-radius: 3px;
        }
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
            background-color: #d0d0d0;
        }
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 16px;
            height: 10px; /* Half of min-height roughly */
            background-color: #e0e0e0;
            border-left: 1px solid #b0b0b0;
            border-bottom-right-radius: 3px;
        }
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
            background-color: #d0d0d0;
        }

        /* SpinBox Up/Down Arrows */
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            /* Using borders to create a triangle */
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #606060; /* Arrow color */
            margin: 0 auto; /* Center the arrow */
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #606060; /* Arrow color */
            margin: 0 auto;
        }
        QSpinBox:disabled, QDoubleSpinBox:disabled {
            background-color: #f0f0f0;
            color: #909090;
        }

        /* Sliders */
        QSlider::groove:horizontal {
            border: 1px solid #b0b0b0;
            background: #f0f0f0; /* Groove color */
            height: 8px; /* Groove thickness */
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #c0c0c0; /* Handle color */
            border: 1px solid #a0a0a0;
            width: 16px; /* Handle width */
            margin: -4px 0; /* Vertical alignment */
            border-radius: 8px; /* Circular handle */
        }
        QSlider::handle:horizontal:hover {
            background: #b0b0b0;
        }
        QSlider::sub-page:horizontal {
            background: #05B8CC; /* Color of the groove before the handle */
            border: 1px solid #b0b0b0;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::add-page:horizontal {
            background: #f0f0f0; /* Color of the groove after the handle */
            border: 1px solid #b0b0b0;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::tick:horizontal {
            height: 10px;
            width: 1px;
            background: #a0a0a0; /* Tick color */
            margin-top: -1px;
        }

        QSlider::groove:vertical {
            border: 1px solid #b0b0b0;
            background: #f0f0f0;
            width: 8px;
            border-radius: 4px;
        }
        QSlider::handle:vertical {
            background: #c0c0c0;
            border: 1px solid #a0a0a0;
            height: 16px;
            margin: 0 -4px;
            border-radius: 8px;
        }
        QSlider::handle:vertical:hover {
            background: #b0b0b0;
        }
        QSlider::sub-page:vertical {
            background: #05B8CC;
            border: 1px solid #b0b0b0;
            width: 8px;
            border-radius: 4px;
        }
        QSlider::add-page:vertical {
            background: #f0f0f0;
            border: 1px solid #b0b0b0;
            width: 8px;
            border-radius: 4px;
        }
        QSlider::tick:vertical {
            width: 10px;
            height: 1px;
            background: #a0a0a0;
            margin-left: -1px;
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
        QScrollBar:vertical {
            background-color: #f0f0f0; /* Track color */
            width: 15px;               /* Width of the vertical scroll bar */
            margin: 16px 0 16px 0;     /* Top/bottom margin for arrows */
            border: 1px solid #dcdcdc; /* Optional: subtle border for the track */
        }
        QScrollBar::handle:vertical {
            background-color: #c0c0c0; /* Handle color */
            min-height: 25px;          /* Minimum handle size */
            border-radius: 7px;
            border: 1px solid #b0b0b0; /* Optional: subtle border for handle */
        }
        QScrollBar::handle:vertical:hover {
            background-color: #a8a8a8;
        }
        QScrollBar::add-line:vertical { /* Area for bottom arrow button */
            border: 1px solid #c0c0c0;
            background-color: #e0e0e0; /* Button background */
            height: 15px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }
        QScrollBar::sub-line:vertical { /* Area for top arrow button */
            border: 1px solid #c0c0c0;
            background-color: #e0e0e0; /* Button background */
            height: 15px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
            background-color: #707070; /* Color of the arrow itself */
            width: 7px;               /* Size of the arrow */
            height: 7px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { /* Empty space */
            background: none;
        }

        /* Horizontal Scrollbar */
        QScrollBar:horizontal {
            background-color: #f0f0f0;
            height: 15px;
            margin: 0 16px 0 16px;   /* Left/right margin for arrows */
            border: 1px solid #dcdcdc;
        }
        QScrollBar::handle:horizontal {
            background-color: #c0c0c0;
            min-width: 25px;
            border-radius: 7px;
            border: 1px solid #b0b0b0;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #a8a8a8;
        }
        QScrollBar::add-line:horizontal { /* Area for right arrow button */
            border: 1px solid #c0c0c0;
            background-color: #e0e0e0;
            width: 15px;
            subcontrol-position: right;
            subcontrol-origin: margin;
        }
        QScrollBar::sub-line:horizontal { /* Area for left arrow button */
            border: 1px solid #c0c0c0;
            background-color: #e0e0e0;
            width: 15px;
            subcontrol-position: left;
            subcontrol-origin: margin;
        }
        QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
            background-color: #707070;
            width: 7px;
            height: 7px;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
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
            padding: 2px 4px;
            color: #e0e0e0;
            min-height: 20px;
        }
        QComboBox::drop-down {
            border: none; /* Often looks better in dark themes */
            width: 18px;
        }
        QComboBox::down-arrow {
            border: solid #b0b0b0; /* Lighter arrow for dark theme */
            border-width: 0 2px 2px 0;            
            padding: 2px;
            margin: 0 0 2px 2px;
        }
        QComboBox QAbstractItemView {
            background-color: #353535;
            color: #e0e0e0;
            selection-background-color: #505050;
            border: 1px solid #505050;
        }

        /* SpinBox Up/Down Buttons */
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 16px;
            height: 10px;
            background-color: #404040;
            border-left: 1px solid #505050;
            border-bottom: 1px solid #505050; /* Separator */
            border-top-right-radius: 3px;
        }
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
            background-color: #505050;
        }
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 16px;
            height: 10px;
            background-color: #404040;
            border-left: 1px solid #505050;
            border-bottom-right-radius: 3px;
        }
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
            background-color: #505050;
        }

        /* SpinBox Up/Down Arrows */
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #b0b0b0; /* Light arrow */
            margin: 0 auto;
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #b0b0b0; /* Light arrow */
            margin: 0 auto;
        }
        QSpinBox:disabled, QDoubleSpinBox:disabled {
            background-color: #353535; /* Use a slightly different shade or same as enabled */
            color: #707070; /* Ensure disabled text color is properly set */
            border: 1px solid #404040;
        }

        /* Sliders */
        QSlider::groove:horizontal {
            border: 1px solid #505050;
            background: #2d2d2d; /* Darker groove */
            height: 8px;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #5a5a5a; /* Handle color */
            border: 1px solid #6a6a6a;
            width: 16px;
            margin: -4px 0;
            border-radius: 8px;
        }
        QSlider::handle:horizontal:hover {
            background: #686868;
        }
        QSlider::sub-page:horizontal {
            background: #05B8CC; /* Active part of the slider */
            border: 1px solid #505050;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::add-page:horizontal {
            background: #2d2d2d; /* Inactive part */
            border: 1px solid #505050;
            height: 8px;
            border-radius: 4px;
        }
        QSlider::tick:horizontal {
            height: 10px;
            width: 1px;
            background: #6a6a6a; /* Tick color */
            margin-top: -1px;
        }

        QSlider::groove:vertical {
            border: 1px solid #505050;
            background: #2d2d2d;
            width: 8px;
            border-radius: 4px;
        }
        QSlider::handle:vertical {
            background: #5a5a5a;
            border: 1px solid #6a6a6a;
            height: 16px;
            margin: 0 -4px;
            border-radius: 8px;
        }
        QSlider::handle:vertical:hover {
            background: #686868;
        }
        QSlider::sub-page:vertical {
            background: #05B8CC;
            border: 1px solid #505050;
            width: 8px;
            border-radius: 4px;
        }
        QSlider::add-page:vertical {
            background: #2d2d2d;
            border: 1px solid #505050;
            width: 8px;
            border-radius: 4px;
        }
        QSlider::tick:vertical {
            width: 10px;
            height: 1px;
            background: #6a6a6a;
            margin-left: -1px;
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
        
        /* Scrollbars */
        QScrollBar:vertical {
            background-color: #2d2d2d; /* Dark track color */
            width: 15px;
            margin: 16px 0 16px 0;
            border: 1px solid #3c3c3c;
        }
        QScrollBar::handle:vertical {
            background-color: #5a5a5a; /* Dark handle color, ensure contrast */
            min-height: 25px;
            border-radius: 7px;
            border: 1px solid #6a6a6a;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #686868;
        }
        QScrollBar::add-line:vertical {
            border: 1px solid #454545;
            background-color: #383838; /* Dark button background */
            height: 15px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }
        QScrollBar::sub-line:vertical {
            border: 1px solid #454545;
            background-color: #383838;
            height: 15px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
            background-color: #b0b0b0; /* Light arrow color for dark theme */
            width: 7px;
            height: 7px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }

        /* Horizontal Scrollbar */
        QScrollBar:horizontal {
            background-color: #2d2d2d;
            height: 15px;
            margin: 0 16px 0 16px;
            border: 1px solid #3c3c3c;
        }
        QScrollBar::handle:horizontal {
            background-color: #5a5a5a;
            min-width: 25px;
            border-radius: 7px;
            border: 1px solid #6a6a6a;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #686868;
        }
        QScrollBar::add-line:horizontal {
            border: 1px solid #454545;
            background-color: #383838;
            width: 15px;
            subcontrol-position: right;
            subcontrol-origin: margin;
        }
        QScrollBar::sub-line:horizontal {
            border: 1px solid #454545;
            background-color: #383838;
            width: 15px;
            subcontrol-position: left;
            subcontrol-origin: margin;
        }
        QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
            background-color: #b0b0b0;
            width: 7px;
            height: 7px;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
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