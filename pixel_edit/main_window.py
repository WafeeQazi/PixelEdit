from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QToolBar,
    QVBoxLayout,
)

from . import image_operations
from .canvas import Canvas
from .document import SUPPORTED_EXTENSIONS, Document

OPEN_FILTER = "Images (*.png *.jpg *.jpeg *.bmp)"
SAVE_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)"
ZOOM_STEP = 1.25
DEFAULT_BRUSH_SIZE = 10
MAX_RECENT_FILES = 8

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

class ImageInfoDialog(QDialog):
    def __init__(self, document, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Info")
        image = document.image
        has_alpha = "A" in image.getbands()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"File: {document.display_name}"))
        layout.addWidget(QLabel(f"Dimensions: {image.width} x {image.height} px"))
        layout.addWidget(QLabel(f"Color Mode: {image.mode}"))
        layout.addWidget(QLabel(f"Transparency: {'Yes' if has_alpha else 'No'}"))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.document = Document()
        self.recent_files = []
        self.canvas = Canvas()
        self.canvas.on_crop_selection_changed = self._set_crop_enabled
        self.canvas.on_stroke_committed = self._commit_stroke
        self.canvas.on_color_picked = self._set_brush_color
        self.canvas.on_text_committed = self._commit_text
        self.canvas.brush_size = DEFAULT_BRUSH_SIZE
        self.setCentralWidget(self.canvas)
        self._create_actions()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()
        self.setAcceptDrops(True)
        self.resize(1000, 700)
        self._refresh_ui()

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
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.undo)
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence.Redo)
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.redo)
        self.clear_history_action = QAction("Clear History", self)
        self.clear_history_action.setEnabled(False)
        self.clear_history_action.triggered.connect(self.clear_history)
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
        self.rotate_cw_action.setShortcut("Ctrl+]")
        self.rotate_cw_action.triggered.connect(self.rotate_clockwise)
        self.rotate_ccw_action = QAction("Rotate Counterclockwise", self)
        self.rotate_ccw_action.setShortcut("Ctrl+[")
        self.rotate_ccw_action.triggered.connect(self.rotate_counterclockwise)
        self.rotate_180_action = QAction("Rotate 180°", self)
        self.rotate_180_action.setShortcut("Ctrl+Shift+R")
        self.rotate_180_action.triggered.connect(self.rotate_180)
        self.flip_h_action = QAction("Flip Horizontal", self)
        self.flip_h_action.setShortcut("Ctrl+Shift+H")
        self.flip_h_action.triggered.connect(self.flip_horizontal)
        self.flip_v_action = QAction("Flip Vertical", self)
        self.flip_v_action.setShortcut("Ctrl+Shift+V")
        self.flip_v_action.triggered.connect(self.flip_vertical)
        self.resize_action = QAction("Resize...", self)
        self.resize_action.setShortcut("Ctrl+R")
        self.resize_action.triggered.connect(self.resize_image)
        self.crop_action = QAction("Crop to Selection", self)
        self.crop_action.setShortcut("Ctrl+Shift+C")
        self.crop_action.setEnabled(False)
        self.crop_action.triggered.connect(self.crop_to_selection)
        self.adjustments_action = QAction("Adjustments...", self)
        self.adjustments_action.setShortcut("Ctrl+M")
        self.adjustments_action.triggered.connect(self.open_adjustments)
        self.grayscale_action = QAction("Grayscale", self)
        self.grayscale_action.setShortcut("Ctrl+Shift+G")
        self.grayscale_action.triggered.connect(self.apply_grayscale)
        self.image_info_action = QAction("Image Info...", self)
        self.image_info_action.setShortcut("Ctrl+Shift+I")
        self.image_info_action.triggered.connect(self.show_image_info)
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        self.select_tool_action = QAction("Selection", self)
        self.select_tool_action.setShortcut("S")
        self.select_tool_action.setCheckable(True)
        self.select_tool_action.setChecked(True)
        self.select_tool_action.triggered.connect(lambda: self._set_tool("select"))
        self.tool_group.addAction(self.select_tool_action)
        self.brush_tool_action = QAction("Brush", self)
        self.brush_tool_action.setShortcut("B")
        self.brush_tool_action.setCheckable(True)
        self.brush_tool_action.triggered.connect(lambda: self._set_tool("brush"))
        self.tool_group.addAction(self.brush_tool_action)
        self.eraser_tool_action = QAction("Eraser", self)
        self.eraser_tool_action.setShortcut("E")
        self.eraser_tool_action.setCheckable(True)
        self.eraser_tool_action.triggered.connect(lambda: self._set_tool("eraser"))
        self.tool_group.addAction(self.eraser_tool_action)
        self.color_picker_action = QAction("Color Picker", self)
        self.color_picker_action.setShortcut("I")
        self.color_picker_action.setCheckable(True)
        self.color_picker_action.triggered.connect(lambda: self._set_tool("pick"))
        self.tool_group.addAction(self.color_picker_action)
        self.text_tool_action = QAction("Text", self)
        self.text_tool_action.setShortcut("T")
        self.text_tool_action.setCheckable(True)
        self.text_tool_action.triggered.connect(lambda: self._set_tool("text"))
        self.tool_group.addAction(self.text_tool_action)

    def _create_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_action)
        self.recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_menu()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.clear_history_action)
        image_menu = self.menuBar().addMenu("&Image")
        image_menu.addAction(self.image_info_action)
        image_menu.addSeparator()
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
        draw_menu = self.menuBar().addMenu("&Draw")
        draw_menu.addAction(self.select_tool_action)
        draw_menu.addAction(self.brush_tool_action)
        draw_menu.addAction(self.eraser_tool_action)
        draw_menu.addAction(self.color_picker_action)
        draw_menu.addAction(self.text_tool_action)
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.zoom_reset_action)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Drawing Toolbar", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.size_label = QLabel(" Brush Size: ")
        toolbar.addWidget(self.size_label)
        self.brush_size_box = QSpinBox()
        self.brush_size_box.setRange(1, 200)
        self.brush_size_box.setValue(DEFAULT_BRUSH_SIZE)
        self.brush_size_box.valueChanged.connect(self._set_brush_size)
        toolbar.addWidget(self.brush_size_box)
        toolbar.addWidget(QLabel(" Color: "))
        self.color_button = QPushButton()
        self.color_button.setFixedSize(24, 24)
        self.color_button.clicked.connect(self.choose_brush_color)
        toolbar.addWidget(self.color_button)
        self._update_color_button()

    def _create_status_bar(self) -> None:
        self.dimensions_label = QLabel()
        self.statusBar().addPermanentWidget(self.dimensions_label)

    def dragEnterEvent(self, event) -> None:
        if self._first_supported_path(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        path = self._first_supported_path(event.mimeData())
        if path is None:
            event.ignore()
            return
        self._open_path(path)
        event.acceptProposedAction()

    def _first_supported_path(self, mime_data):
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            path = url.toLocalFile()
            if path and Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
                return path
        return None

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", OPEN_FILTER)
        if not path:
            return
        self._open_path(path)

    def _open_path(self, path) -> None:
        if not self._confirm_discard_changes():
            return
        try:
            self.document.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Could Not Open Image", str(exc))
            return
        self.canvas.set_image(self.document.image)
        self.canvas.set_zoom(1.0)
        self._refresh_ui()
        self.statusBar().showMessage(f"Opened {self.document.display_name}", 3000)
        self._add_recent_file(path)

    def _add_recent_file(self, path) -> None:
        path = str(path)
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        del self.recent_files[MAX_RECENT_FILES:]
        self._update_recent_menu()

    def _update_recent_menu(self) -> None:
        self.recent_menu.clear()
        if not self.recent_files:
            empty_action = QAction("No Recent Files", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
            return
        for path in self.recent_files:
            action = QAction(path, self)
            action.triggered.connect(lambda checked=False, p=path: self._open_path(p))
            self.recent_menu.addAction(action)
        self.recent_menu.addSeparator()
        clear_action = QAction("Clear Recent Files", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def _clear_recent_files(self) -> None:
        self.recent_files = []
        self._update_recent_menu()

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
        self._apply_operation(image_operations.rotate_90_cw, "Rotated 90° clockwise")

    def rotate_counterclockwise(self) -> None:
        self._apply_operation(image_operations.rotate_90_ccw, "Rotated 90° counterclockwise")

    def rotate_180(self) -> None:
        self._apply_operation(image_operations.rotate_180, "Rotated 180°")

    def flip_horizontal(self) -> None:
        self._apply_operation(image_operations.flip_horizontal, "Flipped horizontally")

    def flip_vertical(self) -> None:
        self._apply_operation(image_operations.flip_vertical, "Flipped vertically")

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
        self._refresh_ui()
        self.statusBar().showMessage(f"Resized to {new_width} x {new_height}", 3000)

    def crop_to_selection(self) -> None:
        if not self.document.has_image:
            return
        box = self.canvas.crop_box()
        if box is None:
            return
        new_image = image_operations.crop(self.document.image, box)
        self.document.apply_edit(new_image)
        self.canvas.set_image(new_image)
        self._refresh_ui()
        self.statusBar().showMessage(f"Cropped to {new_image.width} x {new_image.height}", 3000)

    def open_adjustments(self) -> None:
        if not self.document.has_image:
            return
        dialog = AdjustDialog(self.document.image, self)
        dialog.on_preview = self.canvas.set_image
        if dialog.exec() == QDialog.Accepted:
            self.document.apply_edit(dialog.result_image)
            self.canvas.set_image(dialog.result_image)
            self._refresh_ui()
            self.statusBar().showMessage("Adjustments applied", 3000)
        else:
            self.canvas.set_image(self.document.image)

    def apply_grayscale(self) -> None:
        self._apply_operation(image_operations.grayscale, "Converted to grayscale")

    def show_image_info(self) -> None:
        if not self.document.has_image:
            return
        dialog = ImageInfoDialog(self.document, self)
        dialog.exec()

    def _set_tool(self, tool) -> None:
        self.canvas.set_tool(tool)
        self.size_label.setText(" Font Size: " if tool == "text" else " Brush Size: ")

    def _commit_stroke(self, new_image) -> None:
        self.document.apply_edit(new_image)
        self.canvas.set_image(new_image)
        self._refresh_ui()

    def _commit_text(self, text, position, font_size, color) -> None:
        new_image = image_operations.draw_text(self.document.image, position, text, color, font_size)
        self.document.apply_edit(new_image)
        self.canvas.set_image(new_image)
        self._refresh_ui()
        self.statusBar().showMessage("Added text", 3000)

    def choose_brush_color(self) -> None:
        initial = QColor(*self.canvas.brush_color)
        color = QColorDialog.getColor(initial, self, "Choose Color")
        if not color.isValid():
            return
        self._set_brush_color((color.red(), color.green(), color.blue()))

    def _set_brush_color(self, color) -> None:
        self.canvas.brush_color = color
        self._update_color_button()
        if self.canvas.tool == "pick":
            self.brush_tool_action.setChecked(True)
            self.canvas.set_tool("brush")

    def _set_brush_size(self, size) -> None:
        self.canvas.brush_size = size

    def _update_color_button(self) -> None:
        r, g, b = self.canvas.brush_color
        self.color_button.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); border: 1px solid #888;")

    def undo(self) -> None:
        if not self.document.can_undo:
            return
        self.document.undo()
        self.canvas.set_image(self.document.image)
        self._refresh_ui()
        self.statusBar().showMessage("Undid last edit", 3000)

    def redo(self) -> None:
        if not self.document.can_redo:
            return
        self.document.redo()
        self.canvas.set_image(self.document.image)
        self._refresh_ui()
        self.statusBar().showMessage("Redid last edit", 3000)

    def clear_history(self) -> None:
        if not (self.document.can_undo or self.document.can_redo):
            return
        response = QMessageBox.question(
            self,
            "Clear History",
            "This will permanently remove the ability to undo or redo. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if response != QMessageBox.Yes:
            return
        self.document.clear_history()
        self._refresh_ui()
        self.statusBar().showMessage("History cleared", 3000)

    def _apply_operation(self, operation, message=None) -> None:
        if not self.document.has_image:
            return
        new_image = operation(self.document.image)
        self.document.apply_edit(new_image)
        self.canvas.set_image(new_image)
        self._refresh_ui()
        if message:
            self.statusBar().showMessage(message, 3000)

    def _set_crop_enabled(self, enabled) -> None:
        self.crop_action.setEnabled(enabled)

    def _refresh_ui(self) -> None:
        self._update_title()
        self._update_status()
        self.undo_action.setEnabled(self.document.can_undo)
        self.redo_action.setEnabled(self.document.can_redo)
        self.clear_history_action.setEnabled(self.document.can_undo or self.document.can_redo)

    def _update_title(self) -> None:
        marker = "*" if self.document.modified else ""
        self.setWindowTitle(f"{marker}{self.document.display_name} - PixelEdit")

    def _update_status(self) -> None:
        if not self.document.has_image:
            self.dimensions_label.setText("No image open")
            return
        width, height = self.document.image.size
        zoom_percent = round(self.canvas.zoom * 100)
        self.dimensions_label.setText(f"{width} x {height} px    {zoom_percent}%")

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
