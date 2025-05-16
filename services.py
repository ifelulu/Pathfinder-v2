# --- START OF FILE Warehouse-Path-Finder-main/services.py ---

import json
import math
import multiprocessing
import time
import csv
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from PySide6.QtCore import QObject, Signal, QPointF, QRectF
from PySide6.QtGui import QPolygonF, QTransform
from PySide6.QtWidgets import QFileDialog

# For debug grid visualization
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Assuming model and pathfinding are in the same directory or accessible
from model import WarehouseModel
# Import pathfinding functions (adjust path if needed)
from pathfinding import (create_grid_from_obstacles, dijkstra_precompute,
                         reconstruct_path, COST_OBSTACLE,
                         OBSTACLE_DILATION_ITERATIONS, COST_EMPTY)

# --- Worker function for multiprocessing (needs to be top-level) ---
def _run_dijkstra_worker(args: Tuple[np.ndarray, Tuple[int, int], str]) -> Tuple[str, Optional[np.ndarray], Optional[np.ndarray]]:
    """Worker function for parallel Dijkstra precomputation."""
    grid, start_cell, start_name = args
    try:
        if grid[start_cell] == COST_OBSTACLE:
            # print(f"[Worker] Skipping precomputation for '{start_name}': Start point is inside obstacle at cell {start_cell}.") # Keep commented unless debugging worker
            return start_name, None, None

        dist_map, path_map = dijkstra_precompute(grid, start_cell)
        # print(f"[Worker] Finished Dijkstra for '{start_name}'.") # Keep commented unless debugging worker
        return start_name, dist_map, path_map
    except Exception as e:
        print(f"[Worker] Error during Dijkstra for '{start_name}': {e}")
        import traceback
        traceback.print_exc()
        return start_name, None, None

# --- Service Classes ---

class ProjectService(QObject):
    """Handles saving and loading warehouse project files."""

    project_load_failed = Signal(str)
    project_save_failed = Signal(str)
    project_operation_finished = Signal(str)

    def save_project(self, model: WarehouseModel, file_path: str) -> bool:
        print(f"[ProjectService] Saving project to: {file_path}")
        if not file_path.lower().endswith('.whp'):
            file_path += '.whp'

        project_data = {
            "version": "1.4",
            "pdf_path": model.current_pdf_path,
            "pdf_bounds": {
                "x": model.pdf_bounds.x() if model.pdf_bounds else 0,
                "y": model.pdf_bounds.y() if model.pdf_bounds else 0,
                "width": model.pdf_bounds.width() if model.pdf_bounds else 0,
                "height": model.pdf_bounds.height() if model.pdf_bounds else 0,
            } if model.pdf_bounds else None,
            "scale_info": {
                "pixels_per_unit": model.scale_pixels_per_unit,
                "calibration_unit": model.calibration_unit,
                "display_unit": model.display_unit
            },
            "grid_resolution_factor": model.grid_resolution_factor,
            "staging_area_penalty": model.staging_area_penalty,
            "animation_cart_width": model.animation_cart_width,
            "animation_cart_length": model.animation_cart_length,
            "obstacles": [[(p.x(), p.y()) for p in polygon] for polygon in model.obstacles],
            "staging_areas": [[(p.x(), p.y()) for p in polygon] for polygon in model.staging_areas],
            "user_pathfinding_bounds": [(p.x(), p.y()) for p in model.user_pathfinding_bounds] if model.user_pathfinding_bounds and not model.user_pathfinding_bounds.isEmpty() else None,
            "pick_aisles": {name: (p.x(), p.y()) for name, p in model.pick_aisles.items()},
            "staging_locations": {name: (p.x(), p.y()) for name, p in model.staging_locations.items()},
        }
        try:
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=4)
            print("[ProjectService] Project saved successfully.")
            self.project_operation_finished.emit(f"Project saved to {file_path}")
            return True
        except Exception as e:
            error_msg = f"Failed to save project file:\n{e}"
            print(f"[ProjectService] Error: {error_msg}")
            self.project_save_failed.emit(error_msg)
            return False

    def load_project(self, file_path: str) -> WarehouseModel | None:
        print(f"[ProjectService] Loading project from: {file_path}")
        try:
            with open(file_path, 'r') as f:
                project_data = json.load(f)

            if not isinstance(project_data, dict) or "version" not in project_data:
                raise ValueError("Invalid project file format (missing version).")

            model = WarehouseModel()
            model.set_current_project_path(file_path)
            
            model._current_pdf_path = project_data.get("pdf_path")
            pdf_bounds_data = project_data.get("pdf_bounds")
            if pdf_bounds_data and isinstance(pdf_bounds_data, dict):
                 model._pdf_bounds = QRectF(pdf_bounds_data.get("x",0), pdf_bounds_data.get("y",0),
                                          pdf_bounds_data.get("width",0), pdf_bounds_data.get("height",0))

            scale_info = project_data.get("scale_info", {})
            model._scale_pixels_per_unit = scale_info.get("pixels_per_unit")
            model._calibration_unit = scale_info.get("calibration_unit")
            model._display_unit = scale_info.get("display_unit", "meters")

            model._grid_resolution_factor = project_data.get("grid_resolution_factor", 2.0)
            model._staging_area_penalty = project_data.get("staging_area_penalty", 10.0)
            model._animation_cart_width = project_data.get("animation_cart_width", 2.625)
            model._animation_cart_length = project_data.get("animation_cart_length", 5.458)

            model._obstacles = [QPolygonF([QPointF(px, py) for px, py in obs_points])
                                for obs_points in project_data.get("obstacles", [])]
            model._staging_areas = [QPolygonF([QPointF(px, py) for px, py in area_points])
                                    for area_points in project_data.get("staging_areas", [])]
            
            bounds_data = project_data.get("user_pathfinding_bounds")
            if bounds_data:
                 model._user_pathfinding_bounds = QPolygonF([QPointF(px, py) for px, py in bounds_data])
            else:
                 model._user_pathfinding_bounds = None

            loaded_pick_aisles = project_data.get("pick_aisles", {})
            for name, point_coords_tuple in loaded_pick_aisles.items():
                model._pick_aisles[name] = QPointF(point_coords_tuple[0], point_coords_tuple[1])

            loaded_staging_locations = project_data.get("staging_locations", {})
            for name, point_coords_tuple in loaded_staging_locations.items():
                model._staging_locations[name] = QPointF(point_coords_tuple[0], point_coords_tuple[1])

            print("[ProjectService] Project data loaded successfully.")
            model.mark_project_loaded()
            self.project_operation_finished.emit(f"Project '{model.current_project_path}' loaded.")
            return model

        except Exception as e:
            error_msg = f"Error loading project file:\n{e}"
            print(f"[ProjectService] Error: {error_msg}")
            import traceback
            traceback.print_exc()
            self.project_load_failed.emit(error_msg)
            return None


