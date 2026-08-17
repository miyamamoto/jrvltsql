"""Auto-update and version checking utilities for JLTSQL."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from packaging.version import InvalidVersion, Version

from src.utils.logger import get_logger

logger = get_logger(__name__)

# GitHub repository info
GITHUB_OWNER = "miyamamoto"
GITHUB_REPO = "jrvltsql"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

# Update check state file
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _default_update_check_file() -> Path:
    explicit_state = os.environ.get("JLTSQL_STATE_DIR")
    if explicit_state:
        state_root = Path(explicit_state)
    elif sys.platform == "win32":
        state_root = Path(
            os.environ.get(
                "LOCALAPPDATA",
                Path.home() / "AppData" / "Local",
            )
        ) / "jltsql"
    else:
        state_root = Path(
            os.environ.get(
                "XDG_STATE_HOME",
                Path.home() / ".local" / "state",
            )
        ) / "jltsql"
    return state_root / "update_check.json"


UPDATE_CHECK_FILE = _default_update_check_file()


def get_current_version() -> str:
    """Get the current version from source or installed package metadata.

    Returns:
        Version string (e.g., "2.2.0" or "v2.2.0")
    """
    # A source checkout may intentionally be ahead of the latest release tag.
    # Its project metadata is therefore the source of truth.
    try:
        toml_path = PROJECT_ROOT / "pyproject.toml"
        if toml_path.exists():
            content = toml_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.strip().startswith("version"):
                    # version = "2.2.0"
                    return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass

    # Installed wheels do not carry their source pyproject.
    try:
        from importlib.metadata import version

        return version("jltsql")
    except Exception:
        pass

    # Last-resort compatibility for an unpacked git checkout without project
    # metadata. A tag is not allowed to override either authoritative source.
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return "unknown"


def get_current_commit() -> Optional[str]:
    """Get the current git commit hash.

    Returns:
        Short commit hash or None
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_for_updates() -> Optional[dict]:
    """Check GitHub for the latest release/tag.

    Returns:
        dict with 'latest_version', 'current_version', 'update_available', 'html_url'
        or None on failure
    """
    import urllib.request
    import urllib.error

    current = get_current_version()

    try:
        # Check latest release via GitHub API
        url = f"{GITHUB_API_URL}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "jltsql"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latest = data.get("tag_name", "unknown")
            html_url = data.get("html_url", "")

            return {
                "latest_version": latest,
                "current_version": current,
                "update_available": _version_newer(latest, current),
                "html_url": html_url,
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # No releases yet, try tags
            pass
        else:
            logger.debug("GitHub API error", status=e.code)
            return None
    except Exception as e:
        logger.debug("Failed to check for updates", error=str(e))
        return None

    # Fallback: check tags
    try:
        url = f"{GITHUB_API_URL}/tags?per_page=1"
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "jltsql"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                latest = data[0].get("name", "unknown")
                return {
                    "latest_version": latest,
                    "current_version": current,
                    "update_available": _version_newer(latest, current),
                    "html_url": f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases",
                }
    except Exception as e:
        logger.debug("Failed to check tags", error=str(e))

    return None


def _version_newer(latest: str, current: str) -> bool:
    """Compare PEP 440 versions after stripping an optional ``v`` prefix.

    Returns:
        True if latest is newer than current
    """
    try:
        return Version(latest.lstrip("v")) > Version(current.lstrip("v"))
    except InvalidVersion:
        # Unparseable or unavailable metadata is unknown, not evidence that an
        # update is safe or required.
        return False


def should_check_updates(interval_hours: int = 24) -> bool:
    """Check if enough time has passed since last update check.

    Args:
        interval_hours: Minimum hours between checks

    Returns:
        True if we should check
    """
    try:
        if not UPDATE_CHECK_FILE.exists():
            return True

        data = json.loads(UPDATE_CHECK_FILE.read_text(encoding="utf-8"))
        last_check = data.get("last_check", 0)
        elapsed = time.time() - last_check
        return elapsed > (interval_hours * 3600)
    except Exception:
        return True


def save_update_check_time():
    """Save the current time as last update check."""
    try:
        UPDATE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"last_check": time.time(), "checked_at": datetime.now(timezone.utc).isoformat()}
        UPDATE_CHECK_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def perform_update(verbose: bool = True) -> bool:
    """Perform the update: git pull + pip install -e .

    Args:
        verbose: Print progress messages

    Returns:
        True if update succeeded
    """
    if not (PROJECT_ROOT / ".git").exists():
        if verbose:
            print(
                "This installation is not a git checkout. "
                "Upgrade it with pip or the release installer."
            )
        return False

    try:
        # Step 1: git pull
        if verbose:
            print("Pulling latest changes...")

        result = subprocess.run(
            ["git", "pull", "--ff-only", "origin", "master"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=60,
        )

        if result.returncode != 0:
            if verbose:
                print(f"git pull failed: {result.stderr}")
            logger.error("git pull failed", stderr=result.stderr)
            return False

        if verbose:
            pull_output = result.stdout.strip()
            if "Already up to date" in pull_output:
                print("Already up to date.")
            else:
                print(f"Updated: {pull_output}")

        # Step 2: pip install -e .
        if verbose:
            print("Updating dependencies...")

        pip_exe = _find_pip()
        result = subprocess.run(
            [pip_exe, "install", "-e", "."],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,
        )

        if result.returncode != 0:
            if verbose:
                print(f"pip install failed: {result.stderr}")
            logger.error("pip install failed", stderr=result.stderr)
            return False

        if verbose:
            print("Dependencies updated.")

        return True

    except subprocess.TimeoutExpired:
        if verbose:
            print("Update timed out.")
        return False
    except Exception as e:
        if verbose:
            print(f"Update failed: {e}")
        logger.error("Update failed", error=str(e))
        return False


def _find_pip() -> str:
    """Find the pip executable in the current environment."""
    # Use the same Python that's running this script
    return str(Path(sys.executable).parent / "pip")


def auto_update_check_notice() -> Optional[str]:
    """Check for updates silently and return a notice string if available.

    Returns:
        Notice string or None
    """
    if not should_check_updates():
        return None

    try:
        info = check_for_updates()
        save_update_check_time()

        if info and info.get("update_available"):
            latest = info["latest_version"]
            current = info["current_version"]
            return (
                f"Update available: {current} → {latest}\n"
                f"Run 'jltsql update' to update."
            )
    except Exception:
        pass

    return None
