from PIL import Image

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
