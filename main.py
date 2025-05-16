# --- START OF FILE Warehouse-Path-Finder-main/main.py ---

import sys
import json
import os
import math
import time
import re
import multiprocessing
from typing import Optional, Dict, List, Tuple, Any, Union
from datetime import datetime, timedelta
import webbrowser

# Constants
MAX_RECENT_FILES = 10

import fitz  # PyMuPDF for PDF processing
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QToolBar,
    QMessageBox, QFileDialog, QToolButton, QDialog, QMenu, QStyle, QSplitter,
    QGraphicsItem, QInputDialog, QLineEdit, QGridLayout, QFormLayout,
    QRadioButton, QButtonGroup, QStatusBar, QUndoView, QGraphicsScene,
    QDockWidget
)
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QObject, Signal, Slot, QTimer, QFileInfo, QUrl, QSettings,
    QSize, QTimer, QSettings, Slot, Signal, QModelIndex, QPoint, QPointF,
    QRectF, QDateTime, QFileInfo, QDate, QPointF, QMimeData, QByteArray, QSizeF, QProcess
)
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem, QColor, QPixmap, QIcon, QCursor,
    QAction, QActionGroup, QPolygonF, QUndoStack, QUndoCommand,
    QKeySequence, QShortcut, QPainter, QImage, QPainter, QPixmap, QColor, QImage, QFont, QPen, QBrush, QPolygonF, 
    QTransform, QIcon, QCursor, QDesktopServices
)

from pdf_viewer import PdfViewer
from pdf_viewer_interaction_toolbar import PdfViewerInteractionToolbar
from model import WarehouseModel
from enums import InteractionMode, PointType, AnimationMode
from services import (ProjectService, PathfindingService, AnalysisService, AnimationService, SearchService)
from line_definition_dialog import LineDefinitionDialog
from animation_control_dialog import AnimationControlDialog, _get_cluster_from_name
from picklist_column_dialog import PicklistColumnDialog
from analysis_results_dialog import AnalysisResultsDialog
from animation_picklist_dialog import AnimationPicklistDialog
from project_settings_dialog import ProjectSettingsDialog
from about_dialog import AboutDialog
from workflow_panel import WorkflowPanel
from theme_manager import ThemeManager
from preferences_dialog import PreferencesDialog
from preferences_manager import PreferencesManager
from search_filter_panel import SearchFilterPanel

from status_bar_progress import StatusBarProgress

# Set this to True if you need detailed per-frame logs again temporarily
DEBUG_ANIMATION_VERBOSE = False

