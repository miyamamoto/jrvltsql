"""Unit tests for NVD file reader."""

import tempfile
import zipfile
from pathlib import Path

import pytest

from src.nvlink.nvd_reader import NVDReader


class TestNVDReader:
    """NVDReader tests."""

    def _create_nvd(self, tmp_dir: Path, filename: str, records: list) -> Path:
        """Create a test NVD file (ZIP with records)."""
        nvd_path = tmp_dir / filename
        content = "\r\n".join(records) + "\r\n"
        with zipfile.ZipFile(nvd_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("01.txt", content.encode("cp932"))
        return nvd_path

    def test_find_nvd_files(self, tmp_path):
        """Test finding NVD files."""
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        self._create_nvd(year_dir, "H1NV20260101.nvd", ["H1record1"])
        self._create_nvd(year_dir, "H1NV20260102.nvd", ["H1record2"])

        reader = NVDReader(data_dirs=[tmp_path])
        files = reader.find_nvd_files()
        assert len(files) == 2

    def test_find_nvd_files_by_type(self, tmp_path):
        """Test filtering by record type."""
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        self._create_nvd(year_dir, "H1NV20260101.nvd", ["H1data"])
        self._create_nvd(year_dir, "RENV20260101.nvd", ["REdata"])

        reader = NVDReader(data_dirs=[tmp_path])
        files = reader.find_nvd_files(record_type="H1")
        assert len(files) == 1
        assert "H1" in files[0].name

    def test_find_nvd_files_by_year(self, tmp_path):
        """Test filtering by year."""
        for year in ["2025", "2026"]:
            d = tmp_path / year
            d.mkdir()
            self._create_nvd(d, f"H1NV{year}0101.nvd", [f"H1{year}"])

        reader = NVDReader(data_dirs=[tmp_path])
        files = reader.find_nvd_files(year=2026)
        assert len(files) == 1

    def test_read_records(self, tmp_path):
        """Test reading records from NVD file."""
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        records = ["H1record_line1", "H1record_line2", "H1record_line3"]
        nvd = self._create_nvd(year_dir, "H1NV20260101.nvd", records)

        reader = NVDReader(data_dirs=[tmp_path])
        result = list(reader.read_records(nvd))
        assert len(result) == 3
        assert result[0] == "H1record_line1"

    def test_read_all_records(self, tmp_path):
        """Test reading all records across files."""
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        self._create_nvd(year_dir, "H1NV20260101.nvd", ["rec1", "rec2"])
        self._create_nvd(year_dir, "H1NV20260102.nvd", ["rec3"])

        reader = NVDReader(data_dirs=[tmp_path])
        result = list(reader.read_all_records())
        assert len(result) == 3

    def test_get_stats(self, tmp_path):
        """Test statistics."""
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        self._create_nvd(year_dir, "H1NV20260101.nvd", ["H1data"])
        self._create_nvd(year_dir, "H1NV20260102.nvd", ["H1data2"])

        reader = NVDReader(data_dirs=[tmp_path])
        stats = reader.get_stats()
        assert stats["total_files"] == 2
        assert stats["record_types"]["H1"] == 2

    def test_invalid_nvd_file(self, tmp_path):
        """Test handling of invalid (non-ZIP) file."""
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        bad_file = year_dir / "H1NV20260101.nvd"
        bad_file.write_text("not a zip file")

        reader = NVDReader(data_dirs=[tmp_path])
        result = list(reader.read_records(bad_file))
        assert result == []

    def test_empty_data_dir(self, tmp_path):
        """Test with non-existent data directory."""
        reader = NVDReader(data_dirs=[tmp_path / "nonexistent"])
        files = reader.find_nvd_files()
        assert files == []

    def test_japanese_encoding(self, tmp_path):
        """Test cp932 encoding for Japanese records."""
        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        # Create file with Japanese content
        nvd_path = year_dir / "H1NV20260101.nvd"
        content = "H1テストデータ\r\n"
        with zipfile.ZipFile(nvd_path, "w") as zf:
            zf.writestr("01.txt", content.encode("cp932"))

        reader = NVDReader(data_dirs=[tmp_path])
        result = list(reader.read_records(nvd_path))
        assert len(result) == 1
        assert "テスト" in result[0]
