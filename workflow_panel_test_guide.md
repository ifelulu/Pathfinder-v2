# WorkflowPanel Implementation Testing Guide

This guide provides steps to verify the functionality of tasks 1.1-1.7 related to the WorkflowPanel implementation.

## Step 1: Minimal Component Testing

First, run the minimal test script that verifies the WorkflowPanel class on its own:

```bash
python test_workflow_panel_minimal.py
```

This script checks:
- WorkflowPanel instantiation
- Presence of all required UI elements (buttons, labels, comboboxes)
- Initial button states (disabled as expected)

The test will open a window displaying the WorkflowPanel. Visually verify that:
- The panel has the correct layout
- The "Workflow Steps" title is present
- Three main button sections are visible, plus the path calculation section

## Step 2: Visual Inspection in the Application

Run the full application to verify integration and functionality:

```bash
python main.py
```

### Manual Testing Checklist

#### 1. Verify UI Integration
- [ ] WorkflowPanel is visible on the left side of the application
- [ ] All UI elements are properly sized and aligned
- [ ] Menu items function properly alongside the WorkflowPanel

#### 2. Test Load PDF Button
- [ ] Click "Load PDF" button
- [ ] Verify file dialog opens
- [ ] Select a PDF file
- [ ] Confirm PDF Status label updates to show the filename
- [ ] Verify "Set Scale" button becomes enabled

#### 3. Test Set Scale Button
- [ ] Click "Set Scale" button
- [ ] Draw a line on the PDF by clicking two points
- [ ] Enter a value in the distance dialog
- [ ] Verify Scale Status label updates to show the set scale
- [ ] Confirm "Precompute Paths" button becomes enabled

#### 4. Test Precompute Paths Button
- [ ] Define some obstacles, pick aisles, and staging locations
- [ ] Click "Precompute Paths" button
- [ ] Verify Precomputation Status changes to "In Progress..."
- [ ] After completion, verify status changes to "Ready"
- [ ] Confirm "Calculate Path" button becomes enabled

#### 5. Test Calculate Path Controls
- [ ] Verify pick aisle dropdown is populated with defined points
- [ ] Verify staging location dropdown is populated with defined points
- [ ] Select start and end points
- [ ] Click "Calculate Path" button
- [ ] Verify path appears in the PDF viewer

#### 6. Test State Management
- [ ] After changing the layout (adding an obstacle), verify Precomputation Status changes to "Needed"
- [ ] After loading a new PDF, verify all status labels reset properly

## Expected Results

- All buttons enable/disable at appropriate times based on application state
- Status labels update correctly as operations are performed
- Calculate Path controls function identically to their previous behavior
- Actions are properly synchronized with the main application UI

## Alternative Testing Method

If the full application cannot be launched for testing due to initialization issues, use the test_workflow_panel.py script which provides a simplified testing environment:

```bash
python test_workflow_panel.py
```

This provides a simplified environment to test the WorkflowPanel's core functionality without the complexity of the full application. 