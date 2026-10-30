
import json
import os
import urllib.request
import urllib.error

from datetime import date, datetime, timedelta, timezone
from html import escape


# ==========================================
# CONFIGURATION
# ==========================================

USERNAME = "md-khadimul-islam"
TOKEN = os.environ["GITHUB_TOKEN"]

OUTPUT = "assets/activity.svg"
API_URL = "https://api.github.com/graphql"


# ==========================================
# GITHUB GRAPHQL QUERIES
# ==========================================

USER_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
  }
}
"""

CONTRIBUTION_QUERY = """
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


# ==========================================
# GITHUB API REQUEST
# ==========================================

def github_graphql(query, variables):

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
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API HTTP {error.code}: {details}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not connect to GitHub API: {error}"
        ) from error

    if "errors" in result:
        raise RuntimeError(
            f"GitHub GraphQL error: {result['errors']}"
        )

    return result["data"]


# ==========================================
# FETCH CONTRIBUTION HISTORY
# ==========================================

def fetch_contributions():

    print("Fetching GitHub profile...")

    user = github_graphql(
        USER_QUERY,
        {"login": USERNAME}
    )["user"]

    if user is None:
        raise RuntimeError(
            f"GitHub user not found: {USERNAME}"
        )

    created_at = datetime.fromisoformat(
        user["createdAt"].replace("Z", "+00:00")
    )

    created_date = created_at.date()
    today = datetime.now(timezone.utc).date()

    all_days = {}
    lifetime_total = 0

    print("Fetching contribution history...")

    for year in range(created_date.year, today.year + 1):

        start = datetime(
            year, 1, 1,
            tzinfo=timezone.utc
        )

        end = datetime(
            year, 12, 31, 23, 59, 59,
            tzinfo=timezone.utc
        )

        if year == today.year:
            end = datetime.now(timezone.utc)

        result = github_graphql(
            CONTRIBUTION_QUERY,
            {
                "login": USERNAME,
                "from": start.isoformat(),
                "to": end.isoformat()
            }
        )["user"]["contributionsCollection"]

        lifetime_total += result["totalContributions"]

        for week in result["contributionCalendar"]["weeks"]:

            for item in week["contributionDays"]:

                day = date.fromisoformat(item["date"])

                all_days[day] = item["contributionCount"]

        print(f"Fetched contributions for {year}")

    return all_days, lifetime_total, today, created_date


# ==========================================
# CALCULATE STREAKS
# ==========================================

def calculate_streaks(all_days, today, created_date):

    longest_streak = 0
    running_streak = 0

    # Calculate longest streak
    current_date = created_date

    while current_date <= today:

        contributions = all_days.get(current_date, 0)

        if contributions > 0:

            running_streak += 1

            longest_streak = max(
                longest_streak,
                running_streak
            )

        else:

            running_streak = 0

        current_date += timedelta(days=1)

    # Calculate current streak
    current_streak = 0

    anchor = today

    # If no contributions today, check yesterday
    if all_days.get(today, 0) == 0:
        anchor = today - timedelta(days=1)

    current_date = anchor

    while current_date >= created_date:

        if all_days.get(current_date, 0) > 0:

            current_streak += 1

        else:

            break

        current_date -= timedelta(days=1)

    return current_streak, longest_streak


# ==========================================
# GENERATE ACTIVITY SVG
# ==========================================

