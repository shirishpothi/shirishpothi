#!/usr/bin/env python3

import datetime as dt
import html
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request


GRAPHQL_URL = "https://api.github.com/graphql"
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "generated" / "overview.svg"
FILLER_REPO_PREFIXES = ("contribution-art-fill-",)

ICONS = {
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z",
    "fork": "M5 3.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm0 2.122a2.25 2.25 0 1 0-1.5 0v.878A2.25 2.25 0 0 0 5.75 8.5h1.5v2.128a2.251 2.251 0 1 0 1.5 0V8.5h1.5a2.25 2.25 0 0 0 2.25-2.25v-.878a2.25 2.25 0 1 0-1.5 0v.878a.75.75 0 0 1-.75.75h-4.5A.75.75 0 0 1 5 6.25Zm3.75 7.378a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm3-8.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z",
    "contribution": "M1 2.5A2.5 2.5 0 0 1 3.5 0h8.75a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V1.5h-8a1 1 0 0 0-1 1v6.708A2.492 2.492 0 0 1 3.5 9h3.25a.75.75 0 0 1 0 1.5H3.5a1 1 0 1 0 0 2h5.75a.75.75 0 0 1 0 1.5H3.5A2.5 2.5 0 0 1 1 11.5Zm13.23 7.79a.75.75 0 0 0 1.06-1.06l-2.505-2.505a.75.75 0 0 0-1.06 0L9.22 9.229a.75.75 0 0 0 1.06 1.061l1.225-1.224v6.184a.75.75 0 0 0 1.5 0V9.066Z",
    "calendar": "M4.75 0a.75.75 0 0 1 .75.75V2h5V.75a.75.75 0 0 1 1.5 0V2h1.25A2.75 2.75 0 0 1 16 4.75v8.5A2.75 2.75 0 0 1 13.25 16H2.75A2.75 2.75 0 0 1 0 13.25v-8.5A2.75 2.75 0 0 1 2.75 2H4V.75A.75.75 0 0 1 4.75 0ZM1.5 7v6.25c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25V7Zm1.25-3.5c-.69 0-1.25.56-1.25 1.25V5.5h13v-.75c0-.69-.56-1.25-1.25-1.25Z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 1 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 0 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.492 2.492 0 0 1 4.5 9h8Z",
    "trophy": "M3.75 1.5A1.75 1.75 0 0 0 2 3.25V4H1.75A1.75 1.75 0 0 0 0 5.75v.5A3.75 3.75 0 0 0 3.75 10H5a3 3 0 0 0 2.25 2.83v1.67H5.75a.75.75 0 0 0 0 1.5h4.5a.75.75 0 0 0 0-1.5h-1.5v-1.67A3 3 0 0 0 11 10h1.25A3.75 3.75 0 0 0 16 6.25v-.5A1.75 1.75 0 0 0 14.25 4H14v-.75a1.75 1.75 0 0 0-1.75-1.75Zm-.25 6.99A2.25 2.25 0 0 1 1.5 6.25v-.5A.25.25 0 0 1 1.75 5H2v1.25c0 .834.42 1.57 1.06 2.01.14.095.287.172.44.23ZM14 5h.25a.25.25 0 0 1 .25.25v.5a2.25 2.25 0 0 1-2 2.24c.153-.058.3-.135.44-.23A2.49 2.49 0 0 0 14 6.25Z",
}


def token_from_env() -> str:
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "ACCESS_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value

    try:
        return subprocess.check_output(
            ["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def short_repo_name(name_with_owner: str) -> str:
    return name_with_owner.rsplit("/", 1)[-1]


def should_skip_repo(name_with_owner: str, login: str) -> bool:
    short_name = short_repo_name(name_with_owner).casefold()
    if name_with_owner.casefold() == f"{login}/{login}".casefold():
        return True
    return any(short_name.startswith(prefix) for prefix in FILLER_REPO_PREFIXES)


def graphql(token: str, query: str, variables: dict | None = None) -> dict:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "shirishpothi-readme-stats",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API request failed: {error.code} {body}") from error

    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]


def get_user_summary(token: str, login: str) -> tuple[str, list[dict]]:
    query = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    login
    name
    repositories(
      first: 100
      after: $cursor
      isFork: false
      ownerAffiliations: OWNER
      privacy: PUBLIC
      orderBy: {field: STARGAZERS, direction: DESC}
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        nameWithOwner
        isArchived
        isDisabled
        stargazerCount
        forkCount
      }
    }
  }
}
"""
    repos: list[dict] = []
    display_name = login
    cursor = None

    while True:
        data = graphql(token, query, {"login": login, "cursor": cursor})
        user = data.get("user")
        if not user:
            raise RuntimeError(f"GitHub user not found: {login}")

        display_name = user.get("name") or user.get("login") or login
        page = user["repositories"]
        for repo in page["nodes"]:
            if repo["isArchived"] or repo["isDisabled"]:
                continue
            if should_skip_repo(repo["nameWithOwner"], login):
                continue
            repos.append(repo)

        if not page["pageInfo"]["hasNextPage"]:
            return display_name, repos
        cursor = page["pageInfo"]["endCursor"]


def get_contribution_years(token: str, login: str) -> list[int]:
    query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionYears
    }
  }
}
"""
    data = graphql(token, query, {"login": login})
    years = (
        data.get("user", {})
        .get("contributionsCollection", {})
        .get("contributionYears", [])
    )
    return sorted(int(year) for year in years)


