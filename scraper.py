import asyncio
import json
import time
import typing
import uuid

from PIL import Image
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.protocol.network.events import NetworkEvent
from pydoll.protocol.network.types import Response

from entry_manager import AdEntry
from image_utils import to_image
from utils import is_rectangle_ad, to_element_list


class Scraper:
    async def _retrieve_ads(self) -> list[AdEntry] | None:
        options = ChromiumOptions()
        options.add_argument("--window-size=1920,960")
        # options.add_argument("--headless=new") # ads don't load, possibly because of the page visibility API
        async with Chrome(options=options) as browser:
            tab = await browser.start()

            rectangle_ads: dict[str, Image.Image] = {}

            response_map: dict[str, Response] = {}

            async def handle_response_received(event: typing.Any) -> None:
                request_id = event["params"]["requestId"]
                response_map[request_id] = event["params"]["response"]

            async def handle_loading_finished(event: typing.Any) -> None:
                request_id = event["params"]["requestId"]

                if request_id not in response_map:
                    print("Could not find response for request", request_id)
                    return

                response = response_map[request_id]
                url = response["url"]

                # Only capture API responses
                if ".jpg" in url or ".png" in url and response["status"] == 200:
                    try:
                        # Extract the response body
                        body = await tab.get_network_response_body(request_id)
                        image = to_image(body)
                        # print(
                        #     f"Captured {'image' if image else 'unkwn'} response from: {url} {body[:50]}"
                        # )
                        if image and is_rectangle_ad(image):
                            rectangle_ads[url] = image
                    except Exception as e:
                        print(f"Failed to capture response: {e}")

            await tab.enable_network_events()
            await tab.on(NetworkEvent.RESPONSE_RECEIVED, handle_response_received)
            await tab.on(NetworkEvent.LOADING_FINISHED, handle_loading_finished)
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
                return None

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
                        obj[image.src] = {link, alt: image.alt};       
                        return obj;
                    }, {}))"""
            )

            print(rectangle_ads)
            image_data = json.loads(response["result"]["result"]["value"])

            self.entries: list[AdEntry] = []
            for image_url, image in rectangle_ads.items():
                if image_url not in image_data:
                    print("Could not find image data for", image_url)
                    continue

                link = image_data[image_url]["link"]

                if link == "/premium":
                    print("Skipping /premium")
                    continue

                entry = AdEntry(
                    uid=str(uuid.uuid4()),
                    alt=image_data[image_url]["alt"],
                    link=link,
                    timestamp=int(time.time()),
                    image=image,
                )

                self.entries.append(entry)

            return self.entries

    async def retrieve_ads(self) -> list[AdEntry] | None:
        self.entries: list[AdEntry] = []
        try:
            return await self._retrieve_ads()
        except:
            print("Exception raised by _retrieve_ads()")

        return self.entries
