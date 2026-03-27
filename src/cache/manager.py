"""Local file cache manager for JV-Data raw records."""

import json
import struct
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator, Optional


class CacheManager:
    """Local file cache for JV-Data raw binary records.

    Stores raw JV-Data bytes locally to avoid repeated JV-Link API calls.
    Thread-safe for concurrent RT_ writes.

    Directory structure:
        cache_dir/nl/{SPEC}/{YYYYMMDD}.bin  -- 蓄積系
        cache_dir/rt/{SPEC_CODE}/{YYYYMMDD}.bin  -- 速報系

    Binary format: [uint32-BE length][raw bytes] per record (length-prefixed)
    """

    HEADER = struct.Struct(">I")  # 4-byte big-endian uint32

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self._locks: dict = {}
        self._locks_lock = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    # --- NL_ helpers ---
    def _nl_dir(self, spec: str) -> Path:
        d = self.cache_dir / "nl" / spec.upper()
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _nl_path(self, spec: str, date_str: str) -> Path:
        return self._nl_dir(spec) / f"{date_str}.bin"

    def _index_path(self, spec: str) -> Path:
        return self._nl_dir(spec) / ".index.json"

    def _load_index(self, path: Path) -> dict:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_index(self, path: Path, index: dict):
        path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- NL_ public API ---
    def has_nl(self, spec: str, date_str: str) -> bool:
        """Return True if complete NL cache exists for this spec+date."""
        return self._load_index(self._index_path(spec)).get(date_str, {}).get("complete", False)

    def has_nl_range(self, spec: str, from_date: str, to_date: str) -> bool:
        """Return True if ALL dates in range are fully cached."""
        d = _parse_date(from_date)
        end = _parse_date(to_date)
        index = self._load_index(self._index_path(spec))
        while d <= end:
            if not index.get(d.strftime("%Y%m%d"), {}).get("complete", False):
                return False
            d += timedelta(days=1)
        return True

    def write_nl_record(self, spec: str, date_str: str, raw: bytes) -> None:
        """Append one raw record to NL cache (thread-safe)."""
        path = self._nl_path(spec, date_str)
        with self._lock_for(f"nl:{spec}:{date_str}"):
            with open(path, "ab") as f:
                f.write(self.HEADER.pack(len(raw)))
                f.write(raw)

    def mark_nl_complete(self, spec: str, date_str: str):
        """Mark date as fully cached in NL index."""
        idx_path = self._index_path(spec)
        with self._lock_for(f"idx:{spec}"):
            index = self._load_index(idx_path)
            bin_path = self._nl_path(spec, date_str)
            size = bin_path.stat().st_size if bin_path.exists() else 0
            count = self._count_records(bin_path) if bin_path.exists() else 0
            index[date_str] = {
                "complete": True,
                "count": count,
                "size": size,
                "mtime": _now_iso(),
            }
            self._save_index(idx_path, index)

    def read_nl(self, spec: str, from_date: str, to_date: str) -> Iterator[bytes]:
        """Yield raw record bytes from NL cache for date range."""
        d = _parse_date(from_date)
        end = _parse_date(to_date)
        while d <= end:
            path = self._nl_path(spec, d.strftime("%Y%m%d"))
            if path.exists():
                yield from self._read_bin(path)
            d += timedelta(days=1)

    # --- RT_ public API ---
    def _rt_dir(self, spec_code: str) -> Path:
        d = self.cache_dir / "rt" / spec_code
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _rt_path(self, spec_code: str, date_str: str) -> Path:
        return self._rt_dir(spec_code) / f"{date_str}.bin"

    def write_rt_record(self, spec_code: str, date_str: str, raw: bytes) -> None:
        """Append one raw record to RT cache (thread-safe)."""
        path = self._rt_path(spec_code, date_str)
        with self._lock_for(f"rt:{spec_code}:{date_str}"):
            with open(path, "ab") as f:
                f.write(self.HEADER.pack(len(raw)))
                f.write(raw)

    def read_rt(self, spec_code: str, date_str: str) -> Iterator[bytes]:
        """Yield raw record bytes from RT cache."""
        path = self._rt_path(spec_code, date_str)
        if path.exists():
            yield from self._read_bin(path)

    # --- Binary I/O ---
    def _read_bin(self, path: Path) -> Iterator[bytes]:
        hs = self.HEADER.size
        try:
            with open(path, "rb") as f:
                while True:
                    hdr = f.read(hs)
                    if len(hdr) < hs:
                        break
                    n = self.HEADER.unpack(hdr)[0]
                    data = f.read(n)
                    if len(data) < n:
                        break
                    yield data
        except OSError:
            return

    def _count_records(self, path: Path) -> int:
        return sum(1 for _ in self._read_bin(path))

    # --- Info / Maintenance ---
    def info(self) -> dict:
        """Return cache statistics dict."""
        result = {"nl": {}, "rt": {}, "total_size_bytes": 0}

        nl_base = self.cache_dir / "nl"
        if nl_base.exists():
            for spec_dir in sorted(p for p in nl_base.iterdir() if p.is_dir()):
                spec = spec_dir.name
                idx = self._load_index(spec_dir / ".index.json")
                dates = sorted(idx.keys())
                bins = list(spec_dir.glob("*.bin"))
                sz = sum(b.stat().st_size for b in bins)
                result["nl"][spec] = {
                    "cached_dates": len(dates),
                    "complete_dates": sum(1 for v in idx.values() if v.get("complete")),
                    "date_range": f"{dates[0]}..{dates[-1]}" if dates else "(empty)",
                    "size_bytes": sz,
                }
                result["total_size_bytes"] += sz

        rt_base = self.cache_dir / "rt"
        if rt_base.exists():
            for spec_dir in sorted(p for p in rt_base.iterdir() if p.is_dir()):
                spec = spec_dir.name
                bins = list(spec_dir.glob("*.bin"))
                sz = sum(b.stat().st_size for b in bins)
                dates = sorted(b.stem for b in bins)
                result["rt"][spec] = {
                    "cached_dates": len(dates),
                    "date_range": f"{dates[0]}..{dates[-1]}" if dates else "(empty)",
                    "size_bytes": sz,
                }
                result["total_size_bytes"] += sz

        return result

    def clear(self, spec: Optional[str] = None, date_str: Optional[str] = None, rt: bool = False) -> int:
        """Delete cache files. Returns number of deleted files."""
        deleted = 0
        base = self.cache_dir / ("rt" if rt else "nl")
        if not base.exists():
            return 0
        dirs = [base / spec.upper()] if spec else [p for p in base.iterdir() if p.is_dir()]
        for d in dirs:
            if not d.is_dir():
                continue
            if date_str:
                f = d / f"{date_str}.bin"
                if f.exists():
                    f.unlink()
                    deleted += 1
                idx_path = d / ".index.json"
                if idx_path.exists():
                    idx = self._load_index(idx_path)
                    idx.pop(date_str, None)
                    self._save_index(idx_path, idx)
            else:
                for f in d.glob("*.bin"):
                    f.unlink()
                    deleted += 1
                idx_path = d / ".index.json"
                if idx_path.exists():
                    idx_path.unlink()
        return deleted


def _parse_date(date_str: str) -> date:
    from datetime import datetime
    return datetime.strptime(date_str, "%Y%m%d").date()


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat()
