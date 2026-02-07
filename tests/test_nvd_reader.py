"""Tests for NVD file reader."""

import zipfile
from pathlib import Path

import pytest

from src.nvlink.nvd_reader import (
    PREFIX_TO_RECORD_TYPE,
    RECORD_TYPE_TO_PREFIX,
    get_nvd_prefix,
    get_record_type,
    list_nvd_files,
    read_nvd_file,
    read_records,
)


class TestGetNvdPrefix:
    """Tests for get_nvd_prefix."""

    def test_ra_prefix(self):
        assert get_nvd_prefix("RANV2026020720260207231018.nvd") == "RANV"

    def test_se_prefix(self):
        assert get_nvd_prefix("SENV2026020720260207231018.nvd") == "SENV"

    def test_h1_prefix(self):
        assert get_nvd_prefix("H1NV2026020720260207231020.nvd") == "H1NV"

    def test_bn_prefix(self):
        assert get_nvd_prefix("BNWV2026020720260207231021.nvd") == "BNWV"

    def test_oa_prefix(self):
        assert get_nvd_prefix("OANV2026020620260206231020.nvd") == "OANV"

    def test_unknown_prefix(self):
        assert get_nvd_prefix("XXNV2026020720260207231018.nvd") is None

    def test_rtd_file(self):
        assert get_nvd_prefix("0B1520260207.rtd") is None


class TestGetRecordType:
    """Tests for get_record_type."""

    def test_ra_record(self):
        assert get_record_type("RANV2026020720260207231018.nvd") == "RA"

    def test_se_record(self):
        assert get_record_type("SENV2026020720260207231018.nvd") == "SE"

    def test_ha_record(self):
        assert get_record_type("HANV2026020620260206231021.nvd") == "HA"

    def test_o6_record(self):
        assert get_record_type("O6NV2026020720260207231019.nvd") == "O6"

    def test_unknown(self):
        assert get_record_type("unknown.nvd") is None


class TestPrefixMappings:
    """Tests for prefix/record type mappings."""

    def test_all_prefixes_have_record_types(self):
        assert len(PREFIX_TO_RECORD_TYPE) == 18

    def test_reverse_mapping(self):
        for prefix, rt in PREFIX_TO_RECORD_TYPE.items():
            assert RECORD_TYPE_TO_PREFIX[rt] == prefix

    def test_expected_record_types(self):
        expected = {"RA", "SE", "HR", "HA", "H1", "H6", "O1", "O2", "O3",
                    "O4", "O5", "O6", "OA", "WF", "BN", "CH", "KS", "NC"}
        assert set(PREFIX_TO_RECORD_TYPE.values()) == expected


