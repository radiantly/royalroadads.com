import argparse
import asyncio
from pathlib import Path

import config
from api import API
from entry_manager import EntryManager
from scraper import Scraper
from utils import get_fiction_id_from_url


async def main() -> None:
    parser = argparse.ArgumentParser(prog="RoyalRoadAds")
    scraper = Scraper()
    if ad_entries := await scraper.retrieve_ads():
        here = Path(__file__).parent
        entry_manager = EntryManager(
            ad_images_dir=here / "docs" / "300x250",
            cover_images_dir=here / "docs" / "200x300",
            fiction_json_file_path=here / "docs" / "fiction.json",
            debug_dir_path=here / "debug",
        )

        api = API.from_refresh_token(config.RR_REFRESH_TOKEN, config.RR_CLIENT_SECRET)

        for entry in ad_entries:
            entry_manager.save_ad_entry(entry)

            fiction_id = get_fiction_id_from_url(entry.link)
            if fiction_id and (fiction_entry := api.get_fiction(fiction_id)):
                entry_manager.save_fiction_entry(fiction_entry)
                print("Successfully saved fiction entry", fiction_id)
                await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
