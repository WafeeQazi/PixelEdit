from PIL import Image
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea

from . import image_operations

def pil_image_to_qpixmap(image: Image.Image) -> QPixmap:
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
    qt_format = QImage.Format_RGBA8888 if image.mode == "RGBA" else QImage.Format_RGB888
    raw_bytes = image.tobytes("raw", image.mode)
    qimage = QImage(raw_bytes, image.width, image.height, qt_format)
    return QPixmap.fromImage(qimage.copy())

class ImageLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.mode = "select"
        self.selection_rect: QRect | None = None
        self._drag_start = None
        self.on_selection_changed = None
        self.on_paint_press = None
        self.on_paint_move = None
        self.on_paint_release = None
        self.on_pick = None

    def mousePressEvent(self, event) -> None:
        if self.pixmap() is None or event.button() != Qt.LeftButton:
            return
        pos = event.position().toPoint()
        if self.mode == "select":
            self._drag_start = pos
            self.selection_rect = QRect(pos, pos)
            self.update()
        elif self.mode == "paint" and self.on_paint_press is not None:
            self.on_paint_press(pos)
        elif self.mode == "pick" and self.on_pick is not None:
            self.on_pick(pos)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position().toPoint()
        if self.mode == "select":
            if self._drag_start is None:
                return
            self.selection_rect = QRect(self._drag_start, pos).normalized()
            self.update()
        elif self.mode == "paint" and event.buttons() & Qt.LeftButton and self.on_paint_move is not None:
            self.on_paint_move(pos)

    def mouseReleaseEvent(self, event) -> None:
        if self.mode == "select":
            if self._drag_start is None:
                return
            self._drag_start = None
            if self.selection_rect is not None and (self.selection_rect.width() < 3 or self.selection_rect.height() < 3):
                self.selection_rect = None
            if self.on_selection_changed is not None:
                self.on_selection_changed(self.selection_rect)
            self.update()
        elif self.mode == "paint" and self.on_paint_release is not None:
            self.on_paint_release()

    def clear_selection(self) -> None:
        self.selection_rect = None
        self._drag_start = None
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.mode != "select" or self.selection_rect is None:
            return
        painter = QPainter(self)
        pen = QPen(QColor(255, 255, 255))
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(self.selection_rect)

class Canvas(QScrollArea):
    MIN_ZOOM = 0.1
    MAX_ZOOM = 8.0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.zoom: float = 1.0
        self.tool = "select"
        self.brush_color = (0, 0, 0)
        self.brush_size = 10
        self._pixmap: QPixmap | None = None
        self._source_image: Image.Image | None = None
        self._working_image: Image.Image | None = None
        self._last_point = None
        self.on_crop_selection_changed = None
        self.on_stroke_committed = None
        self.on_color_picked = None
        self.image_label = ImageLabel()
        self.image_label.on_selection_changed = self._on_selection_changed
        self.image_label.on_paint_press = self._on_paint_press
        self.image_label.on_paint_move = self._on_paint_move
        self.image_label.on_paint_release = self._on_paint_release
        self.image_label.on_pick = self._on_pick
        self.setWidget(self.image_label)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignCenter)

    def set_image(self, image: Image.Image | None) -> None:
        self._source_image = image
        self.image_label.clear_selection()
        self._on_selection_changed(None)
        if image is None:
            self._pixmap = None
            self.image_label.clear()
            return
        self._pixmap = pil_image_to_qpixmap(image)
        self._refresh_display()

    def set_zoom(self, zoom: float) -> None:
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))
        self.image_label.clear_selection()
        self._on_selection_changed(None)
        self._refresh_display()

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self.image_label.mode = "select" if tool == "select" else ("pick" if tool == "pick" else "paint")
        self.image_label.clear_selection()
        self._on_selection_changed(None)

    def crop_box(self):
        rect = self.image_label.selection_rect
        if rect is None or self._pixmap is None:
            return None
        image_width = self._pixmap.width()
        image_height = self._pixmap.height()
        left = max(0, min(image_width, round(rect.left() / self.zoom)))
        top = max(0, min(image_height, round(rect.top() / self.zoom)))
        right = max(0, min(image_width, round(rect.right() / self.zoom)))
        bottom = max(0, min(image_height, round(rect.bottom() / self.zoom)))
        if right <= left or bottom <= top:
            return None
        return (left, top, right, bottom)

    def _label_to_image_point(self, point):
        if self._pixmap is None:
            return None
        x = round(point.x() / self.zoom)
        y = round(point.y() / self.zoom)
        x = max(0, min(self._pixmap.width() - 1, x))
        y = max(0, min(self._pixmap.height() - 1, y))
        return x, y

    def _on_paint_press(self, point) -> None:
        if self._source_image is None:
            return
        image_point = self._label_to_image_point(point)
        if image_point is None:
            return
        self._working_image = self._source_image.copy()
        self._last_point = image_point
        self._draw_segment(image_point, image_point)

    def _on_paint_move(self, point) -> None:
        if self._working_image is None:
            return
        image_point = self._label_to_image_point(point)
        if image_point is None:
            return
        self._draw_segment(self._last_point, image_point)
        self._last_point = image_point

    def _on_paint_release(self) -> None:
        if self._working_image is None:
            return
        result = self._working_image
        self._working_image = None
        self._last_point = None
        if self.on_stroke_committed is not None:
            self.on_stroke_committed(result)

    def _draw_segment(self, start, end) -> None:
        if self.tool == "brush":
            image_operations.draw_brush_segment_inplace(self._working_image, start, end, self.brush_color, self.brush_size)
        elif self.tool == "eraser":
            image_operations.erase_segment_inplace(self._working_image, start, end, self.brush_size)
        else:
            return
        self._pixmap = pil_image_to_qpixmap(self._working_image)
        self._refresh_display()

    def _on_pick(self, point) -> None:
        if self._source_image is None:
            return
        image_point = self._label_to_image_point(point)
        if image_point is None:
            return
        pixel = self._source_image.getpixel(image_point)
        color = pixel[:3] if isinstance(pixel, tuple) else (pixel, pixel, pixel)
        if self.on_color_picked is not None:
            self.on_color_picked(color)

    def _on_selection_changed(self, rect) -> None:
        if self.on_crop_selection_changed is not None:
            self.on_crop_selection_changed(rect is not None)

    def _refresh_display(self) -> None:
        if self._pixmap is None:
            return
        target_width = max(1, round(self._pixmap.width() * self.zoom))
        target_height = max(1, round(self._pixmap.height() * self.zoom))
        scaled = self._pixmap.scaled(
            target_width,
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.resize(scaled.size())