class PathfindingService(QObject):
    grid_update_started = Signal()
    grid_update_finished = Signal(bool)
    precomputation_started = Signal(int)
    precomputation_progress = Signal(int, str)
    precomputation_finished = Signal(bool, list)
    export_path_data_complete = Signal(str)
    export_path_image_complete = Signal(str)
    export_path_data_failed = Signal(str)
    export_path_image_failed = Signal(str)

    def _calculate_effective_layout_bounds_for_grid(self, model: WarehouseModel) -> QRectF:
        padding = 50.0

        if model.user_pathfinding_bounds and not model.user_pathfinding_bounds.isEmpty():
            print("[PathfindingService] Using user-defined pathfinding bounds as base for grid.")
            base_rect = model.user_pathfinding_bounds.boundingRect()
            padded_rect = base_rect.adjusted(-padding, -padding, padding, padding)
            final_bounds = padded_rect.intersected(model.pdf_bounds)
            if final_bounds.isValid() and final_bounds.width() > 0 and final_bounds.height() > 0:
                print(f"[PathfindingService] Grid will use user bounds, padded & clipped: {final_bounds}")
                return final_bounds
            else:
                print("[PathfindingService] Warning: User bounds resulted in invalid/empty rect after padding/clipping. Falling back.")

        # CHANGE: Instead of trying to optimize bounds, just use the full PDF bounds to ensure all points are included
        print("[PathfindingService] Using full PDF bounds for grid generation to ensure all points are included.")
        return model.pdf_bounds

    def update_grid(self, model: WarehouseModel) -> bool:
        if not model.current_pdf_path or not model.is_scale_set or not model.pdf_bounds:
            msg = "[PathfindingService] Cannot update grid: PDF path, scale, or bounds not ready."
            print(msg)
            model.set_pathfinding_data(None, None)
            return False

        self.grid_update_started.emit()
        print("[PathfindingService] Updating pathfinding cost grid...")

        # Get base grid bounds from effective layout
        effective_grid_rect_pdf = self._calculate_effective_layout_bounds_for_grid(model)
        
        # Now ensure that ALL points (both pick aisles and staging locations) are within the grid bounds
        # by expanding the bounds if necessary
        all_points = list(model.pick_aisles.values()) + list(model.staging_locations.values())
        expanded_rect = QRectF(effective_grid_rect_pdf)
        
        for point in all_points:
            if not expanded_rect.contains(point):
                print(f"[PathfindingService] Expanding grid bounds to include point: ({point.x():.2f}, {point.y():.2f})")
                # Create a small rect around the point and unite with the expanded rect
                point_rect = QRectF(point.x() - 10, point.y() - 10, 20, 20)
                expanded_rect = expanded_rect.united(point_rect)
        
        # Use the expanded rect for grid generation
        if expanded_rect != effective_grid_rect_pdf:
            print(f"[PathfindingService] Grid bounds expanded from {effective_grid_rect_pdf} to {expanded_rect}")
            effective_grid_rect_pdf = expanded_rect
            
        grid_origin_pdf = effective_grid_rect_pdf.topLeft()
        grid_width_pdf = effective_grid_rect_pdf.width()
        grid_height_pdf = effective_grid_rect_pdf.height()

        # Add a safety factor to ensure we have enough cells
        # Special case for resolution factor of 1.0 - don't add extra cells
        if abs(model.grid_resolution_factor - 1.0) < 0.001:  # Using approximate equality for float comparison
            grid_width_cells = int(grid_width_pdf / model.grid_resolution_factor)
            grid_height_cells = int(grid_height_pdf / model.grid_resolution_factor)
            print("[PathfindingService] Resolution factor is 1.0 - using exact grid size without padding")
        else:
            grid_width_cells = int(grid_width_pdf / model.grid_resolution_factor) + 10
            grid_height_cells = int(grid_height_pdf / model.grid_resolution_factor) + 10

        print(f"[PathfindingService] Grid dimensions: {grid_width_cells}x{grid_height_cells} cells, Origin: ({grid_origin_pdf.x():.2f}, {grid_origin_pdf.y():.2f})")

        if grid_width_cells <= 0 or grid_height_cells <= 0:
            print(f"[PathfindingService] Error: Calculated grid cell dimensions are non-positive. W_cells={grid_width_cells}, H_cells={grid_height_cells} based on effective_rect={effective_grid_rect_pdf}. Attempting full PDF fallback.")
            effective_grid_rect_pdf = model.pdf_bounds
            grid_origin_pdf = effective_grid_rect_pdf.topLeft()
            grid_width_pdf = effective_grid_rect_pdf.width()
            grid_height_pdf = effective_grid_rect_pdf.height()
            
            # Special case for resolution factor of 1.0 - don't add extra cells
            if abs(model.grid_resolution_factor - 1.0) < 0.001:  # Using approximate equality for float comparison
                grid_width_cells = int(grid_width_pdf / model.grid_resolution_factor)
                grid_height_cells = int(grid_height_pdf / model.grid_resolution_factor)
                print("[PathfindingService] Resolution factor is 1.0 - using exact grid size without padding in fallback calculation")
            else:
                grid_width_cells = int(grid_width_pdf / model.grid_resolution_factor) + 10
                grid_height_cells = int(grid_height_pdf / model.grid_resolution_factor) + 10
            
            if grid_width_cells <= 0 or grid_height_cells <= 0:
                 print(f"[PathfindingService] Error: Still invalid grid cell dimensions even with full PDF. W_cells={grid_width_cells}, H_cells={grid_height_cells}")
                 model.set_pathfinding_data(None, None)
                 self.grid_update_finished.emit(False)
                 return False
        
        try:
            print(f"[PathfindingService] Creating grid: {grid_width_cells}x{grid_height_cells} cells, Origin (PDF): {grid_origin_pdf.x():.2f},{grid_origin_pdf.y():.2f}")
            
            # Now validate all points would be in bounds BEFORE creating the grid
            for name, point in model.pick_aisles.items():
                col = (point.x() - grid_origin_pdf.x()) / model.grid_resolution_factor
                row = (point.y() - grid_origin_pdf.y()) / model.grid_resolution_factor
                if col < 0 or col >= grid_width_cells or row < 0 or row >= grid_height_cells:
                    print(f"[PathfindingService] WARNING: Pick aisle {name} would be outside grid bounds! Cell: ({row:.2f}, {col:.2f})")
            
            for name, point in model.staging_locations.items():
                col = (point.x() - grid_origin_pdf.x()) / model.grid_resolution_factor
                row = (point.y() - grid_origin_pdf.y()) / model.grid_resolution_factor
                if col < 0 or col >= grid_width_cells or row < 0 or row >= grid_height_cells:
                    print(f"[PathfindingService] WARNING: Staging location {name} would be outside grid bounds! Cell: ({row:.2f}, {col:.2f})")
            
            grid = create_grid_from_obstacles(
                grid_width_cells, grid_height_cells, 
                obstacles_pdf_list=model.obstacles,         
                resolution_factor=model.grid_resolution_factor,
                grid_origin_pdf=grid_origin_pdf,
                staging_areas_pdf_list=model.staging_areas, 
                staging_penalty=model.staging_area_penalty
            )
            if grid is None:
                raise ValueError("create_grid_from_obstacles returned None")

            model.set_pathfinding_data(grid, grid_origin_pdf)
            print("[PathfindingService] Grid updated successfully.")
            self.grid_update_finished.emit(True)
            return True
        except Exception as e:
            print(f"[PathfindingService] Error updating grid: {e}")
            import traceback
            traceback.print_exc()
            model.set_pathfinding_data(None, None)
            self.grid_update_finished.emit(False)
            return False

    def precompute_all_paths(self, model: WarehouseModel):
        if not model.can_precompute:
            print(f"[PathfindingService] Cannot precompute: Basic prerequisites not met. Scale: {model.is_scale_set}, PDF: {model.current_pdf_path is not None}, PickAisles: {model.has_pick_aisles}")
            self.precomputation_finished.emit(False, []); return

        if not model.grid_is_valid:
            print("[PathfindingService] Grid is not valid, attempting to update/create it first...")
            if not self.update_grid(model):
                 print("[PathfindingService] Grid update failed during precomputation attempt.")
                 self.precomputation_finished.emit(False, []); return
            if not model.grid_is_valid: # Should be true now
                print("[PathfindingService] CRITICAL: Grid still not valid after update_grid call.")
                self.precomputation_finished.emit(False, []); return
        
        grid = model.pathfinding_grid
        grid_origin = model.grid_origin_pdf
        if grid_origin is None: # Should be caught by grid_is_valid
            print("[PathfindingService] CRITICAL: grid_origin_pdf is None in precompute_all_paths.")
            self.precomputation_finished.emit(False, []); return
                
        res_f = model.grid_resolution_factor
        grid_h, grid_w = grid.shape
        start_points_pdf_coords = model.pick_aisles

        self.precomputation_started.emit(len(start_points_pdf_coords))
        print(f"[PathfindingService] Starting precomputation for {len(start_points_pdf_coords)} points (using grid origin: {grid_origin.x():.2f},{grid_origin.y():.2f})...")
        print(f"[PathfindingService] Grid dimensions: {grid_w}x{grid_h} cells, Resolution factor: {res_f}")
        
        tasks, valid_start_names, initial_failed_points = [], [], []
        debug_pick_aisle_cells: List[Tuple[int, int]] = []

        for name, point_pdf in start_points_pdf_coords.items():
            col_raw = (point_pdf.x() - grid_origin.x()) / res_f
            row_raw = (point_pdf.y() - grid_origin.y()) / res_f
            
            col_clamped = max(0, min(int(col_raw), grid_w - 1))
            row_clamped = max(0, min(int(row_raw), grid_h - 1))
            start_cell = (row_clamped, col_clamped)
            debug_pick_aisle_cells.append(start_cell)

            if len(debug_pick_aisle_cells) <= 5 or name.startswith("A1") or name.startswith("D1"):
                print(f"[Service DEBUG] Pick Aisle '{name}': PDF ({point_pdf.x():.2f}, {point_pdf.y():.2f}) "
                      f"-> Grid Cell (Raw float: {row_raw:.2f},{col_raw:.2f}; Clamped int: {row_clamped},{col_clamped})")

            if grid[start_cell] == COST_OBSTACLE:
                initial_failed_points.append(f"{name} (in obstacle at grid cell {start_cell})")
            else:
                tasks.append((grid, start_cell, name))
                valid_start_names.append(name)
        
        # print(f"[Service DEBUG] Saving debug grid with pick aisle cell locations (count: {len(debug_pick_aisle_cells)})...") # Keep commented unless needed
        self.save_grid_for_debug(model, "debug_grid_with_pick_aisles.png", path_cells_to_draw=debug_pick_aisle_cells)

        if not tasks:
            print("[PathfindingService] No valid start points found for precomputation (all might be in obstacles or outside valid grid area).")
            model.set_pathfinding_data(grid, grid_origin, {}, {});
            self.precomputation_finished.emit(True, initial_failed_points);
            return

        start_time = time.time(); results_dist, results_path, successful_count = {}, {}, 0
        final_failed_points_combined = initial_failed_points[:]

        try:
            num_workers = max(1, multiprocessing.cpu_count() - 1 if multiprocessing.cpu_count() > 1 else 1)
            chunksize = max(1, len(tasks) // num_workers if num_workers > 0 else 1)
            with multiprocessing.Pool(processes=num_workers) as pool:
                 for name_mp, dist_map, path_map in pool.imap_unordered(_run_dijkstra_worker, tasks, chunksize=chunksize):
                    if dist_map is not None and path_map is not None:
                        results_dist[name_mp] = dist_map; results_path[name_mp] = path_map; successful_count += 1
                        self.precomputation_progress.emit(successful_count, name_mp)
                    elif name_mp in valid_start_names: 
                        if not any(name_mp in f_item for f_item in final_failed_points_combined):
                             final_failed_points_combined.append(f"{name_mp} (failed during Dijkstra worker)")
                    QObject().thread().msleep(10)
            
            model.set_pathfinding_data(grid, grid_origin, results_dist, results_path)
            duration = time.time() - start_time; success_flag = not bool(final_failed_points_combined)
            print(f"[PathfindingService] Precomputation finished: {duration:.2f}s. Overall Success: {success_flag}. Failures: {final_failed_points_combined}")
            print(f"[PathfindingService] Final grid dimensions: {grid_w}x{grid_h} cells, Grid origin: ({grid_origin.x():.2f}, {grid_origin.y():.2f})")
            
            # Check bounds status of all points
            for name, point in model.pick_aisles.items():
                col = (point.x() - grid_origin.x()) / res_f
                row = (point.y() - grid_origin.y()) / res_f
                if col < 0 or col >= grid_w or row < 0 or row >= grid_h:
                    print(f"[PathfindingService] WARNING: Pick aisle {name} is outside grid bounds! PDF: ({point.x():.2f}, {point.y():.2f}), Cell: ({row:.2f}, {col:.2f})")
            
            for name, point in model.staging_locations.items():
                col = (point.x() - grid_origin.x()) / res_f
                row = (point.y() - grid_origin.y()) / res_f
                if col < 0 or col >= grid_w or row < 0 or row >= grid_h:
                    print(f"[PathfindingService] WARNING: Staging location {name} is outside grid bounds! PDF: ({point.x():.2f}, {point.y():.2f}), Cell: ({row:.2f}, {col:.2f})")
            
            self.precomputation_finished.emit(success_flag, final_failed_points_combined)
        except Exception as e:
            print(f"[PathfindingService] Multiprocessing error: {e}"); import traceback; traceback.print_exc()
            model.set_pathfinding_data(grid, grid_origin, {}, {});
            self.precomputation_finished.emit(False, list(start_points_pdf_coords.keys()))


    def get_shortest_path(self, model: WarehouseModel, start_name: str, end_name: str) -> tuple[list[QPointF] | None, float | None]:
        if not model.path_data_is_valid or start_name not in model.path_maps or start_name not in model.distance_maps:
            # print(f"[PathfindingService get_shortest_path] Cannot get path. PathDataValid: {model.path_data_is_valid}, Start in maps: {start_name in model.path_maps}")
            return None, None

        start_point_pdf = model.pick_aisles.get(start_name)
        end_point_pdf = model.staging_locations.get(end_name)
        grid = model.pathfinding_grid
        grid_origin = model.grid_origin_pdf
        res_f = model.grid_resolution_factor

        if not all([start_point_pdf, end_point_pdf, grid is not None, grid_origin is not None, model.is_scale_set]):
             return None, None

        gh, gw = grid.shape

        # Print out debug information about the points
        print(f"[PathfindingService] get_shortest_path from {start_name} to {end_name}")
        print(f"[PathfindingService] Start point PDF: ({start_point_pdf.x():.2f}, {start_point_pdf.y():.2f})")
        print(f"[PathfindingService] End point PDF: ({end_point_pdf.x():.2f}, {end_point_pdf.y():.2f})")
        print(f"[PathfindingService] Grid origin PDF: ({grid_origin.x():.2f}, {grid_origin.y():.2f})")
        print(f"[PathfindingService] Grid dimensions: {gw}x{gh} cells, Resolution factor: {res_f}")
        
        # Calculate grid cell coordinates
        sc_float = (start_point_pdf.x() - grid_origin.x()) / res_f
        sr_float = (start_point_pdf.y() - grid_origin.y()) / res_f
        ec_float = (end_point_pdf.x() - grid_origin.x()) / res_f
        er_float = (end_point_pdf.y() - grid_origin.y()) / res_f
        
        # Check if points are within grid bounds before clamping
        start_in_bounds = 0 <= sc_float < gw and 0 <= sr_float < gh
        end_in_bounds = 0 <= ec_float < gw and 0 <= er_float < gh
        
        if not start_in_bounds:
            print(f"[PathfindingService] WARNING: Start point {start_name} is outside grid bounds! Raw grid cell: ({sr_float:.2f}, {sc_float:.2f})")
        if not end_in_bounds:
            print(f"[PathfindingService] WARNING: End point {end_name} is outside grid bounds! Raw grid cell: ({er_float:.2f}, {ec_float:.2f})")
        
        # Clamp to grid bounds
        sc = max(0, min(int(sc_float), gw-1))
        sr = max(0, min(int(sr_float), gh-1))
        ec = max(0, min(int(ec_float), gw-1))
        er = max(0, min(int(er_float), gh-1))
        s_cell, e_cell = (sr, sc), (er, ec)
        
        print(f"[PathfindingService] Start grid cell: {s_cell}, End grid cell: {e_cell}")

        # Check if destination is reachable
        dist_grid_cost = model.distance_maps[start_name][er, ec]
        if dist_grid_cost == np.inf:
            print(f"[PathfindingService] No path found from {start_name} to {end_name} - destination unreachable (cost=inf)")
            return None, None

        # Get the path
        path_cells = reconstruct_path(model.path_maps[start_name], s_cell, e_cell)
        if path_cells is None:
            print(f"[PathfindingService] Failed to reconstruct path from {start_name} to {end_name}")
            return None, None

        # Convert cell coordinates back to PDF coordinates
        hf = res_f / 2.0
        path_pts_pdf = [QPointF((c * res_f + hf) + grid_origin.x(), (r * res_f + hf) + grid_origin.y())
                        for r, c in path_cells]

        # Calculate the physical distance
        phys_dist_px = sum(math.dist(p1.toTuple(), p2.toTuple()) for p1, p2 in zip(path_pts_pdf, path_pts_pdf[1:]))
        
        if model.scale_pixels_per_unit is None or model.scale_pixels_per_unit <= 0:
             print("[PathfindingService] Warning: Scale not set or invalid, cannot calculate physical distance.")
             return path_pts_pdf, None

        dist_cal_unit = phys_dist_px / model.scale_pixels_per_unit
        disp_dist = self._convert_distance_units(dist_cal_unit, model.calibration_unit, model.display_unit)
        
        print(f"[PathfindingService] Path found with {len(path_pts_pdf)} points, distance: {disp_dist:.2f} {model.display_unit}")
        return path_pts_pdf, disp_dist

    def _convert_distance_units(self, value: float, from_unit: Optional[str], to_unit: Optional[str]) -> Optional[float]:
        if from_unit == to_unit or not from_unit or not to_unit: return value
        m_to_f = 3.28084
        if from_unit == "meters" and to_unit == "feet": return value * m_to_f
        if from_unit == "feet" and to_unit == "meters": return value / m_to_f
        print(f"[PathfindingService] Warn: Unsupported unit conversion {from_unit} to {to_unit}."); return None

    def save_grid_for_debug(self, model: WarehouseModel, file_path="debug_grid.png", path_cells_to_draw: Optional[List[Tuple[int,int]]] = None):
        if model.pathfinding_grid is None:
            print("[PathfindingService Debug] Grid is None, cannot save.")
            return

        grid_data = model.pathfinding_grid
        viz_grid = np.zeros_like(grid_data, dtype=float)
        val_free = 10.0; val_staging = 50.0; val_obstacle = 100.0
        viz_grid[grid_data == COST_EMPTY] = val_free
        staging_mask_viz = (grid_data > COST_EMPTY) & (grid_data < np.inf)
        viz_grid[staging_mask_viz] = val_staging
        viz_grid[grid_data == np.inf] = val_obstacle
        
        cmap = mcolors.ListedColormap(['white', 'lightblue', 'black'])
        norm_free_thresh = (val_free + val_staging) / 2 
        norm_staging_thresh = (val_staging + val_obstacle) / 2
        bounds_viz = [0, norm_free_thresh, norm_staging_thresh, val_obstacle + 1] 
        norm = mcolors.BoundaryNorm(bounds_viz, cmap.N)

        plt.figure(figsize=(12, 12 * grid_data.shape[0]/grid_data.shape[1] if grid_data.shape[1] > 0 else 12))
        plt.imshow(viz_grid, cmap=cmap, norm=norm, origin='upper', interpolation='nearest')
        
        patches = [
            plt.Rectangle((0,0),1,1,fc='white', label=f'Free Space (Cost ~{COST_EMPTY})'),
            plt.Rectangle((0,0),1,1,fc='lightblue', label=f'Staging Area (Penalty: {model.staging_area_penalty})'),
            plt.Rectangle((0,0),1,1,fc='black', label='Obstacle (Impassable)')
        ]
        plt.legend(handles=patches, bbox_to_anchor=(1.05, 1), loc='upper left')
        
        title_str = f"Pathfinding Grid (Res: {model.grid_resolution_factor}, Dil: {OBSTACLE_DILATION_ITERATIONS} iter"
        if model.grid_origin_pdf:
            title_str += f", Origin: {model.grid_origin_pdf.x():.0f},{model.grid_origin_pdf.y():.0f} PDF)"
        else:
            title_str += ")"
        plt.title(title_str)
        
        if path_cells_to_draw:
            if path_cells_to_draw:
                path_r, path_c = zip(*path_cells_to_draw)
                plt.plot(path_c, path_r, color='magenta', linewidth=0, marker='o', markersize=3)

        # plt.tight_layout(rect=[0, 0, 0.80, 1])
        # plt.savefig(file_path)
        # plt.close()
        # print(f"[PathfindingService Debug] Grid visualization saved to {file_path}")

    def export_path_data_to_csv(self, model: WarehouseModel, start_name: str, end_name: str, file_path: str) -> bool:
        """Export path data to CSV with coordinates, distances, and statistics."""
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'
            
        try:
            path_points, distance = self.get_shortest_path(model, start_name, end_name)
            if path_points is None or distance is None:
                self.export_path_data_failed.emit(f"No valid path found from {start_name} to {end_name}")
                return False
                
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # Write header information
                writer.writerow(["Path Information"])
                writer.writerow(["Start Location", start_name])
                writer.writerow(["End Location", end_name])
                writer.writerow(["Total Distance", f"{distance:.2f} {model.display_unit}"])
                writer.writerow(["Number of Points", len(path_points)])
                writer.writerow(["Grid Resolution Factor", model.grid_resolution_factor])
                writer.writerow([])
                
                # Write point data
                writer.writerow(["Point Index", "X (PDF)", "Y (PDF)", "Distance from Start", "Cumulative Distance"])
                
                # Calculate distances
                cumulative_distance = 0.0
                prev_point = None
                
                for i, point in enumerate(path_points):
                    dist_from_prev = 0.0
                    if prev_point:
                        dist_from_prev = math.dist(prev_point.toTuple(), point.toTuple())
                        if model.scale_pixels_per_unit and model.scale_pixels_per_unit > 0:
                            dist_from_prev = (dist_from_prev / model.scale_pixels_per_unit)
                            dist_from_prev = self._convert_distance_units(
                                dist_from_prev, model.calibration_unit, model.display_unit) or dist_from_prev
                    
                    cumulative_distance += dist_from_prev
                    writer.writerow([
                        i,
                        f"{point.x():.2f}",
                        f"{point.y():.2f}",
                        f"{dist_from_prev:.2f}" if i > 0 else "0.00",
                        f"{cumulative_distance:.2f}"
                    ])
                    prev_point = point
                    
            self.export_path_data_complete.emit(file_path)
            return True
        except Exception as e:
            print(f"[PathfindingService] Error exporting path data: {e}")
            import traceback
            traceback.print_exc()
            self.export_path_data_failed.emit(f"Failed to export path data: {e}")
            return False
            
    def export_path_image(self, model: WarehouseModel, path_points: list, file_path: str, 
                         include_obstacles: bool = True, title: str = None) -> bool:
        """Export a visualization of the path to an image file."""
        if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            file_path += '.png'
            
        try:
            if not path_points:
                self.export_path_image_failed.emit("No path points to export")
                return False
                
            # Set up matplotlib figure with no edges
            plt.figure(figsize=(12, 10))
            ax = plt.gca()
            
            # Draw obstacles if available and requested
            if include_obstacles and model.obstacles:
                for poly in model.obstacles:
                    points = [(p.x(), p.y()) for p in poly]
                    if points:
                        xs, ys = zip(*points)
                        ax.fill(xs, ys, color='gray', alpha=0.5, label='Obstacles')
            
            # Draw staging areas if available
            if model.staging_areas:
                for poly in model.staging_areas:
                    points = [(p.x(), p.y()) for p in poly]
                    if points:
                        xs, ys = zip(*points)
                        ax.fill(xs, ys, color='lightblue', alpha=0.3, label='Staging Areas')
            
            # Draw path
            x_coords = [p.x() for p in path_points]
            y_coords = [p.y() for p in path_points]
            ax.plot(x_coords, y_coords, 'r-', linewidth=2, label='Path')
            
            # Mark start and end points
            ax.plot(x_coords[0], y_coords[0], 'go', markersize=10, label='Start')
            ax.plot(x_coords[-1], y_coords[-1], 'bo', markersize=10, label='End')
            
            # Add title
            if title:
                plt.title(title)
            
            # Add grid and legend
            ax.grid(True, alpha=0.3)
            
            # Remove duplicate labels
            handles, labels = plt.gca().get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            plt.legend(by_label.values(), by_label.keys(), loc='best')
            
            # Equal aspect ratio to preserve shape
            plt.axis('equal')
            
            # Save figure
            plt.savefig(file_path, bbox_inches='tight')
            plt.close()
            
            self.export_path_image_complete.emit(file_path)
            return True
        except Exception as e:
            print(f"[PathfindingService] Error exporting path image: {e}")
            import traceback
            traceback.print_exc()
            self.export_path_image_failed.emit(f"Failed to export path image: {e}")
            return False

class AnalysisService(QObject):
    analysis_started = Signal(str)
    analysis_complete = Signal(list, list, str, str)
    analysis_failed = Signal(str)
    export_complete = Signal(str)
    export_failed = Signal(str)
    export_pdf_complete = Signal(str)
    export_pdf_failed = Signal(str)
    export_excel_complete = Signal(str)
    export_excel_failed = Signal(str)
    def _parse_flexible_datetime(self, time_str: str) -> datetime | None:
        if not time_str: return None
        try: iso_str = time_str.replace(' ', 'T').replace('Z', '+00:00'); dt = datetime.fromisoformat(iso_str); return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError: pass
        for fmt in ["%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]:
            try: dt = datetime.strptime(time_str, fmt); return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            except ValueError: continue
        return None

    def load_and_analyze(self, model: WarehouseModel, file_path: str,
                         dialect: Any, has_header: bool, col_indices: dict):
        print(f"[AnalysisService] Starting analysis for: {file_path}")
        if not model.path_data_is_valid:
            self.analysis_failed.emit("Pathfinding data not ready. Please Precompute."); return
        self.analysis_started.emit(file_path)
        results, warnings_list, proc_count, skip_count, no_start, no_end, no_path = [], [], 0,0,set(),set(),0
        id_idx,start_idx,end_idx,start_t_idx,end_t_idx = col_indices['id'],col_indices['start'],col_indices['end'],col_indices['start_time'],col_indices['end_time']
        path_svc = PathfindingService()
        try:
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                reader = csv.reader(f, dialect=dialect); row_num = 0
                if has_header: next(reader); row_num = 1
                for row_data in reader:
                    row_num+=1; proc_count+=1; p_id,s_name,e_name,s_t_str,e_t_str = f"R{row_num}","", "","",""
                    stat,p_date_str,dist_val = 'Pending',"",np.nan
                    try:
                        used_indices = [idx for idx in [id_idx,start_idx,end_idx,start_t_idx,end_t_idx] if idx >= 0]
                        max_used_idx = max(used_indices) if used_indices else -1
                        if len(row_data) <= max_used_idx : raise IndexError("Short row or invalid index")

                        p_id=row_data[id_idx].strip();s_name=row_data[start_idx].strip();e_name=row_data[end_idx].strip()
                        s_t_str=row_data[start_t_idx].strip() if start_t_idx >= 0 else ""
                        e_t_str=row_data[end_t_idx].strip() if end_t_idx >= 0 else ""
                        
                        p_dt=self._parse_flexible_datetime(s_t_str)
                        if p_dt: p_date_str=p_dt.strftime("%Y-%m-%d")
                        elif s_t_str and start_t_idx >=0 :
                            stat='DateParseErr'; warnings_list.append(f"R{row_num}({p_id}):Bad StartTime '{s_t_str}'")
                        
                        if not s_name or not e_name: stat='MissingLoc'
                        elif s_name not in model.pick_aisles: no_start.add(s_name); stat='MissingStart'
                        elif e_name not in model.staging_locations: no_end.add(e_name); stat='MissingEnd'
                        elif s_name not in model.path_maps: stat=f'NoPrecomp:{s_name}'
                        else:
                            pts,d = path_svc.get_shortest_path(model,s_name,e_name)
                            if pts is None: no_path+=1; stat='Unreachable'; dist_val=np.inf
                            elif d is None: stat='Unit/ScaleErr'
                            else: dist_val=d; stat='Success'
                    except IndexError: stat='MalformedRow'; warnings_list.append(f"R{row_num}:Malformed")
                    except Exception as e: stat='ProcErr'; warnings_list.append(f"R{row_num}({p_id}):Err-{e}")
                    if stat!='Success': skip_count+=1
                    results.append({'id':p_id,'start':s_name,'end':e_name,'distance':dist_val,'status':stat,'date':p_date_str,'start_time':s_t_str,'end_time':e_t_str})
            
            summary_warns = [f"Rows processed: {proc_count}"]
            if no_start: summary_warns.append(f"Missing Starts: {','.join(sorted(list(no_start)))}")
            if no_end: summary_warns.append(f"Missing Ends: {','.join(sorted(list(no_end)))}")
            if no_path > 0: summary_warns.append(f"Unreachable paths: {no_path}")
            if skip_count > 0 : summary_warns.append(f"Total rows with issues (incl. unreachable): {skip_count}")

            summary_warns.extend(warnings_list)
            self.analysis_complete.emit(results, summary_warns, model.display_unit, file_path)
        except Exception as e: self.analysis_failed.emit(f"Analysis failure: {e}")

    def export_results(self, results: list, unit: str, file_path: str):
        if not file_path.lower().endswith('.csv'): file_path += '.csv'
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                hdr = ["Picklist ID", "Start Location", "End Location", f"Distance ({unit})", "Status", "Date", "Orig Start Time", "Orig End Time"]
                w = csv.writer(f); w.writerow(hdr)
                for r_d in results:
                    d = r_d.get('distance'); status_val = r_d.get('status', "ERROR/SKIPPED")
                    d_s = f"{d:.2f}" if pd.notna(d) and d!=np.inf else status_val.upper()
                    w.writerow([r_d.get(k, '') for k in ['id','start','end']] + [d_s] + [status_val, r_d.get('date',''), r_d.get('start_time',''), r_d.get('end_time','')])
            self.export_complete.emit(file_path)
        except Exception as e: self.export_failed.emit(f"Export failed: {e}")

    def export_analysis_results(self, filtered_results: list, unit: str):
        """Opens a file dialog and exports the filtered analysis results."""
        if not filtered_results:
            self.export_failed.emit("No results to export.")
            return
            
        # Determine default filename
        default_name = "analysis_results.csv"
        
        # Get export path using dialog
        file_path, filter_selected = QFileDialog.getSaveFileName(
            None, "Export Analysis Results", 
            default_name, 
            "CSV (*.csv);;Excel (*.xlsx);;PDF Report (*.pdf);;Images (*.png)"
        )
        
        if not file_path:
            return
            
        # Export based on the selected filter
        if "CSV" in filter_selected:
            self.export_results(filtered_results, unit, file_path)
        elif "Excel" in filter_selected:
            self.export_to_excel(filtered_results, unit, file_path)
        elif "PDF" in filter_selected:
            self.export_to_pdf_report(filtered_results, unit, file_path)
        elif "Images" in filter_selected:
            self.export_visualization(filtered_results, unit, file_path)
            
    def export_to_excel(self, results: list, unit: str, file_path: str):
        """Export analysis results to Excel format with multiple sheets for data and charts."""
        if not file_path.lower().endswith('.xlsx'):
            file_path += '.xlsx'
            
        try:
            # Create DataFrame from results
            df = pd.DataFrame(results)
            
            # Filter successful paths for statistics
            success_df = df[df['status'] == 'Success'].copy()
            
            # Create Excel writer and workbook
            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                # Write main data to first sheet
                df.to_excel(writer, sheet_name='All Results', index=False)
                
                # Create statistics sheet
                if not success_df.empty:
                    # Add distance statistics
                    stats_df = pd.DataFrame({
                        'Statistic': [
                            'Count', 'Min Distance', 'Max Distance', 'Mean Distance', 
                            'Median Distance', 'Std Deviation', 'Total Distance'
                        ],
                        'Value': [
                            len(success_df),
                            success_df['distance'].min(),
                            success_df['distance'].max(),
                            success_df['distance'].mean(),
                            success_df['distance'].median(),
                            success_df['distance'].std(),
                            success_df['distance'].sum()
                        ]
                    })
                    
                    stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                    
                    # Get workbook and worksheet references
                    workbook = writer.book
                    stats_sheet = writer.sheets['Statistics']
                    
                    # Add unit formatting to values
                    for idx, val in enumerate(stats_df['Value']):
                        if idx > 0:  # Skip the count value
                            stats_sheet.write(idx+1, 1, f"{val:.2f} {unit}")
                
                # Format the main data sheet
                worksheet = writer.sheets['All Results']
                workbook = writer.book
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'bg_color': '#D9E1F2',
                    'border': 1
                })
                
                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                # Format distance column
                dist_col = df.columns.get_loc('distance')
                dist_format = workbook.add_format({'num_format': f'0.00 "{unit}"'})
                worksheet.set_column(dist_col, dist_col, 12, dist_format)
                
                # Auto-size columns
                for i, col in enumerate(df.columns):
                    column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, column_len)
                
            self.export_excel_complete.emit(file_path)
        except Exception as e:
            print(f"[AnalysisService] Error exporting to Excel: {e}")
            import traceback
            traceback.print_exc()
            self.export_excel_failed.emit(f"Failed to export Excel file: {e}")
            
    def export_to_pdf_report(self, results: list, unit: str, file_path: str):
        """Export analysis results to a PDF report with data, statistics and visualizations."""
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'
            
        try:
            # Create matplotlib figures for the report
            from matplotlib.backends.backend_pdf import PdfPages
            
            with PdfPages(file_path) as pdf:
                # Generate title page
                self._create_pdf_title_page(pdf, results, unit)
                
                # Generate statistics page
                self._create_pdf_statistics_page(pdf, results, unit)
                
                # Generate histogram
                self._create_pdf_histogram_page(pdf, results, unit)
                
                # Generate data table
                self._create_pdf_data_table_page(pdf, results, unit)
                
            self.export_pdf_complete.emit(file_path)
        except Exception as e:
            print(f"[AnalysisService] Error exporting to PDF: {e}")
            import traceback
            traceback.print_exc()
            self.export_pdf_failed.emit(f"Failed to export PDF report: {e}")
            
    def _create_pdf_title_page(self, pdf, results, unit):
        """Create title page for the PDF report."""
        plt.figure(figsize=(11, 8.5))
        plt.axis('off')
        
        # Title
        plt.text(0.5, 0.8, "Warehouse Path Analysis Report", fontsize=24, ha='center')
        
        # Subtitle with timestamp
        plt.text(0.5, 0.7, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                fontsize=14, ha='center')
        
        # Summary info
        success_count = sum(1 for r in results if r.get('status') == 'Success')
        fail_count = len(results) - success_count
        
        info_text = [
            f"Total Paths Analyzed: {len(results)}",
            f"Successful Paths: {success_count}",
            f"Failed/Unreachable Paths: {fail_count}",
            f"Distance Unit: {unit}"
        ]
        
        # Add dates if available
        dates = sorted(list(set(r.get('date', '') for r in results if r.get('date', ''))))
        if dates:
            date_range = f"Date Range: {dates[0]} to {dates[-1]}" if len(dates) > 1 else f"Date: {dates[0]}"
            info_text.append(date_range)
        
        y_pos = 0.6
        for line in info_text:
            plt.text(0.5, y_pos, line, fontsize=12, ha='center')
            y_pos -= 0.05
        
        # Footer
        plt.text(0.5, 0.05, "Warehouse PathFinder", fontsize=10, ha='center')
        
        pdf.savefig()
        plt.close()
        
    def _create_pdf_statistics_page(self, pdf, results, unit):
        """Create statistics page for the PDF report."""
        plt.figure(figsize=(11, 8.5))
        plt.axis('off')
        
        # Title
        plt.text(0.5, 0.95, "Path Statistics", fontsize=18, ha='center')
        
        # Filter successful paths to calculate statistics
        success_data = [r for r in results if r.get('status') == 'Success' and 
                       pd.notna(r.get('distance')) and r.get('distance') != np.inf]
        
        if success_data:
            distances = [r['distance'] for r in success_data]
            
            # Calculate statistics
            stats = {
                'Count': len(distances),
                'Minimum': min(distances),
                'Maximum': max(distances),
                'Mean': sum(distances) / len(distances),
                'Median': sorted(distances)[len(distances) // 2],
                'Std Deviation': np.std(distances),
                'Total': sum(distances)
            }
            
            # Create a table for statistics
            table_data = []
            for key, value in stats.items():
                if key == 'Count':
                    table_data.append([key, f"{value:,}"])
                else:
                    table_data.append([key, f"{value:.2f} {unit}"])
            
            table = plt.table(
                cellText=table_data,
                colLabels=['Statistic', 'Value'],
                loc='center',
                cellLoc='center',
                colWidths=[0.3, 0.3]
            )
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 2)
            
            # Add additional information
            if 'date' in results[0]:
                # Group by date if available
                date_groups = {}
                for r in success_data:
                    date = r.get('date', 'No Date')
                    if date not in date_groups:
                        date_groups[date] = []
                    date_groups[date].append(r['distance'])
                
                # Add date statistics if there are multiple dates
                if len(date_groups) > 1:
                    plt.figtext(0.5, 0.4, "Statistics by Date", fontsize=14, ha='center')
                    
                    date_stats = []
                    for date, dist_list in sorted(date_groups.items()):
                        date_stats.append([
                            date,
                            len(dist_list),
                            f"{sum(dist_list):.2f} {unit}",
                            f"{sum(dist_list)/len(dist_list):.2f} {unit}"
                        ])
                    
                    date_table = plt.table(
                        cellText=date_stats,
                        colLabels=['Date', 'Count', 'Total Distance', 'Average Distance'],
                        loc='center',
                        cellLoc='center',
                        bbox=[0.1, 0.05, 0.8, 0.25]
                    )
                    
                    date_table.auto_set_font_size(False)
                    date_table.set_fontsize(9)
                    date_table.scale(1, 1.5)
        else:
            # No success data
            plt.text(0.5, 0.5, "No successful paths to analyze", fontsize=12, ha='center')
        
        pdf.savefig()
        plt.close()
        
    def _create_pdf_histogram_page(self, pdf, results, unit):
        """Create histogram page for the PDF report."""
        plt.figure(figsize=(11, 8.5))
        
        # Filter successful paths to calculate statistics
        distances_to_plot = [r['distance'] for r in results if r.get('status') == 'Success' and 
                            pd.notna(r.get('distance')) and r.get('distance') != np.inf]
        
        if distances_to_plot:
            plt.hist(distances_to_plot, bins='auto', color='skyblue', edgecolor='black')
            plt.title('Distribution of Path Distances', fontsize=18)
            plt.xlabel(f'Distance ({unit})', fontsize=12)
            plt.ylabel('Frequency', fontsize=12)
            plt.grid(axis='y', alpha=0.7)
        else:
            plt.axis('off')
            plt.text(0.5, 0.5, "No valid distances to plot", fontsize=14, ha='center', va='center')
        
        pdf.savefig()
        plt.close()
        
    def _create_pdf_data_table_page(self, pdf, results, unit):
        """Create data table page for the PDF report."""
        plt.figure(figsize=(11, 8.5))
        plt.axis('off')
        
        # Title
        plt.text(0.5, 0.95, "Path Data", fontsize=18, ha='center')
        
        # Create table data - limit to first 30 rows for readability
        display_results = results[:30]
        
        if display_results:
            table_data = []
            for r in display_results:
                dist_val = r.get('distance')
                if pd.notna(dist_val) and dist_val != np.inf:
                    distance_str = f"{dist_val:.2f} {unit}"
                else:
                    distance_str = "N/A"
                    
                table_data.append([
                    r.get('id', 'N/A'),
                    r.get('start', 'N/A'),
                    r.get('end', 'N/A'),
                    distance_str,
                    r.get('status', 'N/A')
                ])
            
            table = plt.table(
                cellText=table_data,
                colLabels=['ID', 'Start', 'End', 'Distance', 'Status'],
                loc='center',
                cellLoc='center',
                bbox=[0.05, 0.05, 0.9, 0.8]
            )
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            
            # Add note if results were truncated
            if len(results) > 30:
                plt.figtext(0.5, 0.02, f"Note: Showing 30 of {len(results)} total results", 
                         fontsize=8, ha='center')
        else:
            plt.text(0.5, 0.5, "No path data to display", fontsize=14, ha='center')
        
        pdf.savefig()
        plt.close()
        
    def export_visualization(self, results: list, unit: str, file_path: str):
        """Export visualization of the analysis results."""
        if not file_path.lower().endswith('.png'):
            file_path += '.png'
            
        try:
            plt.figure(figsize=(12, 8))
            
            # Filter successful paths to calculate statistics
            distances = [r['distance'] for r in results if r.get('status') == 'Success' and 
                        pd.notna(r.get('distance')) and r.get('distance') != np.inf]
            
            if distances:
                # Create main histogram
                plt.subplot(2, 2, 1)
                plt.hist(distances, bins='auto', color='skyblue', edgecolor='black')
                plt.title('Distance Distribution')
                plt.xlabel(f'Distance ({unit})')
                plt.ylabel('Frequency')
                plt.grid(True, alpha=0.3)
                
                # Create statistics text
                plt.subplot(2, 2, 2)
                plt.axis('off')
                stats_text = [
                    f"Total Paths: {len(results)}",
                    f"Valid Paths: {len(distances)}",
                    f"Min Distance: {min(distances):.2f} {unit}",
                    f"Max Distance: {max(distances):.2f} {unit}",
                    f"Mean Distance: {sum(distances)/len(distances):.2f} {unit}",
                    f"Total Distance: {sum(distances):.2f} {unit}"
                ]
                
                plt.text(0.5, 0.5, "\n".join(stats_text), 
                       ha='center', va='center', fontsize=10)
                
                # Create status pie chart
                plt.subplot(2, 2, 3)
                status_counts = {}
                for r in results:
                    status = r.get('status', 'Unknown')
                    if status not in status_counts:
                        status_counts[status] = 0
                    status_counts[status] += 1
                
                plt.pie(
                    status_counts.values(), 
                    labels=status_counts.keys(),
                    autopct='%1.1f%%',
                    startangle=90
                )
                plt.title('Path Status Distribution')
                
                # If we have date information, add a timeline plot
                if 'date' in results[0]:
                    plt.subplot(2, 2, 4)
                    
                    # Group by date
                    date_distances = {}
                    for r in results:
                        if r.get('status') == 'Success' and pd.notna(r.get('distance')):
                            date = r.get('date', '')
                            if date:
                                if date not in date_distances:
                                    date_distances[date] = []
                                date_distances[date].append(r['distance'])
                    
                    # Calculate averages by date
                    dates = []
                    avg_distances = []
                    for date, dist_list in sorted(date_distances.items()):
                        dates.append(date)
                        avg_distances.append(sum(dist_list) / len(dist_list))
                    
                    if dates:
                        plt.plot(dates, avg_distances, 'o-', color='green')
                        plt.title('Average Distance by Date')
                        plt.xlabel('Date')
                        plt.ylabel(f'Avg Distance ({unit})')
                        plt.xticks(rotation=45)
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                
                plt.suptitle('Path Analysis Visualization', fontsize=16)
                plt.tight_layout()
                plt.subplots_adjust(top=0.9)
            else:
                plt.text(0.5, 0.5, "No valid distances to visualize", 
                       ha='center', va='center', fontsize=14)
            
            plt.savefig(file_path, bbox_inches='tight')
            plt.close()
            
            self.export_complete.emit(file_path)
        except Exception as e:
            print(f"[AnalysisService] Error exporting visualization: {e}")
            import traceback
            traceback.print_exc()
            self.export_failed.emit(f"Failed to export visualization: {e}")

