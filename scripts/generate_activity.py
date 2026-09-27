import datetime as dt
import html
import json
import os
import urllib.request


USERNAME = "anupam99jain"

GRAPHQL_URL = "https://api.github.com/graphql"

OUTPUT_FILE = "assets/activity.svg"


QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          firstDay
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


def github_query(token: str, variables: dict) -> dict:
    payload = json.dumps({
        "query": QUERY,
        "variables": variables,
    }).encode("utf-8")

    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "anupam99jain-profile-generator",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise RuntimeError(json.dumps(result["errors"], indent=2))

    return result["data"]


def contribution_level(count: int, maximum: int) -> int:
    if count == 0:
        return 0

    if maximum <= 0:
        return 1

    ratio = count / maximum

    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    if ratio <= 0.75:
        return 3

    return 4


def generate_svg(calendar: dict) -> str:
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    all_days = []

    for week in weeks:
        for day in week["contributionDays"]:
            all_days.append(day)

    maximum = max(
        (day["contributionCount"] for day in all_days),
        default=0,
    )

    width = 1100
    height = 285

    cell_size = 13
    gap = 4

    grid_x = 72
    grid_y = 92

    colors = [
        "#161B22",
        "#0E4429",
        "#006D32",
        "#26A641",
        "#39D353",
    ]

    svg = []

    svg.append(
        f'''<svg
        width="{width}"
        height="{height}"
        viewBox="0 0 {width} {height}"
        fill="none"
        xmlns="http://www.w3.org/2000/svg">'''
    )

    svg.append("""
        <defs>

            <linearGradient
                id="activityBg"
                x1="0"
                y1="0"
                x2="1100"
                y2="285"
                gradientUnits="userSpaceOnUse">
                <stop stop-color="#050816"/>
                <stop offset="0.55" stop-color="#0B1120"/>
                <stop offset="1" stop-color="#050816"/>
            </linearGradient>

            <linearGradient
                id="activityAccent"
                x1="80"
                y1="0"
                x2="1000"
                y2="0">
                <stop stop-color="#00F5A0"/>
                <stop offset="0.5" stop-color="#00D9F5"/>
                <stop offset="1" stop-color="#8B5CF6"/>
            </linearGradient>

            <filter
                id="activityGlow"
                x="-50%"
                y="-50%"
                width="200%"
                height="200%">
                <feGaussianBlur stdDeviation="12"/>
            </filter>

        </defs>
    """)

    # Background
    svg.append(
        f'<rect width="{width}" height="{height}" rx="24" fill="url(#activityBg)"/>'
    )

    # Ambient glow
    svg.append(
        '<circle cx="960" cy="60" r="100" '
        'fill="#8B5CF6" opacity="0.08" filter="url(#activityGlow)"/>'
    )

    svg.append(
        '<circle cx="120" cy="250" r="90" '
        'fill="#00F5A0" opacity="0.06" filter="url(#activityGlow)"/>'
    )

    # Heading
    svg.append(
        '<text x="40" y="42" '
        'font-family="Arial, Helvetica, sans-serif" '
        'font-size="22" font-weight="700" fill="#FFFFFF">'
        'GITHUB ACTIVITY'
        '</text>'
    )

    # Total
    svg.append(
        f'<text x="40" y="68" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="15" fill="#8B949E">'
        f'{total:,} contributions in the last year'
        f'</text>'
    )

    # Accent line
    svg.append(
        '<rect x="40" y="78" width="180" height="3" rx="2" '
        'fill="url(#activityAccent)"/>'
    )

    # Month labels
    month_positions = {}

    for week_index, week in enumerate(weeks):
        first_day = dt.date.fromisoformat(week["firstDay"])
        label = first_day.strftime("%b")

        if first_day.day <= 7:
            month_positions[week_index] = label

    for week_index, label in month_positions.items():
        x = grid_x + week_index * (cell_size + gap)

        svg.append(
            f'<text x="{x}" y="{grid_y - 15}" '
            f'font-family="Arial, Helvetica, sans-serif" '
            f'font-size="11" fill="#8B949E">'
            f'{html.escape(label)}'
            f'</text>'
        )

    # Weekday labels
    weekday_labels = [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri"),
    ]

    for row, label in weekday_labels:
        y = grid_y + row * (cell_size + gap) + 10

        svg.append(
            f'<text x="25" y="{y}" '
            f'font-family="Arial, Helvetica, sans-serif" '
            f'font-size="10" fill="#6E7681">'
            f'{label}'
            f'</text>'
        )

    # Contribution cells
    for week_index, week in enumerate(weeks):

        for day in week["contributionDays"]:
            date_value = dt.date.fromisoformat(day["date"])

            # Python weekday(): Monday = 0
            row = date_value.weekday()

            x = grid_x + week_index * (cell_size + gap)
            y = grid_y + row * (cell_size + gap)

            count = day["contributionCount"]
            level = contribution_level(count, maximum)

            tooltip = (
                f"{date_value.strftime('%b %d, %Y')}: "
                f"{count} contribution"
                f"{'' if count == 1 else 's'}"
            )

            svg.append(
                f'<rect '
                f'x="{x}" '
                f'y="{y}" '
                f'width="{cell_size}" '
                f'height="{cell_size}" '
                f'rx="3" '
                f'fill="{colors[level]}">'
                f'<title>{html.escape(tooltip)}</title>'
                f'</rect>'
            )

    # Legend
    legend_x = 930
    legend_y = 258

    svg.append(
        f'<text x="{legend_x - 40}" y="{legend_y + 10}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="10" fill="#6E7681">'
        f'Less'
        f'</text>'
    )

    for level in range(5):
        x = legend_x + level * (cell_size + gap)

        svg.append(
            f'<rect x="{x}" y="{legend_y}" '
            f'width="{cell_size}" height="{cell_size}" '
            f'rx="3" fill="{colors[level]}"/>'
        )

    svg.append(
        f'<text x="{legend_x + 5 * (cell_size + gap) + 3}" '
        f'y="{legend_y + 10}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="10" fill="#6E7681">'
        f'More'
        f'</text>'
    )

    svg.append("</svg>")

    return "\n".join(svg)


def main():
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("GITHUB_TOKEN is missing.")

    today = dt.datetime.now(dt.timezone.utc)
    start = today - dt.timedelta(days=365)

    variables = {
        "login": USERNAME,
        "from": start.isoformat(),
        "to": today.isoformat(),
    }

    data = github_query(token, variables)

    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]

    svg = generate_svg(calendar)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(svg)

    print(
        f"Generated {OUTPUT_FILE} "
        f"with {calendar['totalContributions']:,} contributions."
    )


if __name__ == "__main__":
    main()