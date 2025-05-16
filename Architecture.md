# Warehouse Path Finder - System Architecture (v2.1)

## 1. System Overview

The Warehouse Path Finder is a desktop application built with Python and PySide6 (Qt) that allows warehouse managers and logistics planners to visualize warehouse layouts, calculate optimal paths between locations, analyze picklists, and animate warehouse operations over time. The application handles PDF floor plans, user-defined obstacles, pick points, staging areas, and applies pathfinding algorithms to optimize warehouse operations.

This document describes the architecture after significant refactoring and UI improvements aimed at enhancing user experience, accessibility, and visual clarity while maintaining a clean separation of concerns.

## 2. Architectural Pattern

The application follows a **Model-View-Controller (MVC)** pattern, augmented with **Service Layers** to encapsulate complex business logic and enhanced **UI Components** for better user experience.

*   **Model (`model.py`):** `WarehouseModel` class.
    *   Centralizes all application data (project state, layout definitions, settings).
    *   Emits Qt signals when data changes, allowing other components to react.
    *   Does not contain business logic for processing or transforming data (that's for services).
*   **View Components:**
    *   **PDF Viewer (`pdf_viewer.py`):** Displays the warehouse layout, obstacles, points, paths, and animations. Manages graphical items and user drawing interactions. Uses an `InteractionMode` enum.
    *   **Workflow Panel (`workflow_panel.py`):** Provides a structured, step-by-step interface for common operations, with status indicators for each workflow step.
    *   **Interaction Toolbar (`pdf_viewer_interaction_toolbar.py`):** Provides visual access to drawing and editing modes with feedback on the current active mode.
    *   **Search Filter Panel (`search_filter_panel.py`):** Enables searching and filtering of warehouse elements (points, obstacles, paths).
    *   **Status Bar Progress (`status_bar_progress.py`):** Displays operation progress with text messages, progress bars, and spinner indicators.
    *   **Dialogs:** Provide specialized interfaces for tasks like column selection, parameter input, and results display.
*   **Controller/Presenter (`main.py` - `MainWindow`):**
    *   Orchestrates the application.
    *   Initializes the Model, Services, and UI components (View).
    *   Connects user actions from the View (e.g., menu clicks, button presses) to appropriate methods in the Service layers or directly to the Model for simple state changes.
    *   Listens to signals from the Model and Services to update the View (e.g., refresh comboboxes, update status bar, draw paths).
*   **Services (`services.py`):**
    *   Encapsulate distinct domains of business logic.
    *   Operate on data from the `WarehouseModel` and may return results or modify the model (usually via dedicated model methods if complex).
    *   Can emit signals for long-running tasks (e.g., progress, completion).
    *   **Components:**
        *   `ProjectService`: Handles saving and loading project files (JSON).
        *   `PathfindingService`: Manages grid creation, pathfinding algorithms (Dijkstra), path precomputation (including multiprocessing), and physical distance calculations.
        *   `AnalysisService`: Processes picklist CSV files for analysis, calculates distances, and handles results export.
        *   `AnimationService`: Prepares data from timed picklists for animation, including time normalization and path retrieval.
        *   `SearchService`: Handles searching and filtering of warehouse elements.
*   **UI Enhancement Components:**
    *   **Theme Manager (`theme_manager.py`):** Manages application-wide theming (light/dark modes) with consistent color schemes.
    *   **Preferences Manager (`preferences_manager.py`):** Handles user preferences for UI settings, display options, and behavior.
    *   **Accessibility Utils (`accessibility_utils.py`):** Provides utilities for improving application accessibility.

## 3. High-Level Component Diagram

```
                               +-----------------+
                               |   MainWindow    |
                               | (Controller/UI) |
                               +--------+--------+
                                        |
        +-------------------------------+-------------------------------+
        |                               |                               |
+-------v-------+              +--------v--------+              +-------v-------+
|  UI Components|              |  WarehouseModel |              | UI Enhancement|
|  - PdfViewer  |<-------------|  (Data State)   |------------->| - ThemeManager|
|  - WorkflowPnl|              +--------+--------+              | - PrefManager |
|  - SearchPanel|                       ^                       | - AccessUtils |
|  - StatusBar  |                       | (Data Access, Signals)| - Dialogs     |
+---------------+                       |                       +---------------+
                                        |
                           +------------+-------------+
                           |    Service Layer         |
                           | (`services.py`)          |
                           |                          |
                           |  - ProjectService        |
                           |  - PathfindingService    |
                           |  - AnalysisService       |
                           |  - AnimationService      |
                           |  - SearchService         |
                           +--------------------------+
                                        |
                                        | (Utilizes core algorithms)
                                        |
                             +----------v-----------+
                             | Pathfinding Logic    |
                             | (`pathfinding.py`)   |
                             | - Grid Generation    |
                             | - Dijkstra           |
                             +----------------------+
```


## 4. Component Design Details

### 4.1 `WarehouseModel` (`model.py`)
    *   **Purpose:** Central data store.
    *   **Key Data:** PDF path/bounds, scale info, obstacles, staging areas, user-defined pathfinding bounds polygon, pick aisles, staging locations, grid parameters, cart dimensions, derived pathfinding grid/maps, grid origin (PDF coordinates), validity flags.
    *   **Key Signals:** `pdf_path_changed`, `scale_changed`, `layout_changed` (covers user bounds changes), `points_changed`, `grid_parameters_changed`, `project_loaded`, `model_reset`, `grid_invalidated`.

### 4.2 `MainWindow` (`main.py`)
    *   **Purpose:** Application entry point, UI orchestration, event handling.
    *   **Responsibilities:**
        *   Initializes `WarehouseModel`, all services, UI components, and enhancement layers.
        *   Connects UI actions to service calls or model updates.
        *   Updates UI elements based on signals from model/services.
        *   Manages the overall application lifecycle, including undo/redo functionality.
        *   Handles keyboard shortcuts and accessibility features.

### 4.3 `PdfViewer` (`pdf_viewer.py`)
    *   **Purpose:** Visual display and interaction with the warehouse layout.
    *   **Responsibilities:** PDF rendering, drawing tools (scale, obstacles, areas, pathfinding bounds, points), path visualization, animation overlay, mouse/keyboard event handling for interactions. Uses `InteractionMode` enum. Emits signals for user drawing actions.
    *   **Enhancements:** Zoom controls with percentage indicator, fit options (view, width, height), improved mouse interaction, and keyboard navigation.

### 4.4 `WorkflowPanel` (`workflow_panel.py`)
    *   **Purpose:** Provides a structured, step-by-step interface for common operations.
    *   **Features:** Status indicators for each workflow step (PDF loading, scale setting, precomputation), logical action grouping, and visual progress tracking.
    *   **Signals:** Emits signals for point reordering and workflow step completion.

### 4.5 `PdfViewerInteractionToolbar` (`pdf_viewer_interaction_toolbar.py`)
    *   **Purpose:** Provides visual access to drawing and editing modes.
    *   **Features:** Visual feedback on current active mode, mode buttons with intuitive icons, and cancel operation button.
    *   **Signals:** Emits signals for mode changes and operation cancellation.

### 4.6 `SearchFilterPanel` (`search_filter_panel.py`)
    *   **Purpose:** Enables searching and filtering of warehouse elements.
    *   **Features:** Search for points, obstacles, and paths with various filter options.
    *   **Signals:** Emits signals for search requests and result selection.

### 4.7 `StatusBarProgress` (`status_bar_progress.py`)
    *   **Purpose:** Displays operation progress in the status bar.
    *   **Features:** Text messages, progress bars, and spinner indicators.
    *   **Methods:** `show_message()`, `show_progress()`, `show_spinner()`, `update_progress()`.

### 4.8 `ThemeManager` (`theme_manager.py`)
    *   **Purpose:** Manages application-wide theming.
    *   **Features:** Light/dark mode switching, consistent color schemes, and persistent theme settings.
    *   **Signals:** Emits signals for theme changes.

### 4.9 `PreferencesManager` (`preferences_manager.py`)
    *   **Purpose:** Handles user preferences for UI settings.
    *   **Features:** Configurable settings for display options and application behavior.
    *   **Methods:** `show_preferences_dialog()`, `apply_preferences()`, `save_preferences()`, `load_preferences()`.

### 4.10 `Dialogs` (various `.py` files)
    *   **Purpose:** Specialized UI for specific tasks.
    *   **Examples:** `AnalysisResultsDialog`, `AnimationControlDialog`, `PicklistColumnDialog`, `LineDefinitionDialog`, `PreferencesDialog`, `ProjectSettingsDialog`.
    *   **Responsibilities:** Gather user input, display specific information/results, with enhanced visual design and accessibility features.

### 4.11 `Services` (from `services.py`)
    *   All services have been enhanced with better progress reporting and error handling.
    *   `SearchService`: New service for warehouse element searching and filtering.

## 5. Data Flow Examples

### 5.1 UI Workflow Example - Setting Scale:
1.  User clicks "Set Scale" button in the `WorkflowPanel`.
2.  Button click is connected to handler in `MainWindow`.
3.  `MainWindow` calls `PdfViewer.set_mode(InteractionMode.SET_SCALE_START)`.
4.  `PdfViewer` changes its mode and emits `mode_changed` signal.
5.  `PdfViewerInteractionToolbar` receives signal and highlights the appropriate button.
6.  `StatusBarProgress` updates to show "Draw a line of known distance...".
7.  User draws line and enters real-world distance.
8.  `PdfViewer` calculates pixel distance and emits `scale_line_drawn` signal.
9.  `MainWindow` handles signal, asks user for real distance, updates `model.set_scale()`.
10. `WarehouseModel` stores scale data and emits `scale_changed`.
11. `WorkflowPanel` receives signal (via `MainWindow` slot) and updates scale status indicator.
12. `StatusBarProgress` updates to show "Scale set successfully."

### 5.2 UI Workflow Example - Using Theme Manager:
1.  User clicks "Toggle Dark Mode" in the View menu.
2.  `MainWindow` calls `theme_manager.toggle_theme()`.
3.  `ThemeManager` switches theme settings and emits `theme_changed`.
4.  `MainWindow` receives signal and calls appropriate methods on UI components.
5.  `PdfViewer.refresh_styles()` updates colors for graphical items.
6.  `WorkflowPanel.refresh_styles()` updates button and label styles.
7.  `StatusBarProgress` shows "Theme switched to dark mode."

## 6. Key Design Principles Applied

*   **Single Responsibility Principle (SRP):** Each class (Model, Services, View components) has a focused set of responsibilities.
*   **Separation of Concerns (SoC):** Data (Model), UI (View), and application logic (Controller/Services) are distinctly separated.
*   **Loose Coupling:** Components interact primarily through signals and defined interfaces (methods), reducing direct dependencies.
*   **Improved Testability:** Model and Service layers can be tested with less reliance on the full UI stack.
*   **Progressive Disclosure:** UI design guides users through workflows with appropriate information at each step.
*   **Accessibility First:** UI elements designed with keyboard navigation, proper contrast, and screen reader compatibility.
*   **Consistent Visual Language:** Unified design across all components through theme management.

## 7. Future Considerations

*   **Batch Processing:** Add support for processing multiple paths at once with a queue system.
*   **Enhanced Reporting:** Generate comprehensive PDF reports with path visualizations, statistics, and recommendations.
*   **Real-time Collaboration:** Enable multiple users to work on the same project simultaneously.
*   **Machine Learning Integration:** Suggest optimal layouts based on historical path data.
*   **3D Visualization:** Extend to support multi-level warehouse layouts with 3D visualization.
*   **Mobile Companion App:** Develop a mobile interface for warehouse staff to use on the floor.
*   **Cloud Backend:** Add cloud storage for projects and data sharing capabilities. 