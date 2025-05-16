import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QDialogButtonBox, QApplication, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal

class ProjectSettingsDialog(QDialog):
    """Dialog for editing project settings including grid resolution, staging penalty, and cart dimensions."""
    
    def __init__(self, model, parent=None):
        """
        Initialize project settings dialog with values from the warehouse model.
        
        Args:
            model: The WarehouseModel instance to read from and update
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Project Settings")
        self.setMinimumWidth(400)
        
        # Store model reference
        self.model = model
        
        # Get scale unit from model if available
        self.scale_unit = model.scale_unit if hasattr(model, 'scale_unit') and model.scale_unit else "unit"
        
        self._setup_ui()
        self._populate_fields_from_model()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Grid Settings Group
        grid_group = QGroupBox("Pathfinding Grid Settings")
        grid_layout = QFormLayout()
        
        # Grid Resolution Factor
        self.resolution_spinbox = QDoubleSpinBox()
        self.resolution_spinbox.setMinimum(0.5)
        self.resolution_spinbox.setMaximum(50.0)
        self.resolution_spinbox.setSingleStep(0.5)
        self.resolution_spinbox.setDecimals(1)
        self.resolution_spinbox.setToolTip("Controls grid cell size. Lower values create a finer grid (more cells) but slower computation.")
        grid_layout.addRow(f"Grid Resolution Factor ({self.scale_unit}/cell):", self.resolution_spinbox)
        
        # Staging Area Penalty
        self.penalty_spinbox = QDoubleSpinBox()
        self.penalty_spinbox.setMinimum(1.0)
        self.penalty_spinbox.setMaximum(1000.0)
        self.penalty_spinbox.setSingleStep(1.0)
        self.penalty_spinbox.setDecimals(1)
        self.penalty_spinbox.setToolTip("Pathfinding penalty multiplier for staging areas. Higher values discourage paths through staging areas.")
        grid_layout.addRow("Staging Area Penalty:", self.penalty_spinbox)
        
        grid_group.setLayout(grid_layout)
        main_layout.addWidget(grid_group)
        
        # Cart Dimensions Group
        cart_group = QGroupBox("Cart Dimensions")
        cart_layout = QFormLayout()
        
        # Cart Width
        self.cart_width_spinbox = QDoubleSpinBox()
        self.cart_width_spinbox.setMinimum(0.1)
        self.cart_width_spinbox.setMaximum(100.0)
        self.cart_width_spinbox.setSingleStep(0.1)
        self.cart_width_spinbox.setDecimals(3)
        self.cart_width_spinbox.setToolTip("Width of animated carts in project units")
        cart_layout.addRow(f"Cart Width ({self.scale_unit}):", self.cart_width_spinbox)
        
        # Cart Length
        self.cart_length_spinbox = QDoubleSpinBox()
        self.cart_length_spinbox.setMinimum(0.1)
        self.cart_length_spinbox.setMaximum(100.0)
        self.cart_length_spinbox.setSingleStep(0.1)
        self.cart_length_spinbox.setDecimals(3)
        self.cart_length_spinbox.setToolTip("Length of animated carts in project units")
        cart_layout.addRow(f"Cart Length ({self.scale_unit}):", self.cart_length_spinbox)
        
        cart_group.setLayout(cart_layout)
        main_layout.addWidget(cart_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._apply_settings_to_model)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def _populate_fields_from_model(self):
        """Set initial values from the model"""
        # Block signals to avoid unnecessary updates
        self.resolution_spinbox.blockSignals(True)
        self.penalty_spinbox.blockSignals(True)
        self.cart_width_spinbox.blockSignals(True)
        self.cart_length_spinbox.blockSignals(True)
        
        # Set values from model
        self.resolution_spinbox.setValue(self.model.grid_resolution_factor)
        self.penalty_spinbox.setValue(self.model.staging_area_penalty)
        self.cart_width_spinbox.setValue(self.model.animation_cart_width)
        self.cart_length_spinbox.setValue(self.model.animation_cart_length)
        
        # Unblock signals
        self.resolution_spinbox.blockSignals(False)
        self.penalty_spinbox.blockSignals(False)
        self.cart_width_spinbox.blockSignals(False)
        self.cart_length_spinbox.blockSignals(False)
    
    def _apply_settings_to_model(self):
        """Apply new settings to the model and accept dialog"""
        # Get new values
        new_resolution = self.resolution_spinbox.value()
        new_penalty = self.penalty_spinbox.value()
        new_cart_width = self.cart_width_spinbox.value()
        new_cart_length = self.cart_length_spinbox.value()
        
        # Update model with new values
        self.model.set_grid_resolution_factor(new_resolution)
        self.model.set_staging_area_penalty(new_penalty)
        self.model.set_animation_cart_dimensions(new_cart_width, new_cart_length)
        
        # Close dialog
        self.accept()

# Example usage for testing
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # For testing: Create a mock model class
    class MockModel:
        def __init__(self):
            self.grid_resolution_factor = 2.0
            self.staging_area_penalty = 10.0
            self.animation_cart_width = 2.625
            self.animation_cart_length = 5.458
            self.scale_unit = "ft"
            
        def set_grid_resolution_factor(self, value):
            print(f"Setting grid resolution factor to: {value}")
            self.grid_resolution_factor = value
            
        def set_staging_area_penalty(self, value):
            print(f"Setting staging area penalty to: {value}")
            self.staging_area_penalty = value
            
        def set_animation_cart_dimensions(self, width, length):
            print(f"Setting cart dimensions to: {width}x{length}")
            self.animation_cart_width = width
            self.animation_cart_length = length
    
    # Create mock model and dialog
    mock_model = MockModel()
    dialog = ProjectSettingsDialog(mock_model)
    
    # Print initial values
    print(f"Initial model values: Resolution={mock_model.grid_resolution_factor}, "
          f"Penalty={mock_model.staging_area_penalty}, "
          f"Cart: {mock_model.animation_cart_width}x{mock_model.animation_cart_length}")
          
    # Show dialog and handle result
    result = dialog.exec()
    
    # Print final values and result
    print(f"Dialog result: {'Accepted' if result else 'Cancelled'}")
    print(f"Final model values: Resolution={mock_model.grid_resolution_factor}, "
          f"Penalty={mock_model.staging_area_penalty}, "
          f"Cart: {mock_model.animation_cart_width}x{mock_model.animation_cart_length}") 