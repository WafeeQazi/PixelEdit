from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from . import image_operations
from .canvas import Canvas
from .document import Document

OPEN_FILTER = "Images (*.png *.jpg *.jpeg *.bmp)"
SAVE_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)"
ZOOM_STEP = 1.25

class ResizeDialog(QDialog):
    def __init__(self, width, height, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resize Image")
        self.original_width = width
        self.original_height = height
        self.width_box = QSpinBox()
        self.width_box.setRange(1, 20000)
        self.width_box.setValue(width)
        self.height_box = QSpinBox()
        self.height_box.setRange(1, 20000)
        self.height_box.setValue(height)
        self.lock_checkbox = QCheckBox("Keep aspect ratio")
        self.lock_checkbox.setChecked(True)
        self.width_box.valueChanged.connect(self._width_changed)
        self.height_box.valueChanged.connect(self._height_changed)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout()
        form.addRow("Width", self.width_box)
        form.addRow("Height", self.height_box)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.lock_checkbox)
        layout.addWidget(buttons)

    def _width_changed(self, value) -> None:
        if not self.lock_checkbox.isChecked():
            return
        ratio = self.original_height / self.original_width
        new_height = max(1, round(value * ratio))
        self.height_box.blockSignals(True)
        self.height_box.setValue(new_height)
        self.height_box.blockSignals(False)

    def _height_changed(self, value) -> None:
        if not self.lock_checkbox.isChecked():
            return
        ratio = self.original_width / self.original_height
        new_width = max(1, round(value * ratio))
        self.width_box.blockSignals(True)
        self.width_box.setValue(new_width)
        self.width_box.blockSignals(False)

    def values(self):
        return self.width_box.value(), self.height_box.value()

