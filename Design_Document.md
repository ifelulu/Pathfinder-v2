## Warehouse Path Finder - Design Document

**Version:** 2.1 (Updated with UI Improvements)

**1. Introduction & System Overview**

The Warehouse Path Finder is a Python desktop application using the PySide6 (Qt6) framework. It enables warehouse managers and logistics planners to optimize warehouse operations by:
*   Visualizing warehouse layouts from PDF floor plans.
*   Defining layout features: obstacles, pick aisles, staging locations, staging areas with travel penalties, **and optional user-defined pathfinding boundaries**.
*   Calculating optimal (shortest) paths between defined locations using Dijkstra's algorithm **on a potentially cropped grid for efficiency**.
*   Calculating optimal (shortest) paths between defined locations using Dijkstra's algorithm.
*   Analyzing picklist efficiency based on travel distances.
*   Animating warehouse activity over time based on timed picklists.

The application now features a redesigned, user-friendly interface with improved accessibility, theme options, and streamlined workflows.

**2. Architectural Pattern: MVC + Services + Enhanced UI Components**

The application employs a Model-View-Controller (MVC) pattern enhanced with Service Layers and specialized UI components to promote modularity, maintainability, testability, and user experience.

*   **Model (`model.py`):**
    *   `WarehouseModel`: The central data repository holding project state, layout definitions (including **user-defined pathfinding bounds**), pathfinding results (including **grid origin in PDF coordinates**), and settings.
    *   Emits Qt signals upon data changes to notify other components.
    *   Does not contain complex business logic.
*   **View Components:**
    *   **PDF Viewer (`pdf_viewer.py`):** Custom `QGraphicsView` for rendering PDFs, displaying layout elements (obstacles, points, paths, **user pathfinding bounds**), handling drawing interactions (managed by `InteractionMode`, now including `DEFINE_PATHFINDING_BOUNDS`), and showing animations. Features enhanced zoom controls with percentage display and fit options.
    *   **Workflow Panel (`workflow_panel.py`):** Provides a structured, step-by-step interface with status indicators for each workflow stage (PDF loading, scale setting, precomputation, path calculation).
    *   **Interaction Toolbar (`pdf_viewer_interaction_toolbar.py`):** Visual toolbar with mode selection buttons showing the current active drawing/editing mode.
    *   **Search Filter Panel (`search_filter_panel.py`):** Dock widget enabling searching and filtering of warehouse elements (points, obstacles, paths) with results highlighting.
    *   **Status Bar Progress (`status_bar_progress.py`):** Enhanced status bar with text messages, progress bars, and spinner indicators for operation feedback.
    *   **Dialogs:** Provide specialized UIs for tasks like CSV column selection (`PicklistColumnDialog`), analysis results (`AnalysisResultsDialog`), animation control (`AnimationControlDialog`), preferences (`PreferencesDialog`), and project settings (`ProjectSettingsDialog`).
*   **Controller/Presenter (`main.py`):**
    *   `MainWindow`: Orchestrates the application flow.
    *   Initializes Model, Services, and View components.
    *   Connects user actions (menu clicks, button presses) to Service methods or Model updates.
    *   Updates the View in response to signals from the Model and Services.
    *   Manages keyboard shortcuts and accessibility features.
*   **Services (`services.py`):**
    *   Encapsulate domain-specific business logic, operating on the `WarehouseModel`.
    *   May modify the Model or emit signals for progress/completion.
    *   **Key Services:**
        *   `ProjectService`: Handles project file saving/loading (JSON format, now includes **user pathfinding bounds**).
        *   `PathfindingService`: Manages grid creation (calculating effective bounds, determining grid origin, calling low-level rasterization), path precomputation (Dijkstra via `multiprocessing` on the potentially cropped grid), path retrieval, and distance calculation (accounting for grid origin).
        *   `AnalysisService`: Processes picklist CSVs, calculates distances, generates statistics, and handles results export.
        *   `AnimationService`: Prepares timed picklist data for visualization.
        *   `SearchService`: Handles searching and filtering of warehouse elements.
*   **UI Enhancement Components:**
    *   **Theme Manager (`theme_manager.py`):** Manages application-wide theming with light/dark mode options.
    *   **Preferences Manager (`preferences_manager.py`):** Handles user preferences for UI settings and behavior.
    *   **Accessibility Utils (`accessibility_utils.py`):** Provides utilities for improving application accessibility.
*   **Core Logic (`pathfinding.py`):**
    *   Contains low-level pathfinding algorithms (grid generation from obstacles using a **grid origin** for coordinate transformation, Dijkstra implementation, path reconstruction) utilized by `PathfindingService`.
*   **Shared Enums (`enums.py`):**
    *   Defines common enumerations (`InteractionMode` - now with `DEFINE_PATHFINDING_BOUNDS`, `PointType`, `AnimationMode`).

**3. High-Level Component Interaction (See `Architecture.txt` for Diagram)**

User actions in the View (`MainWindow`, `PdfViewer`, Dialogs) trigger methods in the Controller (`MainWindow`). The Controller invokes methods on the appropriate Service. Services interact with the `WarehouseModel` to retrieve or update data and perform calculations (potentially using `pathfinding.py`). The `WarehouseModel` emits signals upon data change. Both the Controller and View components listen to these signals to update the UI accordingly.

**4. Data Flow Examples (See `Architecture.txt` for detailed flows)**

