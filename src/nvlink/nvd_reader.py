"""NVD file reader - reads NV-Link data directly from NVD (ZIP) files.

NVD files are ZIP archives stored by UmaConn (地方競馬DATA) in:
  - Setup data: C:\\UmaConn\\chiho.k-ba\\data\\data\\YYYY\\
  - Cache data: C:\\UmaConn\\chiho.k-ba\\data\\cache\\YYYY\\

Each NVD file contains a single text file (e.g., "07.txt") with
Shift-JIS (CP932) encoded records, one per line (CRLF separated).

This reader bypasses the NVRead COM API, which can return -3 (file not found)
due to read-state management issues. Reading NVD files directly is more reliable.

File naming convention:
  {PREFIX}{DATE}{TIMESTAMP}.nvd
  e.g., RANV2026020720260207231018.nvd
        ^^^^                        prefix (record type)
            ^^^^^^^^                race date
                    ^^^^^^^^^^^^^^  file timestamp

Supported prefixes and record types:
  RANV -> RA (race info)
  SENV -> SE (entry info)
  HRNV -> HR (payouts)
  HANV -> HA (payouts, NAR-specific)
  H1NV -> H1 (vote counts)
  H6NV -> H6 (vote counts, trifecta)
  O1NV-O6NV -> O1-O6 (odds)
  OANV -> OA (odds, NAR-specific)
  WFNV -> WF (WIN5-like)
  BNWV -> BN (owner master)
  CHWV -> CH (trainer master)
  KSWV -> KS (jockey master)
  NCWV -> NC (track master)
"""

from __future__ import annotations

import zipfile
from collections.abc import Generator
from pathlib import Path

# Default UmaConn data paths
DEFAULT_DATA_DIR = Path(r"C:\UmaConn\chiho.k-ba\data\data")
DEFAULT_CACHE_DIR = Path(r"C:\UmaConn\chiho.k-ba\data\cache")

# NVD file prefix to record type mapping
PREFIX_TO_RECORD_TYPE = {
    "RANV": "RA",
    "SENV": "SE",
    "HRNV": "HR",
    "HANV": "HA",
    "H1NV": "H1",
    "H6NV": "H6",
    "O1NV": "O1",
    "O2NV": "O2",
    "O3NV": "O3",
    "O4NV": "O4",
    "O5NV": "O5",
    "O6NV": "O6",
    "OANV": "OA",
    "WFNV": "WF",
    "BNWV": "BN",
    "CHWV": "CH",
    "KSWV": "KS",
    "NCWV": "NC",
}

# Record type to NVD prefix mapping (reverse)
RECORD_TYPE_TO_PREFIX = {v: k for k, v in PREFIX_TO_RECORD_TYPE.items()}


def get_nvd_prefix(filename: str) -> str | None:
    """Extract NVD prefix from filename.

    Args:
        filename: NVD filename (e.g., "RANV2026020720260207231018.nvd")

    Returns:
        Prefix string (e.g., "RANV") or None if not recognized.
    """
    for prefix in PREFIX_TO_RECORD_TYPE:
        if filename.startswith(prefix):
            return prefix
    return None


def get_record_type(filename: str) -> str | None:
    """Get record type from NVD filename.

    Args:
        filename: NVD filename (e.g., "RANV2026020720260207231018.nvd")

    Returns:
        Record type (e.g., "RA") or None if not recognized.
    """
    prefix = get_nvd_prefix(filename)
    if prefix:
        return PREFIX_TO_RECORD_TYPE[prefix]
    return None


def read_nvd_file(filepath: Path) -> list[bytes]:
    """Read all records from a single NVD file.

    Args:
        filepath: Path to the NVD file.

    Returns:
        List of record data as bytes (CP932 encoded).

    Raises:
        FileNotFoundError: If file does not exist.
        zipfile.BadZipFile: If file is not a valid ZIP.
    """
    records = []
    with zipfile.ZipFile(filepath) as zf:
        for entry_name in zf.namelist():
            with zf.open(entry_name) as ef:
                content = ef.read()
                # Split by CRLF (standard NVD line separator)
                for line in content.split(b"\r\n"):
                    if line.strip():
                        records.append(line)
    return records


