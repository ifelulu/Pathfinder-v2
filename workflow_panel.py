from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, 
    QHBoxLayout, QFrame, QSizePolicy, QComboBox, QStyle,
    QListView, QAbstractItemView
)
from PySide6.QtCore import Qt, QModelIndex, Signal
from PySide6.QtGui import QColor, QDrag, QStandardItemModel, QStandardItem

# Try to import ThemeManager for theme detection
try:
    from theme_manager import ThemeManager
    HAS_THEME_MANAGER = True
except ImportError:
    HAS_THEME_MANAGER = False


class DraggableListView(QListView):
    """A custom list view that supports drag and drop for reordering items."""
    
    items_reordered = Signal(list)  # Signal emitted when items are reordered
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
    def dropEvent(self, event):
        """Handle drop events to reorder items."""
        # Call the parent implementation to handle the actual drop
        super().dropEvent(event)
        
        # After the drop, emit a signal with the new order
        model = self.model()
        items = []
        for i in range(model.rowCount()):
            items.append(model.index(i, 0).data())
        
        self.items_reordered.emit(items)


class DraggableComboBox(QComboBox):
    """A combo box with a draggable popup view for reordering items."""
    
    items_reordered = Signal(list)  # Signal emitted when items are reordered
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create a custom view for the combo box
        self.view = DraggableListView()
        self.view.items_reordered.connect(self.items_reordered)
        self.setView(self.view)
        
        # Create a custom model to manage items
        self.setModel(QStandardItemModel())


