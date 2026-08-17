from PIL import Image, ImageEnhance

def rotate_90_cw(image):
    return image.transpose(Image.ROTATE_270)

def rotate_90_ccw(image):
    return image.transpose(Image.ROTATE_90)

def rotate_180(image):
    return image.transpose(Image.ROTATE_180)

def flip_horizontal(image):
    return image.transpose(Image.FLIP_LEFT_RIGHT)

def flip_vertical(image):
    return image.transpose(Image.FLIP_TOP_BOTTOM)

def resize(image, width, height):
    return image.resize((width, height), Image.LANCZOS)

def crop(image, box):
    return image.crop(box)

def _apply_enhancer(image, enhancer_cls, factor):
    if image.mode == "RGBA":
        alpha = image.split()[-1]
        enhanced = enhancer_cls(image.convert("RGB")).enhance(factor)
        enhanced = enhanced.convert("RGBA")
        enhanced.putalpha(alpha)
        return enhanced
    return enhancer_cls(image).enhance(factor)

def adjust_brightness(image, factor):
    return _apply_enhancer(image, ImageEnhance.Brightness, factor)

def adjust_contrast(image, factor):
    return _apply_enhancer(image, ImageEnhance.Contrast, factor)

def adjust_saturation(image, factor):
    return _apply_enhancer(image, ImageEnhance.Color, factor)

def grayscale(image):
    gray = image.convert("L").convert("RGB")
    if image.mode == "RGBA":
        gray = gray.convert("RGBA")
        gray.putalpha(image.split()[-1])
    return gray
