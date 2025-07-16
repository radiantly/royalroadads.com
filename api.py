import io
from typing import Self

import requests
import urllib3
from PIL import Image

from entry_manager import FictionEntry


class API:
    API_HOST = "api.royalroad.com"
    AUTH_HOST = "auth.royalroad.com"

    def __init__(self, session: requests.Session):
        self.session = session
        pass

    @classmethod
    def from_access_token(cls, access_token: str) -> Self:
        headers = {
            "Authorization": "Bearer " + access_token,
            "Accept": "application/json",
            "User-Agent": urllib3.util.SKIP_HEADER,
            "CustomUserAgent": "Royal Road Mobile/1.92.871 ( Android; 14; Arm64; Phone ) MAUI/9.0.5",
            "X-Mature-Content": "true",
        }
        session = requests.Session()
        session.headers.update(headers)

        return cls(session=session)

    @classmethod
    def from_refresh_token(cls, refresh_token: str, client_secret: str) -> Self:
        response = requests.post(
            f"https://{cls.AUTH_HOST}/connect/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": "royalroad-mobile",
                "client_secret": client_secret,
            },
            headers={
                "Accept": "application/json",
                "User-Agent": urllib3.util.SKIP_HEADER,
            },
        ).json()

        return cls.from_access_token(response["access_token"])

    def get_fiction(self, fiction_id: int) -> FictionEntry | None:
        r = self.session.get(f"https://{self.API_HOST}/v1/fiction/{fiction_id}")

        if r.status_code != 200:
            print(r.status_code, r.text)
            return None

        fiction = r.json()

        cover_image_url = fiction["cover"]
        if not cover_image_url:
            print(f"Skipping {fiction_id}, no cover image")
            return None

        r = self.session.get(cover_image_url)

        if r.status_code != 200:
            print(r.status_code, "Failed to retrieve cover image", cover_image_url)
            return None
        try:
            cover_image = Image.open(io.BytesIO(r.content))
        except Exception as exception:
            print("Failed to load cover image from", cover_image_url, exception)
            return None

        return FictionEntry.from_api(fiction, cover_image)


if __name__ == "__main__":
    from config import RR_CLIENT_SECRET, RR_REFRESH_TOKEN

    api = API.from_refresh_token(RR_REFRESH_TOKEN, RR_CLIENT_SECRET)
    print(api.get_fiction(21220))
