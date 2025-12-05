"""Stylish progress display for JLTSQL using rich library.

This module provides beautiful, informative progress bars for data fetching operations.
"""

import threading
import time
from contextlib import contextmanager
from typing import Optional

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.style import Style
from rich.table import Table
from rich.text import Text


# JV-Data スペック名の日本語説明
SPEC_DESCRIPTIONS = {
    # 蓄積系データ
    "RACE": "レース詳細",
    "DIFF": "差分データ",
    "BLOD": "血統データ",
    "SNAP": "スナップショット",
    "SLOP": "坂路調教",
    "WOOD": "ウッドチップ調教",
    "YSCH": "開催スケジュール",
    "HOSE": "馬マスタ",
    "HOYU": "馬主マスタ",
    "CHOK": "調教師マスタ",
    "KISI": "騎手マスタ",
    "BRDR": "生産者マスタ",
    "TOKU": "特別レース名",
    "COMM": "コメントデータ",
    "PARA": "パラメータ",
    "MING": "出馬表データ",
    # 速報系データ
    "0B12": "オッズ（単複枠）",
    "0B13": "オッズ（馬連）",
    "0B14": "オッズ（ワイド）",
    "0B15": "オッズ（馬単）",
    "0B16": "オッズ（3連複）",
    "0B17": "オッズ（3連単）",
    "0B11": "レース結果",
    "0B20": "騎手変更",
    # 時系列オッズデータ
    "0B30": "単勝オッズ",
    "0B31": "複勝・枠連オッズ",
    "0B32": "馬連オッズ",
    "0B33": "ワイドオッズ",
    "0B34": "馬単オッズ",
    "0B35": "3連複オッズ",
    "0B36": "3連単オッズ",
    "0B41": "レース払戻（単複枠）",
    "0B42": "レース払戻（馬連）",
    "0B51": "票数（単複枠）",
    "0B52": "票数（馬連）",
}

# スペックのカテゴリ分類
SPEC_CATEGORIES = {
    # 蓄積系データ（JVOpen: 1986年〜全期間）
    "RACE": "蓄積系",
    "DIFF": "蓄積系",
    "BLOD": "蓄積系",
    "SNAP": "蓄積系",
    "SLOP": "蓄積系",
    "WOOD": "蓄積系",
    "YSCH": "蓄積系",
    "HOSE": "蓄積系",
    "HOYU": "蓄積系",
    "CHOK": "蓄積系",
    "KISI": "蓄積系",
    "BRDR": "蓄積系",
    "TOKU": "蓄積系",
    "COMM": "蓄積系",
    "PARA": "蓄積系",
    "MING": "蓄積系",
    # 速報系データ（JVRTOpen: 当日〜直近）
    "0B11": "速報系",
    "0B12": "速報系",
    "0B13": "速報系",
    "0B14": "速報系",
    "0B15": "速報系",
    "0B16": "速報系",
    "0B17": "速報系",
    "0B41": "速報系",
    "0B42": "速報系",
    "0B51": "速報系",
    "0B52": "速報系",
    # 時系列データ（JVRTOpen: 過去12ヶ月）
    "0B20": "時系列",
    "0B30": "時系列",
    "0B31": "時系列",
    "0B32": "時系列",
    "0B33": "時系列",
    "0B34": "時系列",
    "0B35": "時系列",
    "0B36": "時系列",
}

# カテゴリごとの期間説明
CATEGORY_PERIODS = {
    "蓄積系": "1986年〜",
    "速報系": "当日データ",
    "時系列": "過去12ヶ月",
}


class CompactTimeColumn(ProgressColumn):
    """Compact time display showing elapsed/remaining."""

    def render(self, task) -> Text:
        elapsed = task.elapsed
        if elapsed is None:
            return Text("-:--", style="dim")

        # Format elapsed time
        elapsed_mins = int(elapsed // 60)
        elapsed_secs = int(elapsed % 60)
        elapsed_str = f"{elapsed_mins}:{elapsed_secs:02d}"

        # Calculate remaining time
        if task.total and task.completed > 0 and elapsed > 0:
            speed = task.completed / elapsed
            remaining = (task.total - task.completed) / speed if speed > 0 else 0
            remaining_mins = int(remaining // 60)
            remaining_secs = int(remaining % 60)
            remaining_str = f"{remaining_mins}:{remaining_secs:02d}"
            return Text(f"{elapsed_str}/{remaining_str}", style="cyan")

        return Text(elapsed_str, style="cyan")


class StatsDisplay:
    """Dynamic stats display that updates without recreating the object."""

    def __init__(self):
        self._lock = threading.Lock()
        self.fetched = 0
        self.parsed = 0
        self.failed = 0
        self.skipped = 0
        self.inserted = 0
        self.speed: Optional[float] = None

    def update(self, fetched: int = 0, parsed: int = 0, failed: int = 0,
               skipped: int = 0, inserted: int = 0, speed: Optional[float] = None):
        with self._lock:
            self.fetched = fetched
            self.parsed = parsed
            self.failed = failed
            self.skipped = skipped
            self.inserted = inserted
            self.speed = speed

    def __rich__(self) -> RenderableType:
        """Generate compact stats display."""
        with self._lock:
            parts = []

            # Build compact stats line
            parts.append(f"[bold cyan]取得[/]: [green]{self.fetched:,}[/]")
            parts.append(f"[bold cyan]成功[/]: [green]{self.parsed:,}[/]")

            if self.skipped > 0:
                parts.append(f"[bold yellow]スキップ[/]: [yellow]{self.skipped:,}[/]")

            if self.failed > 0:
                parts.append(f"[bold red]失敗[/]: [red]{self.failed:,}[/]")

            if self.inserted > 0:
                parts.append(f"[bold cyan]挿入[/]: [cyan]{self.inserted:,}[/]")

            if self.speed is not None:
                parts.append(f"[bold yellow]速度[/]: [yellow]{self.speed:,.0f}/秒[/]")

            return Text.from_markup("  ".join(parts))


class JVLinkProgressDisplay:
    """Stylish progress display for JV-Link data operations.

    Features:
    - Clean, compact layout with Panel border
    - Real-time progress bar with file count
    - Compact statistics display
    - Download progress section (when downloading)
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize progress display.

        Args:
            console: Rich console instance (creates new if None)
        """
        # Force UTF-8 encoding for Windows console compatibility
        self.console = console or Console(force_terminal=True, legacy_windows=True)

        # Thread safety lock for shared state
        self._lock = threading.Lock()

        # Rate limiting for updates (avoid screen flickering)
        self._last_update_time = 0.0
        self._min_update_interval = 0.15  # 150ms minimum between updates

        # Current spec being processed
        self._current_spec = ""
        self._current_status = ""
        self._file_progress = ""

        # Create main progress bar for overall operations
        self.progress = Progress(
            SpinnerColumn(style="green"),
            TextColumn("{task.description}", style="bold white"),
            BarColumn(
                bar_width=35,
                style="bar.back",
                complete_style="green",
                finished_style="bright_green",
            ),
            TextColumn("[bold]{task.percentage:>3.0f}%[/]"),
            CompactTimeColumn(),
            console=self.console,
            expand=False,
        )

        # Create simple progress for downloads
        self.download_progress = Progress(
            SpinnerColumn(style="magenta"),
            TextColumn("{task.description}", style="bold magenta"),
            BarColumn(
                bar_width=35,
                style="bar.back",
                complete_style="magenta",
                finished_style="bright_magenta",
            ),
            TextColumn("[bold]{task.percentage:>3.0f}%[/]"),
            TextColumn("[cyan]{task.fields[status]}[/]"),
            console=self.console,
            expand=False,
        )

        # Use StatsDisplay for dynamic updates
        self.stats_display = StatsDisplay()

        # State
        self._layout: Optional[Table] = None
        self._has_download = False
        self.live: Optional[Live] = None
        self.tasks = {}

    def _create_layout(self) -> Panel:
        """Create the display layout with Panel border.

        Returns a Panel containing the progress display.
        """
        # Create main content table
        content = Table.grid(expand=True, padding=(0, 1))
        content.add_column()

        # Download section (if active)
        if self._has_download:
            content.add_row(Text("📥 ダウンロード", style="bold magenta"))
            content.add_row(self.download_progress)
            content.add_row(Text(""))

        # Processing section
        content.add_row(Text("⚙️  処理中", style="bold green"))
        content.add_row(self.progress)

        # File progress info
        if self._file_progress:
            content.add_row(Text(f"   {self._file_progress}", style="dim"))

        content.add_row(Text(""))

        # Stats section
        content.add_row(Text("📊 統計", style="bold cyan"))
        content.add_row(self.stats_display)

        # Wrap in Panel
        return Panel(
            content,
            title="[bold blue]JLTSQL データ取得[/]",
            border_style="blue",
            padding=(0, 1),
        )

    def _should_update(self) -> bool:
        """Check if enough time has passed for an update."""
        with self._lock:
            current_time = time.time()
            if current_time - self._last_update_time >= self._min_update_interval:
                self._last_update_time = current_time
                return True
            return False

    def start(self):
        """Start the live display."""
        with self._lock:
            if self.live is None:
                self.live = Live(
                    self._create_layout(),
                    console=self.console,
                    refresh_per_second=4,
                    transient=False,
                    vertical_overflow="visible",
                )
                self.live.start()

    def stop(self):
        """Stop the live display."""
        with self._lock:
            if self.live:
                self.live.stop()
                self.live = None
            # Reset state for next use
            self._has_download = False
            self._file_progress = ""
            self._layout = None

    def _refresh_layout(self):
        """Refresh the layout in live display."""
        if self.live:
            self.live.update(self._create_layout())

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
        self._has_download = True
        task_id = self.download_progress.add_task(
            description,
            total=total or 100,
            status="待機中...",
        )
        self._refresh_layout()
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
        self._current_spec = description
        task_id = self.progress.add_task(
            description,
            total=total or 100,
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
            status: Status message (used for file progress display)
        """
        update_dict = {}
        if advance is not None:
            update_dict["advance"] = advance
        if completed is not None:
            update_dict["completed"] = completed
        if total is not None:
            update_dict["total"] = total

        # Extract file progress from status if it contains file info
        if status is not None:
            self._file_progress = status
            # Refresh layout to show file progress
            self._refresh_layout()

        self.progress.update(task_id, **update_dict)

    def update_stats(
        self,
        fetched: int = 0,
        parsed: int = 0,
        failed: int = 0,
        skipped: int = 0,
        inserted: int = 0,
        speed: Optional[float] = None,
    ):
        """Update statistics display.

        Args:
            fetched: Number of records fetched
            parsed: Number of records parsed
            failed: Number of failed records
            skipped: Number of records/specs skipped (e.g., contract not available)
            inserted: Number of records inserted to database
            speed: Processing speed (records/sec)
        """
        self.stats_display.update(
            fetched=fetched,
            parsed=parsed,
            failed=failed,
            skipped=skipped,
            inserted=inserted,
            speed=speed,
        )

    def print_success(self, message: str):
        """Print success message.

        Args:
            message: Success message
        """
        self.console.print(f"[bold green]✓[/] {message}")

    def print_error(self, message: str):
        """Print error message.

        Args:
            message: Error message
        """
        self.console.print(f"[bold red]✗[/] {message}")

    def print_warning(self, message: str):
        """Print warning message.

        Args:
            message: Warning message
        """
        self.console.print(f"[bold yellow]⚠[/] {message}")

    def print_info(self, message: str):
        """Print info message.

        Args:
            message: Info message
        """
        self.console.print(f"[bold cyan]ℹ[/] {message}")

    def print_separator(self):
        """Print a separator line between specs."""
        self.console.print()

    def print_spec_header(self, spec: str):
        """Print a header for a new spec processing.

        Args:
            spec: The spec name being processed
        """
        # スペック名の日本語説明を取得
        description = SPEC_DESCRIPTIONS.get(spec, "")
        # カテゴリと期間を取得
        category = SPEC_CATEGORIES.get(spec, "")
        period = CATEGORY_PERIODS.get(category, "") if category else ""

        self.console.print()
        # フォーマット: ━━━ SPEC (説明) ━━━ [カテゴリ: 期間]
        parts = [f"[bold blue]━━━[/] [bold white]{spec}[/]"]
        if description:
            parts.append(f"[dim]({description})[/]")
        parts.append("[bold blue]━━━[/]")
        if category and period:
            parts.append(f"[cyan][{category}: {period}][/]")
        self.console.print(" ".join(parts))

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
            pass

    def __enter__(self):
        """Enter context manager."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.stop()
        return False
