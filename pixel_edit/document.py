from pathlib import Path

from PIL import Image

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}

class Document:
    def __init__(self) -> None:
        self.image: Image.Image | None = None
        self.file_path: Path | None = None
        self.modified: bool = False

    @property
    def has_image(self) -> bool:
        return self.image is not None

    @property
    def display_name(self) -> str:
        return self.file_path.name if self.file_path else "Untitled"

    def open(self, path: str) -> None:
        image = Image.open(path)
        image.load()
        self.image = image
        self.file_path = Path(path)
        self.modified = False

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
