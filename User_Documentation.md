## Warehouse Path Finder - User Documentation

**(This is largely based on the README.md content)**

**1. Introduction**

Welcome to the Warehouse Path Finder! This application helps you visualize your warehouse layout, optimize paths, analyze picklist efficiency, and simulate warehouse operations through an intuitive, accessible interface.

**2. Core Features**

*   **Visualize:** Load and view PDF floor plans with enhanced zoom controls and drag-and-drop support.
*   **Scale:** Calibrate the layout to real-world units (meters/feet) with guided scale setting.
*   **Define:** Interactively draw obstacles, staging areas (with travel penalties), **optional user-defined pathfinding boundaries**, pick aisles (start points), and staging locations (end points) using the dedicated Interaction Toolbar.
*   **Pathfind:**
    *   Generates an internal grid based on your layout, which can be **cropped to the relevant area** for efficiency.
    *   Precomputes all shortest paths from pick aisles using Dijkstra's algorithm with visual progress tracking.
    *   Calculates and displays the shortest path and distance between any selected pick aisle and staging location.
*   **Analyze:**
    *   Import picklist data from CSV files with intuitive column mapping.
    *   Calculate travel distance for each picklist item.
    *   View results, statistics, and histograms with filtering options. Export enhanced CSVs.
*   **Animate:**
    *   Import timed picklist data (CSV) with improved setup dialogs.
    *   Visualize warehouse activity with moving "carts" or path lines.
    *   Control playback speed and filter by date/location through the enhanced Animation Control Dialog.
*   **UI Enhancements:**
    *   Workflow Panel for step-by-step guidance through application processes.
    *   Theme support with light and dark modes for visual comfort.
    *   Search and filter capabilities for finding warehouse elements.
    *   Status bar with progress indicators for long-running operations.
    *   Comprehensive keyboard shortcuts for efficient operation.
*   **Accessibility Features:**
    *   Keyboard navigation optimized for all operations.
    *   Screen reader compatibility for visually impaired users.
    *   High contrast options and configurable text sizes.
*   **Save/Load:** Store and retrieve your entire project setup (layout, scale, settings, **including user pathfinding bounds**) in `.whp` files with recent files history.

**3. The User Interface**

### 3.1 Main Application Window

The Warehouse Path Finder interface consists of these main components:

*   **Menu Bar:** Contains File, Edit, Tools, View, Units, Export, and Help menus.
*   **Main Toolbar:** Quick access to common operations (open, save, analyze, animate).
*   **Interaction Toolbar:** Tools for drawing and editing warehouse elements.
*   **Workflow Panel:** Left sidebar guiding you through the application workflow with status indicators.
*   **PDF Viewer:** Central area displaying the warehouse layout and pathfinding results.
*   **Search Panel:** Right sidebar for finding and filtering warehouse elements (toggle with View menu).
*   **Status Bar:** Bottom area displaying operation status, progress, and zoom controls.

### 3.2 Workflow Panel

The Workflow Panel guides you through the main steps of using the application:

1. **PDF Loading:** Load your warehouse floor plan with status indicator.
2.  **Set Scale:** Set the real-world scale with status indicator.
3.  **Path Precomputation:** Precompute all possible paths with status indicator.
4.  **Path Calculation:** Select start/end points and calculate specific paths.

Each step shows its current status (not done, in progress, or complete) to help you track your progress and understand what needs to be done next.

### 3.3 Interaction Toolbar

The Interaction Toolbar provides easy access to drawing and editing modes:

*   **Navigation Mode:** Pan and select without drawing.
*   **Scale Setting:** Draw a line of known distance to set scale.
*   **Drawing Tools:** Draw obstacles and staging areas.
*   **Point Placement:** Add pick aisles and staging locations.
*   **Line Definition:** Create multiple points along a line.
*   **Bounds Definition:** Set custom pathfinding boundaries.
*   **Edit Mode:** Move or delete existing elements.
*   **Cancel Button:** Exit current drawing operation.

The active mode is visually highlighted to show your current operation.

### 3.4 Search and Filter Panel

The Search Panel allows you to find specific elements in your warehouse:

*   **Search Points:** Find pick aisles or staging locations by name.
*   **Search Obstacles:** Find obstacles by properties (size, location).
*   **Search Paths:** Find paths between specific points with criteria.
*   **Results List:** Shows search results with highlight and goto capabilities.

**4. Getting Started**

### 4.1 Setup and Running

