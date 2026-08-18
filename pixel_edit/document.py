from pathlib import Path

from PIL import Image

from .history import History

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}

class Document:
    def __init__(self) -> None:
        self.file_path: Path | None = None
        self.modified: bool = False
        self._history = History()

    @property
    def image(self) -> Image.Image | None:
        return self._history.current

    @property
    def has_image(self) -> bool:
        return self._history.current is not None

    @property
    def display_name(self) -> str:
        return self.file_path.name if self.file_path else "Untitled"

    @property
    def can_undo(self) -> bool:
        return self._history.can_undo

    @property
    def can_redo(self) -> bool:
        return self._history.can_redo

    def open(self, path: str) -> None:
        image = Image.open(path)
        image.load()
        self._history.reset(image)
        self.file_path = Path(path)
        self.modified = False

    def apply_edit(self, new_image: Image.Image) -> None:
        self._history.push(new_image)
        self.modified = True

    def undo(self) -> None:
        if not self._history.can_undo:
            return
        self._history.undo()
        self.modified = True

    def redo(self) -> None:
        if not self._history.can_redo:
            return
        self._history.redo()
        self.modified = True

    def clear_history(self) -> None:
        self._history.clear()

    def save(self, path: str | None = None) -> None:
        if self.image is None:
            raise ValueError("There is no image to save.")
        target = Path(path) if path is not None else self.file_path
        if target is None:
            raise ValueError("No file path was given to save to.")
        image_to_save = self.image
        if target.suffix.lower() in (".jpg", ".jpeg") and image_to_save.mode in ("RGBA", "P"):
            image_to_save = image_to_save.convert("RGB")
        image_to_save.save(target)
        self.file_path = target
        self.modified = False