# --- Helper function for natural sorting ---
def natural_sort_key(s: str) -> list:
    """
    Create a sort key for natural string sorting (e.g., A1, A2, A10).
    Ensures proper sorting with letter part first, then numeric part in numerical order (not lexicographical).
    Examples: A1, A2, A3, ... A9, A10, A11, B1, B2, etc.
    """
    if not s:  # Handle empty strings
        return []
    
    import re
    
    # Split the string into a list of strings and numbers
    # This regex matches letters/non-digits and digits separately
    parts = re.findall(r'([A-Za-z]+|\d+)', s)
    
    # Convert to appropriate types for sorting (strings for letters, integers for numbers)
    result = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))  # Convert digits to integers for proper numerical sorting
        else:
            result.append(part.lower())  # Convert letters to lowercase for case-insensitive sorting
            
    return result

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Warehouse Path Finder")
        self.setGeometry(100, 100, 1200, 800)

        # --- Initialize Model and Services ---
        self.model = WarehouseModel(self)
        self.project_service = ProjectService(self)
        self.pathfinding_service = PathfindingService(self)
        self.analysis_service = AnalysisService(self)
        self.animation_service = AnimationService(self)
        self.search_service = SearchService(self)
        
        # --- Recent Files ---
        self.recent_files_actions = []
        self.settings = QSettings("WarehousePathFinder", "PathFinder")
        
        # --- Undo Stack ---
        self.undo_stack = QUndoStack(self)
        
        # --- Theme Manager ---
        self.theme_manager = ThemeManager()
        
        # --- Preferences Manager ---
        self.preferences_manager = PreferencesManager(self)
        
        # --- Setup UI Components ---
        self._create_ui()
        self._create_menu_bar()
        self._create_tool_bar()
        self._connect_signals()
        self._update_recent_files_menu()
        
        # --- Initialize UI state ---
        self._update_all_ui_states()
        
        # Apply the saved theme
        self.theme_manager.apply_theme()
        
        # Apply saved preferences
        self.preferences_manager.apply_all_preferences(self)
        
        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
        # Show the window
        self.show()

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create PDF viewer
        self.pdf_viewer = PdfViewer()
        
        # Create workflow panel
        self.workflow_panel = WorkflowPanel()
        
        # Create zoom control panel
        zoom_control_panel = QWidget()
        zoom_control_layout = QHBoxLayout(zoom_control_panel)
        zoom_control_layout.setContentsMargins(5, 2, 5, 2)
        zoom_control_layout.setSpacing(2)  # Reduce spacing between elements
        
        # Zoom label showing current percentage
        self.zoom_percentage_label = QLabel("100%")
        self.zoom_percentage_label.setToolTip("Current zoom level")
        self.zoom_percentage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_percentage_label.setFixedWidth(40)  # Reduce width
        self.zoom_percentage_label.setObjectName("zoomPercentageLabel")
        
        # Zoom buttons
        zoom_in_button = QPushButton("+")
        zoom_in_button.setFixedSize(20, 20)  # Make button smaller and square
        zoom_in_button.setToolTip("Zoom in")
        zoom_in_button.clicked.connect(self.pdf_viewer.zoom_in)
        zoom_in_button.setObjectName("zoomInButton")
        
        zoom_out_button = QPushButton("-")
        zoom_out_button.setFixedSize(20, 20)  # Make button smaller and square
        zoom_out_button.setToolTip("Zoom out")
        zoom_out_button.clicked.connect(self.pdf_viewer.zoom_out)
        zoom_out_button.setObjectName("zoomOutButton")
        
        # Fit buttons
        fit_all_button = QPushButton("Fit")
        fit_all_button.setToolTip("Fit to view")
        fit_all_button.setFixedSize(30, 20)  # Make button smaller
        fit_all_button.clicked.connect(self.pdf_viewer.zoom_fit)
        fit_all_button.setObjectName("fitAllButton")
        
        fit_width_button = QPushButton("↔")  # Horizontal double arrow
        fit_width_button.setToolTip("Fit to width")
        fit_width_button.setFixedSize(20, 20)  # Make button smaller
        fit_width_button.clicked.connect(self.pdf_viewer.zoom_fit_width)
        fit_width_button.setObjectName("fitWidthButton")
        
        fit_height_button = QPushButton("↕")  # Vertical double arrow
        fit_height_button.setToolTip("Fit to height")
        fit_height_button.setFixedSize(20, 20)  # Make button smaller
        fit_height_button.clicked.connect(self.pdf_viewer.zoom_fit_height)
        fit_height_button.setObjectName("fitHeightButton")
        
        # Add widgets to zoom control layout
        zoom_control_layout.addWidget(zoom_out_button)
        zoom_control_layout.addWidget(self.zoom_percentage_label)
        zoom_control_layout.addWidget(zoom_in_button)
        zoom_control_layout.addStretch(1)
        zoom_control_layout.addWidget(fit_all_button)
        zoom_control_layout.addWidget(fit_width_button)
        zoom_control_layout.addWidget(fit_height_button)
        
        # Use combos and button from workflow panel
        self.start_combo = self.workflow_panel.start_combo
        self.end_combo = self.workflow_panel.end_combo
        self.calculate_button = self.workflow_panel.calculate_button
        
        # Keep these UI elements for now
        self.resolution_spinbox = QDoubleSpinBox()
        self.penalty_spinbox = QDoubleSpinBox()
        self.granularity_label = QLabel("Path Detail Granularity: N/A")

        # Animation related
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(50) # (50ms = 20 FPS)
        self.animation_control_dialog: Optional[AnimationControlDialog] = None
        self.current_animation_time_s: float = 0.0
        self.animation_speed_multiplier: float = 1.0
        self._animation_data_prepared: List[Dict[str, Any]] = []
        self._animation_earliest_dt_prepared: Optional[datetime] = None # Correct type hint
        self._animation_mode_current = AnimationMode.CARTS
        self._path_visibility_duration_s_current = 300
        self._keep_paths_visible_current = False
        self._animation_active_start_clusters: set[str] = set()
        self._animation_active_end_clusters: set[str] = set()
        self._animation_selected_date_filter: str = "All Dates" # Default
        self._filtered_min_time_s: Optional[float] = None
        self._filtered_max_time_s: Optional[float] = None
        self._filtered_earliest_dt: Optional[datetime] = None # Correct type hint

        # Cache for last analysis
        self._last_analysis_detailed_results: Optional[List[Dict[str, Any]]] = None
        self._last_analysis_warnings: Optional[List[str]] = None
        self._last_analysis_unit: Optional[str] = None
        self._last_analysis_input_filename: Optional[str] = None
        
        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.workflow_panel)
        splitter.addWidget(self.pdf_viewer)
        splitter.setSizes([200, 1000])  # Default sizes
        
        # Add the splitter to the main layout
        main_layout.addWidget(splitter)
        
        # Create status bar with progress indicator
        self.status_progress = StatusBarProgress(self)
        self.statusBar().addPermanentWidget(self.status_progress, 1)  # Add with stretch 1
        
        # Move zoom control panel to the status bar instead of adding it to main layout
        self.statusBar().addPermanentWidget(zoom_control_panel, 0)  # Add with no stretch
        
        self.status_progress.show_message("Ready. Open a PDF or Project to start.")
        print("[MainWindow] UI creation complete.")
        
        # Set up proper tab order for the main UI components
        self.setTabOrder(self.workflow_panel.load_pdf_button, self.workflow_panel.set_scale_button)
        self.setTabOrder(self.workflow_panel.set_scale_button, self.workflow_panel.precompute_paths_button)
        self.setTabOrder(self.workflow_panel.precompute_paths_button, self.workflow_panel.start_combo)
        self.setTabOrder(self.workflow_panel.start_combo, self.workflow_panel.end_combo)
        self.setTabOrder(self.workflow_panel.end_combo, self.workflow_panel.calculate_button)
        
        # Make PDF viewer focusable (it already has StrongFocus policy)
        
        # Ensure all PDF viewer interaction buttons are also properly keyboard navigable
        # These will be set in the _create_tool_bar method

        # Create search filter panel as a dock widget
        self.search_filter_panel = SearchFilterPanel()
        self.search_dock = QDockWidget("Search & Filter", self)
        self.search_dock.setWidget(self.search_filter_panel)
        self.search_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.search_dock)
        
        # Make the search dock closable but not initially visible
        self.search_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | 
                                    QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                    QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.search_dock.hide()  # Start with search panel hidden
        
    def _create_menu_bar(self):
        # Create menu bar with appropriate icons for actions
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        
        # File menu actions with icons
        self.open_pdf_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "&Open PDF...", self)
        self.open_pdf_action.setShortcut("Ctrl+O")
        self.open_pdf_action.setToolTip("Open a PDF floor plan of the warehouse (Ctrl+O)")
        file_menu.addAction(self.open_pdf_action)
        
        self.open_project_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "Open P&roject...", self)
        self.open_project_action.setShortcut("Ctrl+R")
        self.open_project_action.setToolTip("Open a saved warehouse project file (Ctrl+R)")
        file_menu.addAction(self.open_project_action)
        
        # Recent Files submenu
        self.recent_files_menu = QMenu("Recent &Files", self)
        self.recent_files_menu.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        file_menu.addMenu(self.recent_files_menu)
        
        # Create the recent file actions
        for i in range(MAX_RECENT_FILES):
            action = QAction(self)
            action.setVisible(False)
            self.recent_files_actions.append(action)
            self.recent_files_menu.addAction(action)
            action.triggered.connect(self._open_recent_file)
        
        # Add separator and clear action to recent files menu
        self.recent_files_menu.addSeparator()
        self.clear_recent_action = QAction("Clear Recent Files", self)
        self.clear_recent_action.triggered.connect(self._clear_recent_files)
        self.recent_files_menu.addAction(self.clear_recent_action)
        
        # Add separator after the recent files
        file_menu.addSeparator()
        
        # Save project actions
        self.save_project_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "&Save Project", self)
        self.save_project_action.setShortcut("Ctrl+S")
        self.save_project_action.setToolTip("Save the current warehouse project (Ctrl+S)")
        file_menu.addAction(self.save_project_action)
        
        self.save_project_as_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save Project &As...", self)
        self.save_project_as_action.setShortcut("Ctrl+Shift+S")
        self.save_project_as_action.setToolTip("Save the current warehouse project to a new file (Ctrl+Shift+S)")
        file_menu.addAction(self.save_project_as_action)
        
        # Exit action
        file_menu.addSeparator()
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Alt+F4")
        file_menu.addAction(self.exit_action)
        
        # Edit menu with Undo/Redo
        edit_menu = menu_bar.addMenu("&Edit")
        # These actions are created in _create_tool_bar, so we can't add them here
        # Will be referenced directly in the toolbar
        
        # Tools menu with options for setting scale, defining paths, etc.
        tools_menu = menu_bar.addMenu("&Tools")
        
        # Scale tool
        self.set_scale_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Set &Scale...", self)
        self.set_scale_action.setShortcut("Ctrl+L")
        self.set_scale_action.setToolTip("Set the scale for distance calculations (Ctrl+L)")
        tools_menu.addAction(self.set_scale_action)
        
        # Draw obstacle
        self.draw_obstacle_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Draw &Obstacle", self)
        self.draw_obstacle_action.setToolTip("Draw an obstacle polygon on the warehouse layout")
        tools_menu.addAction(self.draw_obstacle_action)
        
        # Define staging area
        self.define_staging_area_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Draw S&taging Area", self)
        self.define_staging_area_action.setToolTip("Draw a staging area polygon on the warehouse layout")
        tools_menu.addAction(self.define_staging_area_action)
        
        # Define pathfinding bounds
        self.define_bounds_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Define &Bounds", self)
        self.define_bounds_action.setToolTip("Define the pathfinding bounds on the warehouse layout")
        tools_menu.addAction(self.define_bounds_action)
        
        # Set start point
        self.set_start_point_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Set &Start Point", self)
        self.set_start_point_action.setToolTip("Place a starting point on the warehouse layout")
        tools_menu.addAction(self.set_start_point_action)
        
        # Set end point
        self.set_end_point_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Set &End Point", self)
        self.set_end_point_action.setToolTip("Place an ending point on the warehouse layout")
        tools_menu.addAction(self.set_end_point_action)
        
        # Define aisle line
        self.define_aisle_line_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Define Aisle &Line", self)
        self.define_aisle_line_action.setToolTip("Define a line of pick aisle points")
        tools_menu.addAction(self.define_aisle_line_action)
        
        # Define staging line
        self.define_staging_line_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Define Staging Lin&e", self)
        self.define_staging_line_action.setToolTip("Define a line of staging location points")
        tools_menu.addAction(self.define_staging_line_action)
        
        # Edit mode
        self.edit_mode_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "&Edit Mode", self)
        self.edit_mode_action.setToolTip("Enable edit mode to modify drawn objects")
        self.edit_mode_action.setCheckable(True)  # This action is checkable
        tools_menu.addAction(self.edit_mode_action)
        
        tools_menu.addSeparator()
        
        # Precompute paths
        self.precompute_paths_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), "&Precompute Paths", self)
        self.precompute_paths_action.setShortcut("Ctrl+P")
        self.precompute_paths_action.setToolTip("Precompute all possible paths for analysis (Ctrl+P)")
        tools_menu.addAction(self.precompute_paths_action)
        
        # Project Settings
        self.project_settings_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), "Project &Settings...", self)
        self.project_settings_action.setToolTip("Configure project settings like grid resolution")
        tools_menu.addAction(self.project_settings_action)
        
        tools_menu.addSeparator()
        
        # Analysis tools
        self.analyze_picklist_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView), "&Analyze Picklist CSV...", self)
        self.analyze_picklist_action.setShortcut("Ctrl+T")
        self.analyze_picklist_action.setToolTip("Analyze a picklist CSV file (Ctrl+T)")
        tools_menu.addAction(self.analyze_picklist_action)
        
        self.view_last_analysis_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "View &Last Analysis", self)
        self.view_last_analysis_action.setToolTip("View results from the last picklist analysis")
        tools_menu.addAction(self.view_last_analysis_action)
        
        self.export_last_analysis_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "&Export Last Analysis", self)
        self.export_last_analysis_action.setToolTip("Export results from the last picklist analysis")
        tools_menu.addAction(self.export_last_analysis_action)
        
        # Animation tools
        self.animate_picklist_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "An&imate Picklist...", self)
        self.animate_picklist_action.setShortcut("Ctrl+I")
        self.animate_picklist_action.setToolTip("Animate warehouse operations from a picklist (Ctrl+I)")
        tools_menu.addAction(self.animate_picklist_action)
        
        tools_menu.addSeparator()
        
        # Add Clear menu
        clear_menu = tools_menu.addMenu("&Clear")
        clear_menu.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        
        self.clear_obstacles_action = QAction("Clear All &Obstacles", self)
        self.clear_obstacles_action.setToolTip("Remove all obstacles from the warehouse")
        clear_menu.addAction(self.clear_obstacles_action)
        
        self.clear_staging_areas_action = QAction("Clear All &Staging Areas", self)
        self.clear_staging_areas_action.setToolTip("Remove all staging areas from the warehouse")
        clear_menu.addAction(self.clear_staging_areas_action)
        
        self.clear_pick_aisles_action = QAction("Clear All Pick &Aisles", self)
        self.clear_pick_aisles_action.setToolTip("Remove all pick aisles (start points) from the warehouse")
        clear_menu.addAction(self.clear_pick_aisles_action)
        
        self.clear_staging_locations_action = QAction("Clear All Staging &Locations", self)
        self.clear_staging_locations_action.setToolTip("Remove all staging locations (end points) from the warehouse")
        clear_menu.addAction(self.clear_staging_locations_action)
        
        self.clear_pathfinding_bounds_action = QAction("Clear Pathfinding &Bounds", self)
        self.clear_pathfinding_bounds_action.setToolTip("Remove custom pathfinding bounds")
        clear_menu.addAction(self.clear_pathfinding_bounds_action)
        
        # Units menu with options for measurement units
        units_menu = menu_bar.addMenu("&Units")
        
        self.meters_action = QAction("&Meters", self)
        self.meters_action.setCheckable(True)
        self.meters_action.setToolTip("Display distances in meters")
        units_menu.addAction(self.meters_action)
        
        self.feet_action = QAction("&Feet", self)
        self.feet_action.setCheckable(True)
        self.feet_action.setToolTip("Display distances in feet")
        units_menu.addAction(self.feet_action)
        
        # Create a unit group for exclusive selection
        unit_group = QActionGroup(self)
        unit_group.setExclusive(True)
        unit_group.addAction(self.meters_action)
        unit_group.addAction(self.feet_action)
        
        # View menu with options for zoom, etc.
        view_menu = menu_bar.addMenu("&View")
        
        # Theme toggling action
        self.toggle_theme_action = QAction("Toggle &Dark Mode", self)
        self.toggle_theme_action.setCheckable(True)
        self.toggle_theme_action.setChecked(self.theme_manager.get_current_theme() == ThemeManager.DARK_THEME)
        # Set icon based on current theme
        theme_icon = QStyle.StandardPixmap.SP_DialogApplyButton
        if self.theme_manager.get_current_theme() == ThemeManager.DARK_THEME:
            theme_icon = QStyle.StandardPixmap.SP_DialogCancelButton
        self.toggle_theme_action.setIcon(self.style().standardIcon(theme_icon))
        self.toggle_theme_action.setShortcut("Ctrl+T")  # Add keyboard shortcut
        self.toggle_theme_action.setToolTip("Toggle between light and dark themes (Ctrl+T)")
        self.toggle_theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.toggle_theme_action)
        
        # Preferences action
        self.preferences_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "&Preferences...", self)
        self.preferences_action.setShortcut("Ctrl+,")  # Change from Ctrl+P to Ctrl+,
        self.preferences_action.setToolTip("Configure application preferences (Ctrl+,)")
        self.preferences_action.triggered.connect(self._show_preferences_dialog)
        view_menu.addAction(self.preferences_action)
        
        # Add separator for zoom-related actions
        view_menu.addSeparator()
        
        self.zoom_in_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Zoom &In", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        view_menu.addAction(self.zoom_in_action)
        
        self.zoom_out_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "Zoom &Out", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        view_menu.addAction(self.zoom_out_action)
        
        self.zoom_fit_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "&Fit to View", self)
        self.zoom_fit_action.setShortcut("Ctrl+0")
        view_menu.addAction(self.zoom_fit_action)
        
        # Interaction Mode submenu - Moved to Toolbar
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        self.about_action = QAction("&About", self)
        help_menu.addAction(self.about_action)
        
        # Connect menu actions
        self.open_pdf_action.triggered.connect(self._handle_open_pdf_action)
        self.open_project_action.triggered.connect(self._handle_open_project_action)
        self.save_project_action.triggered.connect(self._handle_save_project_action)
        self.save_project_as_action.triggered.connect(self._handle_save_project_as_action)
        self.exit_action.triggered.connect(self.close)
        
        self.set_scale_action.triggered.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.SET_SCALE_START))
        self.precompute_paths_action.triggered.connect(lambda: self.pathfinding_service.precompute_all_paths(self.model))
        self.project_settings_action.triggered.connect(self._show_project_settings_dialog)
        self.analyze_picklist_action.triggered.connect(self._trigger_picklist_analysis)
        self.animate_picklist_action.triggered.connect(self._trigger_picklist_animation)
        
        self.clear_obstacles_action.triggered.connect(self._handle_clear_obstacles_action)
        self.clear_staging_areas_action.triggered.connect(self._handle_clear_staging_areas_action)
        self.clear_pick_aisles_action.triggered.connect(self._handle_clear_pick_aisles_action)
        self.clear_staging_locations_action.triggered.connect(self._handle_clear_staging_locations_action)
        self.clear_pathfinding_bounds_action.triggered.connect(self._handle_clear_bounds_action)
        
        self.zoom_in_action.triggered.connect(self.pdf_viewer.zoom_in)
        self.zoom_out_action.triggered.connect(self.pdf_viewer.zoom_out)
        self.zoom_fit_action.triggered.connect(self.pdf_viewer.zoom_fit)
        
        self.about_action.triggered.connect(self._show_about_dialog)
        
        # Connect theme manager signal
        self.theme_manager.theme_changed.connect(self._handle_theme_changed)
        
        # Add keyboard shortcuts to menu items for better accessibility
        if hasattr(self, 'open_pdf_action') and self.open_pdf_action:
            self.open_pdf_action.setShortcut(QKeySequence("Ctrl+O"))
            self.open_pdf_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'open_project_action') and self.open_project_action:
            self.open_project_action.setShortcut(QKeySequence("Ctrl+P"))
            self.open_project_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'save_project_action') and self.save_project_action:
            self.save_project_action.setShortcut(QKeySequence("Ctrl+S"))
            self.save_project_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'save_project_as_action') and self.save_project_as_action:
            self.save_project_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
            self.save_project_as_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'exit_action') and self.exit_action:
            self.exit_action.setShortcut(QKeySequence("Alt+F4"))
            self.exit_action.setShortcutVisibleInContextMenu(True)
        
        # Add Export menu
        export_menu = menu_bar.addMenu("&Export")
        
        # Export path data
        self.export_path_data_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), "Export Current &Path Data...", self)
        self.export_path_data_action.setToolTip("Export the current path data to CSV")
        export_menu.addAction(self.export_path_data_action)
        
        # Export path image
        self.export_path_image_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), "Export Path &Image...", self)
        self.export_path_image_action.setToolTip("Export the current path as an image")
        export_menu.addAction(self.export_path_image_action)
        
        export_menu.addSeparator()
        
        # Export analysis results
        self.export_analysis_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Export &Analysis Results...", self)
        self.export_analysis_action.setToolTip("Export the analysis results to various formats")
        export_menu.addAction(self.export_analysis_action)
        
        # Export PDF report
        self.export_pdf_report_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Generate PDF &Report...", self)
        self.export_pdf_report_action.setToolTip("Generate a comprehensive PDF report")
        export_menu.addAction(self.export_pdf_report_action)
        
        export_menu.addSeparator()
        
        # Export layout image
        self.export_layout_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), "Export Complete &Layout...", self)
        self.export_layout_action.setToolTip("Export the entire warehouse layout as an image")
        export_menu.addAction(self.export_layout_action)
        
        # Add Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        # About action with icon
        self.about_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation), "&About", self)
        help_menu.addAction(self.about_action)
        
        # Documentation action with icon
        self.documentation_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "View &Documentation", self)
        help_menu.addAction(self.documentation_action)
        
    def _toggle_high_contrast(self):
        """Toggle high contrast mode for better accessibility"""
        is_enabled = self.theme_manager.toggle_high_contrast()
        self.high_contrast_action.setChecked(is_enabled)
        
        # Update status message
        mode_name = "enabled" if is_enabled else "disabled"
        self.status_progress.show_message(f"High contrast mode {mode_name}", 3000)
        
    def _show_preferences_dialog(self):
        """Show the preferences dialog"""
        if self.preferences_manager.show_preferences_dialog(self):
            # Preferences were changed and applied
            self.status_progress.show_message("Preferences updated", 3000)

    def _create_tool_bar(self):
        # Create main toolbar
        self.main_toolbar = self.addToolBar("Main Toolbar")
        self.main_toolbar.setMovable(True)
        
        # Create toolbar actions with icons
        # File operations
        self.toolbar_open_pdf_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Open PDF", self)
        self.toolbar_open_pdf_action.setToolTip("Open a PDF floor plan of the warehouse (Ctrl+O)")
        
        self.toolbar_open_project_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "Open Project", self)
        self.toolbar_open_project_action.setToolTip("Open a saved warehouse project file (Ctrl+R)")
        
        self.toolbar_save_project_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save Project", self)
        self.toolbar_save_project_action.setToolTip("Save the current warehouse project (Ctrl+S)")
        
        # Add file actions to toolbar
        self.main_toolbar.addAction(self.toolbar_open_pdf_action)
        self.main_toolbar.addAction(self.toolbar_open_project_action)
        self.main_toolbar.addAction(self.toolbar_save_project_action)
        self.main_toolbar.addSeparator()
        
        # Add Undo/Redo actions
        self.undo_action = self.undo_stack.createUndoAction(self, "&Undo")
        self.undo_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.undo_action.setShortcut("Ctrl+Z")
        
        self.redo_action = self.undo_stack.createRedoAction(self, "&Redo")
        self.redo_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.redo_action.setShortcut("Ctrl+Y")
        
        self.main_toolbar.addAction(self.undo_action)
        self.main_toolbar.addAction(self.redo_action)
        self.main_toolbar.addSeparator()
        
        # Create actions for Tools operations
        self.toolbar_set_scale_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton), "Set Scale", self)
        self.toolbar_set_scale_action.setToolTip("Set the scale for distance calculations (Ctrl+L)")
        
        self.toolbar_precompute_paths_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), "Precompute Paths", self)
        self.toolbar_precompute_paths_action.setToolTip("Precompute all possible paths (Ctrl+P)")
        
        self.toolbar_analyze_picklist_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView), "Analyze Picklist", self)
        self.toolbar_analyze_picklist_action.setToolTip("Analyze a picklist CSV file (Ctrl+T)")
        
        self.toolbar_animate_picklist_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "Animate Picklist", self)
        self.toolbar_animate_picklist_action.setToolTip("Animate warehouse operations from a picklist (Ctrl+I)")
        
        # Add tool actions to toolbar
        self.main_toolbar.addAction(self.toolbar_set_scale_action)
        self.main_toolbar.addAction(self.toolbar_precompute_paths_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.toolbar_analyze_picklist_action)
        self.main_toolbar.addAction(self.toolbar_animate_picklist_action)
        
        # Create PdfViewerInteractionToolbar
        self.interaction_toolbar = PdfViewerInteractionToolbar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.interaction_toolbar)
        
        # Connect file actions to existing handlers
        self.toolbar_open_pdf_action.triggered.connect(self._handle_open_pdf_action)
        self.toolbar_open_project_action.triggered.connect(self._handle_open_project_action)
        self.toolbar_save_project_action.triggered.connect(self._handle_save_project_action)
        
        # Connect tool actions to existing handlers
        self.toolbar_set_scale_action.triggered.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.SET_SCALE_START))
        self.toolbar_precompute_paths_action.triggered.connect(lambda: self.pathfinding_service.precompute_all_paths(self.model))
        self.toolbar_analyze_picklist_action.triggered.connect(self._trigger_picklist_analysis)
        self.toolbar_animate_picklist_action.triggered.connect(self._trigger_picklist_animation)

        # Connect interaction toolbar signals
        self.interaction_toolbar.mode_changed.connect(self.pdf_viewer.set_mode)
        self.interaction_toolbar.cancel_operation_requested.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.IDLE))
        
        # Make sure all toolbar buttons are keyboard accessible
        for action in self.main_toolbar.actions():
            if not action.shortcut().isEmpty():
                # If already has a shortcut, make sure it's visible
                action.setShortcutVisibleInContextMenu(True)

    def _connect_signals(self):
        # PdfViewer Signals - Explicitly connect them for clarity
        self.pdf_viewer.scale_line_drawn.connect(self._handle_scale_line_drawn)
        self.pdf_viewer.polygon_drawn.connect(self._handle_polygon_drawn)
        self.pdf_viewer.point_placement_requested.connect(self._handle_point_placement_requested)
        self.pdf_viewer.line_definition_requested.connect(self._handle_line_definition_requested)
        self.pdf_viewer.delete_items_requested.connect(self._handle_delete_items_requested)
        self.pdf_viewer.item_moved_in_edit.connect(self._handle_item_moved_in_edit)
        self.pdf_viewer.status_update.connect(lambda msg, timeout: self.status_progress.show_message(msg, timeout))
        self.pdf_viewer.mode_changed.connect(self._handle_pdf_viewer_mode_changed) # This connects to the next method
        self.pdf_viewer.zoom_level_changed.connect(self._handle_zoom_level_changed)
        self.pdf_viewer.pdf_dropped.connect(self._handle_pdf_dropped)
        
        # WorkflowPanel Signals
        self.workflow_panel.pick_aisles_reordered.connect(self._handle_pick_aisles_reordered)
        self.workflow_panel.staging_locations_reordered.connect(self._handle_staging_locations_reordered)
        
        # Model Signals
        self._connect_model_signals() # Call helper method for model signals
        
        # Service Signals
        self.project_service.project_operation_finished.connect(lambda msg: self.status_progress.show_message(msg, 5000))
        self.project_service.project_load_failed.connect(lambda err: QMessageBox.critical(self, "Load Error", err))
        self.project_service.project_save_failed.connect(lambda err: QMessageBox.critical(self, "Save Error", err))
        
        # Grid update signals
        self.pathfinding_service.grid_update_started.connect(self._handle_grid_update_started)
        self.pathfinding_service.grid_update_finished.connect(self._handle_grid_update_finished)
        
        # Precomputation signals
        self.pathfinding_service.precomputation_started.connect(self._handle_precomputation_started)
        self.pathfinding_service.precomputation_progress.connect(self._handle_precomputation_progress)
        self.pathfinding_service.precomputation_finished.connect(self._handle_precomputation_finished)
        
        # Analysis signals
        self.analysis_service.analysis_started.connect(self._handle_analysis_started)
        self.analysis_service.analysis_complete.connect(self._handle_analysis_complete)
        self.analysis_service.analysis_failed.connect(lambda err: QMessageBox.critical(self, "Analysis Error", err))
        self.analysis_service.export_complete.connect(lambda fp: QMessageBox.information(self, "Export Successful", f"Results exported to {fp}"))
        self.analysis_service.export_failed.connect(lambda err: QMessageBox.critical(self, "Export Error", err))
        
        # Animation signals
        self.animation_service.preparation_started.connect(self._handle_animation_preparation_started)
        self.animation_service.preparation_complete.connect(self._handle_animation_data_prepared)
        self.animation_service.preparation_failed.connect(lambda err: QMessageBox.critical(self, "Animation Prep Error", err))
        self.animation_service.preparation_warning.connect(lambda warn: QMessageBox.warning(self, "Animation Prep Warning", warn))

        # UI Element Signals (from _create_menu_bar originally, make sure these actions exist)
        # File menu actions
        self.open_pdf_action.triggered.connect(self._handle_open_pdf_action)
        self.open_project_action.triggered.connect(self._handle_open_project_action)
        self.save_project_action.triggered.connect(self._handle_save_project_action)
        self.save_project_as_action.triggered.connect(self._handle_save_project_as_action)
        self.exit_action.triggered.connect(self.close) # From _create_menu_bar

        # Tools menu actions
        self.set_scale_action.triggered.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.SET_SCALE_START))
        self.precompute_paths_action.triggered.connect(lambda: self.pathfinding_service.precompute_all_paths(self.model))
        self.project_settings_action.triggered.connect(self._show_project_settings_dialog)
        self.analyze_picklist_action.triggered.connect(self._trigger_picklist_analysis)
        self.view_last_analysis_action.triggered.connect(self._view_last_analysis_results_dialog)
        self.export_last_analysis_action.triggered.connect(self._export_last_analysis_results_dialog) # Connects to new name
        self.animate_picklist_action.triggered.connect(self._trigger_picklist_animation)
        self.animation_timer.timeout.connect(self._handle_animation_tick) # Animation timer

        # Clear menu actions
        self.clear_obstacles_action.triggered.connect(self._handle_clear_obstacles_action)
        self.clear_staging_areas_action.triggered.connect(self._handle_clear_staging_areas_action)
        self.clear_pick_aisles_action.triggered.connect(self._handle_clear_pick_aisles_action)
        self.clear_staging_locations_action.triggered.connect(self._handle_clear_staging_locations_action)
        self.clear_pathfinding_bounds_action.triggered.connect(self._handle_clear_bounds_action)

        # Zoom actions from View Menu
        self.zoom_in_action.triggered.connect(self.pdf_viewer.zoom_in)
        self.zoom_out_action.triggered.connect(self.pdf_viewer.zoom_out)
        self.zoom_fit_action.triggered.connect(self.pdf_viewer.zoom_fit)
        
        # Connect workflow panel buttons
        self.workflow_panel.load_pdf_button.clicked.connect(self._handle_open_pdf_action)
        self.workflow_panel.set_scale_button.clicked.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.SET_SCALE_START))
        self.workflow_panel.precompute_paths_button.clicked.connect(lambda: self.pathfinding_service.precompute_all_paths(self.model))
        self.workflow_panel.calculate_button.clicked.connect(self._handle_calculate_single_path)

        # Connect search panel signals
        self.search_filter_panel.search_points.connect(self._handle_search_points)
        self.search_filter_panel.search_obstacles.connect(self._handle_search_obstacles)
        self.search_filter_panel.search_paths.connect(self._handle_search_paths)
        
        # Connect search service signals to update UI
        self.search_service.search_points_completed.connect(self._handle_search_points_results)
        self.search_service.search_obstacles_completed.connect(self._handle_search_obstacles_results)
        self.search_service.search_paths_completed.connect(self._handle_search_paths_results)
        
        # Connect highlight and goto buttons
        self.search_filter_panel.highlight_button.clicked.connect(self._highlight_selected_result)
        self.search_filter_panel.goto_button.clicked.connect(self._goto_selected_result)

        # Export menu actions connections (these QActions are created in _create_menu_bar)
        self.export_path_data_action.triggered.connect(self._handle_export_path_data)
        self.export_path_image_action.triggered.connect(self._handle_export_path_image)
        # self.export_analysis_action is already connected above to _export_last_analysis_results_dialog
        self.export_pdf_report_action.triggered.connect(self._handle_export_pdf_report)
        self.export_layout_action.triggered.connect(self._handle_export_layout)
        
        # Help menu actions connections (these QActions are created in _create_menu_bar)
        self.about_action.triggered.connect(self._show_about_dialog) # From _create_menu_bar
        self.documentation_action.triggered.connect(self._show_documentation) # From _create_menu_bar
        
        # Connect theme manager signal
        self.theme_manager.theme_changed.connect(self._handle_theme_changed) # From _create_menu_bar
        
        # Add keyboard shortcuts to menu items for better accessibility (These ensure shortcuts are active)
        if hasattr(self, 'open_pdf_action') and self.open_pdf_action:
            self.open_pdf_action.setShortcut(QKeySequence("Ctrl+O"))
            self.open_pdf_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'open_project_action') and self.open_project_action:
            self.open_project_action.setShortcut(QKeySequence("Ctrl+P")) # Check if this shortcut is correct, was Ctrl+R before in one place
            self.open_project_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'save_project_action') and self.save_project_action:
            self.save_project_action.setShortcut(QKeySequence("Ctrl+S"))
            self.save_project_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'save_project_as_action') and self.save_project_as_action:
            self.save_project_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
            self.save_project_as_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'exit_action') and self.exit_action:
            self.exit_action.setShortcut(QKeySequence("Alt+F4"))
            self.exit_action.setShortcutVisibleInContextMenu(True)
        
    @Slot(InteractionMode)
    def _handle_pdf_viewer_mode_changed(self, mode: InteractionMode):
        """Update the interaction toolbar when the PdfViewer mode changes."""
        self.interaction_toolbar.set_active_mode(mode)
        
        # Also update the status bar with the current mode
        self.statusBar().showMessage(f"Mode: {mode.name}", 2000)

    # --- Model Signal Handlers ---
    @Slot()
    def _handle_model_reset(self):
        print("[MainWindow] Model has been reset.")
        self.pdf_viewer._clear_scene_items(clear_pdf=True)
        self._update_all_ui_states()
        self.status_progress.show_message("Model reset. Open a PDF or Project.", 5000)
        self.setWindowTitle("Warehouse Path Finder")
        self._last_analysis_detailed_results = None; self._last_analysis_warnings = None
        self._last_analysis_unit = None; self._last_analysis_input_filename = None
        self._stop_animation_and_close_dialog()

    @Slot(str)
    def _handle_pdf_loaded_in_model(self, pdf_path: str):
        print(f"[MainWindow] Model reports PDF path set: {pdf_path}")
        if pdf_path and self.model.pdf_bounds: # Check if bounds also exist
            success, _ = self.pdf_viewer.load_pdf(pdf_path) # Viewer loads its own copy
            if success:
                # Model already has bounds, just ensure viewer draws items
                self._redraw_viewer_from_model()
                self.status_progress.show_message(f"Loaded PDF: {pdf_path}. Set scale.", 5000)
            else:
                QMessageBox.critical(self, "PDF Load Error", f"Failed to load PDF into viewer: {pdf_path}")
                self.model.reset()
        elif not pdf_path: # Model was reset, pdf_path is None
             self.pdf_viewer._clear_scene_items(clear_pdf=True)
        self._update_all_ui_states(); self._update_window_title()

    @Slot(float, str, str)
    def _handle_scale_changed_in_model(self, pixels_per_unit, calib_unit, disp_unit):
        self.status_progress.show_message(f"Scale: {pixels_per_unit:.2f} px/{calib_unit}. Display: {disp_unit}. Ready for layout.", 5000)
        self._update_all_ui_states() # Updates granularity label and action states

    @Slot()
    def _handle_layout_or_points_changed_in_model(self):
        print("[MainWindow] Model layout or points changed. Redrawing viewer.")
        self._redraw_viewer_from_model()
        self._update_all_ui_states()
        
        # Update search panel point combos when points change
        self.search_filter_panel.update_point_combos(
            self.model.pick_aisles,
            self.model.staging_locations
        )

    def _redraw_viewer_from_model(self):
        """Clears and redraws all model-managed items in the PdfViewer."""
        self.pdf_viewer.clear_obstacles()
        for obs_poly in self.model.obstacles: self.pdf_viewer.add_obstacle_item(obs_poly)
        self.pdf_viewer.clear_staging_areas()
        for sa_poly in self.model.staging_areas: self.pdf_viewer.add_staging_area_item(sa_poly)
        self.pdf_viewer.clear_all_points()
        for name, pos in self.model.pick_aisles.items(): self.pdf_viewer.add_pick_aisle_item(name, pos)        
        for name, pos in self.model.staging_locations.items(): self.pdf_viewer.add_staging_location_item(name, pos)        
        self.pdf_viewer.clear_path() # Clear any old path if layout changed        # --- ADD BOUNDS DRAWING ---        self.pdf_viewer.draw_pathfinding_bounds_item(self.model.user_pathfinding_bounds)

    @Slot()
    def _handle_project_loaded_in_model(self):
        print("[MainWindow] Project loaded in model. Updating UI.")
        if self.model.current_pdf_path:
            success, bounds = self.pdf_viewer.load_pdf(self.model.current_pdf_path)
            if success and bounds:
                # If model didn't have bounds from project file, set them now from viewer
                if not self.model.pdf_bounds: self.model._pdf_bounds = bounds
            else:
                QMessageBox.warning(self, "Project Load", f"Could not load associated PDF: {self.model.current_pdf_path}")
        else: self.pdf_viewer._clear_scene_items(clear_pdf=True)
        self._redraw_viewer_from_model()
        self.status_progress.show_message(f"Project '{QFileInfo(self.model.current_project_path).fileName()}' loaded.", 5000)
        
        # Explicitly update WorkflowPanel button states
        pdf_loaded = self.model.current_pdf_path is not None
        scale_set = self.model.is_scale_set
        
        # Update PDF status
        if pdf_loaded:
            self.workflow_panel.update_pdf_status(QFileInfo(self.model.current_pdf_path).fileName())
            self.workflow_panel.set_scale_button.setEnabled(True)
        else:
            self.workflow_panel.update_pdf_status("Not loaded")
            self.workflow_panel.set_scale_button.setEnabled(False)
        
        # Update scale status
        if scale_set:
            self.workflow_panel.update_scale_status(f"Set (1px = {self.model.scale_pixels_per_unit:.3f} {self.model.display_unit})")
            self.workflow_panel.precompute_paths_button.setEnabled(True)
        else:
            self.workflow_panel.update_scale_status("Not set")
            self.workflow_panel.precompute_paths_button.setEnabled(False)
        
        # Update precomputation status based on grid validity
        if self.model.grid_is_valid:
            self.workflow_panel.update_precomputation_status("Ready")
            self.workflow_panel.precompute_paths_button.setEnabled(False)  # Already precomputed
            self.workflow_panel.calculate_button.setEnabled(self.model.can_calculate_paths)
            
            # Update grid dimensions if grid is valid
            if self.model.pathfinding_grid is not None:
                grid_h, grid_w = self.model.pathfinding_grid.shape
                self.workflow_panel.update_grid_dimensions(grid_w, grid_h)
        else:
            self.workflow_panel.update_precomputation_status("Needed")
            self.workflow_panel.precompute_paths_button.setEnabled(scale_set)
            self.workflow_panel.calculate_button.setEnabled(False)
            self.workflow_panel.update_grid_dimensions(0, 0)  # Reset grid dimensions
            
        self._update_window_title(); self._update_all_ui_states()

    @Slot()
    def _handle_grid_invalidated_in_model(self):
        print("[MainWindow] Model grid invalidated. Clearing visual path.")
        self.pdf_viewer.clear_path()
        self.status_progress.show_message("Path data is stale. Re-calculate or Precompute.", 3000)
        
        # Reset the grid dimensions display
        self.workflow_panel.update_grid_dimensions(0, 0)
        
        self._update_all_ui_states()

    @Slot(float, float)
    def _handle_cart_dimensions_changed_in_model(self, width: float, length: float):
        if self.animation_control_dialog:
            self.animation_control_dialog.update_cart_dimensions(width, length)
            # Update the animation visual display
            self.pdf_viewer.clear_animation_overlay()
            self._update_animation_frame()
            print(f"[MainWindow] Updated animation frame to reflect cart dimensions: {width:.3f}x{length:.3f} {self.model.display_unit}")

    # --- PdfViewer Signal Handlers ---
    @Slot(QPointF, QPointF)
    def _handle_scale_line_drawn(self, p1: QPointF, p2: QPointF):
        print(f"[MainWindow] _handle_scale_line_drawn called with p1: {p1}, p2: {p2}") # Debug print

        pixel_dist = math.dist(p1.toTuple(), p2.toTuple())
        print(f"[MainWindow] Calculated pixel_dist: {pixel_dist}") # Debug print

        if pixel_dist < 1e-6:
            self.status_progress.show_message("Scale line too short. Please try again.", 3000)
            print("[MainWindow] Scale line too short, re-entering SET_SCALE_START mode.") # Debug print
            self.pdf_viewer.set_mode(InteractionMode.SET_SCALE_START)
            return

        unit_to_use = self.model.display_unit
        print(f"[MainWindow] Showing QInputDialog for scale with unit: {unit_to_use}") # Debug print

        # Fix the multi-line string formatting
        dialog_text = f"The drawn line is {pixel_dist:.2f} pixels long.\nEnter its real-world distance (in {unit_to_use}):"
        real_dist_str, ok = QInputDialog.getText(self, "Set Scale", dialog_text)
        
        print(f"[MainWindow] QInputDialog result: ok={ok}, text='{real_dist_str}'") # Debug print

        if ok and real_dist_str:
            try:
                real_dist = float(real_dist_str)
                if real_dist <= 0:
                    raise ValueError("Distance must be positive.")
                
                self.model.set_scale(pixel_dist / real_dist, unit_to_use)
                # Status message for scale set will be handled by _handle_scale_changed_in_model
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for the distance.")
                print("[MainWindow] Invalid distance input, re-entering SET_SCALE_START mode.") # Debug print
                self.pdf_viewer.set_mode(InteractionMode.SET_SCALE_START) # Allow retry
        else:
            self.status_progress.show_message("Scale setting cancelled by user.", 3000)
            print("[MainWindow] Scale setting cancelled by user.") # Debug print
        
        # Ensure mode is reset if not already handled or re-entered for retry
        if self.pdf_viewer.current_mode not in [InteractionMode.IDLE, InteractionMode.SET_SCALE_START]:
            print(f"[MainWindow] Explicitly setting PdfViewer mode to IDLE from _handle_scale_line_drawn (current: {self.pdf_viewer.current_mode.name})")
            self.pdf_viewer.set_mode(InteractionMode.IDLE)

    @Slot(InteractionMode, QPolygonF)
    def _handle_polygon_drawn(self, mode_type: InteractionMode, polygon: QPolygonF):
        """Handle a new polygon drawn by the user based on current mode."""
        import commands  # Import locally to avoid circular imports
        
        if mode_type == InteractionMode.DRAW_OBSTACLE:
            command = commands.AddObstacleCommand(self.model, polygon)
            self.undo_stack.push(command)
            print(f"[MainWindow] Added obstacle via undo stack")
            self.status_progress.show_message("Obstacle added.", 3000)
            
        elif mode_type == InteractionMode.DEFINE_STAGING_AREA:
            command = commands.AddStagingAreaCommand(self.model, polygon)
            self.undo_stack.push(command)
            print(f"[MainWindow] Added staging area via undo stack")
            self.status_progress.show_message("Staging area added.", 3000)
            
        elif mode_type == InteractionMode.DEFINE_PATHFINDING_BOUNDS:
            command = commands.SetBoundsCommand(self.model, polygon)
            self.undo_stack.push(command)
            print(f"[MainWindow] Set pathfinding bounds via undo stack")
            self.status_progress.show_message("Pathfinding bounds set.", 3000)
        # Model changes will trigger PdfViewer redraw via _handle_layout_or_points_changed_in_model

    @Slot(PointType, QPointF)
    def _handle_point_placement_requested(self, point_type: PointType, pos: QPointF):
        """Handle point placement requests from the PdfViewer."""
        import commands  # Import locally to avoid circular imports
        
        if point_type == PointType.PICK_AISLE:
            # Ask user for the name of the new pick aisle
            name, ok = QInputDialog.getText(self, "New Pick Aisle", "Enter pick aisle name:", QLineEdit.EchoMode.Normal, f"PA{len(self.model.pick_aisles) + 1}")
            if ok and name:
                if name in self.model.pick_aisles:
                    QMessageBox.warning(self, "Duplicate Name", f"A pick aisle named '{name}' already exists.\nPlease choose a different name.")
                    return
                
                command = commands.AddPickAisleCommand(self.model, name, pos)
                self.undo_stack.push(command)
                print(f"[MainWindow] Added pick aisle '{name}' via undo stack")
                self.status_progress.show_message(f"Pick aisle '{name}' added at {pos.x():.2f}, {pos.y():.2f}", 3000)
                
        elif point_type == PointType.STAGING_LOCATION:
            # Ask user for the name of the new staging location
            name, ok = QInputDialog.getText(self, "New Staging Location", "Enter staging location name:", QLineEdit.EchoMode.Normal, f"SL{len(self.model.staging_locations) + 1}")
            if ok and name:
                if name in self.model.staging_locations:
                    QMessageBox.warning(self, "Duplicate Name", f"A staging location named '{name}' already exists.\nPlease choose a different name.")
                    return
                
                command = commands.AddStagingLocationCommand(self.model, name, pos)
                self.undo_stack.push(command)
                print(f"[MainWindow] Added staging location '{name}' via undo stack")
                self.status_progress.show_message(f"Staging location '{name}' added at {pos.x():.2f}, {pos.y():.2f}", 3000)

    @Slot(PointType, QPointF, QPointF)
    def _handle_line_definition_requested(self, point_type: PointType, p1: QPointF, p2: QPointF):
        dialog = LineDefinitionDialog(point_type.value, self)
        if dialog.exec():
            params = dialog.get_parameters()
            if params: self._generate_points_on_line_from_model(point_type, *params, p1, p2)
            else: QMessageBox.warning(self, f"Define {point_type.value} Line", "Invalid parameters.")
        # Viewer stays in its line drawing start mode unless user cancels it.

    @Slot(list)
    def _handle_delete_items_requested(self, items_to_delete_refs: List[QGraphicsItem]):
        if not items_to_delete_refs: return
        
        # Identify what types of items are being deleted
        obstacles_count = 0
        staging_areas_count = 0
        pick_aisles = []
        staging_locations = []
        
        # Pre-analyze the items to determine their types
        for item_ref in items_to_delete_refs:
            # Check if it's an obstacle
            for viewer_item in self.pdf_viewer._obstacle_items:
                if viewer_item is item_ref:
                    obstacles_count += 1
                    break
                    
            # Check if it's a staging area
            for viewer_item in self.pdf_viewer._staging_area_items:
                if viewer_item is item_ref:
                    staging_areas_count += 1
                    break
            
            # Check if it's a pick aisle (start point)
            for name, (marker, _) in self.pdf_viewer._start_point_items.items():
                if marker is item_ref and name not in pick_aisles:
                    pick_aisles.append(name)
                    break
                
            # Check if it's a staging location (end point)
            for name, (marker, _) in self.pdf_viewer._end_point_items.items():
                if marker is item_ref and name not in staging_locations:
                    staging_locations.append(name)
                    break
        
        # Build a detailed message about what's being deleted
        msg_parts = []
        if obstacles_count > 0:
            msg_parts.append(f"{obstacles_count} obstacle{'s' if obstacles_count > 1 else ''}")
        if staging_areas_count > 0:
            msg_parts.append(f"{staging_areas_count} staging area{'s' if staging_areas_count > 1 else ''}")
        if pick_aisles:
            msg_parts.append(f"{len(pick_aisles)} pick aisle{'s' if len(pick_aisles) > 1 else ''} ({', '.join(pick_aisles)})")
        if staging_locations:
            msg_parts.append(f"{len(staging_locations)} staging location{'s' if len(staging_locations) > 1 else ''} ({', '.join(staging_locations)})")
        
        msg = "Delete " + ", ".join(msg_parts) + "?"
        
        # Show confirmation dialog
        confirm = QMessageBox.question(self, "Confirm Deletion", msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.No: 
            self.pdf_viewer.scene().clearSelection()
            return
        
        import commands  # Import locally to avoid circular imports
        
        # Process obstacles
        for item_ref in items_to_delete_refs:
            for i, viewer_item in enumerate(self.pdf_viewer._obstacle_items):
                if viewer_item is item_ref:
                    # Get the polygon from the model using the viewer item as reference
                    for obstacle_poly in self.model.obstacles:
                        if self.pdf_viewer.item_to_model_polygon_map.get(viewer_item) == obstacle_poly:
                            command = commands.RemoveObstacleCommand(self.model, obstacle_poly)
                            self.undo_stack.push(command)
                            print(f"[MainWindow] Removed obstacle via undo stack")
                            break
        
        # Process staging areas
        for item_ref in items_to_delete_refs:
            for i, viewer_item in enumerate(self.pdf_viewer._staging_area_items):
                if viewer_item is item_ref:
                    # Get the polygon from the model using the viewer item as reference
                    for staging_poly in self.model.staging_areas:
                        if self.pdf_viewer.item_to_model_polygon_map.get(viewer_item) == staging_poly:
                            command = commands.RemoveStagingAreaCommand(self.model, staging_poly)
                            self.undo_stack.push(command)
                            print(f"[MainWindow] Removed staging area via undo stack")
                            break
        
        # Process pick aisles (start points)
        for name in pick_aisles:
            command = commands.RemovePickAisleCommand(self.model, name)
            self.undo_stack.push(command)
            print(f"[MainWindow] Removed pick aisle '{name}' via undo stack")
        
        # Process staging locations (end points)
        for name in staging_locations:
            command = commands.RemoveStagingLocationCommand(self.model, name)
            self.undo_stack.push(command)
            print(f"[MainWindow] Removed staging location '{name}' via undo stack")
        
        self.pdf_viewer.scene().clearSelection()
        
        # Show confirmation
        details = ", ".join(msg_parts)
        self.status_progress.show_message(f"Deleted: {details}", 3000)

    @Slot(QGraphicsItem, object)
    def _handle_item_moved_in_edit(self, moved_item: QGraphicsItem, new_geometry: Any):
        """Handle when an item has been moved in the editor."""
        import commands  # Import locally to avoid circular imports
        
        if isinstance(new_geometry, QPolygonF):  # Obstacle or Staging Area
            model_polygon = self.pdf_viewer.item_to_model_polygon_map.get(moved_item)
            if model_polygon:
                # Find if it's an obstacle or staging area
                if model_polygon in self.model.obstacles:
                    command = commands.RemoveObstacleCommand(self.model, model_polygon)
                    self.undo_stack.push(command)
                    # Now add the new one at the new position
                    command = commands.AddObstacleCommand(self.model, new_geometry)
                    self.undo_stack.push(command)
                    print(f"[MainWindow] Moved obstacle via undo stack")
                    self.status_progress.show_message("Obstacle moved.", 3000)
                elif model_polygon in self.model.staging_areas:
                    command = commands.RemoveStagingAreaCommand(self.model, model_polygon)
                    self.undo_stack.push(command)
                    # Now add the new one at the new position
                    command = commands.AddStagingAreaCommand(self.model, new_geometry)
                    self.undo_stack.push(command)
                    print(f"[MainWindow] Moved staging area via undo stack")
                    self.status_progress.show_message("Staging area moved.", 3000)
        
        elif isinstance(new_geometry, tuple) and len(new_geometry) == 3:  # Point (pick aisle or staging location)
            # Unpack the tuple: (point_id, scene_pos, is_start_point)
            point_id, scene_pos, is_start_point = new_geometry
            
            if is_start_point:
                # This is a pick aisle (start point)
                command = commands.RemovePickAisleCommand(self.model, point_id)
                self.undo_stack.push(command)
                command = commands.AddPickAisleCommand(self.model, point_id, scene_pos)
                self.undo_stack.push(command)
                print(f"[MainWindow] Moved pick aisle '{point_id}' via undo stack")
                self.status_progress.show_message(f"Pick aisle '{point_id}' moved.", 3000)
            else:
                # This is a staging location (end point)
                command = commands.RemoveStagingLocationCommand(self.model, point_id)
                self.undo_stack.push(command)
                command = commands.AddStagingLocationCommand(self.model, point_id, scene_pos)
                self.undo_stack.push(command)
                print(f"[MainWindow] Moved staging location '{point_id}' via undo stack")
                self.status_progress.show_message(f"Staging location '{point_id}' moved.", 3000)

    # --- UI Action Handlers ---
    def _handle_open_pdf_action(self):
        self._stop_animation_and_close_dialog()
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF Layout", "", "PDF Files (*.pdf)")
        if file_path:
            self._open_pdf_file(file_path)
        else: 
            self.status_progress.show_message("Open PDF cancelled.", 3000)

    def _disconnect_model_signals(self):
        """Helper to disconnect signals from the current self.model instance."""
        if self.model: # Check if a model exists
            try:
                self.model.pdf_path_changed.disconnect(self._handle_pdf_path_changed_in_model)
                self.model.scale_changed.disconnect(self._handle_scale_changed_in_model)
                self.model.layout_changed.disconnect(self._handle_layout_or_points_changed_in_model)
                self.model.points_changed.disconnect(self._handle_layout_or_points_changed_in_model)
                self.model.grid_parameters_changed.disconnect(self._handle_grid_params_changed_in_model)
                self.model.project_loaded.disconnect(self._handle_project_loaded_in_model)
                self.model.model_reset.disconnect(self._handle_model_reset)
                self.model.grid_invalidated.disconnect(self._handle_grid_invalidated_in_model)
                self.model.cart_dimensions_changed.disconnect(self._handle_cart_dimensions_changed_in_model)
                self.model.save_state_changed.disconnect(self._update_action_states) # Was _update_save_actions_state
                print("[MainWindow] Disconnected signals from old model.")
            except RuntimeError as e:
                # This can happen if signals were never connected or already disconnected
                print(f"[MainWindow] Info: Error disconnecting model signals (might be normal): {e}")
            except AttributeError as e:
                 print(f"[MainWindow] Info: AttributeError disconnecting model signals (model might be incomplete): {e}")


    def _connect_model_signals(self):
        """Connect model signals to their handlers."""
        self.model.pdf_path_changed.connect(self._handle_pdf_path_changed_in_model)
        self.model.pdf_bounds_set.connect(self._handle_pdf_bounds_set_in_model)
        self.model.scale_changed.connect(self._handle_scale_changed_in_model)
        
        self.model.layout_changed.connect(self._handle_layout_or_points_changed_in_model)
        self.model.points_changed.connect(self._handle_layout_or_points_changed_in_model)
        
        self.model.grid_parameters_changed.connect(self._handle_grid_parameters_changed_in_model)
        self.model.project_loaded.connect(self._handle_project_loaded_in_model)
        self.model.model_reset.connect(self._handle_model_reset)
        
        # Connect to save state changed to update undo/redo actions
        self.model.save_state_changed.connect(self._update_all_ui_states)
        
        # Connect undo stack's signals to update UI when undo/redo availability changes
        self.undo_stack.canUndoChanged.connect(self._update_all_ui_states)
        self.undo_stack.canRedoChanged.connect(self._update_all_ui_states)

    @Slot()
    def _handle_open_project_action(self):
        self._stop_animation_and_close_dialog()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Warehouse Project", "", "Warehouse Project Files (*.whp)"
        )
        if file_path:
            self._open_project_file(file_path)
        else:
            self.status_progress.show_message("Open Project cancelled.", 3000)

    def _handle_save_project_action(self):
        if self.model.current_project_path:
            saved = self.project_service.save_project(self.model, self.model.current_project_path)
            if saved:
                self._add_to_recent_files(self.model.current_project_path)
            return saved
        else:
            return self._handle_save_project_as_action()

    def _handle_save_project_as_action(self):
        if not self.model.is_saveable:
            QMessageBox.warning(self, "Save", "No data to save.")
            return False
        
        sugg_name = (QFileInfo(self.model.current_pdf_path).baseName() if self.model.current_pdf_path else "untitled") + ".whp"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", sugg_name, "Warehouse Project Files (*.whp)")
        if file_path:
            if self.project_service.save_project(self.model, file_path):
                self.model.set_current_project_path(file_path) # Update model's knowledge of its path
                self._update_window_title()
                self._add_to_recent_files(file_path)
                return True
            return False
        return False

    def _toggle_edit_mode(self, checked: bool):
        self.pdf_viewer.set_mode(InteractionMode.EDIT if checked else InteractionMode.IDLE)
        # set_edit_mode_flags is now called within pdf_viewer.set_mode
        self.status_progress.show_message("Edit Mode ON. Select items or use Rubberband. Uncheck to exit." if checked else "Edit Mode OFF.", 0 if checked else 3000)


    def _generate_points_on_line_from_model(self, point_type: PointType, cluster: str, start_num: int, end_num: int, p1: QPointF, p2: QPointF):
        # ... (logic as before, calling self.model.add_pick_aisle or self.model.add_staging_location)
        added_count, duplicates_skipped = 0, 0
        total_points_in_range = (end_num - start_num) + 1
        if point_type == PointType.PICK_AISLE:
            x, y_s, y_e = (p1.x()+p2.x())/2, min(p1.y(),p2.y()), max(p1.y(),p2.y())
            num_pairs = (total_points_in_range + 1) // 2; current_val = start_num
            if num_pairs < 1: return
            spacing = (y_e - y_s) / max(1, num_pairs - 1) if num_pairs > 1 else 0
            for i in range(num_pairs):
                y = y_s + i * spacing if num_pairs > 1 else (y_s + y_e) / 2
                for j in range(2):
                    if current_val + j <= end_num:
                        name = f"{cluster}{current_val + j}"
                        if self.model.add_pick_aisle(name, QPointF(x,y)): added_count += 1
                        else: duplicates_skipped += 1
                current_val += 2
        elif point_type == PointType.STAGING_LOCATION:
            y, x_s, x_e = (p1.y()+p2.y())/2, min(p1.x(),p2.x()), max(p1.x(),p2.x())
            num_points = total_points_in_range
            if num_points < 1: return
            spacing = (x_e - x_s) / max(1, num_points - 1) if num_points > 1 else 0
            for i in range(num_points):
                x = x_s + i * spacing if num_points > 1 else (x_s + x_e) / 2
                name = f"{cluster}{start_num + i}"
                if self.model.add_staging_location(name, QPointF(x,y)): added_count +=1
                else: duplicates_skipped +=1
        msg = f"Added {added_count} {point_type.value}(s)."; msg += f" Skipped {duplicates_skipped} duplicates." if duplicates_skipped else ""
        self.status_progress.show_message(msg, 3000)

    def _handle_calculate_single_path(self):
        if not self.model.can_calculate_paths: 
            QMessageBox.warning(self, "Error", "Set PDF, scale, and points."); 
            return
            
        start_n, end_n = self.start_combo.currentText(), self.end_combo.currentText()
        if not start_n or not end_n: 
            QMessageBox.warning(self, "Selection", "Select start and end points."); 
            return

        if not self.model.grid_is_valid or start_n not in self.model.path_maps:
            QMessageBox.information(self, "Info", f"Path data for '{start_n}' needs precomputation. Run Tools > Precompute All Paths."); 
            return

        self.status_progress.show_message(f"Calculating path: {start_n} to {end_n}...")
        self.status_progress.show_spinner(True)
        QApplication.processEvents()
        
        path_pts, dist = self.pathfinding_service.get_shortest_path(self.model, start_n, end_n)
        
        # Store the path and distance for export functionality
        self._last_calculated_path = path_pts
        self._last_path_distance = dist
        self._last_path_start = start_n
        self._last_path_end = end_n
        
        self.pdf_viewer.draw_path(path_pts)
        
        self.status_progress.show_spinner(False)
        if path_pts:
            unit = self.model.display_unit
            self.status_progress.show_message(f"Path: {start_n} to {end_n}. Distance: {dist:.2f} {unit}", 5000)
        else:
            self.status_progress.show_message(f"No path found from {start_n} to {end_n}", 5000)
        self._update_action_states()
        
    def _trigger_picklist_analysis(self):
        # ... (Logic remains similar, calls self.analysis_service.load_and_analyze) ...
        if not self.model.can_analyze_or_animate: QMessageBox.warning(self, "Analyze", "Set PDF, scale, points & precompute paths."); return
        fp, _ = QFileDialog.getOpenFileName(self, "Open Picklist for Analysis", "", "CSV (*.csv);;Text (*.txt)")
        if not fp: self.status_progress.show_message("Analysis cancelled."); return
        try:
            dlg = PicklistColumnDialog(fp, self)
            if dlg.exec(): sel = dlg.get_selected_columns(); self.analysis_service.load_and_analyze(self.model, fp, sel['dialect'], sel['has_header'], sel['indices']) if sel else self.status_progress.show_message("Col selection invalid.")
            else: self.status_progress.show_message("Col selection cancelled.")
        except RuntimeError as e: QMessageBox.critical(self, "File Error", f"Cannot process picklist preview: {e}")


    def _view_last_analysis_results_dialog(self):
        # ... (Logic remains similar, instantiates AnalysisResultsDialog with cached data) ...
        if not self._last_analysis_detailed_results: QMessageBox.information(self, "View Results", "No analysis results."); return
        dates = sorted(list(set(r.get('date','') for r in self._last_analysis_detailed_results if r.get('date'))))
        dlg = AnalysisResultsDialog(self._last_analysis_input_filename or "N/A", self._last_analysis_warnings,
                                   self._last_analysis_detailed_results, self._last_analysis_unit or self.model.display_unit, dates, self)
        dlg.export_filtered_requested.connect(self._export_filtered_analysis_data)
        dlg.exec()

    def _export_last_analysis_results_dialog(self): # Renamed from _export_last_analysis_results
        if not self._last_analysis_detailed_results: QMessageBox.information(self, "Export", "No results to export."); return
        default_name = "analysis_results.csv"
        if self._last_analysis_input_filename: default_name = f"{QFileInfo(self._last_analysis_input_filename).baseName()}_analysis.csv"
        fp, _ = QFileDialog.getSaveFileName(self, "Export Analysis", default_name, "CSV (*.csv)")
        if fp: self.analysis_service.export_results(self._last_analysis_detailed_results, self._last_analysis_unit or self.model.display_unit, fp)

    @Slot(list, str) # Slot for the signal from AnalysisResultsDialog
    def _export_filtered_analysis_data(self, filtered_results: list, unit: str):
        """Export filtered analysis results data."""
        # Get export path using dialog
        self.analysis_service.export_analysis_results(filtered_results, unit)
        
    def _show_project_settings_dialog(self):
        """Show the project settings dialog to edit grid resolution, staging penalty, and cart dimensions."""
        # Create the settings dialog with current model values
        dialog = ProjectSettingsDialog(self.model, self)
        
        # Show the dialog
        if dialog.exec():
            # The dialog will update the model directly via set_* methods
            # Just update the UI to reflect any changes
            self._update_all_ui_states()
            self.status_progress.show_message("Project settings updated", 3000)
            
    def _trigger_picklist_animation(self):
        """Present dialog to select picklist file and prepare animation data."""
        if not self.model.can_analyze_or_animate: 
            QMessageBox.warning(self, "Animate", "Set PDF, scale, points & precompute.") 
            return
            
        fp, _ = QFileDialog.getOpenFileName(self, "Open Picklist for Animation", "", "CSV (*.csv);;Text (*.txt)")
        if not fp: 
            self.status_progress.show_message("Animation cancelled.")
            return
            
        try:
            dlg = AnimationPicklistDialog(fp, self)
            if dlg.exec(): 
                sel = dlg.get_animation_selection_data()
                if sel:
                    self.animation_service.prepare_animation_data(self.model, fp, sel) 
                else:
                    self.status_progress.show_message("Animation column selection invalid.")
            else: 
                self.status_progress.show_message("Animation column selection cancelled.")
        except RuntimeError as e: 
            QMessageBox.critical(self, "File Error", f"Cannot process animation file preview: {e}")

    @Slot(bool)
    def _handle_grid_update_finished(self, success: bool):
        if success:
            self.status_progress.show_message("Grid updated successfully!", 3000)
            # Update grid dimensions in the workflow panel
            if self.model.pathfinding_grid is not None:
                grid_h, grid_w = self.model.pathfinding_grid.shape
                self.workflow_panel.update_grid_dimensions(grid_w, grid_h)
        else:
            self.status_progress.show_message("Grid update failed.", 3000)
        self.status_progress.show_spinner(False)
        self._update_all_ui_states()
        
    @Slot(int)
    def _handle_precomputation_started(self, point_count: int):
        self.status_progress.show_message(f"Precomputing paths for {point_count} points...")
        self.status_progress.show_progress(True, 0, point_count)
        self.workflow_panel.update_precomputation_status("In progress...")
        self._update_all_ui_states()
    
    @Slot(int, str)
    def _handle_precomputation_progress(self, done_count: int, current_point: str):
        self.status_progress.show_message(f"Precomputed {done_count} paths (current: {current_point})...")
        self.status_progress.update_progress(done_count)
    
    @Slot(str)
    def _handle_analysis_started(self, file_path: str):
        file_name = QFileInfo(file_path).fileName()
        self.status_progress.show_message(f"Analyzing: {file_name}...")
        self.status_progress.show_spinner(True)
    
    @Slot(str)
    def _handle_animation_preparation_started(self, file_path: str):
        file_name = QFileInfo(file_path).fileName()
        self.status_progress.show_message(f"Preparing animation: {file_name}...")
        self.status_progress.show_spinner(True)
    
    @Slot(bool, list)
    def _handle_precomputation_finished(self, success: bool, failed_points: List[str]):
        self.status_progress.show_progress(False)
        self.status_progress.show_spinner(False)
        
        if success:
            self.status_progress.show_message("Path precomputation completed successfully!", 5000)
            self.workflow_panel.update_precomputation_status("Complete")
        else:
            msg = f"Path precomputation completed with {len(failed_points)} failed points."
            self.status_progress.show_message(msg, 5000)
            self.workflow_panel.update_precomputation_status("Partial")
            if failed_points:
                QMessageBox.warning(self, "Precomputation Warning", 
                                  f"Failed to precompute {len(failed_points)} points.\n"
                                  f"First few: {', '.join(failed_points[:5])}"
                                  f"{' and more...' if len(failed_points) > 5 else ''}")
        
        # Update grid dimensions in the workflow panel
        if self.model.pathfinding_grid is not None:
            grid_h, grid_w = self.model.pathfinding_grid.shape
            self.workflow_panel.update_grid_dimensions(grid_w, grid_h)
        
        self._update_all_ui_states()

    @Slot(list, list, str, str)
    def _handle_analysis_complete(self, detailed_results, warnings_list, unit, input_filename):
        self.status_progress.show_spinner(False)
        file_base_name = QFileInfo(input_filename).fileName()
        self.status_progress.show_message(f"Analysis of '{file_base_name}' complete.", 5000)

        # Cache the results for "View Last Analysis" and "Export Last Analysis"
        self._last_analysis_detailed_results = detailed_results
        self._last_analysis_warnings = warnings_list
        self._last_analysis_unit = unit
        self._last_analysis_input_filename = input_filename # Store the original full path

        self._update_all_ui_states() # Update actions like "View Last Analysis"

        # Automatically show the results dialog
        if detailed_results: # Only show if there's something to show
            self._view_last_analysis_results_dialog()
        elif warnings_list: # If no results but there are warnings, maybe still show them
            QMessageBox.information(self, "Analysis Info",
                                    "Analysis complete, but no data rows were successfully processed.\n\n" +
                                    "\n".join(warnings_list[:5]) + ("..." if len(warnings_list) > 5 else ""))
        else:
            QMessageBox.information(self, "Analysis Info", "Analysis complete. No data processed and no warnings.")

    @Slot(list, object) 
    def _handle_animation_data_prepared(self, animation_data_from_signal: List[Dict[str, Any]], earliest_dt_from_signal: Optional[datetime]):
        print(f"[MainWindow] _handle_animation_data_prepared received {len(animation_data_from_signal)} items.")
        if animation_data_from_signal:
            print(f"[MainWindow] Sample received animation data item: {animation_data_from_signal[0]}")
            if 'start_dt' in animation_data_from_signal[0]:
                print(f"[MainWindow] Sample item start_dt: {animation_data_from_signal[0]['start_dt']} (type: {type(animation_data_from_signal[0]['start_dt'])})")
            else:
                print("[MainWindow] WARNING: Received anim_data item MISSING 'start_dt'!")
        print(f"[MainWindow] Received earliest_dt: {earliest_dt_from_signal}")

        # 1. Stop any existing animation and close its dialog FIRST
        self._stop_animation_and_close_dialog()

        # 2. Check if new data is valid
        if not animation_data_from_signal:
            QMessageBox.warning(self, "Animation Data", "No valid animation data could be prepared.")
            self.statusBar().showMessage("Animation data preparation resulted in no usable entries.", 5000)
            self._animation_data_prepared = [] # Ensure it's empty if new data is bad
            self._animation_earliest_dt_prepared = None
            self._update_all_ui_states()
            return

        # 3. Now assign the new data to instance variables
        self._animation_data_prepared = animation_data_from_signal
        self._animation_earliest_dt_prepared = earliest_dt_from_signal
        self.statusBar().showMessage("Animation data ready. Opening controls...", 3000)

        # 4. Extract clusters and dates from the newly set self._animation_data_prepared
        all_starts_set = set()
        all_ends_set = set()
        unique_dates_str_set = set()

        print(f"[MainWindow] Processing {len(self._animation_data_prepared)} items for dialog setup...")

        for idx, item in enumerate(self._animation_data_prepared):
            start_name = item.get('start_name')
            end_name = item.get('end_name')
            item_start_dt = item.get('start_dt')

            if start_name:
                start_cluster = _get_cluster_from_name(start_name)
                if start_cluster: all_starts_set.add(start_cluster)
            if end_name:
                end_cluster = _get_cluster_from_name(end_name)
                if end_cluster: all_ends_set.add(end_cluster)
            if item_start_dt and isinstance(item_start_dt, datetime):
                unique_dates_str_set.add(item_start_dt.strftime("%Y-%m-%d"))
        
        sorted_unique_dates = sorted(list(unique_dates_str_set))
        
        print(f"[MainWindow] Extracted Start Clusters: {all_starts_set}")
        print(f"[MainWindow] Extracted End Clusters: {all_ends_set}")
        print(f"[MainWindow] Extracted Unique Dates (strings): {unique_dates_str_set}")
        print(f"[MainWindow] Sorted Unique Dates for Dialog: {sorted_unique_dates}")

        # 5. Create and show the dialog
        self.animation_control_dialog = AnimationControlDialog(
            all_starts_set,
            all_ends_set,
            sorted_unique_dates,
            self.model.animation_cart_width,
            self.model.animation_cart_length,
            self.model.display_unit,
            self
        )
        # ... (connections and showing the dialog) ...
        self.animation_control_dialog.play_pause_toggled.connect(self._toggle_animation_playback)
        self.animation_control_dialog.reset_clicked.connect(self._reset_animation_state_and_frame)
        self.animation_control_dialog.speed_changed.connect(self._set_animation_speed)
        self.animation_control_dialog.filters_changed.connect(self._apply_animation_filters)
        self.animation_control_dialog.cart_dimensions_changed.connect(self.model.set_animation_cart_dimensions)
        self.animation_control_dialog.open_project_settings.connect(self._show_project_settings_dialog)
        self.animation_control_dialog.rejected.connect(self._stop_animation_and_close_dialog)

        initial_date_filter = "All Dates"
        if sorted_unique_dates:
            initial_date_filter = sorted_unique_dates[0]
        
        # This will also call _apply_animation_filters which resets to the new range
        self.animation_control_dialog.select_date(initial_date_filter)
        
        # If select_date doesn't trigger filters_changed (e.g., if it's already the current text),
        # explicitly apply filters to ensure time ranges are set.
        # However, select_date in AnimationControlDialog *should* trigger currentTextChanged
        # if the index actually changes. If it's already on the desired text,
        # we need to ensure _apply_animation_filters is called.
        current_dialog_date = self.animation_control_dialog.date_combo.currentText()
        if initial_date_filter == current_dialog_date : # If select_date didn't cause a change signal
            self._apply_animation_filters(
                current_dialog_date,
                sorted(list(all_starts_set)),
                sorted(list(all_ends_set)),
                AnimationMode(self.animation_control_dialog.mode_combo.currentText()),
                self.animation_control_dialog.path_duration_spinbox.value(),
                self.animation_control_dialog.keep_paths_checkbox.isChecked()
            )
        
        self.animation_control_dialog.show()

    def _stop_animation_and_close_dialog(self):
        """Stop animation playback and close the control dialog."""
        self.animation_timer.stop()
        self.pdf_viewer.clear_animation_overlay()
        if self.animation_control_dialog:
            # Disconnect to prevent issues if dialog is already closing
            try: 
                self.animation_control_dialog.rejected.disconnect(self._stop_animation_and_close_dialog)
            except RuntimeError: 
                pass # Signal was not connected or already disconnected
            self.animation_control_dialog.close()
            self.animation_control_dialog = None
        self.current_animation_time_s = 0.0
        self._animation_data_prepared = []
        self._animation_earliest_dt_prepared = None
        print("[MainWindow] Animation stopped and dialog closed.")

    @Slot(bool)
    def _toggle_animation_playback(self, play: bool):
        """Toggle animation playback between playing and paused states."""
        if play and self._animation_data_prepared:
            if self._filtered_max_time_s is not None and self.current_animation_time_s >= self._filtered_max_time_s:
                self._reset_animation_state_and_frame()
            self.animation_timer.start()
            self.statusBar().showMessage("Animation Playing...", 0)
        else:
            self.animation_timer.stop()
            self.statusBar().showMessage("Animation Paused.", 3000)

    @Slot()
    def _reset_animation_state_and_frame(self):
        self.current_animation_time_s = self._filtered_min_time_s if self._filtered_min_time_s is not None else 0.0
        self._update_animation_frame() # Draw initial frame
        if self.animation_control_dialog:
            self.animation_control_dialog.update_time_display(self.current_animation_time_s, self._filtered_earliest_dt)
            self.animation_control_dialog.update_progress(self.current_animation_time_s, self._filtered_min_time_s or 0.0, self._filtered_max_time_s or 0.0)
            self.animation_control_dialog.play_pause_button.setChecked(False)
        self.animation_timer.stop() # Ensure stopped on reset
        self.statusBar().showMessage("Animation Reset.", 3000)

    @Slot(int)
    def _set_animation_speed(self, speed: int): self.animation_speed_multiplier = float(speed)

    @Slot(str, list, list, AnimationMode, int, bool)
    def _apply_animation_filters(self, date_str, start_clusters, end_clusters, mode, duration_min, keep_paths):
        self._animation_selected_date_filter = date_str
        self._animation_active_start_clusters = set(start_clusters)
        self._animation_active_end_clusters = set(end_clusters)
        self._animation_mode_current = mode
        self._path_visibility_duration_s_current = duration_min * 60
        self._keep_paths_visible_current = keep_paths
        self._recalculate_filtered_animation_time_range()
        self._reset_animation_state_and_frame()
        self.statusBar().showMessage(f"Animation filters updated. Mode: {mode.value}", 3000)

    def _recalculate_filtered_animation_time_range(self):
        if not self._animation_data_prepared: self._filtered_min_time_s=0.0; self._filtered_max_time_s=0.0; self._filtered_earliest_dt=None; return
        min_t, max_t, earliest_dt_filt, found = float('inf'), float('-inf'), None, False
        for item in self._animation_data_prepared:
            item_date_str = item['start_dt'].strftime("%Y-%m-%d")
            if self._animation_selected_date_filter == "All Dates" or item_date_str == self._animation_selected_date_filter:
                found=True; min_t=min(min_t,item['start_time_s']); max_t=max(max_t,item['end_time_s'])
                if earliest_dt_filt is None or item['start_dt'] < earliest_dt_filt: earliest_dt_filt = item['start_dt']
        if found: self._filtered_min_time_s=min_t; self._filtered_max_time_s=max_t if max_t>min_t else min_t; self._filtered_earliest_dt=earliest_dt_filt
        else: self._filtered_min_time_s=0.0; self._filtered_max_time_s=0.0; self._filtered_earliest_dt=None
        print(f"[MainWindow] Filtered anim range: [{self._filtered_min_time_s}, {self._filtered_max_time_s}] for date '{self._animation_selected_date_filter}'")

    @Slot()
    def _handle_animation_tick(self):
        if not self._animation_data_prepared or self._filtered_max_time_s is None: return
        time_increment = (self.animation_timer.interval()/1000.0) * self.animation_speed_multiplier
        self.current_animation_time_s += time_increment
        if self.current_animation_time_s >= self._filtered_max_time_s:
            self.current_animation_time_s = self._filtered_max_time_s; self.animation_timer.stop()
            if self.animation_control_dialog: self.animation_control_dialog.play_pause_button.setChecked(False)
            self.statusBar().showMessage("Animation Finished.", 3000)
        self._update_animation_frame()
        if self.animation_control_dialog:
            self.animation_control_dialog.update_time_display(self.current_animation_time_s, self._filtered_earliest_dt) # Pass filtered earliest dt
            self.animation_control_dialog.update_progress(self.current_animation_time_s, self._filtered_min_time_s or 0.0, self._filtered_max_time_s or 0.0)

    def _update_animation_frame(self):
        if not self._animation_data_prepared:
            return

        active_items_for_frame = []
        current_time_s = self.current_animation_time_s

        # Optional: Print current time only once per few ticks to reduce spam
        if not hasattr(self, '_anim_tick_count'):
            self._anim_tick_count = 0
        # Increase interval for status print (e.g., every 500 ticks instead of 200)
        self._anim_tick_count = (self._anim_tick_count + 1) % 500
        
        if self._anim_tick_count == 1: # Print status periodically
            print(f"[ANIM TICK STATUS] Global Time: {current_time_s:.2f}s. "
                  f"Filtered Range: [{self._filtered_min_time_s if self._filtered_min_time_s is not None else 'N/A'}, "
                  f"{self._filtered_max_time_s if self._filtered_max_time_s is not None else 'N/A'}]. "
                  f"Mode: {self._animation_mode_current.value}. "
                  f"Date Filter: '{self._animation_selected_date_filter}'")
            if self.model.scale_pixels_per_unit:
                 pass # No need to print scale every time unless debugging scale issues
                 # print(f"    Scale is: {self.model.scale_pixels_per_unit:.2f} px/{self.model.calibration_unit}")
            else:
                print(f"    WARNING: Scale is NOT SET (model.scale_pixels_per_unit is None). Carts may not display correctly.")


        scale_px_per_unit = self.model.scale_pixels_per_unit if self.model.scale_pixels_per_unit is not None and self.model.scale_pixels_per_unit > 0 else 1.0

        for item_idx, item in enumerate(self._animation_data_prepared):
            item_start_dt = item.get('start_dt')
            if not isinstance(item_start_dt, datetime):
                if self._anim_tick_count == 1 and item_idx < 2 : print(f"[ANIM FRAME WARN] Item {item_idx} has invalid start_dt: {item_start_dt}")
                continue

            item_date_str = item_start_dt.strftime("%Y-%m-%d")
            
            # Date Filter Check
            date_match = (self._animation_selected_date_filter == "All Dates" or
                          item_date_str == self._animation_selected_date_filter)
            if not date_match:
                continue
            
            # Cluster Filter Check
            start_cluster = _get_cluster_from_name(item.get('start_name'))
            end_cluster = _get_cluster_from_name(item.get('end_name'))
            start_cluster_match = (not self._animation_active_start_clusters or
                                   (start_cluster and start_cluster in self._animation_active_start_clusters))
            end_cluster_match = (not self._animation_active_end_clusters or
                                 (end_cluster and end_cluster in self._animation_active_end_clusters))
            if not (start_cluster_match and end_cluster_match):
                continue

            item_start_s, item_end_s, path_points = item['start_time_s'], item['end_time_s'], item['path_points']
            item_id = item.get('id', f'Item_{item_idx}')

            if self._animation_mode_current == AnimationMode.CARTS:
                if item_start_s <= current_time_s <= item_end_s and len(path_points) > 1:
                    duration = item_end_s - item_start_s
                    progress = (current_time_s - item_start_s) / duration if duration > 1e-6 else 1.0
                    progress = max(0.0, min(1.0, progress))
                    
                    idx_float = progress * (len(path_points) -1)
                    seg_idx = int(idx_float); seg_prog = idx_float - seg_idx
                    seg_idx = min(seg_idx, len(path_points)-2) 
                    next_idx = min(seg_idx + 1, len(path_points) - 1)
                    
                    p1, p2 = path_points[seg_idx], path_points[next_idx]
                    pos = QPointF(p1.x()+(p2.x()-p1.x())*seg_prog, p1.y()+(p2.y()-p1.y())*seg_prog)
                    angle = math.degrees(math.atan2(p2.y()-p1.y(), p2.x()-p1.x()))
                    
                    cart_width_px = self.model.animation_cart_width * scale_px_per_unit
                    cart_length_px = self.model.animation_cart_length * scale_px_per_unit

                   
                    if cart_width_px > 0.1 and cart_length_px > 0.1 :
                        active_items_for_frame.append({
                            'pos': pos, 'angle': angle,
                            'width': cart_width_px, 'length': cart_length_px
                        })

            elif self._animation_mode_current == AnimationMode.PATH_LINES:
                is_visible_this_tick = False; alpha = 255; draw_progress = 0.0
                if self._keep_paths_visible_current:
                    if item_start_s <= current_time_s: is_visible_this_tick = True; draw_progress = 1.0
                else: 
                    if item_start_s <= current_time_s <= (item_end_s + self._path_visibility_duration_s_current):
                        is_visible_this_tick = True
                        duration = item_end_s - item_start_s
                        draw_progress = (current_time_s-item_start_s)/duration if duration > 1e-6 else 1.0
                        draw_progress = max(0.0,min(1.0,draw_progress))
                        if current_time_s > item_end_s and self._path_visibility_duration_s_current > 1e-6:
                            fade_p = (current_time_s-item_end_s)/self._path_visibility_duration_s_current
                            alpha=int(255*(1.0-max(0.0,min(1.0,fade_p))))
                
                if is_visible_this_tick and alpha > 0 and len(path_points) > 1:

                    active_items_for_frame.append({
                        'id': item_id, 'points': path_points, 'draw_progress': draw_progress,
                        'alpha': alpha, 'start_cluster': start_cluster
                    })
        
        
        self.pdf_viewer.update_animation_overlay(self._animation_mode_current, active_items_for_frame)
        self.pdf_viewer.viewport().update()

    # ... (rest of the code remains unchanged)
            
    def _open_project_file(self, file_path):
        """Open a project file."""
        # Check for unsaved changes
        if self.model.is_saveable and self.model.needs_save:
            reply = QMessageBox.question(
                self, 
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before opening a new project?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                # Try to save and handle the case if save fails
                if self.model.current_project_path:
                    saved = self.project_service.save_project(self.model, self.model.current_project_path)
                    if not saved:
                        return
                else:
                    # Show save dialog
                    saved = self._handle_save_project_as_action()
                    if not saved:
                        return
            elif reply == QMessageBox.StandardButton.Cancel:
                self.status_progress.show_message("Open Project cancelled.", 3000)
                return
                
        if os.path.exists(file_path):
            loaded_model = self.project_service.load_project(file_path)
            if loaded_model:
                # Disconnect signals from the old model BEFORE replacing it
                self._disconnect_model_signals()
                
                self.model = loaded_model  # Replace current model with the newly loaded one
                self.model.setParent(self) # Ensure proper Qt object ownership if model is a QObject

                # Connect signals to the new model instance
                self._connect_model_signals()
                
                # Manually trigger project_loaded handling sequence for the new model.
                self._handle_project_loaded_in_model()
                
                # Add to recent files after successful load
                self._add_to_recent_files(file_path)
                
                # Show success message
                self.status_progress.show_message(f"Project '{QFileInfo(file_path).fileName()}' loaded successfully.", 5000)
                
                # Close any open menus and focus back on the main window
                for action in self.menuBar().actions():
                    menu = action.menu()
                    if menu and menu.isVisible():
                        menu.close()
                
                # Set focus back to the main window
                self.setFocus()
                
                # Process events to ensure UI updates properly
                QApplication.processEvents()
        else:
            QMessageBox.warning(self, "File Not Found", f"The file {file_path} no longer exists.")
            # Remove from recent files
            self._remove_from_recent_files(file_path)
            
    def _remove_from_recent_files(self, file_path):
        """Remove a file from the recent files list."""
        recent_files = self.settings.value("recentFiles", [])
        if not isinstance(recent_files, list):
            recent_files = []
            
        if file_path in recent_files:
            recent_files.remove(file_path)
            self.settings.setValue("recentFiles", recent_files)
            self._update_recent_files_menu()
            
    def _clear_recent_files(self):
        """Clear the recent files list."""
        self.settings.setValue("recentFiles", [])
        self._update_recent_files_menu()

    @Slot(str)
    def _handle_pdf_path_changed_in_model(self, path: str):
        """Handler for when the PDF path changes in the model."""
        if path:
            # PDF loaded, update the viewer
            if self.pdf_viewer.current_pdf_path != path:
                self.pdf_viewer.load_pdf(path)
        else:
            # PDF was reset to None
            self.pdf_viewer.clear_pdf()
        self._update_all_ui_states()

    @Slot(QRectF)
    def _handle_pdf_bounds_set_in_model(self, bounds: QRectF):
        """Handler for when the PDF bounds are set in the model."""
        print(f"[MainWindow] PDF bounds set in model: {bounds}")
        # The PDF viewer is updated when the PDF path changes, so we don't need to do that here
        # Just update UI states to reflect the new bounds
        self._update_all_ui_states()
        
    @Slot()
    def _handle_grid_parameters_changed_in_model(self):
        """Handler for when grid parameters change in the model."""
        self._update_spinbox_values_from_model()  # Ensure UI reflects model
        self._update_granularity_label()
        
        # Update grid dimensions if available
        if self.model.pathfinding_grid is not None:
            grid_h, grid_w = self.model.pathfinding_grid.shape
            self.workflow_panel.update_grid_dimensions(grid_w, grid_h)
            
        self._update_all_ui_states()  # Actions might depend on this

    @Slot(str)
    def _handle_theme_changed(self, theme: str):
        """Handle theme change events"""
        is_dark = (theme == ThemeManager.DARK_THEME)
        self.toggle_theme_action.setChecked(is_dark)
        
        # Update the icon based on the current theme
        theme_icon = QStyle.StandardPixmap.SP_DialogCancelButton if is_dark else QStyle.StandardPixmap.SP_DialogApplyButton
        self.toggle_theme_action.setIcon(self.style().standardIcon(theme_icon))
        
        # Update action text based on current theme
        self.toggle_theme_action.setText("Toggle &Light Mode" if is_dark else "Toggle &Dark Mode")
        
        # Refresh PDF viewer styles
        if hasattr(self, 'pdf_viewer') and self.pdf_viewer:
            self.pdf_viewer.refresh_styles()
        
        # Refresh workflow panel styles
        if hasattr(self, 'workflow_panel') and self.workflow_panel:
            self.workflow_panel.refresh_styles()
            
        self.statusBar().showMessage(f"Theme switched to {'dark' if is_dark else 'light'} mode", 3000)
    
    def _toggle_theme(self):
        """Toggle between light and dark themes"""
        self.theme_manager.toggle_theme()

    def _show_preferences_dialog(self):
        """Show the preferences dialog"""
        if self.preferences_manager.show_preferences_dialog(self):
            # Preferences were changed and applied
            self.status_progress.show_message("Preferences updated", 3000)

    @Slot(float)
    def _handle_zoom_level_changed(self, zoom_level: float):
        """Update the zoom percentage label when the zoom level changes."""
        self.zoom_percentage_label.setText(f"{zoom_level:.0f}%")

    def _setup_keyboard_shortcuts(self):
        """Setup additional keyboard shortcuts that are not in the menus"""
        # Check for actual keyboard shortcuts after all menus are created
        if hasattr(self, 'save_project_action') and self.save_project_action:
            self.save_project_action.setShortcut(QKeySequence("Ctrl+S"))
            self.save_project_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'save_project_as_action') and self.save_project_as_action:
            self.save_project_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
            self.save_project_as_action.setShortcutVisibleInContextMenu(True)
            
        if hasattr(self, 'exit_action') and self.exit_action:
            self.exit_action.setShortcut(QKeySequence("Alt+F4"))
            self.exit_action.setShortcutVisibleInContextMenu(True)
        
        # Set up custom shortcut for "calculate path"
        self.calculate_path_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.calculate_path_shortcut.activated.connect(self._handle_calculate_single_path)

        # Shortcuts for drawing modes not accessible through toolbar
        self.obstacle_shortcut = QShortcut(QKeySequence("Alt+O"), self)
        self.obstacle_shortcut.activated.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.DRAW_OBSTACLE))
        
        self.staging_area_shortcut = QShortcut(QKeySequence("Alt+S"), self)
        self.staging_area_shortcut.activated.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.DEFINE_STAGING_AREA))
        
        self.pathfinding_bounds_shortcut = QShortcut(QKeySequence("Alt+B"), self)
        self.pathfinding_bounds_shortcut.activated.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.DEFINE_PATHFINDING_BOUNDS))
        
        self.pick_aisle_shortcut = QShortcut(QKeySequence("Alt+P"), self)
        self.pick_aisle_shortcut.activated.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.SET_START_POINT))
        
        self.staging_location_shortcut = QShortcut(QKeySequence("Alt+L"), self)
        self.staging_location_shortcut.activated.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.SET_END_POINT))
        
        self.aisle_line_shortcut = QShortcut(QKeySequence("Alt+A"), self)
        self.aisle_line_shortcut.activated.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.DEFINE_AISLE_LINE_START))
        
        self.staging_line_shortcut = QShortcut(QKeySequence("Alt+T"), self)
        self.staging_line_shortcut.activated.connect(lambda: self.pdf_viewer.set_mode(InteractionMode.DEFINE_STAGING_LINE_START))
        
        # F1 key for help
        self.help_shortcut = QShortcut(QKeySequence("F1"), self)
        self.help_shortcut.activated.connect(self._show_help)

    def _show_help(self):
        """Show help information, especially keyboard shortcuts"""
        help_text = """
<h3>Keyboard Shortcuts:</h3>
<table>
<tr><td><b>Ctrl+O</b></td><td>Open PDF</td></tr>
<tr><td><b>Ctrl+P</b></td><td>Open Project</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Save Project</td></tr>
<tr><td><b>Ctrl+Shift+S</b></td><td>Save Project As</td></tr>
<tr><td><b>Ctrl++</b></td><td>Zoom In</td></tr>
<tr><td><b>Ctrl+-</b></td><td>Zoom Out</td></tr>
<tr><td><b>Ctrl+0</b></td><td>Fit to View</td></tr>
<tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
<tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
<tr><td><b>P</b></td><td>Pan Mode</td></tr>
<tr><td><b>Esc</b></td><td>Cancel/Idle Mode</td></tr>
<tr><td><b>F1</b></td><td>Show Help</td></tr>
</table>
"""
        QMessageBox.information(self, "Keyboard Shortcuts", help_text)

    def keyPressEvent(self, event):
        """Handle key press events for better keyboard navigation"""
        # Pass key events to super class first for default processing
        super().keyPressEvent(event)
        
        # Check for keyboard navigation keys
        if event.key() == Qt.Key_Tab:
            # Handle tab navigation - this is mostly handled by Qt automatically
            pass
        elif event.key() == Qt.Key_Space and self.pdf_viewer.hasFocus():
            # Space key acts like a click when a button has focus
            focused_widget = QApplication.focusWidget()
            if isinstance(focused_widget, QPushButton):
                focused_widget.click()

    @Slot(str)
    def _handle_pdf_dropped(self, file_path):
        """Handle PDF file dropped onto the PDF viewer."""
        print(f"[MainWindow] PDF file dropped: {file_path}")
        self.status_progress.show_message(f"Loading dropped PDF: {file_path}", 3000)
        
        # Check for unsaved changes before loading new PDF
        if self.model.is_saveable and self.model.needs_save:
            reply = QMessageBox.question(
                self, 
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before loading a new PDF?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                # Try to save and handle the case if save fails
                if self.model.current_project_path:
                    saved = self.project_service.save_project(self.model, self.model.current_project_path)
                    if not saved:
                        return
                else:
                    # Show save dialog
                    saved = self._handle_save_project_as_action()
                    if not saved:
                        return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
            # If Discard, we continue with loading
        
        # Load the PDF using the existing method that handles everything correctly
        self._open_pdf_file(file_path)
        
    @Slot(list)
    def _handle_pick_aisles_reordered(self, new_order):
        """Handle reordering of pick aisles in the combo box."""
        print(f"[MainWindow] Pick aisles reordered: {new_order}")
        self.status_progress.show_message("Pick aisles order updated.", 3000)
        # For now, we just update the UI but don't change any model data
        # In a future version, we could implement an order preference in the model
        
    @Slot(list)
    def _handle_staging_locations_reordered(self, new_order):
        """Handle reordering of staging locations in the combo box."""
        print(f"[MainWindow] Staging locations reordered: {new_order}")
        self.status_progress.show_message("Staging locations order updated.", 3000)
        # For now, we just update the UI but don't change any model data
        # In a future version, we could implement an order preference in the model

    @Slot()
    def _toggle_search_panel(self):
        """Toggle the visibility of the search and filter panel"""
        if self.search_dock.isVisible():
            self.search_dock.hide()
            self.toggle_search_panel_action.setChecked(False)
        else:
            self.search_dock.show()
            self.toggle_search_panel_action.setChecked(True)
            
            # Update point comboboxes with current points when showing panel
            self.search_filter_panel.update_point_combos(
                self.model.pick_aisles,
                self.model.staging_locations
            )
    
    @Slot()
    def _handle_search_points(self, search_text, filter_options):
        """Handle search points request from the search panel"""
        results = self.search_service.search_points(
            self.model, 
            search_text, 
            filter_options
        )
    
    @Slot()
    def _handle_search_obstacles(self, search_text, filter_options):
        """Handle search obstacles request from the search panel"""
        results = self.search_service.search_obstacles(
            self.model, 
            search_text, 
            filter_options
        )
    
    @Slot()
    def _handle_search_paths(self, start_point, end_point, filter_options):
        """Handle search paths request from the search panel"""
        results = self.search_service.filter_paths(
            self.model, 
            start_point, 
            end_point, 
            filter_options,
            self.pathfinding_service
        )
    
    @Slot(list)
    def _handle_search_points_results(self, results):
        """Handle search points results from the search service"""
        self.search_filter_panel.display_results(results, 'points')
    
    @Slot(list)
    def _handle_search_obstacles_results(self, results):
        """Handle search obstacles results from the search service"""
        self.search_filter_panel.display_results(results, 'obstacles')
    
    @Slot(list)
    def _handle_search_paths_results(self, results):
        """Handle search paths results from the search service"""
        self.search_filter_panel.display_results(results, 'paths')
    
    
    
    def _highlight_selected_result(self):
        """Highlight the selected search result in the PDF viewer"""
        selected_items = self.search_filter_panel.results_list.selectedItems()
        if not selected_items:
            return
            
        result_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        if not result_data:
            return
            
        # Different handling based on result type
        if 'point_type' in result_data:
            # Point result
            point_name = result_data['name']
            if result_data['point_type'] == 'pick_aisle':
                self.pdf_viewer.highlight_point(point_name, PointType.PICK_AISLE)
            else:
                self.pdf_viewer.highlight_point(point_name, PointType.STAGING_LOCATION)
                
        elif 'polygon' in result_data:
            # Obstacle result
            obstacle_idx = result_data['id'] - 1  # Convert 1-based to 0-based
            self.pdf_viewer.highlight_obstacle(obstacle_idx, result_data['is_staging_area'])
            
        elif 'path_points' in result_data:
            # Path result
            self.pdf_viewer.highlight_path(result_data['path_points'])
    
    def _goto_selected_result(self):
        """Center the view on the selected search result"""
        selected_items = self.search_filter_panel.results_list.selectedItems()
        if not selected_items:
            return
            
        result_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        if not result_data:
            return
            
        # Different handling based on result type
        if 'position' in result_data:
            # Point result
            self.pdf_viewer.goto_scene_position(result_data['position'])
                
        elif 'polygon' in result_data:
            # Obstacle result - center on polygon centroid
            polygon = result_data['polygon']
            if not polygon.isEmpty():
                centroid = QPointF(0, 0)
                for i in range(polygon.size()):
                    centroid += polygon.at(i)
                centroid /= polygon.size()
                self.pdf_viewer.goto_scene_position(centroid)
            
        elif 'path_points' in result_data and result_data['path_points']:
            # Path result - center on middle point of path
            path_points = result_data['path_points']
            mid_idx = len(path_points) // 2
            self.pdf_viewer.goto_scene_position(path_points[mid_idx])
    
    # ... (rest of the code remains unchanged)

    def _handle_export_path_data(self):
        """Export current path data to CSV."""
        if not hasattr(self, '_last_calculated_path') or not self._last_calculated_path:
            QMessageBox.information(self, "Export Path Data", "No path is currently displayed. Calculate a path first.")
            return
            
        start_name = self.start_combo.currentText()
        end_name = self.end_combo.currentText()
        
        # Get file path using dialog
        default_name = f"{start_name}_to_{end_name}_path.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Path Data", default_name, "CSV (*.csv)"
        )
        
        if file_path:
            self.status_progress.show_message(f"Exporting path data to {file_path}...")
            self.status_progress.show_spinner(True)
            QApplication.processEvents()
            
            result = self.pathfinding_service.export_path_data_to_csv(
                self.model, start_name, end_name, file_path
            )
            
            self.status_progress.show_spinner(False)
            if result:
                self.status_progress.show_message(f"Path data exported to {file_path}", 3000)
            else:
                self.status_progress.show_message("Failed to export path data", 3000)
    
    def _handle_export_path_image(self):
        """Export current path as an image."""
        if not hasattr(self, '_last_calculated_path') or not self._last_calculated_path:
            QMessageBox.information(self, "Export Path Image", "No path is currently displayed. Calculate a path first.")
            return
            
        start_name = self.start_combo.currentText()
        end_name = self.end_combo.currentText()
        
        # Get file path using dialog
        default_name = f"{start_name}_to_{end_name}_path.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Path Image", default_name, "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        
        if file_path:
            self.status_progress.show_message(f"Exporting path image to {file_path}...")
            self.status_progress.show_spinner(True)
            QApplication.processEvents()
            
            # Create a title for the image
            title = f"Path from {start_name} to {end_name}"
            if hasattr(self, '_last_path_distance') and self._last_path_distance:
                title += f" - Distance: {self._last_path_distance:.2f} {self.model.display_unit}"
            
            result = self.pathfinding_service.export_path_image(
                self.model, self._last_calculated_path, file_path, 
                include_obstacles=True, title=title
            )
            
            self.status_progress.show_spinner(False)
            if result:
                self.status_progress.show_message(f"Path image exported to {file_path}", 3000)
            else:
                self.status_progress.show_message("Failed to export path image", 3000)
                
    def _handle_export_pdf_report(self):
        """Generate comprehensive PDF report with all analysis results."""
        if not self._last_analysis_detailed_results:
            QMessageBox.information(self, "Generate PDF Report", "No analysis results available. Run an analysis first.")
            return
        
        # Get file path using dialog
        default_name = "warehouse_analysis_report.pdf"
        if self._last_analysis_input_filename:
            default_name = f"{QFileInfo(self._last_analysis_input_filename).baseName()}_report.pdf"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Generate PDF Report", default_name, "PDF (*.pdf)"
        )
        
        if file_path:
            self.status_progress.show_message(f"Generating PDF report to {file_path}...")
            self.status_progress.show_spinner(True)
            QApplication.processEvents()
            
            try:
                self.analysis_service.export_to_pdf_report(
                    self._last_analysis_detailed_results,
                    self._last_analysis_unit or self.model.display_unit,
                    file_path
                )
                
                self.status_progress.show_spinner(False)
                self.status_progress.show_message(f"PDF report generated at {file_path}", 3000)
            except Exception as e:
                self.status_progress.show_spinner(False)
                QMessageBox.critical(self, "PDF Generation Error", f"Failed to generate PDF report: {e}")
                self.status_progress.show_message("Failed to generate PDF report", 3000)
                
    def _handle_export_layout(self):
        """Export the entire warehouse layout as an image."""
        if not self.model.current_pdf_path:
            QMessageBox.information(self, "Export Layout", "No PDF loaded. Load a warehouse layout first.")
            return
        
        # Get file path using dialog
        default_name = "warehouse_layout.png"
        if self.model.current_pdf_path:
            default_name = f"{QFileInfo(self.model.current_pdf_path).baseName()}_layout.png"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Layout", default_name, "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        
        if file_path:
            self.status_progress.show_message(f"Exporting layout to {file_path}...")
            self.status_progress.show_spinner(True)
            QApplication.processEvents()
            
            # Get the entire scene as an image
            try:
                # For more complex layouts, we'll capture the entire scene
                scene = self.pdf_viewer.scene()
                scene_rect = scene.sceneRect()
                image = QImage(scene_rect.width(), scene_rect.height(), QImage.Format.Format_ARGB32)
                image.fill(Qt.GlobalColor.white)
                
                painter = QPainter(image)
                scene.render(painter)
                painter.end()
                
                image.save(file_path)
                
                self.status_progress.show_spinner(False)
                self.status_progress.show_message(f"Layout exported to {file_path}", 3000)
            except Exception as e:
                self.status_progress.show_spinner(False)
                QMessageBox.critical(self, "Export Error", f"Failed to export layout: {e}")
                self.status_progress.show_message("Failed to export layout", 3000)

    def _handle_clear_obstacles_action(self):
        """Handler for clearing all obstacles with confirmation."""
        if not self.model.obstacles:
            self.status_progress.show_message("No obstacles to clear.", 3000)
            return

        confirm = QMessageBox.question(
            self, 
            "Confirm Clear Obstacles",
            f"Are you sure you want to clear all {len(self.model.obstacles)} obstacles?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            import commands  # Import locally to avoid circular imports
            command = commands.ClearObstaclesCommand(self.model)
            self.undo_stack.push(command)
            self.status_progress.show_message("All obstacles cleared.", 3000)
            
    def _handle_clear_staging_areas_action(self):
        """Handler for clearing all staging areas with confirmation."""
        if not self.model.staging_areas:
            self.status_progress.show_message("No staging areas to clear.", 3000)
            return

        confirm = QMessageBox.question(
            self, 
            "Confirm Clear Staging Areas",
            f"Are you sure you want to clear all {len(self.model.staging_areas)} staging areas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            import commands  # Import locally to avoid circular imports
            command = commands.ClearStagingAreasCommand(self.model)
            self.undo_stack.push(command)
            self.status_progress.show_message("All staging areas cleared.", 3000)

    def _handle_clear_pick_aisles_action(self):
        """Handler for clearing all pick aisles with confirmation."""
        if not self.model.pick_aisles:
            self.status_progress.show_message("No pick aisles to clear.", 3000)
            return

        confirm = QMessageBox.question(
            self, 
            "Confirm Clear Pick Aisles",
            f"Are you sure you want to clear all {len(self.model.pick_aisles)} pick aisles?\n"
            "This will also clear any precomputed path data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            import commands  # Import locally to avoid circular imports
            command = commands.ClearPickAislesCommand(self.model)
            self.undo_stack.push(command)
            self.status_progress.show_message("All pick aisles cleared.", 3000)

    def _handle_clear_staging_locations_action(self):
        """Handler for clearing all staging locations with confirmation."""
        if not self.model.staging_locations:
            self.status_progress.show_message("No staging locations to clear.", 3000)
            return

        confirm = QMessageBox.question(
            self, 
            "Confirm Clear Staging Locations",
            f"Are you sure you want to clear all {len(self.model.staging_locations)} staging locations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            import commands  # Import locally to avoid circular imports
            command = commands.ClearStagingLocationsCommand(self.model)
            self.undo_stack.push(command)
            self.status_progress.show_message("All staging locations cleared.", 3000)

    def _handle_clear_bounds_action(self):
        """Handler for clearing pathfinding bounds with confirmation."""
        if not self.model.user_pathfinding_bounds:
            self.status_progress.show_message("No pathfinding bounds to clear.", 3000)
            return

        confirm = QMessageBox.question(
            self, 
            "Confirm Clear Pathfinding Bounds",
            "Are you sure you want to clear the pathfinding bounds?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            import commands  # Import locally to avoid circular imports
            command = commands.ClearPathfindingBoundsCommand(self.model)
            self.undo_stack.push(command)
            self.status_progress.show_message("Pathfinding bounds cleared.", 3000)

    def _open_recent_file(self):
        """Open a file from the recent files menu."""
        action = self.sender()
        if action:
            file_path = action.data()
            if file_path:
                # Determine if PDF or project file
                if file_path.lower().endswith('.pdf'):
                    self._open_pdf_file(file_path)
                else:
                    self._open_project_file(file_path)
    
    def _update_all_ui_states(self):
        """Update all UI elements based on the current model state."""
        # Update menu and toolbar action states
        self._update_action_states()
        
        # Update spinbox values from model
        self._update_spinbox_values_from_model()
        
        # Update granularity label
        self._update_granularity_label()
        
        # Update window title
        self._update_window_title()
        
        # Update the combo boxes in the workflow panel
        self._update_combo_boxes()
        
        # Process events to ensure UI updates properly
        QApplication.processEvents()
        
    def _update_action_states(self):
        """Update the enabled/disabled state of all actions based on model state."""
        # File actions
        pdf_loaded = self.model.current_pdf_path is not None
        scale_set = self.model.is_scale_set
        can_calculate = self.model.can_calculate_paths
        can_analyze = self.model.can_analyze_or_animate
        
        # Enable/disable file-related actions
        if hasattr(self, 'save_project_action'):
            self.save_project_action.setEnabled(self.model.is_saveable)
        if hasattr(self, 'save_project_as_action'):
            self.save_project_as_action.setEnabled(self.model.is_saveable)
        
        # Enable/disable tool actions
        if hasattr(self, 'set_scale_action'):
            self.set_scale_action.setEnabled(pdf_loaded)
        if hasattr(self, 'draw_obstacle_action'):
            self.draw_obstacle_action.setEnabled(scale_set)
        if hasattr(self, 'define_staging_area_action'):
            self.define_staging_area_action.setEnabled(scale_set)
        if hasattr(self, 'define_bounds_action'):
            self.define_bounds_action.setEnabled(scale_set)
        if hasattr(self, 'set_start_point_action'):
            self.set_start_point_action.setEnabled(scale_set)
        if hasattr(self, 'set_end_point_action'):
            self.set_end_point_action.setEnabled(scale_set)
        if hasattr(self, 'define_aisle_line_action'):
            self.define_aisle_line_action.setEnabled(scale_set)
        if hasattr(self, 'define_staging_line_action'):
            self.define_staging_line_action.setEnabled(scale_set)
        
        # Enable/disable analysis actions
        if hasattr(self, 'precompute_paths_action'):
            self.precompute_paths_action.setEnabled(scale_set and (bool(self.model.pick_aisles) or bool(self.model.staging_locations)))
        if hasattr(self, 'analyze_picklist_action'):
            self.analyze_picklist_action.setEnabled(can_analyze)
        if hasattr(self, 'animate_picklist_action'):
            self.animate_picklist_action.setEnabled(can_analyze)
        if hasattr(self, 'view_last_analysis_action'):
            self.view_last_analysis_action.setEnabled(self._last_analysis_detailed_results is not None)
        if hasattr(self, 'export_last_analysis_action'):
            self.export_last_analysis_action.setEnabled(self._last_analysis_detailed_results is not None)
        
        # Update toolbar actions too
        if hasattr(self, 'toolbar_set_scale_action'):
            self.toolbar_set_scale_action.setEnabled(pdf_loaded)
        if hasattr(self, 'toolbar_precompute_paths_action'):
           self.toolbar_precompute_paths_action.setEnabled(scale_set and (bool(self.model.pick_aisles) or bool(self.model.staging_locations))) 
        if hasattr(self, 'toolbar_analyze_picklist_action'):
            self.toolbar_analyze_picklist_action.setEnabled(can_analyze)
        if hasattr(self, 'toolbar_animate_picklist_action'):
            self.toolbar_animate_picklist_action.setEnabled(can_analyze)
            
        # Update export actions
        if hasattr(self, 'export_path_data_action'):
            self.export_path_data_action.setEnabled(hasattr(self, '_last_calculated_path') and self._last_calculated_path is not None)
        if hasattr(self, 'export_path_image_action'):
            self.export_path_image_action.setEnabled(hasattr(self, '_last_calculated_path') and self._last_calculated_path is not None)
        if hasattr(self, 'export_layout_action'):
            self.export_layout_action.setEnabled(pdf_loaded)
            
        # Update clear actions
        if hasattr(self, 'clear_obstacles_action'):
            self.clear_obstacles_action.setEnabled(len(self.model.obstacles) > 0)
        if hasattr(self, 'clear_staging_areas_action'):
            self.clear_staging_areas_action.setEnabled(len(self.model.staging_areas) > 0)
        if hasattr(self, 'clear_pick_aisles_action'):
            self.clear_pick_aisles_action.setEnabled(len(self.model.pick_aisles) > 0)
        if hasattr(self, 'clear_staging_locations_action'):
            self.clear_staging_locations_action.setEnabled(len(self.model.staging_locations) > 0)
        if hasattr(self, 'clear_pathfinding_bounds_action'):
            self.clear_pathfinding_bounds_action.setEnabled(self.model.user_pathfinding_bounds is not None)

    def _update_spinbox_values_from_model(self):
        """Update UI spinbox values to match the model."""
        if hasattr(self, 'resolution_spinbox'):
            self.resolution_spinbox.setValue(self.model.grid_resolution_factor)
        if hasattr(self, 'penalty_spinbox'):
            self.penalty_spinbox.setValue(self.model.staging_area_penalty)
            
    def _update_granularity_label(self):
        """Update the granularity label with calculated grid dimensions."""
        if hasattr(self, 'granularity_label') and self.model.is_scale_set:
            # Calculate approximate grid dimensions based on PDF size
            if self.model.pdf_bounds and self.model.pdf_bounds.isValid():
                grid_w = round(self.model.pdf_bounds.width() / self.model.grid_resolution_factor)
                grid_h = round(self.model.pdf_bounds.height() / self.model.grid_resolution_factor)
                self.granularity_label.setText(f"Path Detail Granularity: ~{grid_w}x{grid_h} cells")
            else:
                self.granularity_label.setText("Path Detail Granularity: N/A")
        elif hasattr(self, 'granularity_label'):
            self.granularity_label.setText("Path Detail Granularity: N/A")
            
    def _update_window_title(self):
        """Update the window title based on the current model state."""
        title = "Warehouse Path Finder"
        
        if self.model.current_project_path:
            file_name = QFileInfo(self.model.current_project_path).fileName()
            title = f"{file_name} - {title}"
            
        elif self.model.current_pdf_path:
            file_name = QFileInfo(self.model.current_pdf_path).fileName()
            title = f"{file_name} - {title}"
            
        # Add indicator if there are unsaved changes
        if self.model.is_saveable and self.model.needs_save:
            title = f"*{title}"
            
        self.setWindowTitle(title)
        
    def _update_combo_boxes(self):
        """Update the start and end point combo boxes with the current points."""
        # Save current selections
        current_start = self.start_combo.currentText()
        current_end = self.end_combo.currentText()
        
        # Clear and repopulate with sorted items
        self.start_combo.clear()
        sorted_start_keys = sorted(self.model.pick_aisles.keys(), key=natural_sort_key)
        for name in sorted_start_keys:
            self.start_combo.addItem(name)
            
        self.end_combo.clear()
        sorted_end_keys = sorted(self.model.staging_locations.keys(), key=natural_sort_key)
        for name in sorted_end_keys:
            self.end_combo.addItem(name)
            
        # Restore selections if still available
        if current_start and current_start in self.model.pick_aisles:
            index = self.start_combo.findText(current_start)
            if index >= 0:
                self.start_combo.setCurrentIndex(index)
                
        if current_end and current_end in self.model.staging_locations:
            index = self.end_combo.findText(current_end)
            if index >= 0:
                self.end_combo.setCurrentIndex(index)
                
        # Update calculate button state
        self.calculate_button.setEnabled(
            self.start_combo.count() > 0 and 
            self.end_combo.count() > 0 and
            self.model.grid_is_valid
        )
        
    def _open_pdf_file(self, file_path):
        """Open a PDF file and set it in the model."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", f"The file {file_path} does not exist.")
            return
            
        # Reset the model first
        self.model.reset()
        
        # Attempt to load the PDF
        success, bounds = self.pdf_viewer.load_pdf(file_path)
        if success:
            # Set PDF path and bounds in the model
            self.model.set_pdf_path(file_path)
            if bounds:
                self.model.set_pdf_bounds(bounds)
                
            # Update UI state
            self.status_progress.show_message(f"Loaded PDF: {file_path}. Set scale next.", 5000)
            self._add_to_recent_files(file_path)
        else:
            QMessageBox.critical(self, "PDF Load Error", f"Failed to load PDF: {file_path}")
    
    def _add_to_recent_files(self, file_path):
        """Add a file to the recent files list."""
        recent_files = self.settings.value("recentFiles", [])
        if not isinstance(recent_files, list):
            recent_files = []
            
        # Remove file if it already exists
        if file_path in recent_files:
            recent_files.remove(file_path)
            
        # Add to the beginning of the list
        recent_files.insert(0, file_path)
        
        # Keep only the most recent files
        if len(recent_files) > MAX_RECENT_FILES:
            recent_files = recent_files[:MAX_RECENT_FILES]
            
        # Save the updated list
        self.settings.setValue("recentFiles", recent_files)
        
        # Update the menu
        self._update_recent_files_menu()
        
    def _update_recent_files_menu(self):
        """Update the recent files menu with the current list."""
        recent_files = self.settings.value("recentFiles", [])
        if not isinstance(recent_files, list):
            recent_files = []
            
        # Update the visibility of actions
        num_recent_files = min(len(recent_files), MAX_RECENT_FILES)
        
        for i in range(MAX_RECENT_FILES):
            if i < num_recent_files:
                file_path = recent_files[i]
                file_name = QFileInfo(file_path).fileName()
                self.recent_files_actions[i].setText(f"&{i+1} {file_name}")
                self.recent_files_actions[i].setData(file_path)
                self.recent_files_actions[i].setVisible(True)
            else:
                self.recent_files_actions[i].setVisible(False)
                
        # Enable/disable clear action based on whether there are any recent files
        self.clear_recent_action.setEnabled(num_recent_files > 0)
        
        # Show/hide the menu based on whether there are any recent files
        self.recent_files_menu.menuAction().setVisible(num_recent_files > 0)

    def _show_about_dialog(self):
        """Show the About dialog with application information."""
        from about_dialog import AboutDialog
        about_dialog = AboutDialog(self)
        about_dialog.exec()

    def _show_documentation(self):
        """Open documentation in the default web browser."""
        # Open documentation URL or local file
        docs_url = "https://example.com/warehouse-pathfinder/docs"  # Replace with actual docs URL
        webbrowser.open(docs_url)
        
    def _handle_pdf_bounds_set_in_model(self, bounds: QRectF):
        """Handler for when the PDF bounds are set in the model."""
        print(f"[MainWindow] PDF bounds set in model: {bounds}")
        # The PDF viewer is updated when the PDF path changes, so we don't need to do that here
        # Just update UI states to reflect the new bounds
        self._update_all_ui_states()
        
    def _handle_grid_parameters_changed_in_model(self):
        """Handler for when grid parameters change in the model."""
        self._update_spinbox_values_from_model()  # Ensure UI reflects model
        self._update_granularity_label()
        
        # Update grid dimensions if available
        if self.model.pathfinding_grid is not None:
            grid_h, grid_w = self.model.pathfinding_grid.shape
            self.workflow_panel.update_grid_dimensions(grid_w, grid_h)
            
        self._update_all_ui_states()  # Actions might depend on this

    def _handle_grid_update_started(self):
        """Handle the signal that the grid update process has started."""
        self.status_progress.show_message("Updating pathfinding grid...")
        self.status_progress.show_spinner(True)
        self._update_all_ui_states()  # Disable actions during grid update
        
    @Slot(bool)
    def _handle_grid_update_finished(self, success: bool):
        if success:
            self.status_progress.show_message("Grid updated successfully!", 3000)
            # Update grid dimensions in the workflow panel
            if self.model.pathfinding_grid is not None:
                grid_h, grid_w = self.model.pathfinding_grid.shape
                self.workflow_panel.update_grid_dimensions(grid_w, grid_h)
        else:
            self.status_progress.show_message("Grid update failed.", 3000)
        self.status_progress.show_spinner(False)
        self._update_all_ui_states()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())