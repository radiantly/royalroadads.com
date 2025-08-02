import argparse
import io
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

here = Path(__file__).parent
in_path = here / "public"
out_path = here / "public" / "archive"
chunk_size = 1024 * 1024 * 20  # 20MiB (CloudFlare Pages file size limit)


def create():
    # delete if already exists
    if out_path.exists():
        shutil.rmtree(out_path)

    out_path.mkdir()

    with tempfile.TemporaryDirectory() as temp_dir:
        archive_path = Path(
            shutil.make_archive(Path(temp_dir) / "archive", "zip", in_path)
        )

        archive_bytes = archive_path.read_bytes()
        for file_index, byte_index in enumerate(
            range(0, len(archive_bytes), chunk_size)
        ):
            (out_path / f"archive_{file_index}").write_bytes(
                archive_bytes[byte_index : byte_index + chunk_size]
            )


def download_archive() -> bytearray | None:
    BASE_URL = "https://royalroadads.com"

    archive_bytes = bytearray()

    index = 0
    while True:
        response = requests.get(f"{BASE_URL}/archive/archive_{index}")

        if response.status_code != 200:
            print("Failed to get", response.url)
            return None

        print(f"Retrieved {len(response.content)} bytes from {response.url}")
        archive_bytes += response.content

        if len(response.content) != chunk_size:
            return archive_bytes

        index += 1


def populate():
    if not (archive_bytes := download_archive()):
        return

    archive_buffer = io.BytesIO(archive_bytes)

    extract_count = 0

    with zipfile.ZipFile(archive_buffer) as zf:
        for member in zf.infolist():
            if member.filename.endswith(".webp") or member.filename.endswith(".json"):
                zf.extract(member, path=in_path)
                extract_count += 1

    print(f"Populated {extract_count} files")


def main():
    parser = argparse.ArgumentParser(description="Archive operations")
    subparser = parser.add_subparsers(dest="command", help="subcommand", required=True)

    subparser.add_parser("create", help="Create archive")
    subparser.add_parser("populate", help="Populate from archive")

    args = parser.parse_args()

    match args.command:
        case "create":
            create()
        case "populate":
            populate()


if __name__ == "__main__":
    main()
