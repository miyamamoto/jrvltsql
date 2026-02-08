"""Auto-update and version checking utilities for JLTSQL."""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

# GitHub repository info
GITHUB_OWNER = "miyamamoto"
GITHUB_REPO = "jrvltsql"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

# Update check state file
PROJECT_ROOT = Path(__file__).parent.parent.parent
UPDATE_CHECK_FILE = PROJECT_ROOT / "data" / ".update_check.json"


def get_current_version() -> str:
    """Get the current installed version from git tags or pyproject.toml.

    Returns:
        Version string (e.g., "2.2.0" or "v2.2.0")
    """
    # Try git describe first
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

    # Fallback: read from pyproject.toml
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
    """Compare version strings (strip 'v' prefix).

    Returns:
        True if latest is newer than current
    """
    def normalize(v: str) -> list[int]:
        v = v.lstrip("v")
        parts = []
        for p in v.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return parts

    try:
        return normalize(latest) > normalize(current)
    except Exception:
        return latest != current


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
