import argparse
import asyncio
from pathlib import Path

import config
from api import API
from entry_manager import EntryManager
from scraper import Scraper
from utils import get_fiction_id_from_url


async def rra() -> None:
    scraper = Scraper()
    if ad_entries := await scraper.retrieve_ads():
        entry_manager = EntryManager.from_defaults()

        api = API.from_refresh_token(config.RR_REFRESH_TOKEN, config.RR_CLIENT_SECRET)

        for entry in ad_entries:
            entry_manager.save_ad_entry(entry)

            fiction_id = get_fiction_id_from_url(entry.link)
            if fiction_id and (fiction_entry := api.get_fiction(fiction_id)):
                entry_manager.save_fiction_entry(fiction_entry)
                print("Successfully saved fiction entry", fiction_id)
                await asyncio.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(prog="RoyalRoadAds")
    parser.add_argument("--profile", action="store_true")

    args = parser.parse_args()

    if args.profile:
        import pyinstrument

        profiler = pyinstrument.Profiler()
        profiler.start()

    asyncio.run(rra())

    if args.profile:
        profiler.stop()
        profiler.open_in_browser()


if __name__ == "__main__":
    main()
