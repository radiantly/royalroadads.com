@echo off
call :LOG >> rra.log
exit /B

:LOG

git config user.name "Ad Bot"
git config user.email bot@royalroadads.com
git fetch origin
git switch gh-pages
git reset --hard origin/gh-pages
git rebase origin/main
python main.py
git add docs\300x250
git commit -m "Automated: Add ads"
git push --force-with-lease origin gh-pages
