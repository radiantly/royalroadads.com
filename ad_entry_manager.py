import json
from dataclasses import dataclass
from pathlib import Path

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


class AdEntryManager:
    rms_threshold = 10

    def __init__(self, images_dir_path: Path, debug_dir_path: Path):
        self.json_file_path = images_dir_path / "entries.json"
        self.images_dir_path = images_dir_path
        self.debug_dir_path = debug_dir_path

        self.images_dir_path.mkdir(exist_ok=True, parents=True)

        self.entries: list[AdEntry] = []

        # load content
        self.content = (
            json.loads(self.json_file_path.read_text(encoding="utf-8"))
            if self.json_file_path.exists()
            else {}
        )
        for uid, entry_dict in self.content.get("entries", {}).items():
            image = Image.open(self.images_dir_path / f"{uid}.webp")
            entry = AdEntry(
                uid=uid,
                alt=entry_dict["alt"],
                link=entry_dict["link"],
                timestamp=entry_dict["timestamp"],
                image=image,
            )
            self.entries.append(entry)

    def save_entry(self, new_entry: AdEntry):
        # check if an existing matches this entry
        for entry in self.entries:
            if entry.calculate_rms(new_entry.image) < self.rms_threshold:
                print("Removing older entry", entry)
                (self.images_dir_path / entry.file_name).rename(
                    self.debug_dir_path / entry.file_name
                )
                self.entries.remove(entry)

        new_entry.image.save(self.images_dir_path / new_entry.file_name, "webp")
        self.entries.insert(0, new_entry)

        with open(self.json_file_path, "w") as fp:
            content = {
                "entries": {
                    entry.uid: {
                        "alt": entry.alt,
                        "link": entry.link,
                        "timestamp": entry.timestamp,
                    }
                    for entry in self.entries
                }
            }

            json.dump(obj=content, fp=fp)
