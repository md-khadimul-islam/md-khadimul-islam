
import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape

USERNAME = "md-khadimul-islam"
TOKEN = os.environ["GITHUB_TOKEN"]
OUTPUT = "assets/activity.svg"

GRAPHQL_URL = "https://api.github.com/graphql"

def github_graphql(query, variables):
    payload = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-Activity-Generator"
        }
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read())

    if "errors" in result:
        raise RuntimeError(result["errors"])

    return result["data"]


USER_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    contributionYears
  }
}
"""

YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalContributions
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

def fetch_contributions():
    user_data = github_graphql(
        USER_QUERY,
        {"login": USERNAME}
    )["user"]

    created_at = datetime.fromisoformat(
        user_data["createdAt"].replace("Z", "+00:00")
    )

    today = datetime.now(timezone.utc).date()
    first_year = created_at.year

    all_days = {}
    lifetime_total = 0

    for year in range(first_year, today.year + 1):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)

        if year == today.year:
            end = datetime.now(timezone.utc)
        else:
            end = datetime(
                year, 12, 31, 23, 59, 59,
                tzinfo=timezone.utc
            )

        result = github_graphql(
            YEAR_QUERY,
            {
                "login": USERNAME,
                "from": start.isoformat(),
                "to": end.isoformat()
            }
        )["user"]["contributionsCollection"]

        lifetime_total += result["totalContributions"]

        for week in result["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                all_days[date.fromisoformat(day["date"])] = (
                    day["contributionCount"]
                )

    return all_days, lifetime_total, today, created_at.date()


def calculate_streaks(all_days, today, created_date):
    longest = 0
    current = 0
    streak = 0

    day = created_date

    while day <= today:
        count = all_days.get(day, 0)

        if count > 0:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 0

        day += timedelta(days=1)

    if all_days.get(today, 0) > 0:
        current = streak
    elif all_days.get(today - timedelta(days=1), 0) > 0:
        current = streak
    else:
        current = 0

    return current, longest


def generate_svg(all_days, lifetime_total, today, created_date):
    start_date = today - timedelta(days=29)

    last_30 = [
        (start_date + timedelta(days=i))
        for i in range(30)
    ]

    active_days = sum(
        1 for day in last_30
        if all_days.get(day, 0) > 0
    )

    current_streak, longest_streak = calculate_streaks(
        all_days, today, created_date
    )

    max_count = max(
        [all_days.get(day, 0) for day in last_30] + [1]
    )

    squares = []

    for index, day in enumerate(last_30):
        count = all_days.get(day, 0)

        if count == 0:
            fill = "#21262d"
        elif count <= max_count * 0.25:
            fill = "#0e4429"
        elif count <= max_count * 0.50:
            fill = "#006d32"
        elif count <= max_count * 0.75:
            fill = "#26a641"
        else:
            fill = "#39d353"

        x = 248 + index * 14

        squares.append(
            f'<rect x="{x}" y="104" width="11" height="11" '
            f'rx="2" fill="{fill}">'
            f'<title>{escape(str(day))}: {count} contributions</title>'
            f'</rect>'
        )

    squares_svg = "\n".join(squares)

    date_range = (
        f"{start_date.isoformat()} to {today.isoformat()}"
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
    width="900" height="310" viewBox="0 0 900 310">
    <rect width="900" height="310" rx="8" fill="#0d1117"/>

    <text x="28" y="38" fill="#f0f6fc"
        font-size="15" font-weight="bold">
        My GitHub Activity
    </text>

    <text x="450" y="76" text-anchor="middle"
        fill="#58a6ff" font-size="34" font-weight="bold">
        {active_days}
    </text>

    <text x="480" y="76" fill="#8b949e" font-size="17">
        / 30 days
    </text>

    <text x="450" y="94" text-anchor="middle"
        fill="#f0f6fc" font-size="13">
        Days with GitHub contributions in the last 30 days
    </text>

    <text x="450" y="130" text-anchor="middle"
        fill="#8b949e" font-size="10">
        {date_range}
    </text>

    {squares_svg}

    <line x1="28" y1="158" x2="872" y2="158"
        stroke="#30363d"/>

    <line x1="300" y1="180" x2="300" y2="275"
        stroke="#484f58"/>

    <line x1="600" y1="180" x2="600" y2="275"
        stroke="#484f58"/>

    <text x="165" y="220" text-anchor="middle"
        fill="#58a6ff" font-size="30" font-weight="bold">
        {lifetime_total:,}
    </text>

    <text x="165" y="245" text-anchor="middle"
        fill="#f0f6fc" font-size="13">
        Total Contributions
    </text>

    <text x="450" y="220" text-anchor="middle"
        fill="#58a6ff" font-size="30" font-weight="bold">
        {current_streak}
    </text>

    <text x="450" y="245" text-anchor="middle"
        fill="#f0f6fc" font-size="13">
        Current Streak
    </text>

    <text x="735" y="220" text-anchor="middle"
        fill="#58a6ff" font-size="30" font-weight="bold">
        {longest_streak}
    </text>

    <text x="735" y="245" text-anchor="middle"
        fill="#f0f6fc" font-size="13">
        Longest Streak
    </text>

    <text x="450" y="292" text-anchor="middle"
        fill="#8b949e" font-size="10">
        Updated automatically using GitHub contribution data
    </text>
    </svg>
    """

    os.makedirs("assets", exist_ok=True)

    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(svg)


if __name__ == "__main__":
    contributions, total, today, created = fetch_contributions()

    generate_svg(
        contributions,
        total,
        today,
        created
    )

    print("GitHub activity SVG generated successfully.")
