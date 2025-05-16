# Warehouse Path Finder

## Introduction

The Warehouse Path Finder is a desktop application designed to assist warehouse managers and logistics analysts in optimizing warehouse operations. It enables users to:

*   Visualize warehouse layouts from PDF floor plans.
*   Define crucial layout features like obstacles, pick-up locations (Pick Aisles), and drop-off points (Staging Locations), including special zones like Staging Areas with travel penalties.
*   Calculate optimal (shortest) paths between defined locations using pathfinding algorithms.
*   Analyze the efficiency of historical or simulated picklists based on travel distances.
*   Visualize warehouse activity and traffic flow over time through picklist animation.

The application is built using Python and the PySide6 (Qt6) framework, featuring an intuitive, accessible user interface with theme support and streamlined workflows.

## Core Features

*   **PDF Layout Visualization:**
    *   Load, display, zoom, and pan warehouse floor plans from PDF files.
    *   Support for drag-and-drop PDF loading.
    *   Enhanced zoom controls with percentage indicator and fit options (fit to view, width, height).
*   **Layout Scaling & Units:**
    *   Set real-world scale by calibrating a known distance on the PDF (in meters or feet).
    *   Display all calculated distances in user-selected units (meters or feet).
*   **Interactive Layout Definition:**
    *   **Obstacles:** Draw polygonal impassable obstacles (e.g., racks, machinery).
    *   **Staging Areas:** Define polygonal areas where travel is discouraged (configurable cost penalty).
    *   **User-Defined Pathfinding Bounds (Optional):** Draw a specific polygonal area to constrain pathfinding calculations, potentially speeding up precomputation for large PDFs with localized layouts.    
    *   **Pick Aisles:** Define named start points for path calculations.
    *   **Staging Locations:** Define named end points for path calculations.
    *   **Line-Based Point Generation:** Quickly generate series of named points along a drawn line (e.g., for defining multiple aisles or dock doors).
    *   **Edit Layout:** Select, move, or delete defined obstacles, staging areas, and points.
    *   **Improved Interaction Toolbar:** Visual toolbar with mode-specific buttons for drawing and editing operations.
*   **Pathfinding:**
    *   **Grid Representation:** Generates a configurable 2D grid. The grid can be cropped to the relevant layout area (user-defined bounds or auto-calculated from elements) for improved performance.
    *   **Dijkstra-Based Precomputation:** Precomputes shortest paths from all defined Pick Aisles to all reachable grid cells using Dijkstra's algorithm (parallelized with `multiprocessing` for speed).
    *   **Single Path Calculation:** Calculates and displays the shortest path and its physical distance between a selected Pick Aisle and Staging Location using precomputed data.
    *   **Accurate Distance:** Physical distances are measured along the path segments, accounting for the actual route taken, even through staging areas.
*   **Picklist Analysis:**
    *   **CSV Import:** Import picklist data from CSV files with configurable column mapping for Pick ID, Start/End Locations, and Start/End Times.
    *   **Distance Calculation:** Calculates the shortest path distance for each picklist item using the precomputed path data.
    *   **Results & Visualization:** Displays analysis results including summary statistics (total distance, average, min/max) and a histogram of pick distances. Results are filterable by date.
    *   **CSV Export:** Export analysis results, including calculated distances, to a new CSV file.
*   **Picklist Animation:**
    *   **Timed CSV Import:** Import picklist data with timestamps for animating operations.
    *   **Playback Controls:** Animate picks with controls for play/pause, reset, and speed adjustment.
    *   **Visualization Modes:**
        *   **Carts:** Shows moving rectangles ("carts") traversing their calculated paths. Cart dimensions are configurable.
        *   **Path Lines:** Progressively draws path lines as picks occur. Lines can be configured to fade or persist and are color-coded by start location cluster to visualize traffic patterns.
    *   **Filtering:** Filter animations by date and start/end location clusters.
*   **Project Management:**
    *   **Save/Load:** Save the entire project state (PDF reference, scale, all layout definitions including user pathfinding bounds, settings) to a JSON-based project file (`.whp`) and load it back.
    *   **Recent Files:** Quick access to recently opened files through the File menu.