def get_public_contributions_by_year(
    token: str, login: str, years: list[int]
) -> dict[int, int]:
    if not years:
        return {}

    fields = []
    for year in years:
        fields.append(
            f"""
    y{year}: contributionsCollection(
      from: "{year}-01-01T00:00:00Z"
      to: "{year + 1}-01-01T00:00:00Z"
    ) {{
      contributionCalendar {{
        totalContributions
      }}
      restrictedContributionsCount
    }}"""
        )

    query = f"""
query($login: String!) {{
  user(login: $login) {{
{''.join(fields)}
  }}
}}
"""
    data = graphql(token, query, {"login": login})
    user = data.get("user", {})
    public_by_year = {}
    for key, value in user.items():
        total = value.get("contributionCalendar", {}).get("totalContributions", 0)
        restricted = value.get("restrictedContributionsCount", 0)
        public_by_year[int(key.removeprefix("y"))] = max(0, total - restricted)
    return public_by_year


def fmt(value: int) -> str:
    return f"{value:,}"


def row(y: int, icon: str, label: str, value: str) -> str:
    return f"""
  <g class="row" transform="translate(32 {y})">
    <path class="octicon" fill-rule="evenodd" transform="translate(0 -17) scale(1.125)" d="{ICONS[icon]}" />
    <text class="label" x="42" y="0">{html.escape(label)}</text>
    <text class="value" x="560" y="0" text-anchor="end">{html.escape(value)}</text>
  </g>"""


def render_svg(display_name: str, stats: dict[str, str]) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = f"{display_name}'s GitHub Statistics"
    rows = [
        ("star", "Stars", stats["stars"]),
        ("fork", "Forks", stats["forks"]),
        ("contribution", "Public contributions", stats["contributions"]),
        ("calendar", f"{stats['current_year']} contributions", stats["this_year"]),
        ("repo", "Active public repos", stats["repos"]),
        ("trophy", "Most-starred repo", stats["top_repo"]),
    ]

    return f"""<svg width="640" height="276" viewBox="0 0 640 276" fill="none" xmlns="http://www.w3.org/2000/svg">
<style>
  svg {{
    color-scheme: light dark;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }}
  #background {{
    fill: #ffffff;
    stroke: #d0d7de;
  }}
  .title {{
    fill: #0969da;
    font-size: 21px;
    font-weight: 600;
  }}
  .label {{
    fill: #57606a;
    font-size: 18px;
  }}
  .value {{
    fill: #24292f;
    font-size: 18px;
    font-weight: 600;
  }}
  .updated {{
    fill: #6e7781;
    font-size: 12px;
  }}
  .octicon {{
    fill: #57606a;
  }}
  @media (prefers-color-scheme: dark) {{
    #background {{
      fill: #0d1117;
      stroke: #30363d;
    }}
    .title {{
      fill: #58a6ff;
    }}
    .label {{
      fill: #8b949e;
    }}
    .value {{
      fill: #c9d1d9;
    }}
    .updated {{
      fill: #8b949e;
    }}
    .octicon {{
      fill: #8b949e;
    }}
  }}
</style>
<rect id="background" x="0.5" y="0.5" width="639" height="275" rx="8" />
<text class="title" x="32" y="40">{html.escape(title)}</text>
{''.join(row(78 + index * 31, icon, label, value) for index, (icon, label, value) in enumerate(rows))}
<text class="updated" x="32" y="258">Updated {html.escape(now)}</text>
</svg>
"""


def main() -> int:
    login = os.environ.get("GITHUB_USERNAME") or os.environ.get("GITHUB_ACTOR")
    if not login:
        login = "shirishpothi"

    token = token_from_env()
    if not token:
        print("Missing GitHub token. Set GITHUB_TOKEN, GH_TOKEN, or ACCESS_TOKEN.", file=sys.stderr)
        return 1

    display_name, repos = get_user_summary(token, login)
    years = get_contribution_years(token, login)
    public_by_year = get_public_contributions_by_year(token, login, years)
    current_year = dt.datetime.now(dt.timezone.utc).year
    top_repo = max(repos, key=lambda repo: repo["stargazerCount"], default=None)
    top_repo_label = "None yet"
    if top_repo:
        top_repo_label = top_repo["name"]
        if top_repo["stargazerCount"]:
            top_repo_label = f"{top_repo_label} ({fmt(top_repo['stargazerCount'])})"

    stats = {
        "stars": fmt(sum(repo["stargazerCount"] for repo in repos)),
        "forks": fmt(sum(repo["forkCount"] for repo in repos)),
        "contributions": fmt(sum(public_by_year.values())),
        "current_year": str(current_year),
        "this_year": fmt(public_by_year.get(current_year, 0)),
        "repos": fmt(len(repos)),
        "top_repo": top_repo_label,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(display_name, stats), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
