# Football Fixtures Discord Notifier

Fetches same-day football fixtures from ESPN's publicly accessible soccer endpoints and posts upcoming matches to a Discord channel using a webhook.

## Competitions tracked

- Saudi Pro League: Al Hilal, Al Nassr, Al Ittihad, Al Ahli, and Al Qadsiah.
- English Premier League: all matches.
- La Liga: Barcelona, Real Madrid, and Atlético Madrid.
- Ligue 1: Lens.
- AFC Champions League Elite and UEFA Champions League: matches involving the Saudi, Spanish, and French clubs listed above, when those clubs participate.

Kickoff times are converted to `Asia/Riyadh` and displayed in 12-hour format with Arabic AM/PM labels. Each competition is sent in its own Discord message, with a blank line between fixtures. The workflow runs daily at 06:00 Saudi time (03:00 UTC) and can also be started manually from the Actions tab. A fixture ID history in `sent_fixtures.json` prevents repeat announcements across runs.

## GitHub setup

1. In the repository, open **Settings → Secrets and variables → Actions**.
2. Add a repository secret named `DISCORD_WEBHOOK_URL` with the Discord channel webhook URL.
3. Ensure GitHub Actions is enabled, then run **Daily Football Fixtures** manually once to verify setup.

No API-Football account or API key is required. Do not add the webhook URL to source code or commit it.

## Important data-source note

The ESPN soccer endpoints used by this project are publicly accessible but are not an officially supported public API with a published service-level guarantee. ESPN may change the endpoints or response format without notice. GitHub Actions scheduled runs can also start later than the exact scheduled minute. Check the Actions run log if an announcement is missing.
