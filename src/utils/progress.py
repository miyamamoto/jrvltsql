"""Stylish progress display for JLTSQL using rich library.

This module provides beautiful, informative progress bars for data fetching operations.
"""

import time
from contextlib import contextmanager
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text


class JVLinkProgressDisplay:
    """Stylish progress display for JV-Link data operations.

    Features:
    - Multiple concurrent progress bars
    - Download progress with percentage
    - Record fetching with speed metrics
    - Database insertion progress
    - Beautiful styling with colors
    - ETA and elapsed time
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize progress display.

        Args:
            console: Rich console instance (creates new if None)
        """
        # Force UTF-8 encoding for Windows console compatibility
        self.console = console or Console(force_terminal=True, legacy_windows=True)

        # Create main progress bar for overall operations
        self.progress = Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=40, complete_style="green", finished_style="bright_green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("|"),
            TextColumn("[cyan]{task.fields[status]}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            expand=False,
        )

        # Create simple progress for downloads
        self.download_progress = Progress(
            TextColumn("[bold magenta]{task.description}", justify="right"),
            BarColumn(bar_width=40, complete_style="magenta", finished_style="bright_magenta"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("[cyan]{task.fields[status]}"),
            console=self.console,
            expand=False,
        )

        self.stats_table = Table.grid(padding=(0, 2))
        self.stats_table.add_column(style="cyan", justify="right")
        self.stats_table.add_column(style="green")

        self.live: Optional[Live] = None
        self.tasks = {}

    def _create_layout(self) -> Table:
        """Create the display layout."""
        layout = Table.grid(expand=False)
        layout.add_row(Panel(
            self.download_progress,
            title="[bold cyan]データダウンロード",
            border_style="cyan",
            padding=(0, 1),
        ))
        layout.add_row(Panel(
            self.progress,
            title="[bold blue]データ取得・処理",
            border_style="blue",
            padding=(0, 1),
        ))
        layout.add_row(Panel(
            self.stats_table,
            title="[bold green]統計情報",
            border_style="green",
            padding=(0, 1),
        ))
        return layout

    def start(self):
        """Start the live display."""
        if self.live is None:
            self.live = Live(
                self._create_layout(),
                console=self.console,
                refresh_per_second=10,
                transient=False,
            )
            self.live.start()

    def stop(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def add_download_task(
        self,
        description: str,
        total: Optional[float] = None,
    ) -> TaskID:
        """Add a download progress task.

        Args:
            description: Task description
            total: Total download count (None for indeterminate)

        Returns:
            Task ID
        """
        task_id = self.download_progress.add_task(
            description,
            total=total or 100,
            status="待機中...",
        )
        return task_id

    def add_task(
        self,
        description: str,
        total: Optional[float] = None,
    ) -> TaskID:
        """Add a progress task.

        Args:
            description: Task description
            total: Total items to process (None for indeterminate)

        Returns:
            Task ID
        """
        task_id = self.progress.add_task(
            description,
            total=total or 100,
            status="初期化中...",
        )
        self.tasks[description] = task_id
        return task_id

    def update_download(
        self,
        task_id: TaskID,
        advance: Optional[float] = None,
        completed: Optional[float] = None,
        status: Optional[str] = None,
    ):
        """Update download progress.

        Args:
            task_id: Task ID
            advance: Amount to advance
            completed: Set completed amount
            status: Status message
        """
        update_dict = {}
        if advance is not None:
            update_dict["advance"] = advance
        if completed is not None:
            update_dict["completed"] = completed
        if status is not None:
            update_dict["status"] = status

        self.download_progress.update(task_id, **update_dict)
        if self.live:
            self.live.update(self._create_layout())

    def update(
        self,
        task_id: TaskID,
        advance: Optional[float] = None,
        completed: Optional[float] = None,
        total: Optional[float] = None,
        status: Optional[str] = None,
    ):
        """Update progress.

        Args:
            task_id: Task ID
            advance: Amount to advance
            completed: Set completed amount
            total: Set total amount
            status: Status message
        """
        update_dict = {}
        if advance is not None:
            update_dict["advance"] = advance
        if completed is not None:
            update_dict["completed"] = completed
        if total is not None:
            update_dict["total"] = total
        if status is not None:
            update_dict["status"] = status

        self.progress.update(task_id, **update_dict)
        if self.live:
            self.live.update(self._create_layout())

    def update_stats(
        self,
        fetched: int = 0,
        parsed: int = 0,
        failed: int = 0,
        inserted: int = 0,
        speed: Optional[float] = None,
    ):
        """Update statistics display.

        Args:
            fetched: Number of records fetched
            parsed: Number of records parsed
            failed: Number of failed records
            inserted: Number of records inserted to database
            speed: Processing speed (records/sec)
        """
        self.stats_table = Table.grid(padding=(0, 2))
        self.stats_table.add_column(style="cyan", justify="right")
        self.stats_table.add_column(style="green")

        self.stats_table.add_row("取得レコード:", f"[bold green]{fetched:,}[/] 件")
        self.stats_table.add_row("パース成功:", f"[bold green]{parsed:,}[/] 件")
        if failed > 0:
            self.stats_table.add_row("パース失敗:", f"[bold red]{failed:,}[/] 件")
        if inserted > 0:
            self.stats_table.add_row("DB挿入:", f"[bold cyan]{inserted:,}[/] 件")
        if speed is not None:
            self.stats_table.add_row("処理速度:", f"[bold yellow]{speed:.1f}[/] レコード/秒")

        if self.live:
            self.live.update(self._create_layout())

    def print_success(self, message: str):
        """Print success message.

        Args:
            message: Success message
        """
        self.console.print(f"[bold green][OK][/] {message}")

    def print_error(self, message: str):
        """Print error message.

        Args:
            message: Error message
        """
        self.console.print(f"[bold red][ERROR][/] {message}")

    def print_warning(self, message: str):
        """Print warning message.

        Args:
            message: Warning message
        """
        self.console.print(f"[bold yellow][WARNING][/] {message}")

    def print_info(self, message: str):
        """Print info message.

        Args:
            message: Info message
        """
        self.console.print(f"[bold cyan][INFO][/] {message}")

    @contextmanager
    def task_context(self, description: str, total: Optional[float] = None):
        """Context manager for a progress task.

        Args:
            description: Task description
            total: Total items

        Yields:
            Task ID
        """
        task_id = self.add_task(description, total)
        try:
            yield task_id
        finally:
            self.update(task_id, status="完了")

    def __enter__(self):
        """Enter context manager."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.stop()
        return False
