import argparse
import json
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Self

from PIL import Image

from image_utils import calculate_rms


@dataclass(frozen=True, kw_only=True)
class AdEntry:
    uid: str
    alt: str
    link: str
    timestamp: int
    image: Image.Image

    @property
    def file_name(self) -> str:
        return self.uid + ".webp"

    def calculate_rms(self, image: Image.Image) -> float:
        return calculate_rms(image, self.image)

    def dict(self) -> dict[str, Any]:
        d = asdict(self)
        del d["uid"]
        del d["image"]
        return d


@dataclass(frozen=True, kw_only=True)
class FictionEntry:
    id: int
    title: str
    slug: str
    description: str
    cover_image: Image.Image
    status: str
    tags: list[str]
    average_rating: float
    author_id: int
    author_name: str

    # advanced stats
    followers: int
    favorites: int
    ratings: int
    total_views: int
    word_count: int
    page_count: int

    timestamp: int

    @property
    def cover_image_file_name(self) -> str:
        return f"{self.id}.webp"

    @classmethod
    def from_api(
        cls,
        fiction: dict[str, Any],
        cover_image: Image.Image,
        timestamp: int = int(time.time()),
    ) -> Self | None:
        try:
            tags = [tag["slug"].strip() for tag in fiction["tags"] if "slug" in tag]

            return cls(
                id=fiction["id"],
                title=fiction["title"],
                slug=fiction["slug"],
                description=fiction["description"],
                cover_image=cover_image,
                status=fiction["status"],
                tags=tags,
                average_rating=fiction["averageRating"],
                author_id=fiction["authorInfo"]["userId"],
                author_name=fiction["authorInfo"]["username"],
                followers=fiction["advancedStats"]["followers"],
                favorites=fiction["advancedStats"]["favorites"],
                ratings=fiction["advancedStats"]["ratings"],
                total_views=fiction["advancedStats"]["totalViews"],
                word_count=fiction["advancedStats"]["wordCount"],
                page_count=fiction["advancedStats"]["pageCount"],
                timestamp=timestamp,
            )
        except Exception as exception:
            print("Failed to populate FictionEntry object from API:", exception)
            return None

    def dict(self) -> dict[str, Any]:
        d = asdict(self)
        del d["id"]
        del d["cover_image"]
        return d