*   **Enhanced UI Features:**
    *   **Workflow Panel:** Guided workflow interface with status indicators for each step (PDF loading, scale setting, precomputation, path calculation).
    *   **Theme Support:** Toggle between light and dark themes with consistent styling across all components.
    *   **Preferences:** Configurable UI settings for display options and application behavior.
    *   **Search & Filter:** Find and highlight specific points, obstacles, or paths based on various criteria.
    *   **Status Bar Progress:** Visual feedback on operations with text messages, progress bars, and spinner indicators.
*   **Accessibility Improvements:**
    *   **Keyboard Navigation:** Optimized tab order and keyboard shortcuts for all operations.
    *   **Screen Reader Support:** Compatible with screen readers for visually impaired users.
    *   **High Contrast Mode:** Optional high contrast visual theme for better readability.
    *   **Alternative Input Methods:** Support for various input devices beyond mouse and keyboard.

## Technical Architecture (v2.1)

The application follows a Model-View-Controller (MVC) pattern augmented with Service Layers and enhanced UI components:

*   **Model (`model.py`):** `WarehouseModel` class centralizes all application data (layout, settings, derived path data) and emits signals on changes.
*   **View Components:**
    *   **PDF Viewer (`pdf_viewer.py`):** Handles PDF display and drawing interactions.
    *   **Workflow Panel (`workflow_panel.py`):** Provides structured workflow guidance.
    *   **Interaction Toolbar (`pdf_viewer_interaction_toolbar.py`):** Manages drawing and editing modes.
    *   **Search Filter Panel (`search_filter_panel.py`):** Enables element searching and filtering.
    *   **Status Bar Progress (`status_bar_progress.py`):** Provides operation feedback.
    *   **Dialogs:** Manage specific user inputs and results display.
*   **Controller/Presenter (`main.py`):** `MainWindow` orchestrates UI events, interacts with services, and updates the View based on Model/Service feedback.
*   **Services (`services.py`):** Encapsulate business logic:
    *   `ProjectService`: Project file I/O.
    *   `PathfindingService`: Grid generation, Dijkstra precomputation, path calculation.
    *   `AnalysisService`: Picklist analysis logic and CSV processing.
    *   `AnimationService`: Animation data preparation.
    *   `SearchService`: Element searching and filtering.
*   **UI Enhancement Components:**
    *   `ThemeManager`: Manages application-wide theming.
    *   `PreferencesManager`: Handles user preferences settings.
    *   `AccessibilityUtils`: Provides accessibility improvement utilities.
*   **Pathfinding Logic (`pathfinding.py`):** Core algorithms (grid creation, Dijkstra).
*   **Enums (`enums.py`):** Defines shared enumerations like `InteractionMode`.

## Core Libraries Used

*   **Python:** 3.9+
*   **PySide6:** For the Qt6 graphical user interface.
*   **PyMuPDF (fitz):** For PDF rendering and handling.
*   **NumPy:** For efficient numerical operations, especially grid-based pathfinding.
*   **SciPy:** For image processing tasks like obstacle dilation.
*   **Matplotlib:** For generating histograms in the analysis results.
*   **Standard Libraries:** `csv`, `json`, `datetime`, `multiprocessing`.

## Setup and Running

1.  **Prerequisites:**
    *   Python 3.9 or newer.
    *   Ensure `pip` (Python package installer) is available.

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    *   Use the provided `requirements.txt` file:
        ```bash
        pip install -r requirements.txt
        ```

4.  **Run the Application:**
    *   Execute the main script from the project's root directory:
        ```bash
        python main.py
        ```

## Key Files

*   **Core Components:**
    *   `main.py`: Main application window, controller logic.
    *   `model.py`: `WarehouseModel` class for application data.
    *   `services.py`: Houses services for project, pathfinding, analysis, animation, and search.
    *   `pathfinding.py`: Core pathfinding algorithms (grid creation, Dijkstra).
    *   `enums.py`: Defines application-wide enumerations.

*   **UI Components:**
    *   `pdf_viewer.py`: Custom `QGraphicsView` for PDF display and interactive drawing.
    *   `workflow_panel.py`: Guided workflow interface component.
    *   `pdf_viewer_interaction_toolbar.py`: Drawing and editing mode toolbar.
    *   `search_filter_panel.py`: Search and filter interface component.
    *   `status_bar_progress.py`: Enhanced status bar with progress indicators.

*   **UI Enhancement:**
    *   `theme_manager.py`: Theme management component.
    *   `preferences_manager.py`: User preferences component.
    *   `accessibility_utils.py`: Accessibility utilities.

