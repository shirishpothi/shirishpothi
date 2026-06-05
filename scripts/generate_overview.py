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
            if repo["nameWithOwner"].casefold() == f"{login}/{login}".casefold():
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


def get_total_contributions(token: str, login: str, years: list[int]) -> int:
    if not years:
        return 0

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
    return sum(
        value.get("contributionCalendar", {}).get("totalContributions", 0)
        for value in user.values()
    )


def fmt(value: int) -> str:
    return f"{value:,}"


def row(y: int, label: str, value: str, delay: int) -> str:
    return f"""
  <g class="row" style="animation-delay: {delay}ms" transform="translate(24 {y})">
    <circle class="dot" cx="4" cy="-4" r="4" />
    <text class="label" x="20" y="0">{html.escape(label)}</text>
    <text class="value" x="396" y="0" text-anchor="end">{html.escape(value)}</text>
  </g>"""


def render_svg(display_name: str, stats: dict[str, str]) -> str:
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    title = f"{display_name}'s GitHub Statistics"
    rows = [
        ("Stars", stats["stars"]),
        ("Forks", stats["forks"]),
        ("All-time contributions", stats["contributions"]),
        ("Active public repos", stats["repos"]),
    ]

    return f"""<svg width="460" height="188" viewBox="0 0 460 188" fill="none" xmlns="http://www.w3.org/2000/svg">
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
    font-size: 16px;
    font-weight: 600;
  }}
  .label {{
    fill: #57606a;
    font-size: 13px;
  }}
  .value {{
    fill: #24292f;
    font-size: 13px;
    font-weight: 600;
  }}
  .updated {{
    fill: #6e7781;
    font-size: 11px;
  }}
  .dot {{
    fill: #2da44e;
  }}
  .row {{
    opacity: 0;
    animation: fade-in 420ms ease-out forwards;
  }}
  @keyframes fade-in {{
    to {{
      opacity: 1;
    }}
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
    .dot {{
      fill: #3fb950;
    }}
  }}
</style>
<rect id="background" x="0.5" y="0.5" width="459" height="187" rx="6" />
<text class="title" x="24" y="32">{html.escape(title)}</text>
{''.join(row(66 + index * 28, label, value, index * 120) for index, (label, value) in enumerate(rows))}
<text class="updated" x="24" y="166">Updated {html.escape(now)}</text>
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
    stats = {
        "stars": fmt(sum(repo["stargazerCount"] for repo in repos)),
        "forks": fmt(sum(repo["forkCount"] for repo in repos)),
        "contributions": fmt(get_total_contributions(token, login, years)),
        "repos": fmt(len(repos)),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(display_name, stats), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
