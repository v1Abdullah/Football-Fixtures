import os
import json
import re
import requests

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# Configuration
# =========================

API_KEY = os.environ["FOOTBALL_API_KEY"]
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

BASE_URL = "https://v3.football.api-sports.io"
TIMEZONE = ZoneInfo("Asia/Riyadh")
TODAY = datetime.now(TIMEZONE).date()

STATE_FILE = Path("sent_fixtures.json")

# League IDs used by API-Football
LEAGUES = {
    307: {
        "name": "الدوري السعودي للمحترفين",
        "emoji": "🇸🇦",
        "teams": [
            "al hilal",
            "al nassr",
            "al ittihad",
            "al ahli",
            "al qadsiah",
        ],
    },
    39: {
        "name": "الدوري الإنجليزي الممتاز",
        "emoji": "🏴",
        "teams": None,  # All league matches
    },
    140: {
        "name": "الدوري الإسباني",
        "emoji": "🇪🇸",
        "teams": [
            "barcelona",
            "real madrid",
            "atletico madrid",
        ],
    },
    61: {
        "name": "الدوري الفرنسي",
        "emoji": "🇫🇷",
        "teams": ["lens"],
    },
}

SEASON = TODAY.year

# =========================
# Helpers
# =========================

def normalize_name(name):
    """Normalize team names to simplify matching."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    return " ".join(name.split())


def load_sent_fixtures():
    if not STATE_FILE.exists():
        return []

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_sent_fixtures(fixture_ids):
    STATE_FILE.write_text(
        json.dumps(sorted(set(fixture_ids)), indent=2),
        encoding="utf-8",
    )


def get_today_fixtures(league_id):
    url = f"{BASE_URL}/fixtures"

    params = {
        "league": league_id,
        "season": SEASON,
        "date": TODAY.isoformat(),
        "timezone": "Asia/Riyadh",
    }

    response = requests.get(
        url,
        headers={"x-apisports-key": API_KEY},
        params=params,
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    if data.get("errors"):
        raise RuntimeError(
            f"API error for league {league_id}: {data['errors']}"
        )

    return data.get("response", [])


def is_relevant_match(fixture, config):
    home = normalize_name(fixture["teams"]["home"]["name"])
    away = normalize_name(fixture["teams"]["away"]["name"])

    # Premier League: include every match
    if config["teams"] is None:
        return True

    for team in config["teams"]:
        target = normalize_name(team)

        if target in home or target in away:
            return True

    return False


def format_match(fixture):
    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]

    kickoff = datetime.fromisoformat(
        fixture["fixture"]["date"]
    ).astimezone(TIMEZONE)

    kickoff_time = kickoff.strftime("%I:%M %p")

    return (
        f"⚽ **{home} × {away}**\n"
        f"🕒 {kickoff_time} بتوقيت السعودية"
    )


def send_discord_message(message):
    response = requests.post(
        WEBHOOK_URL,
        json={
            "username": "مواعيد المباريات ⚽",
            "content": message,
            "allowed_mentions": {"parse": []},
        },
        timeout=30,
    )

    response.raise_for_status()


# =========================
# Main
# =========================

def main():
    print(f"Checking fixtures for {TODAY.isoformat()}")

    sent_ids = set(load_sent_fixtures())
    new_ids = set()
    sections = []

    for league_id, config in LEAGUES.items():
        print(f"Checking {config['name']}...")

        fixtures = get_today_fixtures(league_id)
        matches = []

        for fixture in fixtures:
            fixture_id = str(fixture["fixture"]["id"])

            # Only announce scheduled matches that have not started
            if fixture["fixture"]["status"]["short"] != "NS":
                continue

            if fixture_id in sent_ids:
                continue

            if not is_relevant_match(fixture, config):
                continue

            matches.append(fixture)
            new_ids.add(fixture_id)

        if matches:
            lines = [
                f"{config['emoji']} **{config['name']}**"
            ]

            for fixture in matches:
                lines.append(format_match(fixture))

            sections.append("\n".join(lines))

    if not sections:
        print("No new relevant matches found today.")
        return

    header = (
        f"⚽ **مباريات اليوم | {TODAY.strftime('%Y-%m-%d')}**\n"
        "🇸🇦 جميع الأوقات بتوقيت السعودية\n"
    )

    # Discord messages have a 2000-character content limit.
    messages = []
    current_message = header

    for section in sections:
        candidate = current_message + "\n" + section + "\n"

        if len(candidate) > 1900 and current_message != header:
            messages.append(current_message)
            current_message = header + "\n" + section + "\n"
        else:
            current_message = candidate

    if current_message.strip() != header.strip():
        messages.append(current_message)

    # Send announcements first. Save IDs only after successful delivery.
    for message in messages:
        send_discord_message(message)

    save_sent_fixtures(sent_ids | new_ids)

    print(f"Successfully announced {len(new_ids)} fixtures.")


if __name__ == "__main__":
    main()
