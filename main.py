import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ESPN's publicly accessible site API. It is not an officially supported API,
# so keep the provider URL isolated here in case it ever changes.
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
TIMEZONE = ZoneInfo("Asia/Riyadh")
TODAY = datetime.now(TIMEZONE).date()
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
STATE_FILE = Path("sent_fixtures.json")

# Saudi Pro League, Premier League, La Liga, Ligue 1, and continental cups.
# Team filters apply only to the Saudi, Spanish, French, and continental
# competitions. The entire Premier League matchday is announced.
COMPETITIONS = [
    {
        "slug": "ksa.1",
        "name": "الدوري السعودي للمحترفين",
        "emoji": "🇸🇦",
        "teams": {"al hilal", "al nassr", "al ittihad", "al ahli", "al qadsiah"},
    },
    {
        "slug": "eng.1",
        "name": "الدوري الإنجليزي الممتاز",
        "emoji": "🏴",
        "teams": None,
    },
    {
        "slug": "esp.1",
        "name": "الدوري الإسباني",
        "emoji": "🇪🇸",
        "teams": {"barcelona", "real madrid", "atletico madrid"},
    },
    {
        "slug": "fra.1",
        "name": "الدوري الفرنسي",
        "emoji": "🇫🇷",
        "teams": {"lens"},
    },
    {
        "slug": "afc.champions",
        "name": "دوري أبطال آسيا للنخبة",
        "emoji": "🌏",
        "teams": {
            "al hilal", "al nassr", "al ittihad", "al ahli", "al qadsiah",
        },
    },
    {
        "slug": "uefa.champions",
        "name": "دوري أبطال أوروبا",
        "emoji": "🏆",
        "teams": {
            "al hilal", "al nassr", "al ittihad", "al ahli", "al qadsiah",
            "barcelona", "real madrid", "atletico madrid", "lens",
        },
    },
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Football-Fixtures/1.0 (daily fixture notifier)"})


def normalize_name(name):
    """Normalize display names while preserving ASCII letters and digits."""
    name = (name or "").lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return " ".join(name.split())


def load_sent_fixtures():
    if not STATE_FILE.exists():
        return set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {str(fixture_id) for fixture_id in data}
    except (json.JSONDecodeError, OSError):
        print("Warning: sent_fixtures.json could not be read; starting with empty history.")
        return set()


def save_sent_fixtures(fixture_ids):
    temporary_file = STATE_FILE.with_suffix(".json.tmp")
    temporary_file.write_text(
        json.dumps(sorted(fixture_ids), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_file.replace(STATE_FILE)


def get_today_events(competition):
    url = f"{BASE_URL}/{competition['slug']}/scoreboard"
    response = SESSION.get(
        url,
        params={"dates": TODAY.strftime("%Y%m%d")},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    events = payload.get("events")
    if not isinstance(events, list):
        raise RuntimeError(
            f"Unexpected ESPN response for {competition['slug']}: missing events list"
        )
    return events


def get_event_details(event):
    event_id = str(event.get("id", ""))
    event_date = event.get("date")
    if not event_id or not event_date:
        return None

    try:
        kickoff = datetime.fromisoformat(event_date.replace("Z", "+00:00")).astimezone(TIMEZONE)
    except (TypeError, ValueError):
        return None

    competition = (event.get("competitions") or [{}])[0]
    competitors = competition.get("competitors") or []
    teams = {}
    for competitor in competitors:
        side = competitor.get("homeAway")
        team = competitor.get("team") or {}
        if side in ("home", "away"):
            teams[side] = team.get("displayName") or team.get("name") or "فريق غير معروف"

    if "home" not in teams or "away" not in teams:
        return None

    status = (event.get("status") or {}).get("type") or {}
    # Include upcoming/scheduled fixtures only, not games already in progress
    # or completed when the daily run starts.
    if status.get("state") not in ("pre", "tbd"):
        return None
    if kickoff.date() != TODAY or kickoff <= datetime.now(TIMEZONE):
        return None

    return {
        "id": event_id,
        "kickoff": kickoff,
        "home": teams["home"],
        "away": teams["away"],
    }


def is_relevant_match(match, competition):
    if competition["teams"] is None:
        return True
    participating_teams = {
        normalize_name(match["home"]),
        normalize_name(match["away"]),
    }
    return bool(participating_teams & competition["teams"])


def format_match(match):
    kickoff_time = match["kickoff"].strftime("%I:%M %p").lstrip("0")
    kickoff_time = kickoff_time.replace("AM", "صباحًا").replace("PM", "مساءً")
    return (
        f"⚽ **{match['home']} × {match['away']}**\n"
        f"🕒 {kickoff_time} بتوقيت السعودية"
    )


def send_discord_message(message):
    if not WEBHOOK_URL:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL secret in GitHub Actions settings.")
    response = SESSION.post(
        WEBHOOK_URL,
        json={
            "username": "مواعيد المباريات ⚽",
            "content": message,
            "allowed_mentions": {"parse": []},
        },
        timeout=30,
    )
    response.raise_for_status()


def split_discord_messages(header, sections, max_length=1850):
    messages = []
    current = header
    for section in sections:
        for line in section.splitlines():
            candidate = current + "\n" + line
            if len(candidate) > max_length and current != header:
                messages.append(current)
                current = header + "\n" + line
            else:
                current = candidate
    if current != header:
        messages.append(current)
    return messages


def main():
    print(f"Checking ESPN fixtures for Saudi date {TODAY.isoformat()}")
    sent_ids = load_sent_fixtures()
    announced_ids = set()
    messages = []

    for competition in COMPETITIONS:
        print(f"Checking {competition['name']} ({competition['slug']})...")
        try:
            events = get_today_events(competition)
        except (requests.RequestException, ValueError, RuntimeError) as error:
            # A provider outage must fail the run instead of silently marking
            # the day as processed. GitHub Actions will show this failure.
            raise RuntimeError(
                f"Could not retrieve {competition['name']} fixtures: {error}"
            ) from error

        lines = []
        for event in events:
            match = get_event_details(event)
            if not match or match["id"] in sent_ids:
                continue
            if not is_relevant_match(match, competition):
                continue
            lines.append(format_match(match))
            announced_ids.add(match["id"])

        if lines:
            header = (
                f"{competition['emoji']} **{competition['name']} | مباريات اليوم "
                f"{TODAY.strftime('%Y-%m-%d')}**\n"
                "🇸🇦 الأوقات بتوقيت السعودية"
            )
            # Keep each competition in its own Discord message. Blank lines
            # between fixtures make long match lists easier to scan.
            section = "\n\n".join(lines)
            messages.extend(split_discord_messages(header, [section]))

    if not messages:
        print("No new relevant upcoming fixtures found today.")
        return

    # Store match IDs only after every message has been delivered successfully.
    for message in messages:
        send_discord_message(message)
    save_sent_fixtures(sent_ids | announced_ids)
    print(f"Successfully announced {len(announced_ids)} fixtures.")


if __name__ == "__main__":
    main()