1.  **Install Python:** Ensure you have Python 3.9 or newer installed.
2.  **Create Virtual Environment (Recommended):**
    ```bash
    # In your project directory
    python -m venv .venv
    # Activate it
    # Windows:
    .\.venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run:**
    ```bash
    python main.py
    ```

### 4.2 Quick Start Guide

1.  **Load PDF:** 
    * Click the "Load PDF" button in the Workflow Panel, or use File > Open PDF, or
    * Simply drag and drop a PDF file onto the application window.
    * Status indicator in Workflow Panel will update to show PDF loaded.

2.  **Set Scale:** 
    * Click the "Set Scale" button in the Workflow Panel.
    * Draw a line between two points representing a known distance.
    * Enter the real-world distance and choose units.
    * Scale status indicator will update when complete.

3.  **Define Layout:** 
    * Use the Interaction Toolbar buttons to select drawing modes.
    * Draw obstacles by clicking points to form polygons (double-click to complete).
    * Draw staging areas similarly.
    * Place pick aisles and staging locations with appropriate toolbar buttons.
    * (Optional) Define pathfinding bounds to focus calculations on your operational area.

4.  **Precompute Paths:** 
    * Click the "Precompute Paths" button in the Workflow Panel.
    * Watch the progress in the status bar.
    * Precomputation status indicator will update when complete.

5.  **Calculate Single Path:** 
    * Select start point from the "From" dropdown in the Workflow Panel.
    * Select end point from the "To" dropdown.
    * Click "Calculate Path" to view the path and distance.

6.  **Analyze Picklist:** 
    * Click the "Analyze Picklist" button on the main toolbar or use Tools > Analyze Picklist.
    * Select a CSV file and map relevant columns.
    * View analysis results in the dialog that appears.

7.  **Animate Picklist:** 
    * Click the "Animate Picklist" button on the main toolbar or use Tools > Animate Picklist.
    * Select a CSV file with timestamp data and map columns.
    * Use the Animation Control Dialog to play, pause, filter, and adjust the visualization.

8.  **Save Project:** 
    * Use File > Save Project to store your work.
    * All settings, layout elements, and scale information will be saved.

**5. Working with UI Features**

### 5.1 Theme Management

To change the application theme:
* Go to View > Toggle Dark Mode
* The entire application will switch between light and dark themes
* Your choice is remembered between sessions

### 5.2 Preferences

To customize application behavior:
* Go to View > Preferences
* Adjust display settings, behavior options, and accessibility features
* Click Apply to see changes immediately or Save to apply and remember them

### 5.3 Search and Filter Panel

To find specific elements:
1. Open the Search Panel using View > Search Panel
2. Select the tab for the element type you want to search for
3. Enter search criteria and click Search
4. Select a result from the list
5. Use Highlight to visually highlight the element or Goto to center the view on it

### 5.4 Status Bar Progress

The status bar provides visual feedback during operations:
* Text messages indicate current status or completed actions
* Progress bars show completion of long-running tasks
* Spinner indicators appear during background processing
* Zoom controls allow adjusting the view magnification

### 5.5 Keyboard Shortcuts

Efficient operation using keyboard shortcuts:
* `Ctrl+O`: Open PDF
* `Ctrl+S`: Save Project
* `Ctrl+Z`/`Ctrl+Y`: Undo/Redo
* `Alt+[Letter]`: Activate drawing modes (see tooltips)
* Arrow keys: Pan the PDF view when focused
* `+`/`-`: Zoom in/out when PDF viewer is focused
* `F1`: View help documentation

**6. Troubleshooting**

*   **PDF Issues:** Check if PDF is valid and not password protected. Ensure `PyMuPDF` is installed correctly (`pip install pymupdf`).
*   **Pathfinding Errors:**
    *   Did you set the scale *before* drawing elements?
    *   Are points placed inside obstacles?
    *   Did you run `Precompute All Paths` after the latest layout change (including pathfinding bounds)?
    *   If using "Define Pathfinding Bounds", ensure it's large enough to include all necessary points and potential paths with some margin.
    *   Try adjusting the "Grid Factor" in the main window (lower value = finer grid, more accurate but slower; higher value = coarser grid, faster but less accurate).
*   **CSV Errors:** Ensure standard CSV format. Check date/time formats (e.g., `YYYY-MM-DD HH:MM:SS`, `MM/DD/YYYY HH:MM`). Use the column selection dialogs carefully.
*   **Slow Animation:** Filter data by date/cluster in Animation Controls. A higher "Grid Factor" can also help.
*   **UI Issues:**
    *   If theme appears inconsistent, try toggling dark/light mode in View menu.
    *   If an operation seems unresponsive, check the status bar for progress indicators.
    *   If keyboard shortcuts don't work, ensure the appropriate component has focus.
    *   Reset preferences to defaults if customizations cause display problems.

**7. Getting Help**

* Press `F1` at any time for context-sensitive help
* Check tooltips by hovering over UI elements
* Refer to the status bar for operation guidance
* View the About dialog (Help > About) for version information
* Consult the full documentation in Help > View Documentation 