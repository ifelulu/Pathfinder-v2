from PySide6.QtWidgets import (
    QToolBar, QStyle
)
from PySide6.QtGui import (
    QIcon, QAction, QActionGroup
)
from PySide6.QtCore import (
    Qt, Signal
)

from enums import InteractionMode

class PdfViewerInteractionToolbar(QToolBar):
    """Toolbar for controlling the PdfViewer interaction modes."""
    
    mode_changed = Signal(InteractionMode)
    cancel_operation_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__("Interaction Toolbar", parent)
        self.setMovable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        
        # Create a action group for exclusive selection
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        
        # Create actions for each interaction mode
        self.actions = {}
        self._setup_actions()
        
        # Add a separator and the cancel button
        self.addSeparator()
        self.cancel_action = QAction("Cancel", self)
        self.cancel_action.setToolTip("Cancel current drawing or mode")
        self.addAction(self.cancel_action)
        
        # Connect signals
        self._connect_signals()
    
    def _setup_actions(self):
        """Create actions for each interaction mode."""
        # Define the actions to create with their tooltips
        action_definitions = {
            InteractionMode.IDLE: {
                "text": "Select",
                "tooltip": "Selection mode - select and move objects"
            },
            InteractionMode.PANNING: {
                "text": "Pan",
                "tooltip": "Pan the view"
            },
            InteractionMode.SET_SCALE_START: {
                "text": "Set Scale",
                "tooltip": "Set the scale for distance calculations"
            },
            InteractionMode.DRAW_OBSTACLE: {
                "text": "Draw Obstacle",
                "tooltip": "Draw an obstacle polygon"
            },
            InteractionMode.DEFINE_STAGING_AREA: {
                "text": "Draw Staging Area",
                "tooltip": "Draw a staging area polygon"
            },
            InteractionMode.DEFINE_PATHFINDING_BOUNDS: {
                "text": "Define Bounds",
                "tooltip": "Define the pathfinding bounds"
            },
            InteractionMode.SET_START_POINT: {
                "text": "Set Start Point",
                "tooltip": "Place a starting point"
            },
            InteractionMode.SET_END_POINT: {
                "text": "Set End Point",
                "tooltip": "Place an ending point"
            },
            InteractionMode.DEFINE_AISLE_LINE_START: {
                "text": "Define Aisle Line",
                "tooltip": "Define a line of pick aisle points"
            },
            InteractionMode.DEFINE_STAGING_LINE_START: {
                "text": "Define Staging Line",
                "tooltip": "Define a line of staging location points"
            },
            InteractionMode.EDIT: {
                "text": "Edit Mode",
                "tooltip": "Edit mode - edit objects"
            }
        }
        
        # Create the actions and add to toolbar
        for mode, definition in action_definitions.items():
            action = QAction(definition["text"], self)
            action.setToolTip(definition["tooltip"])
            action.setCheckable(True)
            action.setData(mode)  # Store the mode in the action's data
            
            self.addAction(action)
            self.actions[mode] = action
            self.mode_group.addAction(action)
    
    def _connect_signals(self):
        """Connect internal signals."""
        # Connect mode group action triggered to mode_changed signal
        self.mode_group.triggered.connect(self._on_mode_action_triggered)
        
        # Connect cancel action
        self.cancel_action.triggered.connect(self.cancel_operation_requested.emit)
    
    def _on_mode_action_triggered(self, action):
        """Handle mode action triggered."""
        # Get the mode from the action's data
        mode = action.data()
        self.mode_changed.emit(mode)
    
    def set_active_mode(self, mode: InteractionMode):
        """Update the toolbar to reflect the current active mode."""
        if mode in self.actions:
            self.actions[mode].setChecked(True)
        else:
            # If mode not in actions (e.g., intermediate states), uncheck all
            for action in self.actions.values():
                action.setChecked(False) 