def generate_svg(
    all_days,
    lifetime_total,
    today,
    created_date
):

    start_date = today - timedelta(days=29)

    last_30_days = [
        start_date + timedelta(days=index)
        for index in range(30)
    ]

    # Days with contributions
    active_days = sum(
        1
        for day in last_30_days
        if all_days.get(day, 0) > 0
    )

    # Calculate streaks
    current_streak, longest_streak = calculate_streaks(
        all_days,
        today,
        created_date
    )

    max_contributions = max(
        [
            all_days.get(day, 0)
            for day in last_30_days
        ] + [1]
    )

    # Generate contribution squares
    squares = []

    for index, day in enumerate(last_30_days):

        count = all_days.get(day, 0)

        if count == 0:
            color = "#21262d"

        elif count <= max_contributions * 0.25:
            color = "#0e4429"

        elif count <= max_contributions * 0.50:
            color = "#006d32"

        elif count <= max_contributions * 0.75:
            color = "#26a641"

        else:
            color = "#39d353"

        x = 240 + (index * 14)

        squares.append(
            f"""
            <rect
                x="{x}"
                y="116"
                width="11"
                height="11"
                rx="2"
                fill="{color}"
            >
                <title>
                    {escape(str(day))}: {count} contributions
                </title>
            </rect>
            """
        )

    squares_svg = "\n".join(squares)

    # Date range
    date_range = (
        f"{start_date.isoformat()} to {today.isoformat()}"
    )

    # ======================================
    # SVG TEMPLATE
    # ======================================

    svg = f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="900"
        height="300"
        viewBox="0 0 900 300"
    >

        <rect
            width="900"
            height="300"
            rx="8"
            fill="#0d1117"
        />

        <!-- Header -->

        <text
            x="28"
            y="35"
            fill="#f0f6fc"
            font-size="15"
            font-weight="bold"
        >
            My GitHub Activity
        </text>

        <!-- Active days -->

        <text
            x="450"
            y="76"
            text-anchor="middle"
            fill="#58a6ff"
            font-size="34"
            font-weight="bold"
        >
            {active_days}
        </text>

        <text
            x="480"
            y="76"
            fill="#8b949e"
            font-size="17"
        >
            / 30 days
        </text>

        <text
            x="450"
            y="99"
            text-anchor="middle"
            fill="#f0f6fc"
            font-size="13"
        >
            Days with GitHub contributions in the last 30 days
        </text>

        <text
            x="450"
            y="110"
            text-anchor="middle"
            fill="#8b949e"
            font-size="9"
        >
            {date_range}
        </text>

        <!-- Contribution calendar -->

        {squares_svg}

        <!-- Divider -->

        <line
            x1="28"
            y1="158"
            x2="872"
            y2="158"
            stroke="#30363d"
        />

        <!-- Statistics dividers -->

        <line
            x1="300"
            y1="180"
            x2="300"
            y2="260"
            stroke="#484f58"
        />

        <line
            x1="600"
            y1="180"
            x2="600"
            y2="260"
            stroke="#484f58"
        />

        <!-- Total contributions -->

        <text
            x="165"
            y="215"
            text-anchor="middle"
            fill="#58a6ff"
            font-size="29"
            font-weight="bold"
        >
            {lifetime_total:,}
        </text>

        <text
            x="165"
            y="240"
            text-anchor="middle"
            fill="#f0f6fc"
            font-size="13"
        >
            Total Contributions
        </text>

        <!-- Current streak -->

        <text
            x="450"
            y="215"
            text-anchor="middle"
            fill="#58a6ff"
            font-size="29"
            font-weight="bold"
        >
            {current_streak}
        </text>

        <text
            x="450"
            y="240"
            text-anchor="middle"
            fill="#f0f6fc"
            font-size="13"
        >
            Current Streak
        </text>

        <!-- Longest streak -->

        <text
            x="735"
            y="215"
            text-anchor="middle"
            fill="#58a6ff"
            font-size="29"
            font-weight="bold"
        >
            {longest_streak}
        </text>

        <text
            x="735"
            y="240"
            text-anchor="middle"
            fill="#f0f6fc"
            font-size="13"
        >
            Longest Streak
        </text>

        <!-- Footer -->

        <text
            x="450"
            y="285"
            text-anchor="middle"
            fill="#8b949e"
            font-size="10"
        >
            Updated automatically using GitHub contribution data
        </text>

    </svg>
    """

    # Save SVG
    os.makedirs("assets", exist_ok=True)

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(svg.strip())

    print(f"SVG generated successfully: {OUTPUT}")

    print(f"Active days: {active_days}/30")
    print(f"Total contributions: {lifetime_total}")
    print(f"Current streak: {current_streak}")
    print(f"Longest streak: {longest_streak}")


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    print("Starting GitHub activity generator...")

    all_days, total, today, created = fetch_contributions()

    generate_svg(
        all_days,
        total,
        today,
        created
    )

    print("GitHub activity update completed!")