class TestReadNvdFile:
    """Tests for read_nvd_file."""

    def test_read_simple_nvd(self, tmp_path):
        """Test reading a simple NVD file."""
        nvd_path = tmp_path / "RANV20260207.nvd"
        with zipfile.ZipFile(nvd_path, "w") as zf:
            content = "RA7line1data\r\nRA7line2data\r\n"
            zf.writestr("07.txt", content.encode("cp932"))

        records = read_nvd_file(nvd_path)
        assert len(records) == 2
        assert records[0] == b"RA7line1data"
        assert records[1] == b"RA7line2data"

    def test_read_empty_lines_skipped(self, tmp_path):
        """Test that empty lines are skipped."""
        nvd_path = tmp_path / "H1NV20260207.nvd"
        with zipfile.ZipFile(nvd_path, "w") as zf:
            content = "H1data1\r\n\r\nH1data2\r\n"
            zf.writestr("07.txt", content.encode("cp932"))

        records = read_nvd_file(nvd_path)
        assert len(records) == 2

    def test_read_japanese_content(self, tmp_path):
        """Test reading Shift-JIS encoded Japanese content."""
        nvd_path = tmp_path / "RANV20260207.nvd"
        with zipfile.ZipFile(nvd_path, "w") as zf:
            content = "RAテストレース名\r\n"
            zf.writestr("07.txt", content.encode("cp932"))

        records = read_nvd_file(nvd_path)
        assert len(records) == 1
        decoded = records[0].decode("cp932")
        assert "テストレース名" in decoded

    def test_file_not_found(self, tmp_path):
        """Test FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            read_nvd_file(tmp_path / "nonexistent.nvd")

    def test_bad_zip(self, tmp_path):
        """Test BadZipFile for invalid ZIP."""
        bad_file = tmp_path / "bad.nvd"
        bad_file.write_text("not a zip")
        with pytest.raises(zipfile.BadZipFile):
            read_nvd_file(bad_file)


class TestListNvdFiles:
    """Tests for list_nvd_files."""

    def _create_nvd(self, directory: Path, name: str):
        """Helper to create a dummy NVD file."""
        fp = directory / name
        with zipfile.ZipFile(fp, "w") as zf:
            zf.writestr("data.txt", b"test")

    def test_list_all_files(self, tmp_path):
        """Test listing all NVD files."""
        cache = tmp_path / "cache" / "2026"
        cache.mkdir(parents=True)
        self._create_nvd(cache, "RANV2026020720260207231018.nvd")
        self._create_nvd(cache, "SENV2026020720260207231018.nvd")
        self._create_nvd(cache, "H1NV2026020720260207231020.nvd")

        files = list_nvd_files(cache_dir=tmp_path / "cache", use_data=False)
        assert len(files) == 3

    def test_filter_by_record_type(self, tmp_path):
        """Test filtering by record type."""
        cache = tmp_path / "cache" / "2026"
        cache.mkdir(parents=True)
        self._create_nvd(cache, "RANV2026020720260207231018.nvd")
        self._create_nvd(cache, "SENV2026020720260207231018.nvd")
        self._create_nvd(cache, "H1NV2026020720260207231020.nvd")

        files = list_nvd_files(
            record_types=["RA"],
            cache_dir=tmp_path / "cache",
            use_data=False,
        )
        assert len(files) == 1
        assert "RANV" in files[0].name

    def test_filter_by_year(self, tmp_path):
        """Test filtering by year."""
        for year in ["2025", "2026"]:
            d = tmp_path / "cache" / year
            d.mkdir(parents=True)
            self._create_nvd(d, f"RANV{year}0101{year}0101231018.nvd")

        files = list_nvd_files(
            year=2026,
            cache_dir=tmp_path / "cache",
            use_data=False,
        )
        assert len(files) == 1
        assert "2026" in files[0].name

    def test_filter_by_from_date(self, tmp_path):
        """Test filtering by from_date."""
        cache = tmp_path / "cache" / "2026"
        cache.mkdir(parents=True)
        self._create_nvd(cache, "RANV2026010120260101231018.nvd")
        self._create_nvd(cache, "RANV2026020720260207231018.nvd")

        files = list_nvd_files(
            from_date="20260201",
            cache_dir=tmp_path / "cache",
            use_data=False,
        )
        assert len(files) == 1
        assert "20260207" in files[0].name

    def test_nonexistent_directory(self, tmp_path):
        """Test with nonexistent directories."""
        files = list_nvd_files(
            data_dir=tmp_path / "nodata",
            cache_dir=tmp_path / "nocache",
        )
        assert len(files) == 0


class TestReadRecords:
    """Tests for read_records generator."""

    def test_read_records(self, tmp_path):
        """Test reading records from NVD files."""
        cache = tmp_path / "cache" / "2026"
        cache.mkdir(parents=True)

        nvd_path = cache / "RANV2026020720260207231018.nvd"
        with zipfile.ZipFile(nvd_path, "w") as zf:
            content = "RArecord1\r\nRArecord2\r\n"
            zf.writestr("07.txt", content.encode("cp932"))

        results = list(read_records(
            cache_dir=tmp_path / "cache",
            use_data=False,
        ))
        assert len(results) == 2
        assert results[0][0] == "RA"  # record_type
        assert results[0][1] == b"RArecord1"  # data
        assert "RANV" in results[0][2]  # filename

    def test_read_multiple_types(self, tmp_path):
        """Test reading multiple record types."""
        cache = tmp_path / "cache" / "2026"
        cache.mkdir(parents=True)

        for prefix, content in [
            ("RANV", "RAdata\r\n"),
            ("SENV", "SEdata1\r\nSEdata2\r\n"),
        ]:
            nvd_path = cache / f"{prefix}2026020720260207231018.nvd"
            with zipfile.ZipFile(nvd_path, "w") as zf:
                zf.writestr("07.txt", content.encode("cp932"))

        results = list(read_records(
            cache_dir=tmp_path / "cache",
            use_data=False,
        ))
        assert len(results) == 3
        types = [r[0] for r in results]
        assert types.count("RA") == 1
        assert types.count("SE") == 2

    def test_corrupted_file_skipped(self, tmp_path):
        """Test that corrupted NVD files are skipped."""
        cache = tmp_path / "cache" / "2026"
        cache.mkdir(parents=True)

        # Create a valid NVD
        valid = cache / "RANV2026020720260207231018.nvd"
        with zipfile.ZipFile(valid, "w") as zf:
            zf.writestr("07.txt", "RAdata\r\n".encode("cp932"))

        # Create a corrupted NVD
        bad = cache / "SENV2026020720260207231018.nvd"
        bad.write_text("not a zip")

        results = list(read_records(
            cache_dir=tmp_path / "cache",
            use_data=False,
        ))
        assert len(results) == 1
        assert results[0][0] == "RA"
