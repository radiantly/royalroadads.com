import argparse
import shutil
import tempfile
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser(description="Archive operations")
    subparser = parser.add_subparsers(dest="command", help="subcommand", required=True)

    subparser.add_parser("create", help="Create archive")

    args = parser.parse_args()

    match args.command:
        case "create":
            create()


if __name__ == "__main__":
    main()
