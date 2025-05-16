# --- START OF FILE Warehouse-Path-Finder-main/pdf_viewer.py ---

import fitz  # PyMuPDF
import math
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsLineItem,
    QGraphicsPolygonItem, QGraphicsItem, QGraphicsEllipseItem, QGraphicsSimpleTextItem,
    QGraphicsPathItem, QMessageBox, QRubberBand, QGraphicsItemGroup, QGraphicsRectItem,
    QMenu, QApplication, QGraphicsPixmapItem, QToolTip
)
from PySide6.QtGui import (
    QPixmap, QImage, QPen, QCursor, QBrush, QColor, QKeyEvent, QFont,
    QPainterPath, QTransform, QMouseEvent, QWheelEvent,
    QPolygonF, QAction
)
from PySide6.QtCore import (
    Qt, Signal, QRectF, QSize, QEvent,
    QPointF, QLineF, QMimeData, QSizeF, Slot
)

# Assuming enums.py is in the same directory or accessible in PYTHONPATH
from enums import InteractionMode, PointType, AnimationMode

# --- CORRECTED IMPORT HERE ---
from typing import Optional, List, Dict, Tuple, Any

# --- Check if theme_manager exists ---
try:
    from theme_manager import ThemeManager
    HAS_THEME_MANAGER = True
except ImportError:
    HAS_THEME_MANAGER = False


# Configuration
OBSTACLE_SNAP_DISTANCE = 10.0 # Scene pixels for snapping polygon close
POINT_MARKER_RADIUS = 5
LABEL_OFFSET_X = 8
LABEL_OFFSET_Y = -POINT_MARKER_RADIUS
STAGING_AREA_ALPHA = int(255 * 0.25) # 25% opacity
ANIMATION_OVERLAY_Z_VALUE = 100
POINTS_Z_VALUE = 20
PATH_Z_VALUE = 15
OBSTACLES_Z_VALUE = 10
STAGING_AREAS_Z_VALUE = 9
PDF_Z_VALUE = 0
BOUNDS_Z_VALUE = 8 # Below staging areas but above PDF

# Set this to True if you need detailed per-frame logs again temporarily
DEBUG_ANIMATION_VERBOSE = False

class PointLabelItem(QGraphicsSimpleTextItem):
    """Custom label that follows its parent point when moved."""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        
    def sceneEventFilter(self, watched, event):
        """Handle events from the watched item (the point)."""
        if event.type() in [QEvent.GraphicsSceneMove, QEvent.GraphicsSceneMouseRelease]:
            # Update label position when point is moved
            point_pos = watched.scenePos()
            self.setPos(point_pos + QPointF(10, 0))  # Offset to the right
            return False  # Don't consume the event
        return False