class WorkflowPanel(QWidget):
    """
    A panel that guides users through the workflow process of:
    1. Loading a PDF
    2. Setting the scale
    3. Precomputing paths
    4. Calculating paths
    """
    
    # Add signals for when items are reordered
    pick_aisles_reordered = Signal(list)
    staging_locations_reordered = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI elements for the workflow panel"""
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)
        
        # Title label
        title_label = QLabel("Workflow Steps")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(title_label)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(separator)
        
        # 1. Load PDF section
        pdf_layout = QVBoxLayout()
        
        # Load PDF button
        self.load_pdf_button = QPushButton("Load PDF")
        self.load_pdf_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.load_pdf_button.setMinimumHeight(30)
        self.load_pdf_button.setToolTip("Load a PDF floor plan of the warehouse")
        pdf_layout.addWidget(self.load_pdf_button)
        
        # PDF status label
        self.pdf_status_label = QLabel("PDF: Not loaded")
        pdf_layout.addWidget(self.pdf_status_label)
        
        # Add to main layout with spacing
        self.layout.addLayout(pdf_layout)
        self.layout.addSpacing(10)
        
        # 2. Set Scale section
        scale_layout = QVBoxLayout()
        
        # Set Scale button
        self.set_scale_button = QPushButton("Set Scale")
        self.set_scale_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.set_scale_button.setMinimumHeight(30)
        self.set_scale_button.setEnabled(False)  # Disabled until PDF is loaded
        self.set_scale_button.setToolTip("Set the scale to convert pixels to real-world measurements")
        scale_layout.addWidget(self.set_scale_button)
        
        # Scale status label
        self.scale_status_label = QLabel("Scale: Not set")
        scale_layout.addWidget(self.scale_status_label)
        
        # Add to main layout with spacing
        self.layout.addLayout(scale_layout)
        self.layout.addSpacing(10)
        
        # 3. Precompute Paths section
        precompute_layout = QVBoxLayout()
        
        # Precompute Paths button
        self.precompute_paths_button = QPushButton("Precompute Paths")
        self.precompute_paths_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.precompute_paths_button.setMinimumHeight(30)
        self.precompute_paths_button.setEnabled(False)  # Disabled until scale is set
        self.precompute_paths_button.setToolTip("Precompute all possible paths between pick aisles and staging locations")
        precompute_layout.addWidget(self.precompute_paths_button)
        
        # Precomputation status label
        self.precomputation_status_label = QLabel("Precomputation: Not ready")
        precompute_layout.addWidget(self.precomputation_status_label)
        
        # Grid dimensions label
        self.grid_dimensions_label = QLabel("Grid: Not available")
        precompute_layout.addWidget(self.grid_dimensions_label)
        
        # Add to main layout
        self.layout.addLayout(precompute_layout)
        self.layout.addSpacing(10)
        
        # 4. Calculate Path section
        calculate_layout = QVBoxLayout()
        
        # Start point selection
        start_layout = QHBoxLayout()
        start_label = QLabel("Pick Aisle (Start):")
        start_label.setToolTip("Select the starting pick aisle location")
        start_layout.addWidget(start_label)
        self.start_combo = DraggableComboBox()
        self.start_combo.setToolTip("Select the starting pick aisle location (drag and drop to reorder)")
        self.start_combo.items_reordered.connect(self.pick_aisles_reordered)
        start_layout.addWidget(self.start_combo)
        calculate_layout.addLayout(start_layout)
        
        # End point selection
        end_layout = QHBoxLayout()
        end_label = QLabel("Staging Location (End):")
        end_label.setToolTip("Select the destination staging location")
        end_layout.addWidget(end_label)
        self.end_combo = DraggableComboBox()
        self.end_combo.setToolTip("Select the destination staging location (drag and drop to reorder)")
        self.end_combo.items_reordered.connect(self.staging_locations_reordered)
        end_layout.addWidget(self.end_combo)
        calculate_layout.addLayout(end_layout)
        
        # Calculate Path button
        self.calculate_button = QPushButton("Calculate Path")
        self.calculate_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_CommandLink))
        self.calculate_button.setMinimumHeight(30)
        self.calculate_button.setEnabled(False)  # Disabled until precomputation is done
        self.calculate_button.setToolTip("Calculate the optimal path between selected points")
        calculate_layout.addWidget(self.calculate_button)
        
        # Add to main layout
        self.layout.addLayout(calculate_layout)
        
        # Add stretch to push everything to the top
        self.layout.addStretch(1)
        
        # Set size policy for the workflow panel
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
    def update_pdf_status(self, text):
        """Update the PDF status label"""
        self.pdf_status_label.setText(f"PDF: {text}")
        
    def update_scale_status(self, text):
        """Update the Scale status label"""
        self.scale_status_label.setText(f"Scale: {text}")
        
    def update_precomputation_status(self, text):
        """Update the Precomputation status label"""
        self.precomputation_status_label.setText(f"Precomputation: {text}") 
        
    def update_grid_dimensions(self, width, height):
        """Update the Grid dimensions label"""
        self.grid_dimensions_label.setText(f"Grid: {width}x{height} cells")
        
    def refresh_styles(self):
        """Refresh the panel's styles to match the current theme"""
        # Find the theme manager
        is_dark_mode = False
        if HAS_THEME_MANAGER:
            import PySide6.QtWidgets
            app = PySide6.QtWidgets.QApplication.instance()
            main_windows = [w for w in app.topLevelWidgets() if w.__class__.__name__ == 'MainWindow']
            if main_windows and hasattr(main_windows[0], 'theme_manager'):
                is_dark_mode = main_windows[0].theme_manager.is_dark_theme()
        
        # Set styles based on theme
        title_color = "#e0e0e0" if is_dark_mode else "#202020"
        title_label = self.findChild(QLabel, "", Qt.FindChildrenRecursively)
        if title_label:
            title_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {title_color};")
            
        # Update separator color
        separator_color = "#505050" if is_dark_mode else "#c0c0c0"
        separator = self.findChild(QFrame, "", Qt.FindChildrenRecursively)
        if separator and separator.frameShape() == QFrame.HLine:
            separator.setStyleSheet(f"background-color: {separator_color};")
            
        # The buttons and other widgets will be styled by the global stylesheet 