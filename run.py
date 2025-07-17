import shlex
import shutil
import subprocess
from pathlib import Path

commands = [
    'git config user.name "Ad Bot"',
    "git config user.email bot@royalroadads.com",
    "git fetch origin",
    "git switch gh-pages",
    "git reset --hard origin/gh-pages",
    "git rebase origin/main",
    "uv run main.py",
    "git add docs\\300x250 docs\\200x300 docs\\fiction.json",
    'git commit -m "Automated: Add ads"',
    "git push --force-with-lease origin gh-pages",
]


def main():
    here = Path(__file__).parent
    with open(here / "rra.log", "a") as f:
        for command in commands:
            args = shlex.split(command)
            args[0] = shutil.which(args[0])
            print(args)
            subprocess.run(args, stdout=f, stderr=f, check=True, text=True, cwd=here)


if __name__ == "__main__":
    main()
