"""NVD file reader for UmaConn (地方競馬DATA) local data files.

NVD files are ZIP archives stored in:
  C:\\UmaConn\\chiho.k-ba\\data\\{data,cache}\\YYYY\\

Each NVD file contains a single text file (e.g., '01.txt') with
CRLF-delimited records. Currently only H1 (票数) records are stored
in NVD files. Other record types (RA, SE, HR, HA, etc.) are only
available via NV-Link live COM stream.

File naming convention:
  {RecordType}NV{YYYYMMDD}{Timestamp}.nvd
  Example: H1NV2026010120260101223011.nvd
"""

import os
import zipfile
from pathlib import Path
from typing import Iterator, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default UmaConn data directories
DEFAULT_DATA_DIRS = [
    Path(r"C:\UmaConn\chiho.k-ba\data\data"),
    Path(r"C:\UmaConn\chiho.k-ba\data\cache"),
]


class NVDReader:
    """Reader for NVD (NV-Link Data) ZIP files.

    Reads and parses records from local NVD files without requiring
    the NV-Link COM API.

    Attributes:
        data_dirs: List of directories to search for NVD files.
        encoding: Character encoding for record data (default: cp932).
    """

    def __init__(
        self,
        data_dirs: Optional[list] = None,
        encoding: str = "cp932",
    ):
        self.data_dirs = data_dirs or DEFAULT_DATA_DIRS
        self.encoding = encoding

    def find_nvd_files(
        self,
        record_type: Optional[str] = None,
        year: Optional[int] = None,
    ) -> list:
        """Find NVD files matching criteria.

        Args:
            record_type: Filter by record type prefix (e.g., 'H1')
            year: Filter by year directory

        Returns:
            List of Path objects for matching NVD files, sorted by name.
        """
        files = []
        for data_dir in self.data_dirs:
            if not data_dir.exists():
                continue

            if year:
                search_dirs = [data_dir / str(year)]
            else:
                search_dirs = [d for d in data_dir.iterdir() if d.is_dir()]

            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue
                for nvd_file in search_dir.glob("*.nvd"):
                    if record_type and not nvd_file.name.startswith(record_type):
                        continue
                    files.append(nvd_file)

        return sorted(files)

    def read_records(
        self,
        nvd_path: Path,
    ) -> Iterator[str]:
        """Read records from a single NVD file.

        Args:
            nvd_path: Path to the NVD file.

        Yields:
            Individual record strings (decoded from cp932).
        """
        try:
            with zipfile.ZipFile(nvd_path, "r") as zf:
                for name in zf.namelist():
                    data = zf.read(name)
                    text = data.decode(self.encoding, errors="replace")
                    for line in text.split("\r\n"):
                        if line.strip():
                            yield line
        except zipfile.BadZipFile:
            logger.error("Invalid NVD file (not a ZIP)", path=str(nvd_path))
        except Exception as e:
            logger.error("Failed to read NVD file", path=str(nvd_path), error=str(e))

    def read_all_records(
        self,
        record_type: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Iterator[str]:
        """Read all records from matching NVD files.

        Args:
            record_type: Filter by record type (e.g., 'H1')
            year: Filter by year

        Yields:
            Individual record strings.
        """
        files = self.find_nvd_files(record_type=record_type, year=year)
        logger.info(
            "Reading NVD files",
            count=len(files),
            record_type=record_type,
            year=year,
        )

        for nvd_file in files:
            yield from self.read_records(nvd_file)

    def get_stats(
        self,
        year: Optional[int] = None,
    ) -> dict:
        """Get statistics about available NVD files.

        Args:
            year: Filter by year

        Returns:
            Dictionary with file counts and record type breakdown.
        """
        stats = {"total_files": 0, "total_size_mb": 0.0, "record_types": {}}
        files = self.find_nvd_files(year=year)

        for f in files:
            stats["total_files"] += 1
            stats["total_size_mb"] += f.stat().st_size / (1024 * 1024)

            # Extract record type from filename
            name = f.name
            if "NV" in name:
                rt = name.split("NV")[0]
                stats["record_types"][rt] = stats["record_types"].get(rt, 0) + 1

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats
