from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSpinBox, QCheckBox, QGroupBox, QFormLayout, QComboBox,
    QDialogButtonBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QFont, QFontDatabase

class PreferencesDialog(QDialog):
    """Dialog for managing user preferences like font size and UI options"""
    
    # Signal emitted when preferences are changed and applied
    preferences_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(400, 350)
        
        # Load current settings
        self.settings = QSettings("WarehousePathFinder", "PathFinder")
        
        # Create the layout
        self._setup_ui()
        
        # Load current values
        self._load_current_values()
    
    def _setup_ui(self):
        """Set up the UI elements for the preferences dialog"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Tab widget for different preference categories
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_appearance_tab()
        self._create_interface_tab()
        
        # Add button box (OK, Cancel, Apply)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_settings)
        main_layout.addWidget(button_box)
        
    def _create_appearance_tab(self):
        """Create the appearance settings tab"""
        appearance_tab = QWidget()
        layout = QVBoxLayout(appearance_tab)
        
        # Font settings group
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout()
        
        # Font size control
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 18)
        self.font_size_spinbox.setSingleStep(1)
        self.font_size_spinbox.setToolTip("Set the application font size (requires restart)")
        font_layout.addRow("Font Size:", self.font_size_spinbox)
        
        # Font family control
        self.font_family_combo = QComboBox()
        font_families = QFontDatabase().families()
        for family in font_families:
            self.font_family_combo.addItem(family)
        self.font_family_combo.setToolTip("Set the application font family (requires restart)")
        font_layout.addRow("Font Family:", self.font_family_combo)
        
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        # Theme preview (could be added in the future)
        
        # Add spacing and stretch to push items to the top
        layout.addStretch(1)
        
        # Add tab to the tab widget
        self.tab_widget.addTab(appearance_tab, "Appearance")
    
    def _create_interface_tab(self):
        """Create the interface settings tab"""
        interface_tab = QWidget()
        layout = QVBoxLayout(interface_tab)
        
        # Toolbar settings group
        toolbar_group = QGroupBox("Toolbar Settings")
        toolbar_layout = QVBoxLayout()
        
        # Show main toolbar option
        self.show_main_toolbar_checkbox = QCheckBox("Show Main Toolbar")
        self.show_main_toolbar_checkbox.setToolTip("Show or hide the main toolbar")
        toolbar_layout.addWidget(self.show_main_toolbar_checkbox)
        
        # Show interaction toolbar option
        self.show_interaction_toolbar_checkbox = QCheckBox("Show Interaction Toolbar")
        self.show_interaction_toolbar_checkbox.setToolTip("Show or hide the PDF viewer interaction toolbar")
        toolbar_layout.addWidget(self.show_interaction_toolbar_checkbox)
        
        # Checkbox for showing tooltips
        self.show_tooltips_checkbox = QCheckBox("Show Tooltips")
        self.show_tooltips_checkbox.setToolTip("Enable or disable tooltips")
        toolbar_layout.addWidget(self.show_tooltips_checkbox)
        
        toolbar_group.setLayout(toolbar_layout)
        layout.addWidget(toolbar_group)
        
        # Status bar settings group
        statusbar_group = QGroupBox("Status Bar Settings")
        statusbar_layout = QVBoxLayout()
        
        # Show status bar option
        self.show_statusbar_checkbox = QCheckBox("Show Status Bar")
        self.show_statusbar_checkbox.setToolTip("Show or hide the status bar")
        statusbar_layout.addWidget(self.show_statusbar_checkbox)
        
        # Status message timeout - with enhanced controls
        timeout_layout = QHBoxLayout()
        
        # Add explicit buttons for more reliable control
        decrease_button = QPushButton("-")
        decrease_button.setFixedWidth(30)
        decrease_button.setToolTip("Decrease timeout")
        timeout_layout.addWidget(decrease_button)
        
        self.statusbar_timeout_spinbox = QSpinBox()
        self.statusbar_timeout_spinbox.setRange(1, 30)  # Allow from 1 to 30 seconds
        self.statusbar_timeout_spinbox.setSingleStep(1)
        self.statusbar_timeout_spinbox.setSuffix(" seconds")
        self.statusbar_timeout_spinbox.setToolTip("Set the default timeout for status bar messages")
        self.statusbar_timeout_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)  # Hide the potentially problematic buttons
        self.statusbar_timeout_spinbox.setKeyboardTracking(True)  # Allow keyboard input to update immediately
        timeout_layout.addWidget(self.statusbar_timeout_spinbox)
        
        increase_button = QPushButton("+")
        increase_button.setFixedWidth(30)
        increase_button.setToolTip("Increase timeout")
        timeout_layout.addWidget(increase_button)
        
        # Connect the custom buttons
        decrease_button.clicked.connect(self._decrease_timeout)
        increase_button.clicked.connect(self._increase_timeout)
        
        statusbar_layout.addWidget(QLabel("Status Message Timeout:"))
        statusbar_layout.addLayout(timeout_layout)
        
        statusbar_group.setLayout(statusbar_layout)
        layout.addWidget(statusbar_group)
        
        # Add spacing and stretch to push items to the top
        layout.addStretch(1)
        
        # Add tab to the tab widget
        self.tab_widget.addTab(interface_tab, "Interface")
    
    def _load_current_values(self):
        """Load current preference values from settings"""
        # Font settings
        default_font = QFont().family()
        self.font_size_spinbox.setValue(int(self.settings.value("preferences/font_size", 9)))
        
        current_family = self.settings.value("preferences/font_family", default_font)
        idx = self.font_family_combo.findText(current_family)
        if idx >= 0:
            self.font_family_combo.setCurrentIndex(idx)
        
        # Toolbar settings
        self.show_main_toolbar_checkbox.setChecked(self.settings.value("preferences/show_main_toolbar", True, type=bool))
        self.show_interaction_toolbar_checkbox.setChecked(self.settings.value("preferences/show_interaction_toolbar", True, type=bool))
        self.show_tooltips_checkbox.setChecked(self.settings.value("preferences/show_tooltips", True, type=bool))
        
        # Status bar settings
        self.show_statusbar_checkbox.setChecked(self.settings.value("preferences/show_statusbar", True, type=bool))
        self.statusbar_timeout_spinbox.setValue(int(self.settings.value("preferences/statusbar_timeout", 3)))
    
    def _apply_settings(self):
        """Apply and save settings"""
        # Font settings
        self.settings.setValue("preferences/font_size", self.font_size_spinbox.value())
        self.settings.setValue("preferences/font_family", self.font_family_combo.currentText())
        
        # Toolbar settings
        self.settings.setValue("preferences/show_main_toolbar", self.show_main_toolbar_checkbox.isChecked())
        self.settings.setValue("preferences/show_interaction_toolbar", self.show_interaction_toolbar_checkbox.isChecked())
        self.settings.setValue("preferences/show_tooltips", self.show_tooltips_checkbox.isChecked())
        
        # Status bar settings
        self.settings.setValue("preferences/show_statusbar", self.show_statusbar_checkbox.isChecked())
        self.settings.setValue("preferences/statusbar_timeout", self.statusbar_timeout_spinbox.value())
        
        # Sync settings to disk
        self.settings.sync()
        
        # Emit signal to notify that preferences have changed
        self.preferences_changed.emit()
    
    def accept(self):
        """Override accept to apply settings before closing"""
        self._apply_settings()
        super().accept()
    
    def _decrease_timeout(self):
        """Decrease the timeout value by 1 second"""
        current_value = self.statusbar_timeout_spinbox.value()
        if current_value > self.statusbar_timeout_spinbox.minimum():
            self.statusbar_timeout_spinbox.setValue(current_value - 1)
            
    def _increase_timeout(self):
        """Increase the timeout value by 1 second"""
        current_value = self.statusbar_timeout_spinbox.value()
        if current_value < self.statusbar_timeout_spinbox.maximum():
            self.statusbar_timeout_spinbox.setValue(current_value + 1) 