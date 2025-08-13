import os
import random
import shlex
import shutil
import subprocess
from datetime import UTC, datetime
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
        f.write(f"Run started at {datetime.now(UTC)}\n")
        f.flush()
        for command in commands:

            # Currently the site is deployed to CF Pages, where the free plan
            # only allows for 500 builds a month. Assuming this script is run
            # every hour, we would easily surpass this so instead only deploy
            # 20% of the time
            if "deploy" in command and random.random() > 0.2:
                break

            args = shlex.split(command, posix=os.name == "posix")
            args[0] = shutil.which(args[0])
            print(args)
            subprocess.run(args, stdout=f, stderr=f, check=True, text=True, cwd=here)


if __name__ == "__main__":
    main()
