import os
import shlex
import shutil
import subprocess
from pathlib import Path

commands = [
    "git fetch origin",
    "git switch main",
    "git reset --hard origin/main",
    "uv run main.py",
    "uv run archive.py create",
    "wrangler pages deploy",
]


def main():
    here = Path(__file__).parent
    with open(here / "rra.log", "a") as f:
        for command in commands:
            args = shlex.split(command, posix=os.name == "posix")
            args[0] = shutil.which(args[0])
            print(args)
            subprocess.run(args, stdout=f, stderr=f, check=True, text=True, cwd=here)


if __name__ == "__main__":
    main()
