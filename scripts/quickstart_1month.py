#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""1 month data fetch test (non-interactive PostgreSQL).

Thin wrapper around quickstart.main() — sets sys.argv and re-enters the
existing CLI so behavior matches a real user run.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.quickstart import main  # noqa: E402


if __name__ == "__main__":
    sys.argv = [
        "quickstart.py",
        "--mode", "simple",
        "--yes",
        "--db-type", "postgresql",
        "--pg-host", "localhost",
        "--pg-port", "5432",
        "--pg-database", "keiba",
        "--pg-user", "postgres",
        "--pg-password", "postgres",
        "--from-date", "20260402",
        "--to-date", "20260502",
        "--log-file", str(project_root / "quickstart_1month.log"),
    ]
    main()