*   **Adding an Obstacle:** User draws -> `PdfViewer` emits signal -> `MainWindow` calls `model.add_obstacle()` -> `Model` updates & emits `layout_changed` -> `MainWindow`/`PdfViewer` update UI/redraw.
*   **Calculating Path:** User selects points & clicks button -> `MainWindow` calls `pathfinding_service.get_shortest_path()` -> `Service` retrieves/computes path from `Model` data -> `Service` returns result -> `MainWindow` calls `pdf_viewer.draw_path()` and updates status.

**5. Key Design Principles**

*   **Single Responsibility Principle (SRP):** Each class has a focused responsibility.
*   **Separation of Concerns (SoC):** Data, UI, and logic are distinctly separated.
*   **Loose Coupling:** Components interact via signals and defined interfaces.
*   **Testability:** Model and Service layers are more easily testable in isolation.

**6. Core Libraries & Technologies**

*   **Language:** Python 3.9+
*   **UI:** PySide6 (Qt6)
*   **PDF Handling:** PyMuPDF (fitz)
*   **Numerical Computation:** NumPy
*   **Image Processing:** SciPy (e.g., obstacle dilation)
*   **Plotting:** Matplotlib (for analysis histograms)
*   **Standard Libraries:** `csv`, `json`, `datetime`, `multiprocessing`

**7. Project Structure**

*   `main.py`: Main application entry point, `MainWindow` controller.
*   `model.py`: `WarehouseModel` data store.
*   `services.py`: Business logic services.
*   `pdf_viewer.py`: Core visualization component.
*   `pathfinding.py`: Pathfinding algorithms.
*   `enums.py`: Shared enumerations.
*   `*.py` (Dialogs): Specific UI dialogs.
*   `requirements.txt`: Dependencies.
*   `README.md`: Project overview and user guide.
*   `Architecture.md`: Detailed architecture description (source for this document).
*   `Test/`: Directory for unit/integration tests (structure TBD).

**8. UI Workflow Design**

The redesigned interface guides users through a logical workflow:

1. **Project Setup Phase:**
   * Load PDF via Workflow Panel or File menu (supports drag-and-drop)
   * Set scale using dedicated button in Workflow Panel
   * Define warehouse elements using the Interaction Toolbar

2. **Layout Definition Phase:**
   * Draw obstacles and staging areas using Interaction Toolbar
   * Place pick aisles and staging locations using Interaction Toolbar
   * Define optional pathfinding bounds to optimize calculations

3. **Pathfinding Phase:**
   * Precompute paths using the Workflow Panel button
   * Select start/end points and calculate paths in Workflow Panel
   * Visualize results in the PDF Viewer

4. **Analysis Phase:**
   * Analyze picklists through dedicated menu/toolbar options
   * View results in enhanced Analysis Results Dialog
   * Export data or generate reports through Export menu

5. **Animation Phase:**
   * Set up animation through dedicated menu/toolbar options
   * Control playback through improved Animation Control Dialog
   * Filter and visualize warehouse operations over time

Each phase includes visual feedback through the Status Bar Progress component, and users can customize their experience through the Preferences Dialog.

**9. New UI Components in Detail**

*   **Workflow Panel:**
    * Provides visual guidance through application workflow
    * Status indicators show completion state of each step
    * Groups related controls logically (PDF loading, scale setting, precomputation, path calculation)
    * Updates status based on model signals

*   **PdfViewer Interaction Toolbar:**
    * Replaces scattered drawing mode buttons with a unified toolbar
    * Visual indicators show current active mode
    * Mode buttons organized by function (drawing tools, editing tools, point placement)
    * Cancel button to exit current drawing operation

*   **Search Filter Panel:**
    * Enables searching for warehouse elements by name, location, or properties
    * Filtering options for specific element types
    * Results list with highlight and goto functions
    * Designed as a dock widget that can be shown/hidden as needed

*   **Theme Manager:**
    * Toggle between light and dark themes
    * Consistent color schemes across all UI components
    * Theme persistence between sessions
    * Improved visual contrast and readability

*   **Preferences Manager:**
    * User-configurable UI settings
    * Options for display preferences, behavior, and accessibility
    * Settings persistence between sessions
    * Apply changes immediately or restore defaults

*   **Status Bar Progress:**
    * Enhanced status messages with appropriate timeout
    * Progress bars for long-running operations
    * Spinner indicators for background processes
    * Consistent visual feedback throughout the application

**10. Accessibility Improvements**

*   **Keyboard Navigation:**
    * Tab order optimized for logical workflow
    * Keyboard shortcuts for common operations
    * Focus indicators for keyboard navigation
    * Arrow key navigation for PDF viewer

*   **Visual Accessibility:**
    * High contrast mode option
    * Configurable font sizes
    * Screen reader compatibility with proper ARIA attributes
    * Color schemes tested for color blindness compatibility

*   **Input Methods:**
    * Support for alternative input devices
    * Mouse-free operation possible through keyboard shortcuts
    * Touch-friendly UI elements where appropriate

**11. Future UI Enhancements**

*   **Data Visualization Dashboard:** Add interactive charts and metrics for warehouse optimization.
*   **Customizable Layouts:** Allow users to rearrange panels and toolbars.
*   **Guided Tutorials:** Interactive tutorials for new users.
*   **Notification System:** Toast notifications for background processes and alerts.
*   **Context-Sensitive Help:** Integrated help system with searchable documentation.
*   **Touch Optimization:** Enhance touch support for tablet use in warehouses. 