class AnimationService(QObject):
    preparation_started = Signal(str)
    preparation_complete = Signal(list, datetime)
    preparation_failed = Signal(str)
    preparation_warning = Signal(str)

    def _parse_flexible_datetime(self, time_str: str) -> datetime | None:
        if not time_str: return None
        try: iso_str = time_str.replace(' ', 'T').replace('Z', '+00:00'); dt = datetime.fromisoformat(iso_str); return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError: pass
        for fmt in ["%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]:
            try: dt = datetime.strptime(time_str, fmt); return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            except ValueError: continue
        return None

    def prepare_animation_data(self, model: WarehouseModel, file_path: str, selection_data: dict):
        if not model.path_data_is_valid:
            self.preparation_failed.emit("Path data invalid. Precompute."); return
        self.preparation_started.emit(file_path)
        try:
            dialect,has_header,indices = selection_data['dialect'],selection_data['has_header'],selection_data['indices']
            id_idx,s_loc_idx,e_loc_idx,s_time_idx,e_time_idx = indices['id'],indices['start_loc'],indices['end_loc'],indices['start_time'],indices['end_time']
        except KeyError as e: self.preparation_failed.emit(f"Missing selection key: {e}"); return

        temp_rows, earliest_dt, warnings_list = [], None, []
        path_svc = PathfindingService()

        try:
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                reader = csv.reader(f, dialect=dialect); row_num = 0
                if has_header: next(reader); row_num = 1
                for row in reader:
                    row_num+=1; temp_data={'row_num':row_num,'id':f"R{row_num}",'valid':False}
                    try:
                        used_indices = [idx for idx in [id_idx,s_loc_idx,e_loc_idx,s_time_idx,e_time_idx] if idx >= 0]
                        max_used_idx = max(used_indices) if used_indices else -1
                        if len(row) <= max_used_idx:
                            raise IndexError("Short row or invalid index")
                        
                        temp_data['id']=row[id_idx].strip(); s_name=row[s_loc_idx].strip(); e_name=row[e_loc_idx].strip()
                        s_t_str=row[s_time_idx].strip(); e_t_str=row[e_time_idx].strip()
                        
                        if not all([s_name,e_name,s_t_str,e_t_str]): 
                            warnings_list.append(f"R{row_num}({temp_data['id']}): Missing required data (locs or times)"); temp_rows.append(temp_data); continue
                        if s_name not in model.pick_aisles or e_name not in model.staging_locations: 
                            warnings_list.append(f"R{row_num}({temp_data['id']}): Loc not found ({s_name} or {e_name})"); temp_rows.append(temp_data); continue
                        
                        s_dt=self._parse_flexible_datetime(s_t_str); e_dt=self._parse_flexible_datetime(e_t_str)
                        if not s_dt or not e_dt: 
                            warnings_list.append(f"R{row_num}({temp_data['id']}): Invalid time format ('{s_t_str}' or '{e_t_str}')"); temp_rows.append(temp_data); continue
                        if s_dt >= e_dt:
                            warnings_list.append(f"R{row_num}({temp_data['id']}): Start time not before end time"); temp_rows.append(temp_data); continue
                        
                        cur_early = s_dt
                        if earliest_dt is None or cur_early < earliest_dt: earliest_dt = cur_early
                        temp_data.update({'start_name':s_name,'end_name':e_name,'start_dt':s_dt,'end_dt':e_dt,'valid':True}); temp_rows.append(temp_data)
                    
                    except IndexError: warnings_list.append(f"R{row_num}: Malformed row (not enough columns)"); temp_rows.append(temp_data)
                    except Exception as e: warnings_list.append(f"R{row_num}({temp_data['id']}): Processing error - {e}"); temp_rows.append(temp_data)
            
            if earliest_dt is None and not temp_rows:
                 self.preparation_failed.emit("CSV file appears to be empty or no rows processed."); return
            if earliest_dt is None and temp_rows:
                 self.preparation_failed.emit("No valid timestamps found in any processed rows."); return

        except Exception as e: self.preparation_failed.emit(f"File read error: {e}"); return

        anim_data = []
        for data in temp_rows:
            if not data.get('valid'): continue
            s_name,e_name,s_dt,e_dt,p_id,r_num = data['start_name'],data['end_name'],data['start_dt'],data['end_dt'],data['id'],data['row_num']
            try:
                s_time_s = max(0.0, (s_dt - earliest_dt).total_seconds())
                e_time_s = max(s_time_s + 1e-6, (e_dt - earliest_dt).total_seconds())
                
                pts, _ = path_svc.get_shortest_path(model, s_name, e_name)
                if pts is None: 
                    warnings_list.append(f"R{r_num}({p_id}): No path found for {s_name}->{e_name}"); continue
                anim_data.append({'id':p_id,'start_name':s_name,'end_name':e_name,'start_time_s':s_time_s,'end_time_s':e_time_s,
                                     'start_dt':s_dt,'end_dt':e_dt,'path_points':pts})
            except Exception as e: warnings_list.append(f"R{r_num}({p_id}) (Path/Time Calc): {e}")

        if not anim_data: 
            summary_warn = "No valid animation entries after path finding."
            if warnings_list: summary_warn += f" First warning: {warnings_list[0]}"
            self.preparation_failed.emit(summary_warn); return
        
        if warnings_list: 
            consolidated_warning = f"Processed with {len(warnings_list)} warnings. First few: {'; '.join(warnings_list[:3])}"
            if len(warnings_list) > 3: consolidated_warning += "..."
            self.preparation_warning.emit(consolidated_warning)
        
        if anim_data and earliest_dt:
            self.preparation_complete.emit(anim_data, earliest_dt)
        elif not earliest_dt and anim_data:
            self.preparation_failed.emit("Animation data prepared but earliest_dt is missing.")

class SearchService(QObject):
    """Handles search and filtering operations for warehouse elements."""
    
    search_points_completed = Signal(list)
    search_obstacles_completed = Signal(list)
    search_paths_completed = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def search_points(self, model: WarehouseModel, search_text: str, filter_options: dict) -> list:
        """Search for points matching the criteria
        
        Args:
            model: The warehouse model
            search_text: Text to search for in point names
            filter_options: Dict with 'pick_aisles' and 'staging_locations' boolean flags
            
        Returns:
            List of matching point dicts with name, type, and position
        """
        results = []
        search_text = search_text.lower()
        
        # Search pick aisles if enabled in filter options
        if filter_options.get('pick_aisles', True):
            for name, pos in model.pick_aisles.items():
                if search_text in name.lower():
                    results.append({
                        'name': name,
                        'type': 'Pick Aisle',
                        'position': pos,
                        'point_type': 'pick_aisle'
                    })
        
        # Search staging locations if enabled in filter options
        if filter_options.get('staging_locations', True):
            for name, pos in model.staging_locations.items():
                if search_text in name.lower():
                    results.append({
                        'name': name,
                        'type': 'Staging Location',
                        'position': pos,
                        'point_type': 'staging_location'
                    })
        
        # Sort results by name
        results.sort(key=lambda x: x['name'])
        
        self.search_points_completed.emit(results)
        return results
    
    def search_obstacles(self, model: WarehouseModel, search_text: str, filter_options: dict) -> list:
        """Search for obstacles matching the criteria
        
        Args:
            model: The warehouse model
            search_text: Text to search for (not currently used since obstacles don't have names)
            filter_options: Dict with 'obstacles' and 'staging_areas' boolean flags
            
        Returns:
            List of matching obstacle dicts with id, type, polygon, and area
        """
        results = []
        
        # Include obstacles if enabled in filter options
        if filter_options.get('obstacles', True):
            for i, polygon in enumerate(model.obstacles):
                # Calculate area as a simple metric for filtering large/small obstacles
                area = self._calculate_polygon_area(polygon)
                
                results.append({
                    'id': i + 1,  # 1-based indexing for display
                    'type': 'Obstacle',
                    'polygon': polygon,
                    'area': area,
                    'is_staging_area': False
                })
        
        # Include staging areas if enabled in filter options
        if filter_options.get('staging_areas', True):
            for i, polygon in enumerate(model.staging_areas):
                area = self._calculate_polygon_area(polygon)
                
                results.append({
                    'id': i + 1,  # 1-based indexing for display
                    'type': 'Staging Area',
                    'polygon': polygon,
                    'area': area,
                    'is_staging_area': True
                })
        
        # Sort results by area (largest first)
        results.sort(key=lambda x: x['area'], reverse=True)
        
        self.search_obstacles_completed.emit(results)
        return results
    
    def filter_paths(self, model: WarehouseModel, start_point: str, end_point: str, 
                    filter_options: dict, pathfinding_service: Optional['PathfindingService'] = None) -> list:
        """Filter possible paths based on criteria
        
        Args:
            model: The warehouse model
            start_point: Start point name or "Any"
            end_point: End point name or "Any"
            filter_options: Dict with filter criteria
            pathfinding_service: Optional pathfinding service for calculating paths
            
        Returns:
            List of paths matching the criteria
        """
        results = []
        
        # Check if we can calculate paths
        if not model.path_data_is_valid:
            self.search_paths_completed.emit([])
            return []
        
        # Define which pick aisles to use as start points
        start_points = list(model.pick_aisles.keys())
        if start_point != "Any":
            start_points = [p for p in start_points if p == start_point]
            
        # Define which staging locations to use as end points
        end_points = list(model.staging_locations.keys())
        if end_point != "Any":
            end_points = [p for p in end_points if p == end_point]
        
        # Calculate paths between selected points
        if pathfinding_service:
            paths = []
            for s_name in start_points:
                for e_name in end_points:
                    path_points, distance = pathfinding_service.get_shortest_path(model, s_name, e_name)
                    if path_points and distance is not None:
                        paths.append({
                            'start': s_name,
                            'end': e_name,
                            'path_points': path_points,
                            'distance': distance,
                            'distance_display': f"{distance:.2f} {model.display_unit}"
                        })
            
            # Apply length filtering if specified
            length_filter = filter_options.get('length_filter', 'Any Length')
            if length_filter != 'Any Length' and paths:
                # Sort paths by distance
                sorted_paths = sorted(paths, key=lambda x: x['distance'])
                
                # Select appropriate subset based on filter
                if length_filter == 'Shortest':
                    # Take approximately the shortest 25% of paths
                    count = max(1, len(sorted_paths) // 4)
                    paths = sorted_paths[:count]
                elif length_filter == 'Medium':
                    # Take the middle 50% of paths
                    start_idx = len(sorted_paths) // 4
                    end_idx = start_idx + (len(sorted_paths) // 2)
                    paths = sorted_paths[start_idx:end_idx]
                elif length_filter == 'Longest':
                    # Take approximately the longest 25% of paths
                    count = max(1, len(sorted_paths) // 4)
                    paths = sorted_paths[-count:]
            
            results = paths
        
        self.search_paths_completed.emit(results)
        return results
    
    def _calculate_polygon_area(self, polygon: QPolygonF) -> float:
        """Calculate the area of a polygon in square pixels"""
        if not polygon or polygon.isEmpty():
            return 0.0
            
        area = 0.0
        j = polygon.size() - 1
        
        for i in range(polygon.size()):
            p1 = polygon.at(i)
            p2 = polygon.at(j)
            area += (p2.x() + p1.x()) * (p2.y() - p1.y())
            j = i
            
        return abs(area) / 2.0

# --- END OF FILE Warehouse-Path-Finder-main/services.py ---