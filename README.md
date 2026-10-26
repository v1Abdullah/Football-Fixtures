# Football Fixtures Discord Notifier

Fetches same-day football fixtures from ESPN's publicly accessible soccer endpoints and posts upcoming matches to a Discord channel using a webhook.

## Competitions tracked


- Saudi Pro League: Al Hilal, Al Nassr, Al Ittihad, Al Ahli, and Al Qadsiah.
- English Premier League: all matches.
- La Liga: Barcelona, Real Madrid, and Atlético Madrid.
- Ligue 1: Lens.
- AFC Champions League Elite and UEFA Champions League: matches involving the Saudi, Spanish, and French clubs listed above, when those clubs participate.

Kickoff times are converted to `Asia/Riyadh` and displayed in 12-hour format with Arabic AM/PM labels. Each competition is sent in its own Discord message, with a blank line between fixtures. The workflow runs daily at 08:17 Saudi time (05:17 UTC) and can also be started manually from the Actions tab. For a one-time webhook check, manually run the workflow with **Send a one-time Discord connection test message** enabled. A fixture ID history in `sent_fixtures.json` prevents repeat announcements across runs.

## GitHub setup

1. In the repository, open **Settings → Secrets and variables → Actions**.
2. Add these repository secrets, each with the webhook URL for its competition: `DISCORD_WEBHOOK_SAUDI`, `DISCORD_WEBHOOK_EPL`, `DISCORD_WEBHOOK_LALIGA`, `DISCORD_WEBHOOK_LIGUE1`, `DISCORD_WEBHOOK_ASIAN_CL`, and `DISCORD_WEBHOOK_UCL`.
3. Ensure GitHub Actions is enabled. To verify all webhook destinations, run **Daily Football Fixtures** manually and enable **Send a one-time Discord connection test message**; this sends one test message to each of the six webhooks.

No API-Football account or API key is required. Do not add the webhook URL to source code or commit it.

## Important data-source note

The ESPN soccer endpoints used by this project are publicly accessible but are not an officially supported public API with a published service-level guarantee. ESPN may change the endpoints or response format without notice. GitHub Actions scheduled runs can also start later than the exact scheduled minute. Check the Actions run log if an announcement is missing.
