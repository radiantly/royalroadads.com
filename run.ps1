function Run-Stuff {
  git config user.name "Ad Bot"
  git config user.email bot@royalroadads.com
  git fetch origin
  git switch gh-pages
  git reset --hard origin/gh-pages
  git rebase origin/main
  python main.py
  git add docs\300x250 docs\200x300 docs\fiction.json
  git commit -m "Automated: Add ads"
  git push --force-with-lease origin gh-pages
} 


Run-Stuff *>&1 | Tee-Object -FilePath rra.log -Append
