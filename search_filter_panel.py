from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QCheckBox, QGroupBox, QScrollArea,
    QListWidget, QListWidgetItem, QScrollBar
)
from PySide6.QtCore import Signal, Slot, Qt, QSize
from PySide6.QtGui import QIcon

class SearchFilterPanel(QWidget):
    """Panel for searching and filtering warehouse items and paths"""
    
    # Signals for search/filter operations
    search_points = Signal(str, dict)  # search_text, filter_options
    search_obstacles = Signal(str, dict)
    search_paths = Signal(str, str, dict)  # start_point, end_point, filter_options
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create a content widget to hold all our controls
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Title
        title_label = QLabel("Search & Filter")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        content_layout.addWidget(title_label)
        
        # Point search section
        point_group = QGroupBox("Find Points")
        point_layout = QVBoxLayout(point_group)
        
        # Point search input
        point_search_layout = QHBoxLayout()
        self.point_search_input = QLineEdit()
        self.point_search_input.setPlaceholderText("Search points by name...")
        self.point_search_button = QPushButton("Find")
        point_search_layout.addWidget(self.point_search_input)
        point_search_layout.addWidget(self.point_search_button)
        point_layout.addLayout(point_search_layout)
        
        # Point filter options
        point_filter_layout = QHBoxLayout()
        self.pick_aisle_checkbox = QCheckBox("Pick Aisles")
        self.pick_aisle_checkbox.setChecked(True)
        self.staging_location_checkbox = QCheckBox("Staging Locations")
        self.staging_location_checkbox.setChecked(True)
        point_filter_layout.addWidget(self.pick_aisle_checkbox)
        point_filter_layout.addWidget(self.staging_location_checkbox)
        point_layout.addLayout(point_filter_layout)
        
        content_layout.addWidget(point_group)
        
        # Obstacle search section
        obstacle_group = QGroupBox("Find Obstacles")
        obstacle_layout = QVBoxLayout(obstacle_group)
        
        obstacle_search_layout = QHBoxLayout()
        self.obstacle_search_input = QLineEdit()
        self.obstacle_search_input.setPlaceholderText("Search obstacles by properties...")
        self.obstacle_search_button = QPushButton("Find")
        obstacle_search_layout.addWidget(self.obstacle_search_input)
        obstacle_search_layout.addWidget(self.obstacle_search_button)
        obstacle_layout.addLayout(obstacle_search_layout)
        
        # Obstacle filter options
        obstacle_filter_layout = QHBoxLayout()
        self.obstacles_checkbox = QCheckBox("Obstacles")
        self.obstacles_checkbox.setChecked(True)
        self.staging_areas_checkbox = QCheckBox("Staging Areas")
        self.staging_areas_checkbox.setChecked(True)
        obstacle_filter_layout.addWidget(self.obstacles_checkbox)
        obstacle_filter_layout.addWidget(self.staging_areas_checkbox)
        obstacle_layout.addLayout(obstacle_filter_layout)
        
        content_layout.addWidget(obstacle_group)
        
        # Path filter section
        path_group = QGroupBox("Filter Paths")
        path_layout = QVBoxLayout(path_group)
        
        # Start point selection
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start:"))
        self.start_combo = QComboBox()
        start_layout.addWidget(self.start_combo)
        path_layout.addLayout(start_layout)
        
        # End point selection
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End:"))
        self.end_combo = QComboBox()
        end_layout.addWidget(self.end_combo)
        path_layout.addLayout(end_layout)
        
        # Path filter options
        path_options_layout = QHBoxLayout()
        
        self.path_length_combo = QComboBox()
        self.path_length_combo.addItems(["Any Length", "Shortest", "Medium", "Longest"])
        path_options_layout.addWidget(QLabel("Length:"))
        path_options_layout.addWidget(self.path_length_combo)
        
        path_layout.addLayout(path_options_layout)
        
        # Filter button
        self.filter_paths_button = QPushButton("Filter Paths")
        path_layout.addWidget(self.filter_paths_button)
        
        content_layout.addWidget(path_group)
        
        # Results section
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.setMinimumHeight(150)
        results_layout.addWidget(self.results_list)
        
        # Action buttons for results
        results_actions = QHBoxLayout()
        self.highlight_button = QPushButton("Highlight")
        self.highlight_button.setEnabled(False)
        self.goto_button = QPushButton("Go To")
        self.goto_button.setEnabled(False)
        results_actions.addWidget(self.highlight_button)
        results_actions.addWidget(self.goto_button)
        results_layout.addLayout(results_actions)
        
        content_layout.addWidget(results_group)
        
        # Create a scroll area and add the content widget to it
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)
        
        # Make scrollbars more visible
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # Apply stylesheet to make scrollbars wider and more visible
        scroll_area.setStyleSheet("""
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 15px;
                margin: 16px 0 16px 0;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-line:vertical {
                background: #d0d0d0;
                height: 16px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-radius: 3px;
            }
            QScrollBar::sub-line:vertical {
                background: #d0d0d0;
                height: 16px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-radius: 3px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 8px;
                height: 8px;
                background: #606060;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # Add the scroll area to the main layout
        main_layout.addWidget(scroll_area)
    
    def _connect_signals(self):
        # Connect search/filter buttons to slots
        self.point_search_button.clicked.connect(self._search_points)
        self.obstacle_search_button.clicked.connect(self._search_obstacles)
        self.filter_paths_button.clicked.connect(self._filter_paths)
        
        # Connect result selection signals
        self.results_list.itemSelectionChanged.connect(self._handle_result_selection)
        self.highlight_button.clicked.connect(self._highlight_selected_result)
        self.goto_button.clicked.connect(self._goto_selected_result)
    
    def update_point_combos(self, pick_aisles, staging_locations):
        """Update the start and end point combo boxes with current points"""
        # Store current selections
        current_start = self.start_combo.currentText()
        current_end = self.end_combo.currentText()
        
        # Clear and repopulate combos
        self.start_combo.clear()
        self.end_combo.clear()
        
        # Add "Any" option first
        self.start_combo.addItem("Any")
        self.end_combo.addItem("Any")
        
        # Add pick aisles to start combo
        for name in sorted(pick_aisles.keys()):
            self.start_combo.addItem(name)
        
        # Add staging locations to end combo
        for name in sorted(staging_locations.keys()):
            self.end_combo.addItem(name)
        
        # Restore previous selections if valid
        start_idx = self.start_combo.findText(current_start)
        if start_idx >= 0:
            self.start_combo.setCurrentIndex(start_idx)
        
        end_idx = self.end_combo.findText(current_end)
        if end_idx >= 0:
            self.end_combo.setCurrentIndex(end_idx)
    
    def _search_points(self):
        """Search for points based on the current input and filter options"""
        search_text = self.point_search_input.text()
        filter_options = {
            'pick_aisles': self.pick_aisle_checkbox.isChecked(),
            'staging_locations': self.staging_location_checkbox.isChecked()
        }
        self.search_points.emit(search_text, filter_options)
    
    def _search_obstacles(self):
        """Search for obstacles based on the current input and filter options"""
        search_text = self.obstacle_search_input.text()
        filter_options = {
            'obstacles': self.obstacles_checkbox.isChecked(),
            'staging_areas': self.staging_areas_checkbox.isChecked()
        }
        self.search_obstacles.emit(search_text, filter_options)
    
    def _filter_paths(self):
        """Filter paths based on the selected start/end points and options"""
        start_point = self.start_combo.currentText()
        end_point = self.end_combo.currentText()
        
        filter_options = {
            'length_filter': self.path_length_combo.currentText()
        }
        
        self.search_paths.emit(start_point, end_point, filter_options)
    
    def _handle_result_selection(self):
        """Enable/disable action buttons based on selection"""
        selected_items = self.results_list.selectedItems()
        has_selection = len(selected_items) > 0
        
        self.highlight_button.setEnabled(has_selection)
        self.goto_button.setEnabled(has_selection)
    
    def _highlight_selected_result(self):
        """Highlight the selected result in the PDF viewer"""
        # This will be implemented in the main window
        selected_items = self.results_list.selectedItems()
        if selected_items:
            # Store result data in item.data(Qt.UserRole)
            selected_item = selected_items[0]
            result_data = selected_item.data(Qt.UserRole)
            # We'll implement this functionality later
    
    def _goto_selected_result(self):
        """Navigate to the selected result in the PDF viewer"""
        # This will be implemented in the main window
        selected_items = self.results_list.selectedItems()
        if selected_items:
            # Store result data in item.data(Qt.UserRole)
            selected_item = selected_items[0]
            result_data = selected_item.data(Qt.UserRole)
            # We'll implement this functionality later
    
    def display_results(self, results, result_type):
        """Display search/filter results in the results list
        
        Args:
            results: List of result items with 'name' and other attributes
            result_type: String indicating the type of results ('points', 'obstacles', 'paths')
        """
        self.results_list.clear()
        
        for result in results:
            item = QListWidgetItem()
            # Set display text based on result type
            if result_type == 'points':
                item.setText(f"{result['name']} ({result['type']})")
            elif result_type == 'obstacles':
                item.setText(f"Obstacle {result['id']} ({result['type']})")
            elif result_type == 'paths':
                # Format distance to 2 decimal places and include unit
                if 'distance_display' in result:
                    distance_text = result['distance_display']
                else:
                    # Format distance to 2 decimal places and add the unit if available
                    distance = result.get('distance', 0.0)
                    unit = result.get('unit', '')
                    distance_text = f"{distance:.2f} {unit}".strip()
                
                item.setText(f"Path: {result['start']} → {result['end']} ({distance_text})")
            
            # Store the full result data for use in action buttons
            item.setData(Qt.UserRole, result)
            
            self.results_list.addItem(item) 