class EntryManager:
    rms_threshold = 10

    def __init__(
        self,
        ad_images_dir: Path,
        cover_images_dir: Path,
        fiction_json_file_path: Path,
        debug_dir_path: Path,
    ):
        self.ad_json_file_path = ad_images_dir / "entries.json"
        self.ad_images_dir = ad_images_dir
        self.cover_images_dir = cover_images_dir
        self.fiction_json_file_path = fiction_json_file_path
        self.debug_dir_path = debug_dir_path

        # create directories if they do not exist
        self.ad_images_dir.mkdir(exist_ok=True, parents=True)
        self.cover_images_dir.mkdir(exist_ok=True, parents=True)
        self.debug_dir_path.mkdir(exist_ok=True, parents=True)

        self.ad_entries = self._load_ad_entries()
        self.fiction = self._load_fiction_entries()

    def _load_json_file(self, json_file_path: Path) -> dict[str, Any]:
        return (
            json.loads(json_file_path.read_text(encoding="utf-8"))
            if json_file_path.exists()
            else {}
        )

    def _load_ad_entries(self) -> dict[str, AdEntry]:
        entries: dict[str, AdEntry] = {}

        content = self._load_json_file(self.ad_json_file_path)

        for uid, entry_dict in reversed(content.get("entries", {}).items()):
            image = Image.open(self.ad_images_dir / f"{uid}.webp")
            entries[uid] = AdEntry(
                **entry_dict,
                uid=uid,
                image=image,
            )

        return entries

    def _load_fiction_entries(self) -> dict[int, FictionEntry]:
        entries: dict[int, FictionEntry] = {}

        content = self._load_json_file(self.fiction_json_file_path)

        for fiction_id_str, entry_dict in reversed(content.get("entries", {}).items()):
            fiction_id = int(fiction_id_str)
            image = Image.open(self.cover_images_dir / f"{fiction_id}.webp")
            entries[fiction_id] = FictionEntry(
                **entry_dict, id=fiction_id, cover_image=image
            )

        return entries

    def find_duplicate_ad_entry(self, new_entry: AdEntry) -> AdEntry | None:
        """Returns an ad entry that has the same image as this one"""

        for entry in self.ad_entries.values():
            if entry.uid == new_entry.uid:
                continue

            if entry.calculate_rms(new_entry.image) < self.rms_threshold:
                return entry

        return None

    def save_ad_entry(self, temp_entry: AdEntry) -> None:
        assert temp_entry.image.size == (300, 250)
        image_path = self.ad_images_dir / temp_entry.file_name
        temp_entry.image.save(image_path, "webp")
        new_entry = replace(temp_entry, image=Image.open(image_path))

        # check if an existing matches this entry
        if duplicate_entry := self.find_duplicate_ad_entry(new_entry):
            print("Removing older entry", duplicate_entry)
            (self.ad_images_dir / duplicate_entry.file_name).rename(
                self.debug_dir_path / duplicate_entry.file_name
            )
            del self.ad_entries[duplicate_entry.uid]

        self.ad_entries[new_entry.uid] = new_entry
        self._write_ad_entries_to_file()

    def save_fiction_entry(self, entry: FictionEntry) -> None:
        if entry.cover_image.size != (200, 300):
            entry = replace(entry, cover_image=entry.cover_image.resize((200, 300)))

        image_path = self.cover_images_dir / entry.cover_image_file_name
        entry.cover_image.save(image_path, "webp")
        entry = replace(entry, cover_image=Image.open(image_path))

        # delete existing entry if it exists.
        # this is required because self.fiction is ordered by timestamp (asc)
        if entry.id in self.fiction:
            del self.fiction[entry.id]

        self.fiction[entry.id] = entry
        self._write_fiction_entries_to_file()

    @staticmethod
    def _write_entries_to_file(
        json_file_path: Path, opaque_entries: dict[Any, Any]
    ) -> None:
        with open(json_file_path, "w") as fp:

            entries = {}
            for key, entry in reversed(opaque_entries.items()):
                entries[str(key)] = entry.dict()

            content = {"entries": entries}

            json.dump(obj=content, fp=fp, indent=2)

    def _write_fiction_entries_to_file(self) -> None:
        return self._write_entries_to_file(self.fiction_json_file_path, self.fiction)

    def _write_ad_entries_to_file(self) -> None:
        return self._write_entries_to_file(self.ad_json_file_path, self.ad_entries)

    def check_for_missing_ad_entries(self, delete: bool = False) -> None:
        webp_paths = list(self.ad_images_dir.glob("*.webp"))
        for webp_path in webp_paths:
            if webp_path.stem in self.ad_entries:
                continue

            if delete:
                print("Removing", webp_path)
                webp_path.unlink()
            else:
                print(webp_path.name, "is missing from", self.ad_json_file_path.name)

        print(f"{len(webp_paths)}/{len(self.ad_entries)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Entry Manager operations")
    subparser = parser.add_subparsers(dest="command", help="subcommand", required=True)

    check_parser = subparser.add_parser("check", help="Check for missing entries")
    check_parser.add_argument("-d", "--delete", action="store_true")

    args = parser.parse_args()

    here = Path(__file__).parent
    entry_manager = EntryManager(
        ad_images_dir=here / "public" / "300x250",
        cover_images_dir=here / "public" / "200x300",
        fiction_json_file_path=here / "public" / "fiction.json",
        debug_dir_path=here / "debug",
    )

    match args.command:
        case "check":
            entry_manager.check_for_missing_ad_entries(delete=args.delete)


if __name__ == "__main__":
    main()
