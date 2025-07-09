import io
import math
from base64 import b64decode

from PIL import Image, ImageChops


def to_image(base64_image: str) -> Image.Image | None:
    try:
        image_data = b64decode(base64_image)
        return Image.open(io.BytesIO(image_data))
    except Exception as e:
        print(e)


def calculate_rms(img1: Image.Image, img2: Image.Image) -> float:
    """Calculate the Root-Mean-Square Error between two images."""

    # if the images have different modes, eg, RGB and RGBA
    # we can assume that they're basically different images
    if img1.mode != img2.mode:
        return float("inf")

    diff = ImageChops.difference(img1, img2)
    h = diff.histogram()

    squares = (value * ((idx % 256) ** 2) for idx, value in enumerate(h))
    sum_of_squares = sum(squares)

    rms = math.sqrt(sum_of_squares / float(img1.size[0] * img1.size[1]))
    return rms
