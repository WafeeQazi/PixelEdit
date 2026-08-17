from PIL import Image
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea

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
        self.selection_rect: QRect | None = None
        self._drag_start = None
        self.on_selection_changed = None

    def mousePressEvent(self, event) -> None:
        if self.pixmap() is None or event.button() != Qt.LeftButton:
            return
        self._drag_start = event.position().toPoint()
        self.selection_rect = QRect(self._drag_start, self._drag_start)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None:
            return
        current = event.position().toPoint()
        self.selection_rect = QRect(self._drag_start, current).normalized()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_start is None:
            return
        self._drag_start = None
        if self.selection_rect is not None and (self.selection_rect.width() < 3 or self.selection_rect.height() < 3):
            self.selection_rect = None
        if self.on_selection_changed is not None:
            self.on_selection_changed(self.selection_rect)
        self.update()

    def clear_selection(self) -> None:
        self.selection_rect = None
        self._drag_start = None
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.selection_rect is None:
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
        self._pixmap: QPixmap | None = None
        self.image_label = ImageLabel()
        self.image_label.on_selection_changed = self._on_selection_changed
        self.on_crop_selection_changed = None
        self.setWidget(self.image_label)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)

    def set_image(self, image: Image.Image | None) -> None:
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