*   **Dialogs:**
    *   `analysis_results_dialog.py`: For displaying analysis results.
    *   `animation_control_dialog.py`: For controlling animations.
    *   `animation_picklist_dialog.py`: For animation setup.
    *   `picklist_column_dialog.py`: For CSV column mapping.
    *   `line_definition_dialog.py`: For line-based point generation.
    *   `preferences_dialog.py`: For user preferences.
    *   `project_settings_dialog.py`: For project-specific settings.
    *   `about_dialog.py`: Application information dialog.

*   **Support Files:**
    *   `requirements.txt`: Python package dependencies.
    *   Documentation files: `README.md`, `Architecture.md`, `Design_Document.md`, `User_Documentation.md`.

## Using the Application (Quick Start)

1.  **File > Open PDF...**: Load your warehouse floor plan (or drag-and-drop a PDF file onto the application).
2.  **Set Scale**: Click the "Set Scale" button in the Workflow Panel, draw a line of known distance, then enter the real-world value.
3.  **Define Layout**: Use the Interaction Toolbar to draw obstacles, staging areas, and place pick/staging points.
4.  **(Optional) Define Bounds**: Use the Interaction Toolbar to define pathfinding bounds for improved performance.
5.  **Precompute Paths**: Click the "Precompute Paths" button in the Workflow Panel after any layout changes.
6.  **Calculate Path**: Select start/end points in the Workflow Panel and click "Calculate Path" to see a route.
7.  **Analyze/Animate**: Use the toolbar buttons or Tools menu for picklist analysis and animation.
8.  **Save Project**: Use File > Save Project to preserve your work.

## Keyboard Shortcuts

*   **File Operations:**
    *   `Ctrl+O`: Open PDF
    *   `Ctrl+R`: Open Project
    *   `Ctrl+S`: Save Project
    *   `Ctrl+Shift+S`: Save Project As

*   **View Controls:**
    *   `Ctrl++`: Zoom In
    *   `Ctrl+-`: Zoom Out
    *   `Ctrl+0`: Fit to View

*   **Edit Operations:**
    *   `Ctrl+Z`: Undo
    *   `Ctrl+Y`: Redo

*   **Tools:**
    *   `Ctrl+L`: Set Scale
    *   `Ctrl+P`: Precompute Paths
    *   `Ctrl+T`: Analyze Picklist
    *   `Ctrl+I`: Animate Picklist

*   **Drawing Modes:**
    *   `Alt+O`: Draw Obstacle
    *   `Alt+S`: Draw Staging Area
    *   `Alt+B`: Define Pathfinding Bounds
    *   `Alt+P`: Place Pick Aisle
    *   `Alt+L`: Place Staging Location
    *   `Alt+A`: Define Aisle Line
    *   `Alt+T`: Define Staging Line

*   **Other:**
    *   `Ctrl+,`: Preferences
    *   `F1`: Help

## Troubleshooting Tips

*   **PDF Issues:** Ensure PDF is not corrupted or password-protected. `PyMuPDF` must be installed.
*   **Pathfinding Problems:**
    *   Ensure scale is set correctly *before* defining elements or pathfinding.
    *   Make sure Pick Aisles/Staging Locations are not inside obstacles.
    *   Run "Precompute All Paths" after any layout changes.
    *   If using "Define Pathfinding Bounds", ensure it encompasses all your pick/staging points and allows reasonable routes between them.
    *   Adjust grid resolution in Project Settings for a trade-off between path precision and computation speed.
*   **CSV Import Errors:**
    *   Verify standard CSV format. Use column selection dialogs to map headers correctly.
    *   Ensure date/time formats are supported (e.g., `YYYY-MM-DD HH:MM:SS`, `MM/DD/YYYY HH:MM`).
*   **Animation Performance:** For large datasets, use date/cluster filters in the Animation Controls. A higher grid resolution can also improve performance.
*   **UI Issues:**
    *   If the theme appears inconsistent, try toggling dark/light mode.
    *   Reset preferences to default if customizations cause display problems.
    *   Check the Status Bar for error messages or operation status.

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file (if available) or:

1.  **Fork** the repository.
2.  Create a **feature branch**.
3.  Make your changes.
4.  Submit a **pull request** with a clear description.

Please adhere to existing code style and add tests for new features.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details. 