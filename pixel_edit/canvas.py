from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea

def pil_image_to_qpixmap(image: Image.Image) -> QPixmap:
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
    qt_format = QImage.Format_RGBA8888 if image.mode == "RGBA" else QImage.Format_RGB888
    raw_bytes = image.tobytes("raw", image.mode)
    qimage = QImage(raw_bytes, image.width, image.height, qt_format)
    return QPixmap.fromImage(qimage.copy())

class Canvas(QScrollArea):
    MIN_ZOOM = 0.1
    MAX_ZOOM = 8.0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.zoom: float = 1.0
        self._pixmap: QPixmap | None = None
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.setWidget(self.image_label)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)

    def set_image(self, image: Image.Image | None) -> None:
        if image is None:
            self._pixmap = None
            self.image_label.clear()
            return
        self._pixmap = pil_image_to_qpixmap(image)
        self._refresh_display()

    def set_zoom(self, zoom: float) -> None:
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))
        self._refresh_display()

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
