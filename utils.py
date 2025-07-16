import re

from PIL import Image
from pydoll.elements.web_element import WebElement


def to_element_list(
    result: WebElement | list[WebElement] | None,
) -> list[WebElement]:

    if result is None:
        return []

    if isinstance(result, WebElement):
        return [result]

    return result


def is_rectangle_ad(image: Image.Image) -> bool:
    return image.size == (300, 250)


def get_fiction_id_from_url(url: str) -> int | None:
    match = re.search(r"royalroad\.com/fiction/(\d+)", url)
    return int(match.group(1)) if match else None