class PdfViewer(QGraphicsView):
    # --- Signals for User Interactions and State Changes ---
    scale_line_drawn = Signal(QPointF, QPointF)
    polygon_drawn = Signal(InteractionMode, QPolygonF)
    point_placement_requested = Signal(PointType, QPointF)
    line_definition_requested = Signal(PointType, QPointF, QPointF)
    # item_moved_in_edit signal now emits new geometry (QPolygonF or QPointF)
    item_moved_in_edit = Signal(QGraphicsItem, object) # QGraphicsItem, (QPolygonF or QPointF) - 'object' is a generic fallback for Any
    delete_items_requested = Signal(list) # list of QGraphicsItem references
    status_update = Signal(str, int)
    view_changed = Signal()
    mode_changed = Signal(InteractionMode)  # New signal to notify when mode changes
    zoom_level_changed = Signal(float)  # Signal to notify when zoom level changes
    pdf_dropped = Signal(str)

    # Add new signals for search-related functionality
    item_highlighted = Signal(str, object)  # item_type, item_data

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.pdf_document: Optional[fitz.Document] = None
        self.current_page_index = 0
        self.current_pdf_path: Optional[str] = None
        self.pixmap_item: Optional[QGraphicsItem] = None
        
        # Track zoom level
        self._base_zoom_level = 1.0
        self._current_zoom_level = 1.0

        self.current_mode = InteractionMode.IDLE
        self._is_panning = False
        self._last_pan_pos = QPointF()
        self._item_being_moved_in_edit: Optional[QGraphicsItem] = None
        self._item_being_moved_in_edit_start_pos: QPointF = QPointF()

        self._temp_drawing_points: List[QPointF] = []
        self._temp_line_item: Optional[QGraphicsLineItem] = None
        self._temp_polygon_item: Optional[QGraphicsPolygonItem] = None

        self._pathfinding_bounds_item: Optional[QGraphicsPolygonItem] = None # Item to display bounds
        self._obstacle_items: List[QGraphicsPolygonItem] = []
        self._staging_area_items: List[QGraphicsPolygonItem] = []
        self._start_point_items: Dict[str, Tuple[QGraphicsEllipseItem, QGraphicsSimpleTextItem]] = {}
        self._end_point_items: Dict[str, Tuple[QGraphicsEllipseItem, QGraphicsSimpleTextItem]] = {}
        self._path_item: Optional[QGraphicsPathItem] = None
        self.animation_overlay_group: Optional[QGraphicsItemGroup] = None
        # Add a mapping from graphics items to model polygons for easier deletion and editing
        self.item_to_model_polygon_map: Dict[QGraphicsItem, QPolygonF] = {}
        # Initialize animation overlay group
        self.animation_overlay_group = self.scene().createItemGroup([])
        self.animation_overlay_group.setZValue(ANIMATION_OVERLAY_Z_VALUE)

        self._setup_styles()
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setMouseTracking(True)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        
        # Enhanced focus handling for better keyboard accessibility
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setInteractive(True)
        
        # Create keyboard navigation indicators
        self._keyboard_focus_rect = None
        self._keyboard_focus_pos = QPointF(0, 0)
        self._keyboard_nav_step = 10  # Pixels to move per key press

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Add properties for search/highlight functionality
        self._highlighted_items = []

    def _setup_styles(self):
        # Check if we're in dark mode
        is_dark_mode = False
        if HAS_THEME_MANAGER:
            # Try to find the theme manager in the application
            app = QApplication.instance()
            main_windows = [w for w in app.topLevelWidgets() if w.__class__.__name__ == 'MainWindow']
            if main_windows and hasattr(main_windows[0], 'theme_manager'):
                is_dark_mode = main_windows[0].theme_manager.is_dark_theme()
        
        # Set colors based on theme
        if is_dark_mode:
            # Dark mode colors
            obstacle_color = QColor(220, 50, 50)  # Brighter red
            staging_area_color = QColor(50, 50, 220)  # Brighter blue
            bounds_color = QColor(180, 50, 180)  # Brighter purple
            path_color = QColor(50, 150, 255)  # Brighter blue for path
            
            # Background color setting for dark mode
            self.setBackgroundBrush(QBrush(QColor(45, 45, 45)))
        else:
            # Light mode colors (original colors)
            obstacle_color = QColor(Qt.GlobalColor.darkRed)
            staging_area_color = QColor(0, 0, 200)
            bounds_color = QColor(128, 0, 128)  # Purple
            path_color = QColor(0, 100, 255)
            
            # Background color setting for light mode
            self.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        
        # Set up pens and brushes with the theme-appropriate colors
        self._obstacle_pen = QPen(obstacle_color, 1)
        self._obstacle_pen.setCosmetic(True)
        self._obstacle_brush = QBrush(QColor(obstacle_color.red(), obstacle_color.green(), obstacle_color.blue(), 60))
        self._obstacle_preview_pen = QPen(obstacle_color, 1, Qt.PenStyle.DashLine)
        self._obstacle_preview_pen.setCosmetic(True)

        self._staging_area_pen = QPen(staging_area_color, 1)
        self._staging_area_pen.setCosmetic(True)
        self._staging_area_brush = QBrush(QColor(staging_area_color.red(), staging_area_color.green(), staging_area_color.blue(), STAGING_AREA_ALPHA))
        self._staging_area_preview_pen = QPen(QColor(0, 150, 150), 1, Qt.PenStyle.DashLine)
        self._staging_area_preview_pen.setCosmetic(True)

        self._bounds_pen = QPen(bounds_color, 3, Qt.PenStyle.SolidLine)
        self._bounds_pen.setCosmetic(True)
        self._bounds_brush = QBrush(Qt.GlobalColor.transparent)
        self._bounds_preview_pen = QPen(bounds_color, 2, Qt.PenStyle.DashLine)
        self._bounds_preview_pen.setCosmetic(True)        

        self._line_def_pen = QPen(Qt.GlobalColor.magenta, 1, Qt.PenStyle.DashLine)
        self._line_def_pen.setCosmetic(True)
        
        # Improve scale line visibility with brighter color and thicker line
        self._scale_line_pen = QPen(QColor(255, 0, 0), 3, Qt.PenStyle.DashLine)
        self._scale_line_pen.setCosmetic(True)

        self._start_point_pen = QPen(Qt.GlobalColor.green, 1)
        self._start_point_pen.setCosmetic(True)
        self._start_point_brush = QBrush(Qt.GlobalColor.green)
        self._end_point_pen = QPen(Qt.GlobalColor.blue, 1)
        self._end_point_pen.setCosmetic(True)
        self._end_point_brush = QBrush(Qt.GlobalColor.blue)
        self._path_pen = QPen(path_color, 2, Qt.PenStyle.SolidLine)
        self._path_pen.setCosmetic(True)
        self._label_font = QFont("Arial", 8)

    def _clear_scene_items(self, clear_pdf=True):
        # ... (rest of the method unchanged) ...
        print("[PdfViewer] Clearing scene items...")
        if clear_pdf and self.pixmap_item and self.pixmap_item.scene():
            self.scene().removeItem(self.pixmap_item)
            self.pixmap_item = None
        self.clear_obstacles()
        self.clear_staging_areas()
        self.clear_all_points()
        self.clear_pathfinding_bounds_item()
        self.clear_path()
        self.clear_animation_overlay()
        self._reset_temp_drawing_items()
        
        # Clear keyboard focus indicator
        self._remove_keyboard_focus_indicator()

    def load_pdf(self, file_path: str) -> tuple[bool, Optional[QRectF]]:
        # ... (rest of the method unchanged) ...
        self.set_mode(InteractionMode.IDLE)
        self._is_panning = False
        self._clear_scene_items(clear_pdf=True)
        try:
            self.pdf_document = fitz.open(file_path)
            if self.pdf_document.page_count > 0:
                self.current_pdf_path = file_path
                self.current_page_index = 0
                bounds = self._display_page(self.current_page_index)
                print(f"[PdfViewer] Loaded PDF: {file_path}")
                return True, bounds
            else: print("[PdfViewer] PDF has no pages."); self.pdf_document = None; self.current_pdf_path = None; return False, None
        except Exception as e:
            print(f"[PdfViewer] Error loading PDF: {e}"); self.pdf_document = None; self.current_pdf_path = None; return False, None


    def _display_page(self, page_number: int) -> Optional[QRectF]:
        """Display the specified page of the PDF. Returns the page bounds or None if error."""
        if not self.pdf_document or page_number < 0 or page_number >= self.pdf_document.page_count:
            return None

        # Clear existing scene items
        self._clear_scene_items(clear_pdf=True)
        
        # Reset zoom level on new page
        self._base_zoom_level = 1.0
        self._current_zoom_level = 1.0

        # Try to display the page
        try:
            # Get the page using PyMuPDF
            page = self.pdf_document.load_page(page_number)
            # Convert the page to a pixmap/image
            # Use a scale factor of 2.0 for higher resolution/quality
            matrix = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=matrix)
            img_data = pix.samples
            
            # Convert to QImage
            q_img = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            
            # Create QPixmap from QImage
            pixmap = QPixmap.fromImage(q_img)
            self.pixmap_item = self.scene().addPixmap(pixmap)
            self.pixmap_item.setZValue(PDF_Z_VALUE)
            
            # Set scene rect
            buffer = 50  # Add some padding around the page
            self.scene().setSceneRect(self.pixmap_item.boundingRect().adjusted(-buffer, -buffer, buffer, buffer))
            
            # Fit the view to show the entire page
            self.resetTransform()
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            
            # Update zoom level after fitInView
            transform = self.transform()
            self._current_zoom_level = (transform.m11() + transform.m22()) / 2.0
            self.zoom_level_changed.emit(self.get_zoom_percentage())
            
            # Return the page bounds
            rect = page.rect
            return QRectF(rect.x0, rect.y0, rect.width, rect.height)
            
        except Exception as e:
            print(f"Error displaying PDF page: {e}")
            return None

    def set_mode(self, mode: InteractionMode):
        print(f"[PdfViewer] Setting mode to: {mode}")
        if self.current_mode == mode:
            return  # Already in this mode
        
        prev_mode = self.current_mode
        
        # Don't reset drawing points when transitioning between related drawing modes
        should_reset_temp_drawing = True
        
        # Define pairs of related drawing modes where we want to preserve temp points
        related_mode_pairs = [
            (InteractionMode.SET_SCALE_START, InteractionMode.SET_SCALE_END),
            (InteractionMode.DEFINE_AISLE_LINE_START, InteractionMode.DEFINE_AISLE_LINE_END),
            (InteractionMode.DEFINE_STAGING_LINE_START, InteractionMode.DEFINE_STAGING_LINE_END)
        ]
        
        # Check if we're transitioning between related modes
        for start_mode, end_mode in related_mode_pairs:
            if (prev_mode == start_mode and mode == end_mode):
                should_reset_temp_drawing = False
                print(f"[PdfViewer DEBUG] Preserving drawing points when transitioning from {prev_mode.name} to {mode.name}")
                print(f"[PdfViewer DEBUG] Current temp_drawing_points: {self._temp_drawing_points}")
                break
                
        # Only reset drawing items if needed
        if should_reset_temp_drawing:
            print(f"[PdfViewer DEBUG] Resetting drawing points when transitioning from {prev_mode.name} to {mode.name}")
            self._reset_temp_drawing_items()
        
        self.current_mode = mode
        
        # Remove keyboard focus indicator when entering panning mode
        if mode == InteractionMode.PANNING:
            self._remove_keyboard_focus_indicator()
        
        # Set edit mode flags based on whether we're in EDIT mode
        self.set_edit_mode_flags(mode == InteractionMode.EDIT)
        
        # Update cursor based on mode
        if mode == InteractionMode.IDLE:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        elif mode == InteractionMode.PANNING:
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        elif mode in (InteractionMode.SET_SCALE_START, InteractionMode.SET_SCALE_END,
                     InteractionMode.SET_START_POINT, InteractionMode.SET_END_POINT):
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        elif mode in (InteractionMode.DRAW_OBSTACLE, InteractionMode.DEFINE_STAGING_AREA, 
                     InteractionMode.DEFINE_PATHFINDING_BOUNDS,
                     InteractionMode.DEFINE_AISLE_LINE_START, InteractionMode.DEFINE_AISLE_LINE_END,
                     InteractionMode.DEFINE_STAGING_LINE_START, InteractionMode.DEFINE_STAGING_LINE_END):
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        elif mode == InteractionMode.EDIT:
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Emit the mode_changed signal
        self.mode_changed.emit(mode)
        
        # Emit status update
        self.status_update.emit(f"Mode: {mode.name}", 2000)

    def set_edit_mode_flags(self, is_edit_mode):
        """Set item flags for interactivity when in edit mode."""
        cursor = Qt.CursorShape.SizeAllCursor if is_edit_mode else Qt.CursorShape.ArrowCursor
        self.viewport().setCursor(cursor)
        
        # Set flags on existing items to make them draggable in edit mode
        for item_list in [self._obstacle_items, self._staging_area_items]:
            for item in item_list:
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, is_edit_mode)
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, is_edit_mode)
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, is_edit_mode)
        
        # Set flags on point items
        for point_dict in [self._start_point_items, self._end_point_items]:
            for point_item, label_item in point_dict.values():
                point_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, is_edit_mode)
                point_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, is_edit_mode)
                point_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, is_edit_mode)
                # Make label follow the point
                if is_edit_mode:
                    point_item.installSceneEventFilter(label_item)
                else:
                    point_item.removeSceneEventFilter(label_item)

    def _reset_temp_drawing_items(self):
        # ... (rest of the method unchanged) ...
        self._temp_drawing_points.clear()
        if self._temp_line_item and self._temp_line_item.scene(): self.scene().removeItem(self._temp_line_item)
        self._temp_line_item = None
        if self._temp_polygon_item and self._temp_polygon_item.scene(): self.scene().removeItem(self._temp_polygon_item)
        self._temp_polygon_item = None


    def mousePressEvent(self, event: QMouseEvent):
        # Add detailed debug prints
        print(f"[PdfViewer DEBUG] mousePressEvent called with button: {event.button()}, pos: {event.pos()}")
        print(f"[PdfViewer DEBUG] Current mode: {self.current_mode.name}")
        
        scene_pos = self.mapToScene(event.pos())
        print(f"[PdfViewer DEBUG] Mapped to scene pos: {scene_pos}")
        
        self._item_being_moved_in_edit = None

        if event.button() == Qt.MouseButton.MiddleButton:
            # Remove keyboard focus indicator when starting to pan
            self._remove_keyboard_focus_indicator()
            
            if self.current_mode in [InteractionMode.IDLE, InteractionMode.EDIT]:
                self.set_mode(InteractionMode.PANNING)
                self._last_pan_pos = event.position()
                self._is_panning = True
                event.accept()
                return
            elif self.current_mode == InteractionMode.PANNING:
                self._last_pan_pos = event.position()
                self._is_panning = True
                event.accept()
                return

        if self.current_mode == InteractionMode.EDIT:
            item_under_cursor = self.itemAt(event.pos())
            if item_under_cursor and (item_under_cursor.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable):
                self._item_being_moved_in_edit = item_under_cursor
                self._item_being_moved_in_edit_start_pos = item_under_cursor.scenePos() 
            elif not item_under_cursor:
                self.rubber_band_origin = event.pos()
                self.rubber_band.setGeometry(QRectF(self.rubber_band_origin, QSize()).toRect().normalized())
                self.rubber_band.show()
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton: 
            print(f"[PdfViewer DEBUG] Calling _handle_left_click with scene_pos: {scene_pos}")
            self._handle_left_click(scene_pos)
        elif event.button() == Qt.MouseButton.RightButton:
            self._handle_right_click_cancel_drawing()
        else:
            super().mousePressEvent(event)


    def _handle_left_click(self, scene_pos: QPointF):
        """Handle left click based on current mode."""
        print(f"[PdfViewer DEBUG] _handle_left_click called in mode: {self.current_mode.name}, scene_pos: {scene_pos}")
        
        mode_actions = {
            InteractionMode.SET_SCALE_START: lambda: self._start_line_draw(scene_pos, InteractionMode.SET_SCALE_END, self._scale_line_pen),
            InteractionMode.SET_SCALE_END: lambda: self._finish_line_draw(scene_pos, self.scale_line_drawn.emit),
            InteractionMode.DRAW_OBSTACLE: lambda: self._handle_polygon_point(scene_pos, InteractionMode.DRAW_OBSTACLE, self._obstacle_brush, self._obstacle_preview_pen),
            InteractionMode.DEFINE_STAGING_AREA: lambda: self._handle_polygon_point(scene_pos, InteractionMode.DEFINE_STAGING_AREA, self._staging_area_brush, self._staging_area_preview_pen),
            InteractionMode.DEFINE_PATHFINDING_BOUNDS: lambda: self._handle_polygon_point(scene_pos, InteractionMode.DEFINE_PATHFINDING_BOUNDS, self._bounds_brush, self._bounds_preview_pen),            
            InteractionMode.SET_START_POINT: lambda: self._request_point_placement(PointType.PICK_AISLE, scene_pos),
            InteractionMode.SET_END_POINT: lambda: self._request_point_placement(PointType.STAGING_LOCATION, scene_pos),
            InteractionMode.DEFINE_AISLE_LINE_START: lambda: self._start_line_draw(scene_pos, InteractionMode.DEFINE_AISLE_LINE_END, self._line_def_pen),
            InteractionMode.DEFINE_AISLE_LINE_END: lambda: self._finish_line_draw(scene_pos, lambda p1, p2: self.line_definition_requested.emit(PointType.PICK_AISLE, p1, p2)),
            InteractionMode.DEFINE_STAGING_LINE_START: lambda: self._start_line_draw(scene_pos, InteractionMode.DEFINE_STAGING_LINE_END, self._line_def_pen),
            InteractionMode.DEFINE_STAGING_LINE_END: lambda: self._finish_line_draw(scene_pos, lambda p1, p2: self.line_definition_requested.emit(PointType.STAGING_LOCATION, p1, p2)),
        }
        
        action = mode_actions.get(self.current_mode)
        print(f"[PdfViewer DEBUG] _handle_left_click found action: {action is not None}")
        if action: 
            print(f"[PdfViewer DEBUG] Executing action for mode: {self.current_mode.name}")
            action()
        else:
            print(f"[PdfViewer DEBUG] No action defined for mode: {self.current_mode.name}")
            
    def _start_line_draw(self, scene_pos: QPointF, next_mode: InteractionMode, pen: QPen):
        print(f"[PdfViewer DEBUG] _start_line_draw: pos={scene_pos}, next_mode={next_mode.name}")
        self._temp_drawing_points = [scene_pos]
        self._temp_line_item = QGraphicsLineItem(QLineF(scene_pos, scene_pos))
        self._temp_line_item.setPen(pen)
        
        # Increase Z-value to make sure the line is visible on top of everything
        self._temp_line_item.setZValue(PDF_Z_VALUE + 10)
        self.scene().addItem(self._temp_line_item)
        
        print(f"[PdfViewer DEBUG] Temporary line item added to scene: {self._temp_line_item}")
        print(f"[PdfViewer DEBUG] Line item visible: {self._temp_line_item.isVisible()}, Line: {self._temp_line_item.line()}")
        print(f"[PdfViewer DEBUG] Scene has item: {self._temp_line_item in self.scene().items()}")
        
        self.set_mode(next_mode)
        self.status_update.emit(f"{next_mode.name.replace('_END', '').replace('_', ' ').title()}: Click end point.", 0)

    def _finish_line_draw(self, scene_pos: QPointF, signal_emitter_func):
        if not self._temp_drawing_points:
            print("[PdfViewer DEBUG] _finish_line_draw: No temp drawing points, returning.") # Debug
            return
        p1 = self._temp_drawing_points[0]; p2 = scene_pos
        print(f"[PdfViewer DEBUG] _finish_line_draw: p1={p1}, p2={p2}")
        print(f"[PdfViewer DEBUG] Line length: {QLineF(p1, p2).length()} pixels")
        print(f"[PdfViewer DEBUG] Emitting scale_line_drawn signal")
        signal_emitter_func(p1, p2) # This is where scale_line_drawn.emit happens
        print("[PdfViewer DEBUG] Signal emitted.")
        self._reset_temp_drawing_items()
        if self.current_mode == InteractionMode.SET_SCALE_END: self.set_mode(InteractionMode.IDLE)
        elif self.current_mode == InteractionMode.DEFINE_AISLE_LINE_END: self.set_mode(InteractionMode.DEFINE_AISLE_LINE_START)
        elif self.current_mode == InteractionMode.DEFINE_STAGING_LINE_END: self.set_mode(InteractionMode.DEFINE_STAGING_LINE_START)


    def _handle_polygon_point(self, scene_pos: QPointF, mode_type: InteractionMode, brush: QBrush, pen: QPen):
        # ... (rest of the method unchanged) ...
        is_closing = False
        if len(self._temp_drawing_points) > 2:
            if QLineF(scene_pos, self._temp_drawing_points[0]).length() < OBSTACLE_SNAP_DISTANCE:
                is_closing = True; scene_pos = self._temp_drawing_points[0]
        status_msg_base = mode_type.name.replace('_', ' ').replace("DEFINE ", "").title()        
        
        if is_closing:
            self.polygon_drawn.emit(mode_type, QPolygonF(self._temp_drawing_points))
            self._reset_temp_drawing_items()
            self.status_update.emit(f"{mode_type.name.replace('_', ' ')} polygon completed. Draw another or cancel.", 0)
            # Reset mode to IDLE after finishing bounds drawing
            if mode_type == InteractionMode.DEFINE_PATHFINDING_BOUNDS:
                 self.set_mode(InteractionMode.IDLE)
                 self.status_update.emit(f"{status_msg_base} defined.", 3000)
            else:
                 self.status_update.emit(f"{status_msg_base} polygon completed. Draw another or cancel.", 0)
        else:
            self._temp_drawing_points.append(scene_pos); n = len(self._temp_drawing_points)
            if n == 1:
                self._temp_polygon_item = QGraphicsPolygonItem(QPolygonF(self._temp_drawing_points)); self._temp_polygon_item.setBrush(brush); self._temp_polygon_item.setPen(pen); self.scene().addItem(self._temp_polygon_item)
                self._temp_line_item = QGraphicsLineItem(); self._temp_line_item.setPen(pen); self.scene().addItem(self._temp_line_item)
            elif self._temp_polygon_item: self._temp_polygon_item.setPolygon(QPolygonF(self._temp_drawing_points + [scene_pos] if n > 0 else [scene_pos])) 
            if self._temp_line_item and n > 1: self._temp_line_item.setLine(QLineF(self._temp_drawing_points[-1], scene_pos)) 

            self.status_update.emit(f"{mode_type.name.replace('_', ' ')}: Point {n} added. Click near start to close or Right-click/Esc to cancel.", 0)

    def _request_point_placement(self, point_type: PointType, scene_pos: QPointF):
        # ... (rest of the method unchanged) ...
        self.point_placement_requested.emit(point_type, scene_pos)
        self.set_mode(InteractionMode.IDLE)


    def mouseMoveEvent(self, event: QMouseEvent):
        # Add debug prints for temp line drawing
        scene_pos = self.mapToScene(event.pos())
        
        if self.current_mode == InteractionMode.PANNING and self._is_panning:
            # Remove keyboard focus indicator during panning
            if self._keyboard_focus_rect is not None:
                self._remove_keyboard_focus_indicator()
                
            delta = event.position() - self._last_pan_pos
            self._last_pan_pos = event.position()
            hs_bar = self.horizontalScrollBar()
            vs_bar = self.verticalScrollBar()
            hs_bar.setValue(hs_bar.value() - int(delta.x()))
            vs_bar.setValue(vs_bar.value() - int(delta.y()))
            event.accept()
            return
            
        if self.current_mode == InteractionMode.EDIT and self.rubber_band.isVisible():
            self.rubber_band.setGeometry(QRectF(self.rubber_band_origin, event.pos()).normalized().toRect())
            super().mouseMoveEvent(event)
            return

        if self._temp_line_item and len(self._temp_drawing_points) == 1:
            print(f"[PdfViewer DEBUG] mouseMoveEvent updating line: {self._temp_drawing_points[0]} -> {scene_pos}")
            self._temp_line_item.setLine(QLineF(self._temp_drawing_points[0], scene_pos))
            print(f"[PdfViewer DEBUG] Updated line: {self._temp_line_item.line()}, visible: {self._temp_line_item.isVisible()}")
        elif self._temp_polygon_item and self._temp_drawing_points:
            preview_poly_points = self._temp_drawing_points + [scene_pos]
            self._temp_polygon_item.setPolygon(QPolygonF(preview_poly_points))
            if len(self._temp_drawing_points) >= 1 and self._temp_line_item:
                 self._temp_line_item.setLine(QLineF(self._temp_drawing_points[-1], scene_pos))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        print(f"[PdfViewer] mouseReleaseEvent with button {event.button()}")
        
        if self._is_panning and event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            # Make sure keyboard focus indicator remains hidden
            self._remove_keyboard_focus_indicator()
            
            if self.current_mode == InteractionMode.PANNING:
                # Revert to previous mode if panning was temporary
                self.set_mode(InteractionMode.IDLE)
            event.accept()
            return
        
        if self.current_mode == InteractionMode.EDIT:
            if self.rubber_band.isVisible():
                # End rubber band selection
                self.rubber_band.hide()
                
                # Get selection rect
                selection_rect = QRectF(self.mapToScene(self.rubber_band_origin), 
                                      self.mapToScene(event.pos()))
                print(f"[PdfViewer] Rubber band selection: {selection_rect}")
                
                # Update existing selection
                # ...
                event.accept()
                return
            
            # Handle item dragging in edit mode
            if self._item_being_moved_in_edit:
                move_delta = self._item_being_moved_in_edit.scenePos() - self._item_being_moved_in_edit_start_pos
                
                # Check if actual movement happened
                if not move_delta.isNull():
                    print(f"[PdfViewer] Item moved in edit mode, delta: {move_delta}")
                    
                    # Get the item type and identify what was moved
                    item_type = type(self._item_being_moved_in_edit)
                    
                    if isinstance(self._item_being_moved_in_edit, QGraphicsPolygonItem):
                        # Polygon item (obstacle or staging area)
                        polygon = self._item_being_moved_in_edit.polygon()
                        # Add the current position to get scene coordinates
                        scene_polygon = QPolygonF()
                        for i in range(polygon.count()):
                            scene_polygon.append(self._item_being_moved_in_edit.mapToScene(polygon.at(i)))
                            
                        self.item_moved_in_edit.emit(self._item_being_moved_in_edit, scene_polygon)
                        
                    elif isinstance(self._item_being_moved_in_edit, QGraphicsEllipseItem):
                        # Point item (start or end point)
                        scene_pos = self._item_being_moved_in_edit.scenePos()
                        
                        # Find which point dictionary this item belongs to
                        point_id = None
                        is_start_point = False
                        
                        for pid, (marker, _) in self._start_point_items.items():
                            if marker == self._item_being_moved_in_edit:
                                point_id = pid
                                is_start_point = True
                                break
                                
                        if point_id is None:
                            for pid, (marker, _) in self._end_point_items.items():
                                if marker == self._item_being_moved_in_edit:
                                    point_id = pid
                                    is_start_point = False
                                    break
                        
                        if point_id is not None:
                            self.item_moved_in_edit.emit(
                                self._item_being_moved_in_edit, 
                                (point_id, scene_pos, is_start_point)
                            )
                
                self._item_being_moved_in_edit = None
                event.accept()
                return
        
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Handle key navigation in the PDF viewer."""
        key = event.key()
        
        # Only handle keys if we have a PDF loaded
        if not self.pixmap_item:
            super().keyPressEvent(event)
            return
            
        # Navigation with arrow keys
        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            # Move the keyboard focus indicator
            if self._keyboard_focus_rect is None:
                # Create the focus indicator if it doesn't exist
                self._create_keyboard_focus_indicator()
                
            # Calculate movement direction
            dx, dy = 0, 0
            if key == Qt.Key_Left:
                dx = -self._keyboard_nav_step
            elif key == Qt.Key_Right:
                dx = self._keyboard_nav_step
            elif key == Qt.Key_Up:
                dy = -self._keyboard_nav_step
            elif key == Qt.Key_Down:
                dy = self._keyboard_nav_step
                
            # Apply the movement
            self._move_keyboard_focus(dx, dy)
            event.accept()
            return
            
        # Handle interaction with current mode
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            # Enter key simulates click at current focus position
            if self._keyboard_focus_rect is not None:
                self._handle_left_click(self._keyboard_focus_pos)
                event.accept()
                return
                
        # Escape key cancels current operation
        elif key == Qt.Key_Escape:
            self.set_mode(InteractionMode.IDLE)
            event.accept()
            return
            
        # Space key for panning toggle - when held down
        elif key == Qt.Key_Space:
            # Store the previous mode to restore when space is released
            self._previous_mode_before_space = self.current_mode
            self.set_mode(InteractionMode.PANNING)
            event.accept()
            return
            
        # Plus/Minus keys for zooming (without Ctrl)
        elif key == Qt.Key_Plus or key == Qt.Key_Equal:
            self.zoom_in()
            event.accept()
            return
        elif key == Qt.Key_Minus:
            self.zoom_out()
            event.accept()
            return
        
        # Let the parent handle other keys
        super().keyPressEvent(event)
        
    def keyReleaseEvent(self, event):
        """Handle key releases for toggled modes."""
        key = event.key()
        
        # Space key released - restore previous mode
        if key == Qt.Key_Space and hasattr(self, '_previous_mode_before_space'):
            if self.current_mode == InteractionMode.PANNING:
                self.set_mode(self._previous_mode_before_space)
                event.accept()
                return
                
        super().keyReleaseEvent(event)
        
    def _create_keyboard_focus_indicator(self):
        """Create a visual indicator for keyboard focus position."""
        if self._keyboard_focus_rect is None:
            # Initialize position to center of view if not set
            if self._keyboard_focus_pos == QPointF(0, 0):
                self._keyboard_focus_pos = self.mapToScene(self.viewport().rect().center())
                
            # Create the focus indicator as a crosshair
            size = 20
            horizontal_line = QGraphicsLineItem(
                QLineF(self._keyboard_focus_pos.x() - size/2, self._keyboard_focus_pos.y(),
                       self._keyboard_focus_pos.x() + size/2, self._keyboard_focus_pos.y())
            )
            vertical_line = QGraphicsLineItem(
                QLineF(self._keyboard_focus_pos.x(), self._keyboard_focus_pos.y() - size/2,
                       self._keyboard_focus_pos.x(), self._keyboard_focus_pos.y() + size/2)
            )
            
            # Use a bright color that will be visible on any background
            keyboard_focus_pen = QPen(QColor(255, 0, 255), 2)  # Magenta, width 2
            horizontal_line.setPen(keyboard_focus_pen)
            vertical_line.setPen(keyboard_focus_pen)
            
            # Add to scene
            self.scene().addItem(horizontal_line)
            self.scene().addItem(vertical_line)
            
            # Store as a list for easy access
            self._keyboard_focus_rect = [horizontal_line, vertical_line]
            
    def _remove_keyboard_focus_indicator(self):
        """Remove the keyboard focus indicator from the scene."""
        if self._keyboard_focus_rect:
            for item in self._keyboard_focus_rect:
                if item.scene() == self.scene():
                    self.scene().removeItem(item)
            self._keyboard_focus_rect = None
            
    def _move_keyboard_focus(self, dx, dy):
        """Move the keyboard focus indicator by the specified delta."""
        if self._keyboard_focus_rect:
            # Update position
            self._keyboard_focus_pos = QPointF(
                self._keyboard_focus_pos.x() + dx,
                self._keyboard_focus_pos.y() + dy
            )
            
            # Remove old indicator
            self._remove_keyboard_focus_indicator()
            
            # Create new indicator at updated position
            self._create_keyboard_focus_indicator()
            
            # Ensure the focus indicator is visible in the viewport
            self.ensureVisible(
                QRectF(self._keyboard_focus_pos.x() - 5, self._keyboard_focus_pos.y() - 5, 10, 10),
                50, 50  # Margin
            )
            
    def focusInEvent(self, event):
        """Show keyboard focus indicator when view gets focus."""
        super().focusInEvent(event)
        self._create_keyboard_focus_indicator()
        
    def focusOutEvent(self, event):
        """Hide keyboard focus indicator when view loses focus."""
        super().focusOutEvent(event)
        self._remove_keyboard_focus_indicator()
        
    def _handle_right_click_cancel_drawing(self):
        if self.current_mode not in [InteractionMode.IDLE, InteractionMode.EDIT, InteractionMode.PANNING]:
            mode_name_before_cancel = self.current_mode.name
            self._reset_temp_drawing_items() # Ensure temp items are cleared on cancel
            self.set_mode(InteractionMode.IDLE)
            self.status_update.emit(f"{mode_name_before_cancel.replace('_', ' ').title()} cancelled.", 3000)

    def contextMenuEvent(self, event):
        """Override to provide context-specific menu based on current mode and item under cursor."""
        # Don't show context menu if we're in a drawing mode - right-click should cancel
        if self.current_mode not in [InteractionMode.IDLE, InteractionMode.EDIT, InteractionMode.PANNING]:
            # Let the regular right-click cancel functionality handle it
            self._handle_right_click_cancel_drawing()
            event.accept()
            return
            
        # Get item under cursor
        item_under_cursor = self.itemAt(event.pos())
        scene_pos = self.mapToScene(event.pos())
        
        # Create menu
        menu = QMenu(self)
        
        # --- Mode-specific menu options ---
        if self.current_mode == InteractionMode.IDLE:
            # General IDLE mode options
            if self.pixmap_item:  # PDF loaded
                menu.addAction("Set Scale").triggered.connect(
                    lambda: self.set_mode(InteractionMode.SET_SCALE_START))
                
                mode_menu = menu.addMenu("Draw Mode")
                mode_menu.addAction("Draw Obstacle").triggered.connect(
                    lambda: self.set_mode(InteractionMode.DRAW_OBSTACLE))
                mode_menu.addAction("Define Staging Area").triggered.connect(
                    lambda: self.set_mode(InteractionMode.DEFINE_STAGING_AREA))
                mode_menu.addAction("Define Pathfinding Bounds").triggered.connect(
                    lambda: self.set_mode(InteractionMode.DEFINE_PATHFINDING_BOUNDS))
                
                point_menu = menu.addMenu("Add Point")
                point_menu.addAction("Add Start Point").triggered.connect(
                    lambda: self.set_mode(InteractionMode.SET_START_POINT))
                point_menu.addAction("Add End Point").triggered.connect(
                    lambda: self.set_mode(InteractionMode.SET_END_POINT))
                
                line_menu = menu.addMenu("Define Line")
                line_menu.addAction("Define Aisle Line").triggered.connect(
                    lambda: self.set_mode(InteractionMode.DEFINE_AISLE_LINE_START))
                line_menu.addAction("Define Staging Line").triggered.connect(
                    lambda: self.set_mode(InteractionMode.DEFINE_STAGING_LINE_START))
                
                menu.addSeparator()
                menu.addAction("Edit Mode").triggered.connect(
                    lambda: self.set_mode(InteractionMode.EDIT))
                    
        elif self.current_mode == InteractionMode.EDIT:
            # EDIT mode options
            menu.addAction("Exit Edit Mode").triggered.connect(
                lambda: self.set_mode(InteractionMode.IDLE))
            menu.addSeparator()
                
        # --- Item-specific menu options ---
        if item_under_cursor:
            # Add item-specific options based on the type of item
            if isinstance(item_under_cursor, QGraphicsPolygonItem):
                if item_under_cursor in self._obstacle_items:
                    menu.addAction("Delete Obstacle").triggered.connect(
                        lambda: self.delete_items_requested.emit([item_under_cursor]))
                elif item_under_cursor in self._staging_area_items:
                    menu.addAction("Delete Staging Area").triggered.connect(
                        lambda: self.delete_items_requested.emit([item_under_cursor]))
                elif item_under_cursor == self._pathfinding_bounds_item:
                    menu.addAction("Clear Pathfinding Bounds").triggered.connect(
                        self.clear_pathfinding_bounds_item)
            
            # Handle point items
            for name, (marker, label) in self._start_point_items.items():
                if item_under_cursor == marker:
                    menu.addAction(f"Delete Start Point '{name}'").triggered.connect(
                        lambda n=name: self.remove_point_item(PointType.PICK_AISLE, n))
                    break
                    
            for name, (marker, label) in self._end_point_items.items():
                if item_under_cursor == marker:
                    menu.addAction(f"Delete End Point '{name}'").triggered.connect(
                        lambda n=name: self.remove_point_item(PointType.STAGING_LOCATION, n))
                    break
                    
            # Handle path item
            if item_under_cursor == self._path_item:
                menu.addAction("Clear Path").triggered.connect(self.clear_path)
                
        # If menu is empty or no specific actions, add some general actions
        if menu.isEmpty():
            if self.pixmap_item:  # PDF loaded
                menu.addAction("Pan Mode").triggered.connect(
                    lambda: self.set_mode(InteractionMode.PANNING))
                
                menu.addSeparator()
                fit_action = menu.addAction("Fit to View")
                fit_action.triggered.connect(
                    lambda: self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio))
                
        # Show the menu if it has any actions
        if not menu.isEmpty():
            menu.exec(event.globalPos())
            event.accept()
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent): # Changed QEvent to QWheelEvent
        # ... (rest of the method unchanged) ...
        if self.current_mode != InteractionMode.IDLE and self.current_mode != InteractionMode.EDIT: event.ignore(); return
        if self._is_panning: event.ignore(); return
        zoom_factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.scale(zoom_factor, zoom_factor)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor) 
        
        # Update zoom level
        self._update_zoom_level(zoom_factor)
        
        self.view_changed.emit()
        event.accept()

    # --- Public Methods to Add/Remove/Update Graphics ---

    def draw_pathfinding_bounds_item(self, polygon: QPolygonF):
        """Draws or updates the visual representation of the pathfinding bounds."""
        self.clear_pathfinding_bounds_item() # Clear previous one if exists
        if polygon and not polygon.isEmpty():
            self._pathfinding_bounds_item = QGraphicsPolygonItem(polygon)
            self._pathfinding_bounds_item.setPen(self._bounds_pen)
            self._pathfinding_bounds_item.setBrush(self._bounds_brush)
            self._pathfinding_bounds_item.setZValue(BOUNDS_Z_VALUE)
            self.scene().addItem(self._pathfinding_bounds_item)

    def clear_pathfinding_bounds_item(self):
        """Removes the visual pathfinding bounds item from the scene."""
        if self._pathfinding_bounds_item and self._pathfinding_bounds_item.scene():
            self.scene().removeItem(self._pathfinding_bounds_item)
        self._pathfinding_bounds_item = None    
    
    # Public Methods to Add/Remove/Update Graphics
    def add_obstacle_item(self, polygon: QPolygonF) -> QGraphicsPolygonItem:
        """Add an obstacle polygon to the scene."""
        item = QGraphicsPolygonItem(polygon)
        item.setBrush(self._obstacle_brush)
        item.setPen(self._obstacle_pen)
        item.setZValue(OBSTACLES_Z_VALUE)
        item.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable) # Default flags
        # Apply movable if currently in edit mode
        if self.current_mode == InteractionMode.EDIT:
             item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.scene().addItem(item)
        self._obstacle_items.append(item)
        # Store in the mapping
        self.item_to_model_polygon_map[item] = polygon
        return item

    def remove_obstacle_item(self, item_ref: QGraphicsPolygonItem):
        """Remove an obstacle polygon from the scene by reference."""
        if item_ref in self._obstacle_items and item_ref.scene():
            # Remove from the mapping before removing from scene
            if item_ref in self.item_to_model_polygon_map:
                del self.item_to_model_polygon_map[item_ref]
            self.scene().removeItem(item_ref)
            self._obstacle_items.remove(item_ref)

    def add_staging_area_item(self, polygon: QPolygonF) -> QGraphicsPolygonItem:
        """Add a staging area polygon to the scene."""
        item = QGraphicsPolygonItem(polygon)
        item.setBrush(self._staging_area_brush)
        item.setPen(self._staging_area_pen)
        item.setZValue(STAGING_AREAS_Z_VALUE)
        item.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable) # Default flags
        # Apply movable if currently in edit mode
        if self.current_mode == InteractionMode.EDIT:
             item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.scene().addItem(item)
        self._staging_area_items.append(item)
        # Store in the mapping
        self.item_to_model_polygon_map[item] = polygon
        return item

    def remove_staging_area_item(self, item_ref: QGraphicsPolygonItem):
        """Remove a staging area polygon from the scene by reference."""
        if item_ref in self._staging_area_items and item_ref.scene():
            # Remove from the mapping before removing from scene
            if item_ref in self.item_to_model_polygon_map:
                del self.item_to_model_polygon_map[item_ref]
            self.scene().removeItem(item_ref)
            self._staging_area_items.remove(item_ref)

    def _add_point_item(self, point_type: PointType, name: str, pos: QPointF):
        target_dict, pen, brush, prefix = (self._start_point_items, self._start_point_pen, self._start_point_brush, "Start") if point_type == PointType.PICK_AISLE else (self._end_point_items, self._end_point_pen, self._end_point_brush, "End")
        if name in target_dict:
            old_marker, _ = target_dict[name]
            if old_marker and old_marker.scene(): self.scene().removeItem(old_marker) # Label is child, will be removed too

        r = POINT_MARKER_RADIUS
        marker = QGraphicsEllipseItem(0, 0, 2 * r, 2 * r) # Origin at (0,0) for its own coordinate system
        marker.setPos(pos.x() - r, pos.y() - r) # Position its top-left in scene coordinates
        marker.setPen(pen); marker.setBrush(brush)
        marker.setToolTip(f"{prefix}: {name}")
        marker.setData(0, {"name": name, "type": point_type.value})
        marker.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable) # Default flags
        marker.setZValue(POINTS_Z_VALUE)
        # Apply movable if currently in edit mode
        if self.current_mode == InteractionMode.EDIT:
             marker.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        label = QGraphicsSimpleTextItem(name, parent=marker) # Child of marker
        label.setFont(self._label_font); label.setBrush(brush)
        label_rel_x = r + LABEL_OFFSET_X # Position relative to marker's local (0,0)
        label_rel_y = r + LABEL_OFFSET_Y
        label.setPos(label_rel_x, label_rel_y)

        self.scene().addItem(marker) # Adding parent marker adds child label too
        target_dict[name] = (marker, label)


    def add_pick_aisle_item(self, name: str, pos: QPointF): self._add_point_item(PointType.PICK_AISLE, name, pos)
    def add_staging_location_item(self, name: str, pos: QPointF): self._add_point_item(PointType.STAGING_LOCATION, name, pos)

    def remove_point_item(self, point_type: PointType, name: str):
        # ... (rest of the method unchanged) ...
        target_dict = self._start_point_items if point_type == PointType.PICK_AISLE else self._end_point_items
        if name in target_dict: marker, _ = target_dict[name]; (self.scene().removeItem(marker) if marker.scene() else None); del target_dict[name]

    def clear_all_points(self):
        # ... (rest of the method unchanged) ...
        for name in list(self._start_point_items.keys()): self.remove_point_item(PointType.PICK_AISLE, name)
        for name in list(self._end_point_items.keys()): self.remove_point_item(PointType.STAGING_LOCATION, name)

    def clear_obstacles(self): [self.remove_obstacle_item(item) for item in list(self._obstacle_items)]; self._obstacle_items.clear()
    def clear_staging_areas(self): [self.remove_staging_area_item(item) for item in list(self._staging_area_items)]; self._staging_area_items.clear()

    def draw_path(self, path_points: Optional[List[QPointF]]):
        # ... (rest of the method unchanged) ...
        self.clear_path()
        if not path_points or len(path_points) < 2: return
        path = QPainterPath(path_points[0]); [path.lineTo(p) for p in path_points[1:]]
        self._path_item = QGraphicsPathItem(path); self._path_item.setPen(self._path_pen); self._path_item.setZValue(PATH_Z_VALUE); self.scene().addItem(self._path_item)


    def clear_path(self):
        # ... (rest of the method unchanged) ...
        if self._path_item and self._path_item.scene(): self.scene().removeItem(self._path_item)
        self._path_item = None

    def clear_animation_overlay(self):
        if self.animation_overlay_group:
            # print(f"[PdfViewer clear_animation_overlay] Clearing {len(self.animation_overlay_group.childItems())} children from group.")
            # This is a standard way to clear a group's children
            for item in self.animation_overlay_group.childItems():
                self.scene().removeItem(item) # Removing from scene also removes from group
                # item.deleteLater() # Could be added if you suspect item leaks, but usually not needed
        else:
            print("[PdfViewer clear_animation_overlay] Animation group is None, creating it")
            self.animation_overlay_group = self.scene().createItemGroup([])
            self.animation_overlay_group.setZValue(ANIMATION_OVERLAY_Z_VALUE)


    def update_animation_overlay(self, mode: AnimationMode, data: list):
        # print(f"[PdfViewer update_animation_overlay] Called with mode: {mode}, data count: {len(data)}")
        
        # Create the animation overlay group if it doesn't exist
        if not self.animation_overlay_group:
            print("[PdfViewer update_animation_overlay] Creating new animation overlay group")
            self.animation_overlay_group = self.scene().createItemGroup([])
            self.animation_overlay_group.setZValue(ANIMATION_OVERLAY_Z_VALUE)
        
        # Clear previous frame's items from the group
        self.clear_animation_overlay()
        
        # Ensure group is visible, though it should be by default
        if not self.animation_overlay_group.isVisible():
            print("[PdfViewer update_animation_overlay] WARNING: Animation group was not visible, setting it visible.")
            self.animation_overlay_group.setVisible(True)

        # Verify we have valid data
        if not data:
            print("[PdfViewer update_animation_overlay] No data provided for animation")
            return

        if mode == AnimationMode.CARTS:
            self._draw_animation_carts(data)
        elif mode == AnimationMode.PATH_LINES:
            self._draw_animation_paths(data)
        
        # Force an update to ensure animations are visible
        self.scene().update()

    # ... (Keep _draw_animation_carts and _draw_animation_paths as debugged in the previous step)

    def _draw_animation_carts(self, active_carts_data: list):
        if not self.animation_overlay_group: return
        if not active_carts_data: return # Added check
        
        for i, cart_data in enumerate(active_carts_data):
            pos, angle, width_px, length_px = cart_data['pos'], cart_data['angle'], cart_data['width'], cart_data['length']
            
            if width_px <= 0.1 or length_px <= 0.1: # More lenient for small scales
                if i < 2: print(f"  Skipping cart {i} due to zero/small size.")
                continue

            cart_rect = QGraphicsRectItem(-length_px / 2, -width_px / 2, length_px, width_px)
            cart_rect.setBrush(QColor(255, 100, 0, 180)); cart_rect.setPen(Qt.PenStyle.NoPen)
            cart_rect.setTransform(QTransform().translate(pos.x(), pos.y()).rotate(angle))
            self.animation_overlay_group.addToGroup(cart_rect)


    def _draw_animation_paths(self, active_paths_data: list):
        if not self.animation_overlay_group: return
        if not active_paths_data: return # Added check

        if not hasattr(self, '_cluster_color_map'): self._cluster_color_map = {}
        # ... (cluster_colors list)
        cluster_colors = [QColor("blue"), QColor("red"), QColor("darkGreen"), QColor("purple"), QColor("orange"), QColor("teal"), QColor("maroon"), QColor("navy"), QColor("olive"), QColor("deeppink")]


        for i, path_data in enumerate(active_paths_data):
            points, draw_prog, alpha, cluster = path_data['points'], path_data['draw_progress'], path_data['alpha'], path_data.get('start_cluster', "default")

            if not points or len(points) < 2 or alpha <= 0:
                if i < 2: print(f"  Skipping path {i} due to no points/alpha.")
                continue

            # ... (rest of path drawing logic) ...
            if cluster not in self._cluster_color_map: self._cluster_color_map[cluster] = cluster_colors[len(self._cluster_color_map) % len(cluster_colors)]
            path_color = self._cluster_color_map[cluster]
            path_to_draw = QPainterPath(points[0])
            total_segments = len(points) - 1
            if total_segments == 0: continue
            length_to_draw_in_segments = draw_prog * total_segments
            for seg_idx in range(total_segments):
                current_segment_progress_val = length_to_draw_in_segments - seg_idx
                if current_segment_progress_val <= 0: break
                p_start, p_end = points[seg_idx], points[seg_idx+1]
                if current_segment_progress_val >= 1.0: path_to_draw.lineTo(p_end)
                else: path_to_draw.lineTo(p_start + (p_end - p_start) * current_segment_progress_val); break
            path_item = QGraphicsPathItem(path_to_draw)
            color_with_alpha = QColor(path_color); color_with_alpha.setAlpha(alpha)
            pen = QPen(color_with_alpha, 2); pen.setCosmetic(True); path_item.setPen(pen)
            self.animation_overlay_group.addToGroup(path_item)
        
    def get_zoom_percentage(self):
        """Return the current zoom level as a percentage."""
        return self._current_zoom_level * 100
        
    def _update_zoom_level(self, zoom_factor):
        """Update the zoom level tracking and emit signal."""
        self._current_zoom_level *= zoom_factor
        self.zoom_level_changed.emit(self.get_zoom_percentage())
        
    def zoom_in(self):
        """Zoom in the view"""
        zoom_factor = 1.25
        self.scale(zoom_factor, zoom_factor)
        self._update_zoom_level(zoom_factor)
        self.view_changed.emit()
        
    def zoom_out(self):
        """Zoom out the view"""
        zoom_factor = 1 / 1.25
        self.scale(zoom_factor, zoom_factor)
        self._update_zoom_level(zoom_factor)
        self.view_changed.emit()
        
    def zoom_to(self, percentage):
        """Zoom to specific percentage"""
        target_level = percentage / 100.0
        factor = target_level / self._current_zoom_level
        self.scale(factor, factor)
        self._current_zoom_level = target_level
        self.zoom_level_changed.emit(percentage)
        self.view_changed.emit()
        
    def zoom_fit(self):
        """Fit the view to the current content"""
        if self.pixmap_item:
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            # Update zoom level based on transformation
            transform = self.transform()
            self._current_zoom_level = (transform.m11() + transform.m22()) / 2.0  # Average of x and y scale
            self.zoom_level_changed.emit(self.get_zoom_percentage())
            self.view_changed.emit()
            
    def zoom_fit_width(self):
        """Fit the view to the width of the current content"""
        if self.pixmap_item:
            rect = self.pixmap_item.boundingRect()
            # Temporarily set the view transform to identity to get viewport width in scene coordinates
            self.resetTransform()
            # Get the viewport width in scene coordinates
            viewport_rect = self.mapToScene(self.viewport().rect()).boundingRect()
            # Calculate the scale factor for width
            width_factor = viewport_rect.width() / rect.width()
            # Apply the transform
            self.scale(width_factor, width_factor)
            self._current_zoom_level = width_factor
            self.zoom_level_changed.emit(self.get_zoom_percentage())
            self.view_changed.emit()
            
    def zoom_fit_height(self):
        """Fit the view to the height of the current content"""
        if self.pixmap_item:
            rect = self.pixmap_item.boundingRect()
            # Temporarily set the view transform to identity to get viewport height in scene coordinates
            self.resetTransform()
            # Get the viewport height in scene coordinates
            viewport_rect = self.mapToScene(self.viewport().rect()).boundingRect()
            # Calculate the scale factor for height
            height_factor = viewport_rect.height() / rect.height()
            # Apply the transform
            self.scale(height_factor, height_factor)
            self._current_zoom_level = height_factor
            self.zoom_level_changed.emit(self.get_zoom_percentage())
            self.view_changed.emit()

    def refresh_styles(self):
        """Refresh the styles when the theme changes"""
        self._setup_styles()
        
        # Refresh all existing items with new style
        
        # Refresh obstacles
        for item in self._obstacle_items:
            item.setPen(self._obstacle_pen)
            item.setBrush(self._obstacle_brush)
            
        # Refresh staging areas
        for item in self._staging_area_items:
            item.setPen(self._staging_area_pen)
            item.setBrush(self._staging_area_brush)
            
        # Refresh bounds
        if self._pathfinding_bounds_item:
            self._pathfinding_bounds_item.setPen(self._bounds_pen)
            self._pathfinding_bounds_item.setBrush(self._bounds_brush)
            
        # Refresh start points
        for name, (ellipse, label) in self._start_point_items.items():
            ellipse.setPen(self._start_point_pen)
            ellipse.setBrush(self._start_point_brush)
            
        # Refresh end points
        for name, (ellipse, label) in self._end_point_items.items():
            ellipse.setPen(self._end_point_pen)
            ellipse.setBrush(self._end_point_brush)
            
        # Refresh path
        if self._path_item:
            self._path_item.setPen(self._path_pen)
            
        # Refresh temporary drawing items
        if self._temp_line_item:
            if self.current_mode == InteractionMode.SET_SCALE:
                self._temp_line_item.setPen(self._scale_line_pen)
            elif self.current_mode in (InteractionMode.DEFINE_AISLE_LINE, InteractionMode.DEFINE_STAGING_LINE):
                self._temp_line_item.setPen(self._line_def_pen)
                
        if self._temp_polygon_item:
            if self.current_mode == InteractionMode.DRAW_OBSTACLE:
                self._temp_polygon_item.setPen(self._obstacle_preview_pen)
            elif self.current_mode == InteractionMode.DEFINE_STAGING_AREA:
                self._temp_polygon_item.setPen(self._staging_area_preview_pen)
            elif self.current_mode == InteractionMode.DEFINE_BOUNDS:
                self._temp_polygon_item.setPen(self._bounds_preview_pen)

    def dragEnterEvent(self, event):
        """Handle drag enter event to accept PDF files."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event):
        """Handle drop event to load the PDF file."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.pdf'):
                    self.pdf_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def add_start_point(self, point_id: str, position: QPointF):
        """Add a start point (pick aisle marker) at the specified position."""
        if point_id in self._start_point_items:
            self.remove_start_point(point_id)
            
        # Create circle marker (point item)
        point_marker = QGraphicsEllipseItem(
            position.x() - POINT_MARKER_RADIUS, position.y() - POINT_MARKER_RADIUS,
            POINT_MARKER_RADIUS * 2, POINT_MARKER_RADIUS * 2
        )
        point_marker.setBrush(QBrush(Qt.GlobalColor.green))
        point_marker.setPen(QPen(Qt.GlobalColor.darkGreen, 1))
        point_marker.setZValue(POINTS_Z_VALUE)
        
        # Create label
        label = PointLabelItem(point_id)
        label.setBrush(QBrush(Qt.GlobalColor.green))
        label.setPos(position + QPointF(LABEL_OFFSET_X, LABEL_OFFSET_Y))  # Offset to the right
        label.setZValue(POINTS_Z_VALUE)
        
        # Add to scene
        self.scene().addItem(point_marker)
        self.scene().addItem(label)
        
        # Store for future reference
        self._start_point_items[point_id] = (point_marker, label)
        return True

    def add_end_point(self, point_id: str, position: QPointF):
        """Add an end point (staging area marker) at the specified position."""
        if point_id in self._end_point_items:
            self.remove_end_point(point_id)
            
        # Create circle marker (point item)
        point_marker = QGraphicsEllipseItem(
            position.x() - POINT_MARKER_RADIUS, position.y() - POINT_MARKER_RADIUS,
            POINT_MARKER_RADIUS * 2, POINT_MARKER_RADIUS * 2
        )
        point_marker.setBrush(QBrush(Qt.GlobalColor.blue))
        point_marker.setPen(QPen(Qt.GlobalColor.darkBlue, 1))
        point_marker.setZValue(POINTS_Z_VALUE)
        
        # Create label
        label = PointLabelItem(point_id)
        label.setBrush(QBrush(Qt.GlobalColor.blue))
        label.setPos(position + QPointF(LABEL_OFFSET_X, LABEL_OFFSET_Y))  # Offset to the right
        label.setZValue(POINTS_Z_VALUE)
        
        # Add to scene
        self.scene().addItem(point_marker)
        self.scene().addItem(label)
        
        # Store for future reference
        self._end_point_items[point_id] = (point_marker, label)
        return True

    def highlight_point(self, point_name, point_type):
        """Highlight a specific point by name and type"""
        self._clear_highlights()
        
        # Find the relevant point items
        point_items = None
        if point_type == PointType.PICK_AISLE:
            if point_name in self._start_point_items:
                point_items = self._start_point_items[point_name]
        elif point_type == PointType.STAGING_LOCATION:
            if point_name in self._end_point_items:
                point_items = self._end_point_items[point_name]
                
        if point_items:
            point_item, label_item = point_items
            # Create highlight effect (e.g., temporary glow or color change)
            orig_brush = point_item.brush()
            orig_pen = point_item.pen()
            
            highlight_pen = QPen(QColor(255, 255, 0), 3)
            highlight_pen.setCosmetic(True)
            point_item.setPen(highlight_pen)
            
            self._highlighted_items.append((point_item, 'point', {'orig_pen': orig_pen}))
            
            # Center view on highlighted point
            self.centerOn(point_item.pos())
            return True
            
        return False
    
    def highlight_obstacle(self, obstacle_idx, is_staging_area=False):
        """Highlight a specific obstacle or staging area by index"""
        self._clear_highlights()
        
        items_list = self._staging_area_items if is_staging_area else self._obstacle_items
        if 0 <= obstacle_idx < len(items_list):
            obstacle_item = items_list[obstacle_idx]
            
            # Store original styling
            orig_pen = obstacle_item.pen()
            
            # Apply highlight styling
            highlight_pen = QPen(QColor(255, 255, 0), 3)
            highlight_pen.setCosmetic(True)
            obstacle_item.setPen(highlight_pen)
            
            self._highlighted_items.append((obstacle_item, 'obstacle', {'orig_pen': orig_pen}))
            
            # Center view on highlighted obstacle
            self.centerOn(obstacle_item.sceneBoundingRect().center())
            return True
            
        return False
    
    def highlight_path(self, path_points):
        """Highlight a specific path"""
        self._clear_highlights()
        
        if path_points and len(path_points) > 1:
            # Create a temporary path item with highlight styling
            path = QPainterPath()
            path.moveTo(path_points[0])
            for i in range(1, len(path_points)):
                path.lineTo(path_points[i])
                
            highlight_path_item = QGraphicsPathItem(path)
            highlight_pen = QPen(QColor(255, 255, 0), 4)
            highlight_pen.setCosmetic(True)
            highlight_path_item.setPen(highlight_pen)
            highlight_path_item.setZValue(PATH_Z_VALUE + 1)  # Ensure it's above regular paths
            
            self.scene().addItem(highlight_path_item)
            self._highlighted_items.append((highlight_path_item, 'path', {'temp_item': True}))
            
            # Center view on the middle point of the path
            mid_idx = len(path_points) // 2
            self.centerOn(path_points[mid_idx])
            return True
            
        return False
    
    def _clear_highlights(self):
        """Clear all highlighted items"""
        for item, item_type, orig_props in self._highlighted_items:
            if item_type == 'path' and orig_props.get('temp_item', False):
                # Remove temporary items
                self.scene().removeItem(item)
            else:
                # Restore original styling
                if 'orig_pen' in orig_props:
                    item.setPen(orig_props['orig_pen'])
                if 'orig_brush' in orig_props:
                    item.setBrush(orig_props['orig_brush'])
        
        self._highlighted_items = []
    
    def goto_scene_position(self, pos):
        """Center the view on a specific scene position"""
        self.centerOn(pos)

# --- END OF FILE Warehouse-Path-Finder-main/pdf_viewer.py ---