
import json
import os
import sys
import urllib.request
import urllib.error

from datetime import date, datetime, timedelta, timezone
from html import escape

# =====================================
# CONFIGURATION
# =====================================

USER = os.environ.get("GH_USER", "md-khadimul-islam")
TOKEN = os.environ["GH_TOKEN"]

OUTPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "assets"

API_URL = "https://api.github.com/graphql"


# =====================================
# FETCH GITHUB CONTRIBUTIONS
# =====================================

def fetch_contributions():

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=29)

    query = """
    query(
        $login: String!,
        $from: DateTime!,
        $to: DateTime!
    ) {
        user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
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

    variables = {
        "login": USER,
        "from": f"{start_date}T00:00:00Z",
        "to": f"{today}T23:59:59Z"
    }

    payload = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-Activity-Generator"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read())

    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"GitHub API error {error.code}: "
            f"{error.read().decode('utf-8', errors='replace')}"
        ) from error

    if result.get("errors"):
        raise RuntimeError(result["errors"])

    user = result["data"]["user"]

    if user is None:
        raise RuntimeError(f"GitHub user not found: {USER}")

    contribution_days = {}

    for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            contribution_days[day["date"]] = day["contributionCount"]

    # Always generate exactly 30 calendar days.
    days = []

    for index in range(30):
        current = start_date + timedelta(days=index)

        days.append({
            "date": current.isoformat(),
            "contributionCount": contribution_days.get(
                current.isoformat(), 0
            )
        })

    return days


# =====================================
# GENERATE SVG
# =====================================

def generate_svg(days, bg, fg, sub, empty, fill, accent):

    WIDTH = 495
    HEIGHT = 170

    CELL = 11
    GAP = 3

    x0 = (WIDTH - (30 * (CELL + GAP) - GAP)) / 2

    maximum = max(
        [day["contributionCount"] for day in days] + [1]
    )

    active = sum(
        1 for day in days
        if day["contributionCount"] > 0
    )

    total = sum(
        day["contributionCount"] for day in days
    )

    rects = []

    for index, day in enumerate(days):

        count = day["contributionCount"]

        opacity = (
            0 if count == 0
            else 0.35 + 0.65 * (count / maximum)
        )

        color = empty if count == 0 else fill

        x = x0 + index * (CELL + GAP)

        rects.append(
            f"""
            <rect
                x="{x:.1f}"
                y="118"
                width="{CELL}"
                height="{CELL}"
                rx="2"
                fill="{color}"
                fill-opacity="{opacity:.2f}"
            >
                <title>
                    {escape(day["date"])}: {count} contributions
                </title>
            </rect>
            """
        )

    start_date = days[0]["date"]
    end_date = days[-1]["date"]

    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="{WIDTH}"
        height="{HEIGHT}"
        viewBox="0 0 {WIDTH} {HEIGHT}"
    >

        <rect
            width="{WIDTH}"
            height="{HEIGHT}"
            rx="6"
            fill="{bg}"
        />

        <g
            font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif"
            text-anchor="middle"
        >

            <text
                x="{WIDTH / 2}"
                y="58"
                font-size="34"
                font-weight="700"
                fill="{accent}"
            >
                {active}
                <tspan
                    font-size="18"
                    fill="{sub}"
                    font-weight="400"
                >
                    / 30 days
                </tspan>
            </text>

            <text
                x="{WIDTH / 2}"
                y="86"
                font-size="14"
                fill="{fg}"
            >
                Days I coded in the last 30 days
            </text>

            <text
                x="{WIDTH / 2}"
                y="106"
                font-size="11"
                fill="{sub}"
            >
                {total} contributions · {start_date} to {end_date}
            </text>

        </g>

        {''.join(rects)}

    </svg>
    """


# =====================================
# SAVE SVG FILES
# =====================================

def main():

    print(f"Fetching GitHub activity for {USER}...")

    days = fetch_contributions()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    dark_svg = generate_svg(
        days,
        "#0D1117",
        "#e6edf3",
        "#7d8590",
        "#21262d",
        "#39d353",
        "#58a6ff"
    )

    light_svg = generate_svg(
        days,
        "#ffffff",
        "#1f2328",
        "#59636e",
        "#ebedf0",
        "#2da44e",
        "#0969da"
    )

    with open(
        f"{OUTPUT_DIR}/activity.svg",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(dark_svg)

    with open(
        f"{OUTPUT_DIR}/activity-light.svg",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(light_svg)

    active = sum(
        1 for day in days
        if day["contributionCount"] > 0
    )

    total = sum(
        day["contributionCount"] for day in days
    )

    print("--------------------------------")
    print(f"GitHub user: {USER}")
    print(f"Active days: {active}/30")
    print(f"Contributions: {total}")
    print("SVG files generated successfully!")
    print("--------------------------------")


if __name__ == "__main__":
    main()
