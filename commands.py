from PySide6.QtGui import QUndoCommand, QPolygonF
from PySide6.QtCore import QPointF

class AddObstacleCommand(QUndoCommand):
    """Command to add an obstacle to the model"""
    
    def __init__(self, model, polygon, description=None):
        super().__init__(description or "Add Obstacle")
        self.model = model
        self.polygon = polygon
        self.added = False
    
    def redo(self):
        self.model.add_obstacle_no_signal(self.polygon)
        self.model.layout_changed.emit()
        self.added = True
    
    def undo(self):
        if self.added:
            # Find the polygon in the model's obstacles list (should be the last one added)
            if self.polygon in self.model.obstacles:
                self.model.remove_obstacle_by_ref_no_signal(self.polygon)
                self.model.layout_changed.emit()
                self.added = False


class RemoveObstacleCommand(QUndoCommand):
    """Command to remove an obstacle from the model"""
    
    def __init__(self, model, polygon, description=None):
        super().__init__(description or "Remove Obstacle")
        self.model = model
        self.polygon = polygon
        self.removed = False
    
    def redo(self):
        if self.polygon in self.model.obstacles:
            self.model.remove_obstacle_by_ref_no_signal(self.polygon)
            self.model.layout_changed.emit()
            self.removed = True
    
    def undo(self):
        if self.removed:
            self.model.add_obstacle_no_signal(self.polygon)
            self.model.layout_changed.emit()
            self.removed = False


class AddStagingAreaCommand(QUndoCommand):
    """Command to add a staging area to the model"""
    
    def __init__(self, model, polygon, description=None):
        super().__init__(description or "Add Staging Area")
        self.model = model
        self.polygon = polygon
        self.added = False
    
    def redo(self):
        self.model.add_staging_area_no_signal(self.polygon)
        self.model.layout_changed.emit()
        self.added = True
    
    def undo(self):
        if self.added:
            if self.polygon in self.model.staging_areas:
                self.model.remove_staging_area_by_ref_no_signal(self.polygon)
                self.model.layout_changed.emit()
                self.added = False


class RemoveStagingAreaCommand(QUndoCommand):
    """Command to remove a staging area from the model"""
    
    def __init__(self, model, polygon, description=None):
        super().__init__(description or "Remove Staging Area")
        self.model = model
        self.polygon = polygon
        self.removed = False
    
    def redo(self):
        if self.polygon in self.model.staging_areas:
            self.model.remove_staging_area_by_ref_no_signal(self.polygon)
            self.model.layout_changed.emit()
            self.removed = True
    
    def undo(self):
        if self.removed:
            self.model.add_staging_area_no_signal(self.polygon)
            self.model.layout_changed.emit()
            self.removed = False


class AddPickAisleCommand(QUndoCommand):
    """Command to add a pick aisle to the model"""
    
    def __init__(self, model, name, position, description=None):
        super().__init__(description or f"Add Pick Aisle '{name}'")
        self.model = model
        self.name = name
        self.position = position
        self.added = False
    
    def redo(self):
        if self.name not in self.model.pick_aisles:
            self.model.add_pick_aisle_no_signal(self.name, self.position)
            self.model.points_changed.emit()
            self.added = True
    
    def undo(self):
        if self.added and self.name in self.model.pick_aisles:
            self.model.remove_pick_aisle_no_signal(self.name)
            self.model.points_changed.emit()
            self.added = False


class RemovePickAisleCommand(QUndoCommand):
    """Command to remove a pick aisle from the model"""
    
    def __init__(self, model, name, description=None):
        super().__init__(description or f"Remove Pick Aisle '{name}'")
        self.model = model
        self.name = name
        self.position = None
        self.removed = False
    
    def redo(self):
        if self.name in self.model.pick_aisles:
            self.position = self.model.pick_aisles.get(self.name)
            self.model.remove_pick_aisle_no_signal(self.name)
            self.model.points_changed.emit()
            self.removed = True
    
    def undo(self):
        if self.removed and self.position:
            self.model.add_pick_aisle_no_signal(self.name, self.position)
            self.model.points_changed.emit()
            self.removed = False


class AddStagingLocationCommand(QUndoCommand):
    """Command to add a staging location to the model"""
    
    def __init__(self, model, name, position, description=None):
        super().__init__(description or f"Add Staging Location '{name}'")
        self.model = model
        self.name = name
        self.position = position
        self.added = False
    
    def redo(self):
        if self.name not in self.model.staging_locations:
            self.model.add_staging_location_no_signal(self.name, self.position)
            self.model.points_changed.emit()
            self.added = True
    
    def undo(self):
        if self.added and self.name in self.model.staging_locations:
            self.model.remove_staging_location_no_signal(self.name)
            self.model.points_changed.emit()
            self.added = False


