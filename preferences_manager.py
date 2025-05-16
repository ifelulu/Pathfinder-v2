from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox, QComboBox, QPushButton, QGroupBox, QFormLayout, QSpinBox, QFontComboBox, QToolBar
from PySide6.QtCore import QObject, QSettings, QEvent, Qt, QCoreApplication
from PySide6.QtGui import QFont

class PreferencesManager(QObject):
    """
    Manages application-wide preferences.
    Responsible for loading, applying, and persisting user preferences.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("WarehousePathFinder", "PathFinder")
        
    def apply_all_preferences(self, main_window=None):
        """Apply all preferences to the application"""
        # Get text scaling factor to determine if we need special handling
        text_scale_factor = float(self.settings.value("preferences/text_scale_factor", 1.0))
        
        # Apply font preferences first (this also adjusts layouts)
        self.apply_font_preferences()
        
        # Apply UI component visibility if main window is provided
        if main_window:
            self.apply_ui_visibility_preferences(main_window)
            
            # When scaling back to 100%, force a UI refresh
            if 0.99 <= text_scale_factor <= 1.01 and hasattr(main_window, 'menuBar'):
                try:
                    # Reset the menuBar
                    menu_bar = main_window.menuBar()
                    if menu_bar:
                        menu_bar.update()
                    
                    # Reset main toolbar if it exists
                    if hasattr(main_window, 'main_toolbar') and main_window.main_toolbar:
                        main_window.main_toolbar.update()
                    
                    # Reset interaction toolbar if it exists
                    if hasattr(main_window, 'interaction_toolbar') and main_window.interaction_toolbar:
                        main_window.interaction_toolbar.update()
                        
                    # Force complete UI update
                    main_window.update()
                except Exception:
                    pass  # Ignore any errors
    
    def apply_font_preferences(self):
        """Apply font preferences to the application"""
        app = QApplication.instance()
        if not app:
            return
            
        # Get font size and family from settings
        font_size = int(self.settings.value("preferences/font_size", 9))
        font_family = self.settings.value("preferences/font_family", QFont().family())
        
        # Get text scaling factor for accessibility
        text_scale_factor = float(self.settings.value("preferences/text_scale_factor", 1.0))
        scaled_size = int(font_size * text_scale_factor)
        
        # Create and set the application font
        font = QFont(font_family, scaled_size)
        app.setFont(font)
        
        # Also apply font to any active main window menus
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'menuBar'):
                try:
                    menu_bar = widget.menuBar()
                    if menu_bar:
                        # If scale factor is near 1.0, explicitly use the base font size
                        if 0.99 <= text_scale_factor <= 1.01:
                            menu_font = QFont(font_family, font_size)  # Use unscaled size
                        else:
                            menu_font = QFont(font_family, scaled_size)
                        menu_bar.setFont(menu_font)
                except Exception:
                    pass  # Ignore any errors
        
        # Always adjust layouts for text scaling, regardless of scale factor
        # This ensures we properly revert when scaling down
        self._adjust_layouts_for_text_scaling(text_scale_factor)
    
    def _adjust_layouts_for_text_scaling(self, scale_factor):
        """Adjust application layouts to accommodate larger text"""
        app = QApplication.instance()
        if not app:
            return
            
        # Get the current stylesheet before we modify it
        current_style = app.styleSheet()
        
        # If scale factor is close to 1.0 (default), remove any previous scaling styles
        if 0.99 <= scale_factor <= 1.01:
            # Remove any existing scaling styles by filtering out lines between our markers
            lines = current_style.split('\n')
            filtered_lines = []
            in_scaling_section = False
            
            for line in lines:
                if "/* BEGIN TEXT SCALING STYLES */" in line:
                    in_scaling_section = True
                    continue
                elif "/* END TEXT SCALING STYLES */" in line:
                    in_scaling_section = False
                    continue
                elif not in_scaling_section:
                    filtered_lines.append(line)
            
            # Apply the stylesheet without the scaling section
            app.setStyleSheet('\n'.join(filtered_lines))
            
            # Reset any directly styled toolbars in all main windows
            font_size = int(self.settings.value("preferences/font_size", 9))
            font_family = self.settings.value("preferences/font_family", QFont().family())
            default_font = QFont(font_family, font_size)
            
            for widget in app.topLevelWidgets():
                # Reset toolbar fonts
                if hasattr(widget, 'findChildren'):
                    try:
                        for toolbar in widget.findChildren(QToolBar):
                            toolbar.setFont(default_font)
                    except Exception:
                        pass
            
            return
            
        # Set layout spacing factors based on scaling
        spacing_factor = min(scale_factor, 1.5)  # Cap at 1.5x to prevent extreme spacing
        
        # Apply to style sheet to adjust spacing in layouts
        spacing_stylesheet = f"""
        /* BEGIN TEXT SCALING STYLES */
        /* Adjust widget spacing for text scaling */
        QWidget {{
            spacing: {int(4 * spacing_factor)}px;
        }}
        
        QPushButton {{
            min-height: {int(24 * spacing_factor)}px;
            padding: {int(4 * spacing_factor)}px {int(8 * spacing_factor)}px;
        }}
        
        QComboBox, QSpinBox, QDoubleSpinBox {{
            min-height: {int(22 * spacing_factor)}px;
            padding: {int(2 * spacing_factor)}px;
        }}
        
        QMenuBar {{
            min-height: {int(28 * spacing_factor)}px;
            padding: {int(2 * spacing_factor)}px;
            font-size: {int(9 * scale_factor)}pt;
        }}
        
        QMenuBar::item {{
            padding: {int(4 * spacing_factor)}px {int(8 * spacing_factor)}px;
            font-size: {int(9 * scale_factor)}pt;
        }}
        
        QMenu {{
            font-size: {int(9 * scale_factor)}pt;
            padding: {int(2 * spacing_factor)}px;
        }}
        
        QMenu::item {{
            padding: {int(4 * spacing_factor)}px {int(20 * spacing_factor)}px {int(4 * spacing_factor)}px {int(8 * spacing_factor)}px;
        }}
        
        /* Apply font size to toolbar */
        QToolBar {{
            font-size: {int(9 * scale_factor)}pt;
        }}
        
        /* Fix for zoom controls being squished at high zoom levels */
        QLabel#zoomPercentageLabel {{
            min-width: {int(40 * scale_factor)}px;
            font-size: {int(9 * scale_factor)}pt;
        }}
        
        QPushButton[objectName^="zoom"] {{
            min-width: {int(20 * scale_factor)}px;
            min-height: {int(20 * scale_factor)}px;
        }}
        
        QPushButton[objectName="fitAllButton"] {{
            min-width: {int(30 * scale_factor)}px;
            min-height: {int(20 * scale_factor)}px;
        }}
        
        QPushButton[objectName="fitWidthButton"],
        QPushButton[objectName="fitHeightButton"] {{
            min-width: {int(20 * scale_factor)}px;
            min-height: {int(20 * scale_factor)}px;
        }}
        /* END TEXT SCALING STYLES */
        """
        
        # Remove any existing scaling styles before adding new ones
        lines = current_style.split('\n')
        filtered_lines = []
        in_scaling_section = False
        
        for line in lines:
            if "/* BEGIN TEXT SCALING STYLES */" in line:
                in_scaling_section = True
                continue
            elif "/* END TEXT SCALING STYLES */" in line:
                in_scaling_section = False
                continue
            elif not in_scaling_section:
                filtered_lines.append(line)
        
        # Append the new spacing adjustments to the filtered stylesheet
        final_stylesheet = '\n'.join(filtered_lines) + spacing_stylesheet
        
        # Apply the stylesheet
        app.setStyleSheet(final_stylesheet)
    
    def apply_ui_visibility_preferences(self, main_window):
        """Apply UI visibility preferences to the main window"""
        if not main_window:
            return
            
        # Show/hide main toolbar
        show_main_toolbar = self.settings.value("preferences/show_main_toolbar", True, type=bool)
        if hasattr(main_window, 'main_toolbar'):
            main_window.main_toolbar.setVisible(show_main_toolbar)
            
        # Show/hide interaction toolbar
        show_interaction_toolbar = self.settings.value("preferences/show_interaction_toolbar", True, type=bool)
        if hasattr(main_window, 'interaction_toolbar'):
            main_window.interaction_toolbar.setVisible(show_interaction_toolbar)
            
        # Show/hide status bar
        show_statusbar = self.settings.value("preferences/show_statusbar", True, type=bool)
        main_window.statusBar().setVisible(show_statusbar)
        
        # Apply tooltip visibility
        show_tooltips = self.settings.value("preferences/show_tooltips", True, type=bool)
        app = QApplication.instance()
        if app:
            if show_tooltips:
                app.restoreOverrideCursor()  # Restore normal cursor/tooltip behavior
            else:
                # Filter events to block tooltips
                app.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Event filter to block tooltips if disabled"""
        if event.type() == QEvent.ToolTip:
            show_tooltips = self.settings.value("preferences/show_tooltips", True, type=bool)
            if not show_tooltips:
                return True  # Block tooltip events
        
        return super().eventFilter(obj, event)  # Pass other events through
    
    def get_status_message_timeout(self):
        """Get the preferred status message timeout"""
        # Get the value in seconds and convert to milliseconds
        timeout_seconds = int(self.settings.value("preferences/statusbar_timeout", 3))
        # Ensure the value is at least 1 second
        timeout_seconds = max(1, timeout_seconds)
        # Convert to milliseconds
        return timeout_seconds * 1000
    
    def show_preferences_dialog(self, parent=None):
        """Show the preferences dialog"""
        dialog = PreferencesDialog(parent, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply changes
            self.apply_all_preferences(parent)
            return True
        return False


class PreferencesDialog(QDialog):
    """Dialog for editing application preferences"""
    
    def __init__(self, parent, preferences_manager):
        super().__init__(parent)
        self.preferences_manager = preferences_manager
        self.settings = preferences_manager.settings
        
        self.setWindowTitle("Preferences")
        self.resize(400, 400)
        
        self._create_ui()
        self._load_current_preferences()
        
    def _create_ui(self):
        """Create the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Font group
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout(font_group)
        
        self.font_family_combo = QFontComboBox()
        font_layout.addRow("Font Family:", self.font_family_combo)
        
        # Replace spin box with combo box for common font sizes
        self.font_size_combo = QComboBox()
        font_sizes = ["6", "7", "8", "9", "10", "11", "12", "14", "16", "18", "20"]
        self.font_size_combo.addItems(font_sizes)
        font_layout.addRow("Base Font Size:", self.font_size_combo)
        
        layout.addWidget(font_group)
        
        # Accessibility group
        accessibility_group = QGroupBox("Accessibility")
        accessibility_layout = QVBoxLayout(accessibility_group)
        
        # Text scaling
        text_scale_layout = QHBoxLayout()
        text_scale_layout.addWidget(QLabel("Text Scaling:"))
        
        self.text_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_scale_slider.setRange(100, 200)  # 100% to 200%
        self.text_scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.text_scale_slider.setTickInterval(25)  # Show ticks at 25% intervals
        text_scale_layout.addWidget(self.text_scale_slider)
        
        self.text_scale_label = QLabel("100%")
        text_scale_layout.addWidget(self.text_scale_label)
        
        # Connect slider value changed
        self.text_scale_slider.valueChanged.connect(self._update_text_scale_label)
        
        accessibility_layout.addLayout(text_scale_layout)
        
        # High contrast checkbox
        self.high_contrast_checkbox = QCheckBox("High Contrast Mode")
        accessibility_layout.addWidget(self.high_contrast_checkbox)
        
        layout.addWidget(accessibility_group)
        
        # UI Visibility group
        visibility_group = QGroupBox("UI Visibility")
        visibility_layout = QVBoxLayout(visibility_group)
        
        self.show_main_toolbar_checkbox = QCheckBox("Show Main Toolbar")
        visibility_layout.addWidget(self.show_main_toolbar_checkbox)
        
        self.show_interaction_toolbar_checkbox = QCheckBox("Show Interaction Toolbar")
        visibility_layout.addWidget(self.show_interaction_toolbar_checkbox)
        
        self.show_statusbar_checkbox = QCheckBox("Show Status Bar")
        visibility_layout.addWidget(self.show_statusbar_checkbox)
        
        self.show_tooltips_checkbox = QCheckBox("Show Tooltips")
        visibility_layout.addWidget(self.show_tooltips_checkbox)
        
        layout.addWidget(visibility_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(self.reset_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
    def _load_current_preferences(self):
        """Load current preferences into UI controls"""
        # Font settings
        font_family = self.settings.value("preferences/font_family", QFont().family())
        self.font_family_combo.setCurrentText(font_family)
        
        font_size = int(self.settings.value("preferences/font_size", 9))
        self.font_size_combo.setCurrentText(str(font_size))
        
        # Text scaling
        text_scale_factor = float(self.settings.value("preferences/text_scale_factor", 1.0))
        self.text_scale_slider.setValue(int(text_scale_factor * 100))
        
        # High contrast
        from theme_manager import ThemeManager
        # Try to get ThemeManager instance from parent if available
        theme_manager = None
        if self.parent() and hasattr(self.parent(), 'theme_manager'):
            theme_manager = self.parent().theme_manager
        
        # Otherwise create a new instance
        if not theme_manager:
            theme_manager = ThemeManager()
            
        self.high_contrast_checkbox.setChecked(theme_manager.is_high_contrast_enabled())
        
        # UI visibility
        self.show_main_toolbar_checkbox.setChecked(
            self.settings.value("preferences/show_main_toolbar", True, type=bool))
        
        self.show_interaction_toolbar_checkbox.setChecked(
            self.settings.value("preferences/show_interaction_toolbar", True, type=bool))
        
        self.show_statusbar_checkbox.setChecked(
            self.settings.value("preferences/show_statusbar", True, type=bool))
        
        self.show_tooltips_checkbox.setChecked(
            self.settings.value("preferences/show_tooltips", True, type=bool))
    
    def accept(self):
        """Save preferences when OK is clicked"""
        # Font settings
        self.settings.setValue("preferences/font_family", self.font_family_combo.currentText())
        self.settings.setValue("preferences/font_size", int(self.font_size_combo.currentText()))
        
        # Text scaling
        self.settings.setValue("preferences/text_scale_factor", self.text_scale_slider.value() / 100.0)
        
        # High contrast
        from theme_manager import ThemeManager
        # Try to get ThemeManager instance from parent if available
        theme_manager = None
        if self.parent() and hasattr(self.parent(), 'theme_manager'):
            theme_manager = self.parent().theme_manager
        
        # Otherwise create a new instance
        if not theme_manager:
            theme_manager = ThemeManager()
            
        # Update high contrast setting if it changed
        if theme_manager.is_high_contrast_enabled() != self.high_contrast_checkbox.isChecked():
            theme_manager.toggle_high_contrast()
        
        # UI visibility
        self.settings.setValue("preferences/show_main_toolbar", 
                              self.show_main_toolbar_checkbox.isChecked())
        
        self.settings.setValue("preferences/show_interaction_toolbar", 
                              self.show_interaction_toolbar_checkbox.isChecked())
        
        self.settings.setValue("preferences/show_statusbar", 
                              self.show_statusbar_checkbox.isChecked())
        
        self.settings.setValue("preferences/show_tooltips", 
                              self.show_tooltips_checkbox.isChecked())
        
        super().accept()
    
    def _reset_to_defaults(self):
        """Reset all preferences to their default values"""
        # Font settings
        self.font_family_combo.setCurrentText(QFont().family())
        self.font_size_combo.setCurrentText("9")
        
        # Text scaling
        self.text_scale_slider.setValue(100)  # 100%
        
        # High contrast
        self.high_contrast_checkbox.setChecked(False)
        
        # UI visibility
        self.show_main_toolbar_checkbox.setChecked(True)
        self.show_interaction_toolbar_checkbox.setChecked(True)
        self.show_statusbar_checkbox.setChecked(True)
        self.show_tooltips_checkbox.setChecked(True)
    
    def _update_text_scale_label(self, value):
        """Update the text scale label when the slider changes"""
        self.text_scale_label.setText(f"{value}%") 