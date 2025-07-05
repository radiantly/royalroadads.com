import argparse
import asyncio
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.commands import DomCommands
from pydoll.elements.web_element import WebElement
from pydoll.protocol.network.events import NetworkEvent

from image_utils import calculate_rms, to_image


@dataclass
class Ad:
    image: Image.Image
    campaign: str


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


def matches_existing_image(
    new_image: Image.Image, existing_images: list[Image.Image], threshold=10
) -> bool:
    for i, existing_image in enumerate(existing_images):
        rms = calculate_rms(new_image, existing_image)
        print(f"{i:4} rms", rms)
        if rms < threshold:
            return True
    return False


def add_entries(new_entries: dict[str, Image.Image]):
    here = Path(__file__).parent
    entries_file_path = here / "entries.json"
    images_path = here / "300x250"
    existing_images = []
    try:
        saved = json.loads(entries_file_path.read_text(encoding="utf-8"))
        if "entries" not in saved:
            saved["entries"] = []
        existing_images = [
            Image.open(images_path / f"{i}.webp") for i in range(len(saved["entries"]))
        ]
    except:
        saved = {"entries": []}

    for link_url, image in new_entries.items():

        if matches_existing_image(image, existing_images):
            image.save(here / "skipped" / f"{uuid.uuid4()}.webp")
            continue

        idx = len(saved["entries"])
        image_path = images_path / f"{idx}.webp"
        saved["entries"].append(link_url)
        image.save(image_path, "webp")

    with open(entries_file_path, "w") as f:
        json.dump(saved, f)


async def get_parent(element: WebElement) -> WebElement | None:
    node_description = await element._describe_node(object_id=element._object_id)
    parent_id = node_description.get("parentId")

    command = DomCommands.resolve_node(node_id=parent_id)
    response = await element._execute_command(command=command)
    parent_object_id = response["result"]["object"]["objectId"]

    parent_node_desc = await element._describe_node(object_id=parent_object_id)
    attributes = parent_node_desc.get("attributes", [])
    tag_name = parent_node_desc.get("nodeName", "").lower()
    attributes.extend(["tag_name", tag_name])

    return WebElement(
        object_id=parent_object_id,
        connection_handler=element._connection_handler,
        attributes_list=attributes,
    )


async def retrieve_ads():
    options = ChromiumOptions()
    options.add_argument("--window-size=1920,960")
    async with Chrome(options=options) as browser:
        tab = await browser.start()

        rectangle_ads: dict[str, Image.Image] = {}

        async def capture_api_responses(event):
            request_id = event["params"]["requestId"]
            response = event["params"]["response"]
            url = response["url"]

            # Only capture API responses
            if ".jpg" in url or ".png" in url and response["status"] == 200:
                try:
                    # Extract the response body
                    body = await tab.get_network_response_body(request_id)
                    image = to_image(body)
                    print(
                        f"Captured {'image' if image else 'unkwn'} response from: {url} {body[:50]}"
                    )
                    if image and is_rectangle_ad(image):
                        rectangle_ads[url] = image
                except Exception as e:
                    print(f"Failed to capture response: {e}")

        await tab.enable_network_events()
        await tab.on(NetworkEvent.RESPONSE_RECEIVED, capture_api_responses)
        await tab.go_to("https://www.royalroad.com/home")

        await asyncio.sleep(2)

        portlets = to_element_list(
            await tab.query(".portlet", find_all=True, raise_exc=False)
        )

        if portlets:
            print(f"{len(portlets)} portlets found.")
        else:
            print(
                "ERROR: Could not find portlet divs. Site design has possibly changed."
            )
            return

        for portlet in portlets:
            await portlet.scroll_into_view()
            await asyncio.sleep(2)

        print(len(rectangle_ads), "rectangle ads found.")

        response = await tab.execute_script(
            """
            return JSON.stringify(Array.from(document.querySelectorAll("iframe"))
                .reduce((obj, iframe) => {
                    const image = iframe.contentDocument?.querySelector("iframe")?.contentDocument?.querySelector("img.imagecreative") ?? null;
                    if (!image?.src) return obj;
                    const a = image.closest("a");
                    if (!a?.href) return obj;
                    const link = new URL(a.href).searchParams.get("url");
                    if (!link) return obj;
                    obj[image.src] = link;       
                    return obj;
                }, {}))"""
        )

        print(rectangle_ads)
        links = json.loads(response["result"]["result"]["value"])

        entries = {
            links[image_url]: image
            for image_url, image in rectangle_ads.items()
            if image_url in links
        }

        add_entries(entries)


def main():
    parser = argparse.ArgumentParser(prog="RoyalRoadAds")
    asyncio.run(retrieve_ads())


if __name__ == "__main__":
    main()