class RemoveStagingLocationCommand(QUndoCommand):
    """Command to remove a staging location from the model"""
    
    def __init__(self, model, name, description=None):
        super().__init__(description or f"Remove Staging Location '{name}'")
        self.model = model
        self.name = name
        self.position = None
        self.removed = False
    
    def redo(self):
        if self.name in self.model.staging_locations:
            self.position = self.model.staging_locations.get(self.name)
            self.model.remove_staging_location_no_signal(self.name)
            self.model.points_changed.emit()
            self.removed = True
    
    def undo(self):
        if self.removed and self.position:
            self.model.add_staging_location_no_signal(self.name, self.position)
            self.model.points_changed.emit()
            self.removed = False


class SetBoundsCommand(QUndoCommand):
    """Command to set or clear the pathfinding bounds"""
    
    def __init__(self, model, new_bounds, description=None):
        super().__init__(description or "Set Pathfinding Bounds")
        self.model = model
        self.new_bounds = new_bounds
        self.old_bounds = model.user_pathfinding_bounds
        self.executed = False
    
    def redo(self):
        self.model.set_user_pathfinding_bounds_no_signal(self.new_bounds)
        self.model.layout_changed.emit()
        self.executed = True
    
    def undo(self):
        if self.executed:
            self.model.set_user_pathfinding_bounds_no_signal(self.old_bounds)
            self.model.layout_changed.emit()


class ClearObstaclesCommand(QUndoCommand):
    """Command to clear all obstacles"""
    
    def __init__(self, model, description=None):
        super().__init__(description or "Clear All Obstacles")
        self.model = model
        self.old_obstacles = model.obstacles.copy() if model.obstacles else []
        self.executed = False
    
    def redo(self):
        if self.old_obstacles:  # Only execute if there were obstacles to clear
            for obstacle in self.model.obstacles.copy():
                self.model.remove_obstacle_by_ref_no_signal(obstacle)
            self.model.layout_changed.emit()
            self.executed = True
    
    def undo(self):
        if self.executed:
            for obstacle in self.old_obstacles:
                self.model.add_obstacle_no_signal(obstacle)
            self.model.layout_changed.emit()


class ClearStagingAreasCommand(QUndoCommand):
    """Command to clear all staging areas"""
    
    def __init__(self, model, description=None):
        super().__init__(description or "Clear All Staging Areas")
        self.model = model
        self.old_staging_areas = model.staging_areas.copy() if model.staging_areas else []
        self.executed = False
    
    def redo(self):
        if self.old_staging_areas:  # Only execute if there were staging areas to clear
            for staging_area in self.model.staging_areas.copy():
                self.model.remove_staging_area_by_ref_no_signal(staging_area)
            self.model.layout_changed.emit()
            self.executed = True
    
    def undo(self):
        if self.executed:
            for staging_area in self.old_staging_areas:
                self.model.add_staging_area_no_signal(staging_area)
            self.model.layout_changed.emit()


class ClearPickAislesCommand(QUndoCommand):
    """Command to clear all pick aisles"""
    
    def __init__(self, model, description=None):
        super().__init__(description or "Clear All Pick Aisles")
        self.model = model
        self.old_pick_aisles = {name: pos for name, pos in model.pick_aisles.items()} if model.pick_aisles else {}
        self.executed = False
    
    def redo(self):
        if self.old_pick_aisles:  # Only execute if there were pick aisles to clear
            for name in list(self.model.pick_aisles.keys()):
                self.model.remove_pick_aisle_no_signal(name)
            self.model.points_changed.emit()
            self.executed = True
    
    def undo(self):
        if self.executed:
            for name, pos in self.old_pick_aisles.items():
                self.model.add_pick_aisle_no_signal(name, pos)
            self.model.points_changed.emit()


class ClearStagingLocationsCommand(QUndoCommand):
    """Command to clear all staging locations"""
    
    def __init__(self, model, description=None):
        super().__init__(description or "Clear All Staging Locations")
        self.model = model
        self.old_staging_locations = {name: pos for name, pos in model.staging_locations.items()} if model.staging_locations else {}
        self.executed = False
    
    def redo(self):
        if self.old_staging_locations:  # Only execute if there were staging locations to clear
            for name in list(self.model.staging_locations.keys()):
                self.model.remove_staging_location_no_signal(name)
            self.model.points_changed.emit()
            self.executed = True
    
    def undo(self):
        if self.executed:
            for name, pos in self.old_staging_locations.items():
                self.model.add_staging_location_no_signal(name, pos)
            self.model.points_changed.emit()


class ClearPathfindingBoundsCommand(QUndoCommand):
    """Command to clear pathfinding bounds"""
    
    def __init__(self, model, description=None):
        super().__init__(description or "Clear Pathfinding Bounds")
        self.model = model
        self.old_bounds = model.user_pathfinding_bounds
        self.executed = False
    
    def redo(self):
        if self.old_bounds:  # Only execute if there were bounds to clear
            self.model.set_user_pathfinding_bounds_no_signal(None)
            self.model.layout_changed.emit()
            self.executed = True
    
    def undo(self):
        if self.executed:
            self.model.set_user_pathfinding_bounds_no_signal(self.old_bounds)
            self.model.layout_changed.emit() 