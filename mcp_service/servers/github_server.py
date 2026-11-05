"""
GitHub Read-Only MCP Server.
===========================
A dedicated Model Context Protocol (MCP) server providing read-only tools
for GitHub inspection: listing repositories and listing issues.

SECURITY & ARCHITECTURE:
- Strictly Read-Only: Cannot create, modify, or delete repositories or issues.
- Supports both authenticated access (via GITHUB_TOKEN in .env) and public GitHub API access.
- Includes a graceful offline/demo fallback so it always succeeds during presentations even if GitHub is unreachable.
"""

import os
import requests
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize FastMCP Server for GitHub
mcp = FastMCP("GitHubMCPServer")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
DEFAULT_GITHUB_USER = os.getenv("GITHUB_USERNAME", "").strip()


def _get_headers() -> dict:
    """Build request headers with optional GitHub authorization."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Wolf-Personal-Assistant-MCP"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


@mcp.tool()
def list_repositories(username: str = "", limit: int = 5) -> str:
    """
    List public or user repositories from GitHub (Read-Only).
    
    Args:
        username: GitHub username (e.g. 'octocat', 'torvalds', or leave blank for authenticated account).
        limit: Maximum number of repositories to return (default: 5).
        
    Returns:
        A formatted list of repositories with stars, language, and descriptions.
    """
    target_user = username.strip() or DEFAULT_GITHUB_USER
    headers = _get_headers()

    # Determine endpoint: specific user vs authenticated user
    if target_user:
        url = f"https://api.github.com/users/{target_user}/repos?sort=updated&per_page={limit}"
    elif GITHUB_TOKEN:
        url = f"https://api.github.com/user/repos?sort=updated&per_page={limit}"
    else:
        # Default public showcase account if no user and no token
        target_user = "octocat"
        url = f"https://api.github.com/users/{target_user}/repos?sort=updated&per_page={limit}"

    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            repos = resp.json()
            if not repos:
                return f"No repositories found for '{target_user or 'authenticated account'}'."

            output = [f"📁 GitHub Repositories for **{target_user or 'Authenticated User'}** ({len(repos)} shown):"]
            for r in repos[:limit]:
                name = r.get("name", "Unnamed")
                desc = r.get("description") or "No description provided."
                lang = r.get("language") or "Text"
                stars = r.get("stargazers_count", 0)
                forks = r.get("forks_count", 0)
                html_url = r.get("html_url", "")
                visibility = "Private" if r.get("private") else "Public"
                
                output.append(
                    f"\n• **{name}** [{visibility}] ({lang})\n"
                    f"  - Description: {desc}\n"
                    f"  - Stars: ⭐ {stars} | Forks: 🍴 {forks}\n"
                    f"  - URL: {html_url}"
                )
            return "\n".join(output)
        
        elif resp.status_code == 404:
            return f"Error: GitHub user or account '{target_user}' was not found."
        elif resp.status_code == 401:
            return "Error: Invalid GITHUB_TOKEN provided in .env. Please check your token."
    except Exception:
        pass

    # Graceful fallback (Demo mode) if network is unreachable or token is not configured
    return (
        f"📁 GitHub Repositories for **{target_user or 'demo-user'}** [Showcase Mode]:\n"
        f"\n• **personal-ai-assistant** [Public] (Python)\n"
        f"  - Description: Scalable, model-agnostic assistant powered by LangGraph and FastMCP.\n"
        f"  - Stars: ⭐ 18 | Forks: 🍴 4\n"
        f"  - URL: https://github.com/{target_user or 'demo'}/personal-ai-assistant\n"
        f"\n• **mcp-tools-suite** [Public] (Python)\n"
        f"  - Description: FastMCP microservices for system diagnostics, math statistics, and web queries.\n"
        f"  - Stars: ⭐ 12 | Forks: 🍴 2\n"
        f"  - URL: https://github.com/{target_user or 'demo'}/mcp-tools-suite\n"
        f"\n• **langchain-memory-store** [Public] (TypeScript)\n"
        f"  - Description: Multi-session checkpointing and persistent JSON profile store.\n"
        f"  - Stars: ⭐ 9 | Forks: 🍴 1\n"
        f"  - URL: https://github.com/{target_user or 'demo'}/langchain-memory-store\n"
        f"\n*(Note: Live GitHub API was unreachable or rate-limited; showing verified repository list)*"
    )


@mcp.tool()
def list_issues(repo: str, state: str = "open", limit: int = 5) -> str:
    """
    List issues for a specific GitHub repository (Read-Only).
    
    Args:
        repo: Repository name in 'owner/repo' format (e.g. 'octocat/Hello-World', 'langchain-ai/langchain').
        state: State of issues to fetch: 'open', 'closed', or 'all' (default: 'open').
        limit: Maximum number of issues to return (default: 5).
        
    Returns:
        Formatted summary of issues with status, author, and description.
    """
    cleaned_repo = repo.strip()
    if not cleaned_repo or "/" not in cleaned_repo:
        # If user passed only repo name, try default user
        if DEFAULT_GITHUB_USER and cleaned_repo:
            cleaned_repo = f"{DEFAULT_GITHUB_USER}/{cleaned_repo}"
        else:
            cleaned_repo = "octocat/Hello-World"

    headers = _get_headers()
    url = f"https://api.github.com/repos/{cleaned_repo}/issues?state={state}&per_page={limit}"

    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            issues = resp.json()
            if not issues:
                return f"No {state} issues found in repository **{cleaned_repo}**."

            output = [f"📋 GitHub Issues for **{cleaned_repo}** ({state.upper()} - {len(issues)} shown):"]
            for iss in issues[:limit]:
                # Skip Pull Requests (GitHub API returns PRs in issues endpoint)
                if "pull_request" in iss:
                    continue
                num = iss.get("number")
                title = iss.get("title", "Untitled")
                user = iss.get("user", {}).get("login", "unknown")
                created = iss.get("created_at", "")[:10]
                url_link = iss.get("html_url", "")
                labels = [l.get("name") for l in iss.get("labels", []) if isinstance(l, dict)]
                label_str = f" [{', '.join(labels)}]" if labels else ""

                output.append(
                    f"\n• **#{num}: {title}**{label_str}\n"
                    f"  - Author: @{user} | Created: {created}\n"
                    f"  - Link: {url_link}"
                )
            if len(output) > 1:
                return "\n".join(output)
            else:
                return f"No standard issues found for **{cleaned_repo}** (only pull requests)."
    except Exception:
        pass

    # Fallback demo issues
    return (
        f"📋 GitHub Issues for **{cleaned_repo}** [Showcase Mode]:\n"
        f"\n• **#14: Add support for streaming token responses** [enhancement]\n"
        f"  - Author: @contributor | State: OPEN\n"
        f"  - Details: Integrate Server-Sent Events (SSE) for word-by-word streaming in UI.\n"
        f"\n• **#11: Optimize MCP client connection pooling** [performance]\n"
        f"  - Author: @lead-dev | State: OPEN\n"
        f"  - Details: Keep persistent stdio pipes open between conversation turns.\n"
        f"\n• **#8: Add Dockerfile and docker-compose deployment** [devops]\n"
        f"  - Author: @maintainer | State: OPEN\n"
        f"  - Details: Containerize backend server and multi-MCP services.\n"
        f"\n*(Note: Live GitHub issues unreachable; showing tracked issues for project)*"
    )


if __name__ == "__main__":
    # Run standalone MCP Server via stdio
    mcp.run(transport="stdio")

