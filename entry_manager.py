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

    def _load_ad_entries(self) -> list[AdEntry]:
        entries: list[AdEntry] = []

        content = self._load_json_file(self.ad_json_file_path)

        for uid, entry_dict in content.get("entries", {}).items():
            image = Image.open(self.ad_images_dir / f"{uid}.webp")
            entry = AdEntry(
                uid=uid,
                alt=entry_dict["alt"],
                link=entry_dict["link"],
                timestamp=entry_dict["timestamp"],
                image=image,
            )
            entries.append(entry)

        return entries

    def _load_fiction_entries(self) -> dict[int, FictionEntry]:
        entries: dict[int, FictionEntry] = {}

        content = self._load_json_file(self.fiction_json_file_path)

        for fiction_id_str, entry_dict in content.get("entries", {}).items():
            fiction_id = int(fiction_id_str)
            image = Image.open(self.cover_images_dir / f"{fiction_id}.webp")
            entries[fiction_id] = FictionEntry(
                **entry_dict, id=fiction_id, cover_image=image
            )

        return entries

    def save_ad_entry(self, temp_entry: AdEntry) -> None:
        assert temp_entry.image.size == (300, 250)
        image_path = self.ad_images_dir / temp_entry.file_name
        temp_entry.image.save(image_path, "webp")
        new_entry = replace(temp_entry, image=Image.open(image_path))

        # check if an existing matches this entry
        for entry in self.ad_entries:
            if entry.calculate_rms(new_entry.image) < self.rms_threshold:
                print("Removing older entry", entry)
                (self.ad_images_dir / entry.file_name).rename(
                    self.debug_dir_path / entry.file_name
                )
                self.ad_entries.remove(entry)

        self.ad_entries.insert(0, new_entry)
        self._write_ad_entries_to_file()

    def save_fiction_entry(self, entry: FictionEntry) -> None:
        if entry.cover_image.size != (200, 300):
            entry = replace(entry, cover_image=entry.cover_image.resize((200, 300)))

        image_path = self.cover_images_dir / entry.cover_image_file_name
        entry.cover_image.save(image_path, "webp")
        entry = replace(entry, cover_image=Image.open(image_path))

        self.fiction[entry.id] = entry
        self._write_fiction_entries_to_file()

    def _write_fiction_entries_to_file(self) -> None:
        with open(self.fiction_json_file_path, "w") as fp:
            content = {
                "entries": {entry.id: entry.dict() for entry in self.fiction.values()}
            }

            json.dump(obj=content, fp=fp, indent=2)

    def _write_ad_entries_to_file(self) -> None:
        with open(self.ad_json_file_path, "w") as fp:
            content = {
                "entries": {
                    entry.uid: {
                        "alt": entry.alt,
                        "link": entry.link,
                        "timestamp": entry.timestamp,
                    }
                    for entry in self.ad_entries
                }
            }

            json.dump(obj=content, fp=fp, indent=2)
