"""S3 sync for local JV-Data cache.

Supports AWS S3 and S3-compatible storage (e.g., Cloudflare R2).
Credentials are loaded from encrypted storage via CredentialManager.

Usage::

    from src.cache.s3_sync import S3Syncer
    from src.cache.credentials import CredentialManager
    from pathlib import Path

    creds = CredentialManager().load(password="your-password")
    syncer = S3Syncer(cache_dir=Path("data/cache"), credentials=creds)

    syncer.upload()     # local → S3
    syncer.download()   # S3 → local
    syncer.sync()       # bidirectional
"""

import os
from pathlib import Path
from typing import Callable, Optional


class S3SyncError(Exception):
    pass


class S3Syncer:
    """Sync local cache files with S3 (or S3-compatible) storage.

    Syncs the contents of ``cache_dir/`` to/from ``s3://bucket/prefix/``.
    Comparison is done by file size; files that differ are uploaded/downloaded.
    Files that exist only on one side are transferred to the other.

    Args:
        cache_dir: Local cache root (e.g., ``data/cache``).
        credentials: Dict with S3 connection info:
            - ``endpoint_url`` (str): e.g. ``https://<id>.r2.cloudflarestorage.com``
              (omit for AWS S3)
            - ``aws_access_key_id`` (str)
            - ``aws_secret_access_key`` (str)
            - ``bucket_name`` (str)
            - ``region_name`` (str, optional, default ``auto`` for R2)
            - ``prefix`` (str, optional, default ``jrvltsql-cache``)
        on_progress: Optional callback(action, key, size_bytes) for each file.
    """

    def __init__(
        self,
        cache_dir: Path,
        credentials: dict,
        on_progress: Optional[Callable[[str, str, int], None]] = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.creds = credentials
        self.on_progress = on_progress
        self._client = None

    # ------------------------------------------------------------------
    # S3 client
    # ------------------------------------------------------------------

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise S3SyncError(
                    "boto3 is required for S3 sync.\n"
                    "Install: pip install boto3"
                )
            kwargs = {
                "aws_access_key_id": self.creds["aws_access_key_id"],
                "aws_secret_access_key": self.creds["aws_secret_access_key"],
                "region_name": self.creds.get("region_name", "auto"),
            }
            if "endpoint_url" in self.creds and self.creds["endpoint_url"]:
                kwargs["endpoint_url"] = self.creds["endpoint_url"]
            self._client = boto3.client("s3", **kwargs)
        return self._client

    @property
    def bucket(self) -> str:
        return self.creds["bucket_name"]

    @property
    def prefix(self) -> str:
        p = self.creds.get("prefix", "jrvltsql-cache").rstrip("/")
        return p

    def _s3_key(self, local_path: Path) -> str:
        rel = local_path.relative_to(self.cache_dir)
        return f"{self.prefix}/{rel.as_posix()}"

    def _local_path(self, s3_key: str) -> Path:
        rel = s3_key[len(self.prefix) + 1:]  # strip "prefix/"
        return self.cache_dir / rel.replace("/", os.sep)

    # ------------------------------------------------------------------
    # List helpers
    # ------------------------------------------------------------------

    def _list_local(self) -> dict[str, int]:
        """Return {relative_posix_path: size_bytes} for all cache files."""
        result = {}
        if not self.cache_dir.exists():
            return result
        for f in self.cache_dir.rglob("*"):
            if f.is_file() and (f.suffix == ".bin" or f.name == ".index.json"):
                rel = f.relative_to(self.cache_dir).as_posix()
                result[rel] = f.stat().st_size
        return result

    def _list_s3(self) -> dict[str, int]:
        """Return {relative_posix_path: size_bytes} for all S3 objects under prefix."""
        client = self._get_client()
        result = {}
        paginator = client.get_paginator("list_objects_v2")
        s3_prefix = self.prefix + "/"
        for page in paginator.paginate(Bucket=self.bucket, Prefix=s3_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                rel = key[len(s3_prefix):]  # strip prefix/
                if rel:
                    result[rel] = obj["Size"]
        return result

    # ------------------------------------------------------------------
    # Transfer helpers
    # ------------------------------------------------------------------

    def _upload_file(self, local_path: Path, s3_key: str):
        client = self._get_client()
        size = local_path.stat().st_size
        client.upload_file(str(local_path), self.bucket, s3_key)
        if self.on_progress:
            self.on_progress("upload", s3_key, size)

    def _download_file(self, s3_key: str, local_path: Path):
        client = self._get_client()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(self.bucket, s3_key, str(local_path))
        size = local_path.stat().st_size
        if self.on_progress:
            self.on_progress("download", s3_key, size)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(self, dry_run: bool = False) -> dict:
        """Upload local cache files to S3 (local → S3).

        Skips files where S3 already has the same size.

        Returns:
            {"uploaded": N, "skipped": N, "errors": N, "bytes": total}
        """
        local = self._list_local()
        s3 = self._list_s3()
        stats = {"uploaded": 0, "skipped": 0, "errors": 0, "bytes": 0}

        for rel, local_size in local.items():
            s3_key = f"{self.prefix}/{rel}"
            if s3.get(rel) == local_size:
                stats["skipped"] += 1
                continue
            local_path = self.cache_dir / rel.replace("/", os.sep)
            if dry_run:
                print(f"  [DRY] upload {rel} ({local_size:,} bytes)")
                stats["uploaded"] += 1
                stats["bytes"] += local_size
                continue
            try:
                self._upload_file(local_path, s3_key)
                stats["uploaded"] += 1
                stats["bytes"] += local_size
            except Exception as e:
                stats["errors"] += 1
                print(f"  [ERR] upload {rel}: {e}")

        return stats

    def download(self, dry_run: bool = False) -> dict:
        """Download S3 files to local cache (S3 → local).

        Skips files where local already has the same size.

        Returns:
            {"downloaded": N, "skipped": N, "errors": N, "bytes": total}
        """
        local = self._list_local()
        s3 = self._list_s3()
        stats = {"downloaded": 0, "skipped": 0, "errors": 0, "bytes": 0}

        for rel, s3_size in s3.items():
            if local.get(rel) == s3_size:
                stats["skipped"] += 1
                continue
            s3_key = f"{self.prefix}/{rel}"
            local_path = self.cache_dir / rel.replace("/", os.sep)
            if dry_run:
                print(f"  [DRY] download {rel} ({s3_size:,} bytes)")
                stats["downloaded"] += 1
                stats["bytes"] += s3_size
                continue
            try:
                self._download_file(s3_key, local_path)
                stats["downloaded"] += 1
                stats["bytes"] += s3_size
            except Exception as e:
                stats["errors"] += 1
                print(f"  [ERR] download {rel}: {e}")

        return stats

    def sync(self, dry_run: bool = False) -> dict:
        """Bidirectional sync: upload new local files, download new S3 files.

        Files existing only locally → uploaded to S3.
        Files existing only in S3 → downloaded to local.
        Files with same size on both sides → skipped.
        Files with different sizes → local version wins (uploaded).

        Returns:
            Combined stats dict.
        """
        up = self.upload(dry_run=dry_run)
        down = self.download(dry_run=dry_run)
        return {
            "uploaded": up["uploaded"],
            "downloaded": down["downloaded"],
            "skipped": up["skipped"] + down["skipped"],
            "errors": up["errors"] + down["errors"],
            "bytes_up": up["bytes"],
            "bytes_down": down["bytes"],
        }

    def test_connection(self) -> bool:
        """Test S3 connection. Returns True if successful."""
        try:
            client = self._get_client()
            client.head_bucket(Bucket=self.bucket)
            return True
        except Exception as e:
            raise S3SyncError(f"S3 connection failed: {e}")
