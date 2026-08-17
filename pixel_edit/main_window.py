from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QToolBar

from .canvas import Canvas
from .document import Document

OPEN_FILTER = "Images (*.png *.jpg *.jpeg *.bmp)"
SAVE_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)"
ZOOM_STEP = 1.25

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.document = Document()
        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)
        self._create_actions()
        self._create_menu_bar()
        self._create_toolbar()
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

    def _create_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.zoom_reset_action)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)

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