class AdjustDialog(QDialog):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adjustments")
        self.original_image = image
        self.result_image = image
        self.on_preview = None
        self.brightness_slider, brightness_row = self._build_slider_row()
        self.contrast_slider, contrast_row = self._build_slider_row()
        self.saturation_slider, saturation_row = self._build_slider_row()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout()
        form.addRow("Brightness", brightness_row)
        form.addRow("Contrast", contrast_row)
        form.addRow("Saturation", saturation_row)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setMinimumWidth(320)

    def _build_slider_row(self):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 200)
        slider.setValue(100)
        value_label = QLabel("100%")
        value_label.setFixedWidth(40)
        slider.valueChanged.connect(lambda value: value_label.setText(f"{value}%"))
        slider.valueChanged.connect(self._update_preview)
        row = QHBoxLayout()
        row.addWidget(slider)
        row.addWidget(value_label)
        return slider, row

    def _update_preview(self, _value=None) -> None:
        image = image_operations.adjust_brightness(self.original_image, self.brightness_slider.value() / 100)
        image = image_operations.adjust_contrast(image, self.contrast_slider.value() / 100)
        image = image_operations.adjust_saturation(image, self.saturation_slider.value() / 100)
        self.result_image = image
        if self.on_preview is not None:
            self.on_preview(image)

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.document = Document()
        self.canvas = Canvas()
        self.canvas.on_crop_selection_changed = self._set_crop_enabled
        self.setCentralWidget(self.canvas)
        self._create_actions()
        self._create_menu_bar()
        self.resize(1000, 700)
        self._update_title()
        self._update_status()

    def _create_actions(self) -> None:
        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.triggered.connect(self.open_image)
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_image)
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_as_action.triggered.connect(self.save_image_as)
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)
        self.zoom_in_action = QAction("Zoom In", self)
        self.zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action = QAction("Zoom Out", self)
        self.zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.zoom_reset_action = QAction("Actual Size", self)
        self.zoom_reset_action.setShortcut("Ctrl+0")
        self.zoom_reset_action.triggered.connect(self.zoom_reset)
        self.rotate_cw_action = QAction("Rotate Clockwise", self)
        self.rotate_cw_action.triggered.connect(self.rotate_clockwise)
        self.rotate_ccw_action = QAction("Rotate Counterclockwise", self)
        self.rotate_ccw_action.triggered.connect(self.rotate_counterclockwise)
        self.rotate_180_action = QAction("Rotate 180°", self)
        self.rotate_180_action.triggered.connect(self.rotate_180)
        self.flip_h_action = QAction("Flip Horizontal", self)
        self.flip_h_action.triggered.connect(self.flip_horizontal)
        self.flip_v_action = QAction("Flip Vertical", self)
        self.flip_v_action.triggered.connect(self.flip_vertical)
        self.resize_action = QAction("Resize...", self)
        self.resize_action.triggered.connect(self.resize_image)
        self.crop_action = QAction("Crop to Selection", self)
        self.crop_action.setEnabled(False)
        self.crop_action.triggered.connect(self.crop_to_selection)
        self.adjustments_action = QAction("Adjustments...", self)
        self.adjustments_action.triggered.connect(self.open_adjustments)
        self.grayscale_action = QAction("Grayscale", self)
        self.grayscale_action.triggered.connect(self.apply_grayscale)

    def _create_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        image_menu = self.menuBar().addMenu("&Image")
        image_menu.addAction(self.rotate_cw_action)
        image_menu.addAction(self.rotate_ccw_action)
        image_menu.addAction(self.rotate_180_action)
        image_menu.addSeparator()
        image_menu.addAction(self.flip_h_action)
        image_menu.addAction(self.flip_v_action)
        image_menu.addSeparator()
        image_menu.addAction(self.resize_action)
        image_menu.addAction(self.crop_action)
        image_menu.addSeparator()
        image_menu.addAction(self.adjustments_action)
        image_menu.addAction(self.grayscale_action)
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.zoom_reset_action)

    def open_image(self) -> None:
        if not self._confirm_discard_changes():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", OPEN_FILTER)
        if not path:
            return
        try:
            self.document.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Could Not Open Image", str(exc))
            return
        self.canvas.set_image(self.document.image)
        self.canvas.set_zoom(1.0)
        self._update_title()
        self._update_status()

    def save_image(self) -> None:
        if not self.document.has_image:
            return
        if self.document.file_path is None:
            self.save_image_as()
            return
        try:
            self.document.save()
        except Exception as exc:
            QMessageBox.critical(self, "Could Not Save Image", str(exc))
            return
        self._update_title()
        self.statusBar().showMessage(f"Saved to {self.document.file_path}", 3000)

    def save_image_as(self) -> None:
        if not self.document.has_image:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image As", "", SAVE_FILTER)
        if not path:
            return
        try:
            self.document.save(path)
        except Exception as exc:
            QMessageBox.critical(self, "Could Not Save Image", str(exc))
            return
        self._update_title()
        self.statusBar().showMessage(f"Saved to {self.document.file_path}", 3000)

    def zoom_in(self) -> None:
        self.canvas.set_zoom(self.canvas.zoom * ZOOM_STEP)
        self._update_status()

    def zoom_out(self) -> None:
        self.canvas.set_zoom(self.canvas.zoom / ZOOM_STEP)
        self._update_status()

    def zoom_reset(self) -> None:
        self.canvas.set_zoom(1.0)
        self._update_status()

    def rotate_clockwise(self) -> None:
        self._apply_operation(image_operations.rotate_90_cw)

    def rotate_counterclockwise(self) -> None:
        self._apply_operation(image_operations.rotate_90_ccw)

    def rotate_180(self) -> None:
        self._apply_operation(image_operations.rotate_180)

    def flip_horizontal(self) -> None:
        self._apply_operation(image_operations.flip_horizontal)

    def flip_vertical(self) -> None:
        self._apply_operation(image_operations.flip_vertical)

    def resize_image(self) -> None:
        if not self.document.has_image:
            return
        width, height = self.document.image.size
        dialog = ResizeDialog(width, height, self)
        if dialog.exec() != QDialog.Accepted:
            return
        new_width, new_height = dialog.values()
        new_image = image_operations.resize(self.document.image, new_width, new_height)
        self.document.apply_edit(new_image)
        self.canvas.set_image(new_image)
        self._update_title()
        self._update_status()

    def crop_to_selection(self) -> None:
        if not self.document.has_image:
            return
        box = self.canvas.crop_box()
        if box is None:
            return
        new_image = image_operations.crop(self.document.image, box)
        self.document.apply_edit(new_image)
        self.canvas.set_image(new_image)
        self._update_title()
        self._update_status()

    def open_adjustments(self) -> None:
        if not self.document.has_image:
            return
        dialog = AdjustDialog(self.document.image, self)
        dialog.on_preview = self.canvas.set_image
        if dialog.exec() == QDialog.Accepted:
            self.document.apply_edit(dialog.result_image)
            self.canvas.set_image(dialog.result_image)
            self._update_title()
            self._update_status()
        else:
            self.canvas.set_image(self.document.image)

    def apply_grayscale(self) -> None:
        self._apply_operation(image_operations.grayscale)

    def _apply_operation(self, operation) -> None:
        if not self.document.has_image:
            return
        new_image = operation(self.document.image)
        self.document.apply_edit(new_image)
        self.canvas.set_image(new_image)
        self._update_title()
        self._update_status()

    def _set_crop_enabled(self, enabled) -> None:
        self.crop_action.setEnabled(enabled)

    def _update_title(self) -> None:
        marker = "*" if self.document.modified else ""
        self.setWindowTitle(f"{marker}{self.document.display_name} - PixelEdit")

    def _update_status(self) -> None:
        if not self.document.has_image:
            self.statusBar().showMessage("No image open")
            return
        width, height = self.document.image.size
        zoom_percent = round(self.canvas.zoom * 100)
        self.statusBar().showMessage(f"{width} x {height} px    {zoom_percent}%")

    def _confirm_discard_changes(self) -> bool:
        if not self.document.modified:
            return True
        response = QMessageBox.question(
            self,
            "Unsaved Changes",
            "The current image has unsaved changes. Discard them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if response == QMessageBox.Save:
            self.save_image()
            return not self.document.modified
        return response == QMessageBox.Discard

    def closeEvent(self, event) -> None:
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()