def list_nvd_files(
    record_types: list[str] | None = None,
    year: int | None = None,
    from_date: str | None = None,
    data_dir: Path | None = None,
    cache_dir: Path | None = None,
    use_cache: bool = True,
    use_data: bool = True,
) -> list[Path]:
    """List NVD files matching the given criteria.

    Args:
        record_types: Filter by record types (e.g., ["RA", "SE", "HR"]).
                     None means all types.
        year: Filter by year directory (e.g., 2026). None means all years.
        from_date: Only include files with race date >= this (YYYYMMDD format).
        data_dir: Override default data directory.
        cache_dir: Override default cache directory.
        use_cache: Include cache directory files.
        use_data: Include data directory files.

    Returns:
        Sorted list of NVD file paths.
    """
    data_dir = data_dir or DEFAULT_DATA_DIR
    cache_dir = cache_dir or DEFAULT_CACHE_DIR

    # Determine which prefixes to look for
    if record_types:
        prefixes = set()
        for rt in record_types:
            prefix = RECORD_TYPE_TO_PREFIX.get(rt)
            if prefix:
                prefixes.add(prefix)
    else:
        prefixes = set(PREFIX_TO_RECORD_TYPE.keys())

    files = []
    search_dirs = []
    if use_data and data_dir.exists():
        if year:
            d = data_dir / str(year)
            if d.exists():
                search_dirs.append(d)
        else:
            search_dirs.extend(
                d for d in sorted(data_dir.iterdir()) if d.is_dir()
            )
    if use_cache and cache_dir.exists():
        if year:
            d = cache_dir / str(year)
            if d.exists():
                search_dirs.append(d)
        else:
            search_dirs.extend(
                d for d in sorted(cache_dir.iterdir()) if d.is_dir()
            )

    for directory in search_dirs:
        for fp in sorted(directory.iterdir()):
            if fp.suffix.lower() != ".nvd":
                continue
            prefix = get_nvd_prefix(fp.name)
            if prefix and prefix in prefixes:
                # Check from_date filter
                if from_date and len(fp.name) >= 12:
                    # Extract race date from filename (after prefix, 8 digits)
                    file_date = fp.name[4:12]
                    if file_date < from_date:
                        continue
                files.append(fp)

    return files


def read_records(
    record_types: list[str] | None = None,
    year: int | None = None,
    from_date: str | None = None,
    data_dir: Path | None = None,
    cache_dir: Path | None = None,
    use_cache: bool = True,
    use_data: bool = False,
) -> Generator[tuple[str, bytes, str], None, None]:
    """Read records from NVD files.

    Yields tuples of (record_type, data_bytes, filename) similar to
    the NVLinkWrapper.nv_read() interface.

    Args:
        record_types: Filter by record types (e.g., ["RA", "SE"]).
        year: Filter by year.
        from_date: Only include files with date >= this (YYYYMMDD).
        data_dir: Override data directory.
        cache_dir: Override cache directory.
        use_cache: Include cache files (default: True).
        use_data: Include data/setup files (default: False, to avoid duplicates).

    Yields:
        (record_type, data_bytes, filename) tuples.
    """
    files = list_nvd_files(
        record_types=record_types,
        year=year,
        from_date=from_date,
        data_dir=data_dir,
        cache_dir=cache_dir,
        use_cache=use_cache,
        use_data=use_data,
    )

    for filepath in files:
        rec_type = get_record_type(filepath.name)
        if rec_type is None:
            continue
        try:
            records = read_nvd_file(filepath)
            for record in records:
                yield rec_type, record, filepath.name
        except (zipfile.BadZipFile, OSError):
            # Skip corrupted files
            continue
