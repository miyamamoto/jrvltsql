"""Batch processing utilities for JLTSQL.

This module provides utilities for batch processing of JV-Data.
"""

from datetime import datetime, timedelta
from itertools import islice
from typing import Iterator, List, Optional, Tuple

from src.database.base import BaseDatabase
from src.database.schema import create_all_tables
from src.fetcher.historical import HistoricalFetcher, validate_date_range
from src.importer.importer import DataImporter, ImporterError
from src.jvlink.constants import (
    jvopen_supports_end_timestamp,
    validate_jvopen_combination,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# option=4 (分割セットアップ) streams an accumulated range through JVOpen, so
# one import can run for hours. Held in a single transaction, an interrupted
# run leaves nothing behind and the retry starts over from the beginning -- a
# long enough range never gets imported at all. Commit it in bounded record
# groups instead, and split ranges over a year into end-bounded chunk opens
# (see _should_split_setup_range) so no single open carries an unbounded tail.
SPLIT_SETUP_OPTION = 4
SETUP_COMMIT_INTERVAL = 10000


def _chunks(records: Iterator[dict], size: int) -> Iterator[Iterator[dict]]:
    """Split the record stream into chunks of at most ``size`` records.

    Only one chunk is held at a time, so the caller can commit per chunk
    without the memory of a whole run. An empty stream still yields one empty
    chunk, so a run with no records takes the same path as any other.
    """
    records = iter(records)
    yielded = False
    while chunk := list(islice(records, size)):
        yielded = True
        yield iter(chunk)
    if not yielded:
        yield iter(())


def _accumulate_stats(totals: dict, stats: dict) -> None:
    """Add one import's statistics into a running total, in place."""
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            totals[key] = totals.get(key, 0) + value
        else:
            totals[key] = value


class BatchProcessor:
    """Batch processor for JV-Data import.

    Coordinates fetching, parsing, and importing of JV-Data in batches.
    Fetches data from JV-Link starting from the specified date and filters
    records client-side based on the end date.

    Note:
        Service key must be configured in JRA-VAN DataLab application
        before using this class.

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> db = SQLiteDatabase({"path": "./keiba.db"})
        >>> processor = BatchProcessor(database=db)
        >>> with db:
        ...     # Fetches from 20240601 onwards, imports records <= 20240630
        ...     processor.process_date_range(
        ...         data_spec="RACE",
        ...         from_date="20240601",
        ...         to_date="20240630",
        ...     )
    """

    def __init__(
        self,
        database: BaseDatabase,
        batch_size: int = 1000,
        sid: str = "UNKNOWN",
        show_progress: bool = True,
        cache_manager=None,
    ):
        """Initialize batch processor.

        Args:
            database: Database handler instance
            batch_size: Records per batch
            sid: Session ID for JV-Link API (default: "UNKNOWN")
            show_progress: Show stylish progress display (default: True)
            cache_manager: Optional CacheManager for local file cache read/write
        """
        self.fetcher = HistoricalFetcher(
            sid,
            show_progress=show_progress,
        )
        self.importer = DataImporter(database, batch_size)
        self.database = database
        self.cache_manager = cache_manager

        logger.info(
            "BatchProcessor initialized",
            sid=sid,
            show_progress=show_progress,
        )

    def __del__(self):
        """Release JV-Link COM/bridge resources when processor is garbage-collected."""
        try:
            if hasattr(self.fetcher, 'jvlink') and hasattr(self.fetcher.jvlink, 'cleanup'):
                self.fetcher.jvlink.cleanup()
        except Exception:
            pass

    def process_date_range(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        option: int = 1,
        auto_commit: bool = True,
        ensure_tables: bool = True,
    ) -> dict:
        """Process data for a date range.

        Args:
            data_spec: Data specification code
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD) - records are filtered to this date
            option: JVOpen option:
                    1=通常データ（差分データ取得）
                    2=今週データ（直近のレースのみ）
                    3=セットアップ（全データ取得、ダイアログ表示）
                    4=分割セットアップ（初回のみダイアログ）
            auto_commit: Whether to auto-commit
            ensure_tables: Whether to ensure tables exist

        Returns:
            Dictionary with processing statistics

        Raises:
            ValueError: If data_spec or option violates the JVOpen contract

        Note:
            For setup requests (option 3/4) on specs that permit an official
            end timestamp, JVOpen is bounded to the requested range; other
            requests fetch from from_date onwards. In every mode records are
            filtered client-side to only import those with dates <= to_date.

            option=4 commits every SETUP_COMMIT_INTERVAL records rather than
            once for the whole data spec, so an interrupted run keeps what it
            already imported. Ranges over 370 days on end-capable specs are
            additionally split into bounded yearly JVOpen chunks; committed
            chunks survive a later chunk's failure, and with the cache
            enabled a retry replays completed chunks from local cache.

        Examples:
            >>> processor = BatchProcessor(database=db)
            >>> stats = processor.process_date_range("RACE", "20240601", "20240630")
            >>> print(f"Imported {stats['records_imported']} records")
        """
        # Stop before schema creation or transaction state for invalid input.
        validate_jvopen_combination(data_spec, option)
        validate_date_range(from_date, to_date)

        logger.info(
            "Starting batch processing",
            data_spec=data_spec,
            from_date=from_date,
            to_date=to_date,
            option=option,
        )

        if self._should_split_setup_range(data_spec, from_date, to_date, option):
            return self._process_split_setup_range(
                data_spec=data_spec,
                from_date=from_date,
                to_date=to_date,
                option=option,
                auto_commit=auto_commit,
                ensure_tables=ensure_tables,
            )

        # Ensure tables exist
        if ensure_tables:
            logger.info("Ensuring all tables exist")
            create_all_tables(self.database)

        # Fetch and import records (use cache if available)
        try:
            if self.cache_manager:
                records = self.fetcher.fetch_with_cache(
                    self.cache_manager, data_spec, from_date, to_date, option
                )
            else:
                records = self.fetcher.fetch(data_spec, from_date, to_date, option)
            # Where the transaction breaks is decided here and nowhere else.
            # Committing inside DataImporter would make a later parser/import
            # rejection impossible to roll back.
            commit_per_chunk = option == SPLIT_SETUP_OPTION and auto_commit
            groups = (
                _chunks(records, SETUP_COMMIT_INTERVAL)
                if commit_per_chunk
                else iter([records])
            )

            import_totals: dict = {}
            fetch_failures_seen = 0
            for group in groups:
                begin_transaction = getattr(self.database, "begin_transaction", None)
                if begin_transaction is not None:
                    begin_transaction()

                import_stats = self.importer.import_records(group, auto_commit=False)
                _accumulate_stats(import_totals, import_stats)

                if commit_per_chunk:
                    # A chunk that saw a rejection -- by the importer, or by
                    # the fetcher/parser while the chunk was consumed -- is
                    # rolled back whole; the chunks committed before it stay
                    # committed. Fetch failures count lazily as the stream is
                    # consumed, so compare the cumulative count per chunk.
                    fetch_failures_total = int(
                        self.fetcher.get_statistics().get("records_failed", 0) or 0
                    )
                    chunk_fetch_failures = fetch_failures_total - fetch_failures_seen
                    fetch_failures_seen = fetch_failures_total
                    self._raise_if_rejected(
                        {
                            "records_failed": (
                                int(import_stats.get("records_failed", 0) or 0)
                                + chunk_fetch_failures
                            )
                        }
                    )
                    self.database.commit()

            # Combine statistics
            fetch_stats = self.fetcher.get_statistics()
            combined_stats = {
                **fetch_stats,
                **import_totals,
                "records_failed": (
                    int(fetch_stats.get("records_failed", 0) or 0)
                    + int(import_totals.get("records_failed", 0) or 0)
                ),
            }

            self._raise_if_rejected(combined_stats)

            if auto_commit and not commit_per_chunk:
                self.database.commit()

            logger.info("Batch processing completed", **combined_stats)

            return combined_stats

        except Exception as e:
            try:
                self.database.rollback()
            except Exception as rollback_error:
                logger.warning(
                    "Batch rollback failed",
                    error=str(rollback_error),
                )
            logger.error("Batch processing failed", error=str(e))
            raise

    @staticmethod
    def _raise_if_rejected(stats: dict) -> None:
        failed_records = int(stats.get("records_failed", 0) or 0)
        if failed_records:
            raise ImporterError(f"Import rejected {failed_records} record(s)")

    @staticmethod
    def _should_split_setup_range(
        data_spec: str, from_date: str, to_date: str, option: int
    ) -> bool:
        # セットアップ (option 3/4) の長期間要求は、終了ポイント時刻を許す
        # dataspec に限り年単位の境界付き JVOpen に分割する。fetch が公式の
        # 開始-終了 fromtime を送るため、各チャンクは自分の窓だけを取得し
        # テールを反復しない。終了時刻禁止 spec（DIFN 等、仕様書 p.18）は
        # fromtime を閉じられず、分割すると各チャンクが fromtime 以降の
        # 全データを返す O(n^2) の反復になるため、option を問わず単一
        # オープンのままにする。
        if option not in (3, 4):
            return False
        if not jvopen_supports_end_timestamp(data_spec):
            return False
        start = datetime.strptime(from_date, "%Y%m%d")
        end = datetime.strptime(to_date, "%Y%m%d")
        return (end - start).days > 370

    def _iter_year_chunks(self, from_date: str, to_date: str) -> Iterator[Tuple[str, str]]:
        start = datetime.strptime(from_date, "%Y%m%d")
        end = datetime.strptime(to_date, "%Y%m%d")
        year = start.year
        while year <= end.year:
            chunk_start = max(start, datetime(year, 1, 1))
            chunk_end = min(end, datetime(year, 12, 31))
            yield chunk_start.strftime("%Y%m%d"), chunk_end.strftime("%Y%m%d")
            year += 1

    def _process_split_setup_range(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        option: int,
        auto_commit: bool,
        ensure_tables: bool,
    ) -> dict:
        # 年チャンクは日付レベルで連続する (次チャンクの from = 前チャンクの
        # to + 1日)。fetch はセットアップの排他的開始点を「チャンク from の
        # 前日 23:59:59」に符号化するため、隣接チャンクは提供タイムスタンプ
        # 空間で「次チャンクの排他的開始点 = 直前チャンクの包含終了点」と
        # なり、秒単位まで正確に・隙間も重複もなく敷き詰められる
        # （開始は「より大きい」、終了は「まで」）。
        logger.info(
            "Splitting setup range into bounded yearly chunks",
            data_spec=data_spec,
            from_date=from_date,
            to_date=to_date,
            option=option,
        )
        if ensure_tables:
            create_all_tables(self.database)

        if option == SPLIT_SETUP_OPTION:
            # option=4: 各チャンクの内側の process_date_range がトランザク
            # ション境界を所有する（auto_commit 時は SETUP_COMMIT_INTERVAL
            # 毎にコミット、失敗したグループはチャンク内でロールバック）。
            # 外側でトランザクションを張らないことで所有権の曖昧さを避け、
            # コミット済みの先行チャンクは後続チャンクの失敗で失われない。
            # auto_commit=False の場合は従来どおり呼び出し元だけが唯一の
            # コミット境界を持つ（内側は begin のみ行いコミットしない）。
            #
            # 再実行の契約: キャッシュ有効時、完了したチャンクは fetch が
            # そのチャンク窓の complete マーカーを付けるため、同じ引数での
            # 再実行は同一分割を再導出し、完了済みチャンクをローカル
            # キャッシュから再生する（プロバイダ再取得なし・インポートは
            # 冪等upsert）。キャッシュ無効時は各チャンクの再ダウンロードに
            # なるが、いずれも境界付きでテールは反復しない。
            option4_stats: dict = {}
            for idx, (chunk_from, chunk_to) in enumerate(
                self._iter_year_chunks(from_date, to_date), start=1
            ):
                logger.info(
                    "Processing bounded setup chunk",
                    chunk_index=idx,
                    chunk_from=chunk_from,
                    chunk_to=chunk_to,
                    data_spec=data_spec,
                )
                chunk_stats = self.process_date_range(
                    data_spec=data_spec,
                    from_date=chunk_from,
                    to_date=chunk_to,
                    option=option,
                    auto_commit=auto_commit,
                    ensure_tables=False,
                )
                _accumulate_stats(option4_stats, chunk_stats)
            return option4_stats

        # option=3: 従来どおり全チャンクを単一トランザクションで所有し、
        # 全チャンク成功時のみ一括コミットする（部分的な耐久性を作らない）。
        combined_stats: dict = {}
        try:
            begin_transaction = getattr(self.database, "begin_transaction", None)
            if begin_transaction is not None:
                begin_transaction()

            for idx, (chunk_from, chunk_to) in enumerate(
                self._iter_year_chunks(from_date, to_date), start=1
            ):
                logger.info(
                    "Processing setup chunk",
                    chunk_index=idx,
                    chunk_from=chunk_from,
                    chunk_to=chunk_to,
                    data_spec=data_spec,
                )
                chunk_stats = self.process_date_range(
                    data_spec=data_spec,
                    from_date=chunk_from,
                    to_date=chunk_to,
                    option=option,
                    auto_commit=False,
                    ensure_tables=False,
                )
                _accumulate_stats(combined_stats, chunk_stats)

            if auto_commit:
                self.database.commit()
            return combined_stats
        except Exception:
            try:
                self.database.rollback()
            except Exception as rollback_error:
                logger.warning(
                    "Split setup rollback failed",
                    error=str(rollback_error),
                )
            raise

    def process_month(
        self,
        year: int,
        month: int,
        data_spec: str = "RACE",
        option: int = 1,
        auto_commit: bool = True,
    ) -> dict:
        """Process data for a specific month.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)
            data_spec: Data specification code
            auto_commit: Whether to auto-commit

        Returns:
            Dictionary with processing statistics

        Examples:
            >>> processor = BatchProcessor(database=db)
            >>> stats = processor.process_month(2024, 6, "RACE")
        """
        # Calculate date range
        start = datetime(year, month, 1)

        # Last day of month
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(days=1)

        from_date = start.strftime("%Y%m%d")
        to_date = end.strftime("%Y%m%d")

        logger.info(f"Processing month: {year}/{month:02d}")

        return self.process_date_range(data_spec, from_date, to_date, option=option, auto_commit=auto_commit)

    def process_year(
        self,
        year: int,
        data_spec: str = "RACE",
        option: int = 1,
        auto_commit: bool = True,
    ) -> dict:
        """Process data for a specific year.

        Args:
            year: Year (e.g., 2024)
            data_spec: Data specification code
            auto_commit: Whether to auto-commit

        Returns:
            Dictionary with processing statistics

        Examples:
            >>> processor = BatchProcessor(database=db)
            >>> stats = processor.process_year(2024, "RACE")
        """
        from_date = f"{year}0101"
        to_date = f"{year}1231"

        logger.info(f"Processing year: {year}")

        return self.process_date_range(data_spec, from_date, to_date, option=option, auto_commit=auto_commit)

    def process_multiple_specs(
        self,
        data_specs: List[str],
        from_date: str,
        to_date: str,
        auto_commit: bool = True,
    ) -> dict:
        """Process multiple data specifications.

        Args:
            data_specs: List of data specification codes
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD)
            auto_commit: Whether to auto-commit

        Returns:
            Dictionary mapping data_spec to statistics

        Examples:
            >>> processor = BatchProcessor(database=db)
            >>> specs = ["RACE", "DIFN"]
            >>> results = processor.process_multiple_specs(
            ...     specs, "20240601", "20240630"
            ... )
        """
        results = {}
        successful_specs = []
        failed_specs = []

        for data_spec in data_specs:
            logger.info(f"Processing data spec: {data_spec}")

            try:
                stats = self.process_date_range(
                    data_spec=data_spec,
                    from_date=from_date,
                    to_date=to_date,
                    auto_commit=auto_commit,
                    ensure_tables=False,  # Only check once
                )
                results[data_spec] = stats
                successful_specs.append(data_spec)

            except Exception as e:
                logger.error(
                    f"Failed to process {data_spec}",
                    data_spec=data_spec,
                    error=str(e),
                )
                results[data_spec] = {"error": str(e)}
                failed_specs.append(data_spec)

        # Add partial success summary
        total_specs = len(data_specs)
        success_count = len(successful_specs)
        failure_count = len(failed_specs)

        results["_summary"] = {
            "total_specs": total_specs,
            "successful": success_count,
            "failed": failure_count,
            "success_rate": f"{success_count}/{total_specs}",
            "successful_specs": successful_specs,
            "failed_specs": failed_specs,
        }

        # Log partial success summary
        if failure_count > 0:
            logger.warning(
                f"Partial success: {success_count}/{total_specs} specs completed successfully",
                successful=success_count,
                failed=failure_count,
                successful_specs=successful_specs,
                failed_specs=failed_specs,
            )
        else:
            logger.info(
                f"All specs completed successfully: {success_count}/{total_specs}",
                successful_specs=successful_specs,
            )

        return results

    def get_combined_statistics(self) -> dict:
        """Get combined statistics from fetcher and importer.

        Returns:
            Dictionary with combined statistics
        """
        return {
            **self.fetcher.get_statistics(),
            **self.importer.get_statistics(),
        }

    def reset_statistics(self):
        """Reset all statistics."""
        self.fetcher.reset_statistics()
        self.importer.reset_statistics()
