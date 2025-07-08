@echo off
call :LOG >> rra.log
exit /B

:LOG

git config user.name "Ad Bot"
git config user.email bot@royalroadads.com
git fetch origin
git reset --hard origin/main
python main.py
git add public\300x250
git commit -m "Automated: Add ads"
git push origin main
