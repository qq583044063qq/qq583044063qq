# Install to qq583044063qq/qq583044063qq

1. Extract the ZIP, keeping the paths intact.
2. Copy `README.md`, `scripts/generate_profile_stats.py`, `.github/workflows/profile-stats.yml`, and all three `assets/stats/*.svg` files to the root of the profile repository. Do **not** delete `.github/workflows/wakatimeMain.yml`.
3. Commit and push the files to `main`.
4. Go to **Actions → Generate Profile Statistics → Run workflow** to generate the first real cards. The included SVG files are neutral placeholders until this first run.
5. In **Settings → Actions → General**, ensure Actions has permission to write repository contents. If the repo/org policy prohibits this, ask an admin to enable writes.

The workflow uses GitHub's automatic `GITHUB_TOKEN` — no additional PAT or new secret is needed. Its generated metrics include public repositories only; the contribution calendar uses GitHub GraphQL. If GraphQL access is unavailable, the card explicitly displays an unavailable value rather than fabricating a number.

The existing WakaTime section is preserved and will continue to be managed by the separate WakaTime workflow. The schedule is daily 03:15 Beijing time (UTC 19:15), staggered after WakaTime's 02:30 run.
