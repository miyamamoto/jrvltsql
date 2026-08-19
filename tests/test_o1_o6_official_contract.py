"""O1-O6（オッズ1〜6）公式契約テスト。

一次資料は公式仕様書 JV-Data Ver.4.9.0.1 の「７．オッズ1（単複枠）」〜
「１２．オッズ6（3連単）」節。以下の公式値を固定する。

- レコード長: O1 962 / O2 2042 / O3 2654 / O4 4031 / O5 12293 / O6 83285
- データ区分: 1:中間 2:前日売最終 3:最終 4:確定 5:確定(月曜) 9:レース中止
  0:該当レコード削除
- 発売フラグ: 0:発売なし 1:発売前取消 3:発売後取消 7:発売あり
- オッズ部の繰返し: O1 単勝28×8・複勝28×12・枠連36×9、O2 153×13、O3 153×17、
  O4 306×13、O5 816×15、O6 4896×17
- オッズ・人気順の提供値には数値以外に "000000":無投票、"------":発売前取消、
  "******":発売後取消、空白:登録なし がある（桁数はレコードごとに異なる）
- 票数合計は各11バイト（返還分票数を含む）
"""

import os
from pathlib import Path
from typing import Mapping
from uuid import uuid4

import pytest

from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.realtime.updater import RealtimeUpdater
from src.parser.o1_parser import O1Parser
from src.parser.o2_parser import O2Parser
from src.parser.o3_parser import O3Parser
from src.parser.o4_parser import O4Parser
from src.parser.o5_parser import O5Parser
from src.parser.o6_parser import O6Parser

OFFICIAL_DATA_KUBUN = ("1", "2", "3", "4", "5", "9")
OFFICIAL_SALE_FLAGS = ("0", "1", "3", "7")


class _Layout:
    """One official odds record layout (O2-O6 share the same shape)."""

    def __init__(
        self,
        parser_class: type,
        *,
        flag_field: str,
        entries: int,
        combination_width: int,
        odds_fields: tuple[tuple[str, int], ...],
        favourite_width: int,
    ) -> None:
        self.parser_class = parser_class
        self.record_type = parser_class.RECORD_TYPE
        self.length = parser_class.RECORD_LENGTH
        self.flag_field = flag_field
        self.entries = entries
        self.combination_width = combination_width
        self.odds_fields = odds_fields
        self.favourite_width = favourite_width
        self.item_width = (
            combination_width + sum(width for _, width in odds_fields) + favourite_width
        )

    @property
    def total_offset(self) -> int:
        return 40 + self.entries * self.item_width

    def combination(self, index: int) -> bytes:
        """An official ascending combination number for slot ``index``."""

        if self.combination_width == 4:
            return f"01{index + 2:02d}".encode("ascii")
        return f"0102{index + 3:02d}".encode("ascii")

    def raw(
        self,
        *,
        data_kubun: str = "1",
        sale_flag: bytes = b"7",
        filled: int = 3,
        odds: Mapping[str, bytes] | None = None,
        favourite: bytes | None = None,
        total: bytes = b"00000123456",
    ) -> bytes:
        data = bytearray(b" " * self.length)
        data[0:2] = self.record_type.encode("ascii")
        data[2:3] = data_kubun.encode("ascii")
        data[3:11] = b"20260101"
        data[11:15] = b"2026"
        data[15:19] = b"0101"
        data[19:21] = b"05"
        data[21:23] = b"01"
        data[23:25] = b"01"
        data[25:27] = b"11"
        data[27:35] = b"01011200"
        data[35:37] = b"18"
        data[37:39] = b"18"
        data[39:40] = sale_flag
        favourite_value = favourite if favourite is not None else b"0" * self.favourite_width
        for index in range(filled):
            position = 40 + index * self.item_width
            data[position:position + self.combination_width] = self.combination(index)
            position += self.combination_width
            for field_name, width in self.odds_fields:
                provided = (odds or {}).get(field_name)
                value = provided if provided is not None else b"0" * (width - 1) + b"1"
                assert len(value) == width
                data[position:position + width] = value
                position += width
            data[position:position + self.favourite_width] = favourite_value
        data[self.total_offset:self.total_offset + 11] = total
        data[self.length - 2:self.length] = b"\r\n"
        raw = bytes(data)
        assert len(raw) == self.length
        return raw

    def rows(self, **kwargs) -> list[dict]:
        parsed = self.parser_class().parse(self.raw(**kwargs))
        assert parsed is not None
        return parsed


LAYOUTS = {
    "O2": _Layout(
        O2Parser,
        flag_field="UmarenFlag",
        entries=153,
        combination_width=4,
        odds_fields=(("Odds", 6),),
        favourite_width=3,
    ),
    "O3": _Layout(
        O3Parser,
        flag_field="WideFlag",
        entries=153,
        combination_width=4,
        odds_fields=(("OddsLow", 5), ("OddsHigh", 5)),
        favourite_width=3,
    ),
    "O4": _Layout(
        O4Parser,
        flag_field="UmatanFlag",
        entries=306,
        combination_width=4,
        odds_fields=(("Odds", 6),),
        favourite_width=3,
    ),
    "O5": _Layout(
        O5Parser,
        flag_field="SanrenpukuFlag",
        entries=816,
        combination_width=6,
        odds_fields=(("Odds", 6),),
        favourite_width=3,
    ),
    "O6": _Layout(
        O6Parser,
        flag_field="SanrentanFlag",
        entries=4896,
        combination_width=6,
        odds_fields=(("Odds", 7),),
        favourite_width=4,
    ),
}

ALL_RECORD_TYPES = tuple(LAYOUTS)


def test_official_record_lengths() -> None:
    assert O1Parser.RECORD_LENGTH == 962
    assert O2Parser.RECORD_LENGTH == 2042
    assert O3Parser.RECORD_LENGTH == 2654
    assert O4Parser.RECORD_LENGTH == 4031
    assert O5Parser.RECORD_LENGTH == 12293
    assert O6Parser.RECORD_LENGTH == 83285


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_official_array_geometry_matches_the_specification(record_type: str) -> None:
    """繰返し回数と1件あたりのバイト数が公式のオッズ部と一致する。"""

    layout = LAYOUTS[record_type]
    # 40 バイトのヘッダ＋発売フラグの後にオッズ部が始まり、票数合計11＋CRLF2で終わる。
    assert layout.total_offset + 11 + 2 == layout.length


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
@pytest.mark.parametrize("data_kubun", OFFICIAL_DATA_KUBUN)
def test_official_statuses_are_parsed(record_type: str, data_kubun: str) -> None:
    rows = LAYOUTS[record_type].rows(data_kubun=data_kubun)
    assert rows[0]["DataKubun"] == data_kubun


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_unofficial_status_is_rejected(record_type: str) -> None:
    layout = LAYOUTS[record_type]
    assert layout.parser_class().parse(layout.raw(data_kubun="8")) is None


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
@pytest.mark.parametrize("sale_flag", OFFICIAL_SALE_FLAGS)
def test_official_sale_flags_are_parsed(record_type: str, sale_flag: str) -> None:
    layout = LAYOUTS[record_type]
    rows = layout.rows(sale_flag=sale_flag.encode("ascii"))
    assert rows[0][layout.flag_field] == sale_flag


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_no_vote_combinations_are_preserved(record_type: str) -> None:
    """公式の "000000":無投票 も提供値なので、行を捨ててはならない。"""

    layout = LAYOUTS[record_type]
    zero_odds = {name: b"0" * width for name, width in layout.odds_fields}
    rows = layout.rows(odds=zero_odds, favourite=b" " * layout.favourite_width)
    combinations = [row["Kumi"] for row in rows]
    assert combinations == [
        layout.combination(index).decode("ascii") for index in range(3)
    ]
    for row in rows:
        for name, width in layout.odds_fields:
            assert row[name] == "0" * width


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
@pytest.mark.parametrize("marker", ("-", "*"))
def test_cancellation_markers_are_preserved(record_type: str, marker: str) -> None:
    """発売前取消 '---...' と発売後取消 '***...' は公式の提供値として保持する。"""

    layout = LAYOUTS[record_type]
    rows = layout.rows(
        odds={name: (marker * width).encode("ascii") for name, width in layout.odds_fields},
        favourite=(marker * layout.favourite_width).encode("ascii"),
    )
    assert len(rows) == 3
    for row in rows:
        for name, width in layout.odds_fields:
            assert row[name] == marker * width
        assert row["Ninki"] == marker * layout.favourite_width


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_unregistered_slots_are_not_stored(record_type: str) -> None:
    """登録なし（空白）のスロットは組番を持たないので行にしない。"""

    layout = LAYOUTS[record_type]
    rows = layout.rows(filled=2)
    assert [row["Kumi"] for row in rows] == [
        layout.combination(index).decode("ascii") for index in range(2)
    ]


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_records_without_a_combination_keep_the_official_total(record_type: str) -> None:
    """組合せが1件も無い snapshot でも公式の票数合計を失わない。"""

    layout = LAYOUTS[record_type]
    rows = layout.rows(data_kubun="9", filled=0, sale_flag=b"1")
    assert len(rows) == 1
    assert rows[0]["Kumi"] == layout.parser_class.TOTAL_COMBINATION
    assert rows[0]["Vote"] == "00000123456"


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_official_total_is_preserved(record_type: str) -> None:
    layout = LAYOUTS[record_type]
    rows = layout.rows(total=b"00098765432")
    assert {row["Vote"] for row in rows} == {"00098765432"}


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_combinations_keep_the_official_ascending_order(record_type: str) -> None:
    layout = LAYOUTS[record_type]
    rows = layout.rows(filled=5)
    assert [row["Kumi"] for row in rows] == sorted(row["Kumi"] for row in rows)


def _valid_row(record_type: str) -> dict:
    return LAYOUTS[record_type].rows()[0]


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_valid_rows_pass_validation(record_type: str) -> None:
    layout = LAYOUTS[record_type]
    layout.parser_class.validate_current_fields(_valid_row(record_type))


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
@pytest.mark.parametrize(
    "overrides",
    (
        pytest.param({"DataKubun": "8"}, id="unofficial-status"),
        pytest.param({"MakeDate": "20260230"}, id="impossible-make-date"),
        pytest.param({"MakeDate": "2026010"}, id="short-make-date"),
        pytest.param({"MonthDay": "0230"}, id="impossible-race-day"),
        pytest.param({"JyoCD": "5"}, id="short-venue"),
        pytest.param({"RaceNum": "1"}, id="short-race-number"),
        pytest.param({"TorokuTosu": "1"}, id="short-registered-count"),
        pytest.param({"SyussoTosu": "x8"}, id="non-numeric-starting-count"),
        pytest.param({"Kumi": "01"}, id="short-combination"),
        pytest.param({"Ninki": "1"}, id="short-favourite-order"),
        pytest.param({"Ninki": "**"}, id="short-cancel-marker"),
        pytest.param({"Vote": "123"}, id="short-total"),
    ),
)
def test_domain_violations_are_rejected(record_type: str, overrides: dict) -> None:
    layout = LAYOUTS[record_type]
    row = {**_valid_row(record_type), **overrides}
    with pytest.raises(ValueError):
        layout.parser_class.validate_current_fields(row)


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_unofficial_sale_flag_is_rejected(record_type: str) -> None:
    layout = LAYOUTS[record_type]
    row = {**_valid_row(record_type), layout.flag_field: "9"}
    with pytest.raises(ValueError):
        layout.parser_class.validate_current_fields(row)


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_short_odds_values_are_rejected(record_type: str) -> None:
    layout = LAYOUTS[record_type]
    for name, width in layout.odds_fields:
        row = {**_valid_row(record_type), name: "0" * (width - 1)}
        with pytest.raises(ValueError):
            layout.parser_class.validate_current_fields(row)


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_erase_rows_only_need_the_official_key(record_type: str) -> None:
    """データ区分0（該当レコード削除）は本文を持たない。"""

    layout = LAYOUTS[record_type]
    row = {
        "RecordSpec": record_type,
        "DataKubun": "0",
        "MakeDate": "20260101",
        "Year": "2026",
        "MonthDay": "0101",
        "JyoCD": "05",
        "Kaiji": "01",
        "Nichiji": "01",
        "RaceNum": "11",
    }
    layout.parser_class.validate_current_fields(row)


def _o1_raw(
    *,
    data_kubun: str = "1",
    tan_odds: bytes = b"0123",
    tan_favourite: bytes = b"01",
    fuku_low: bytes = b"0011",
    fuku_high: bytes = b"0022",
    fuku_favourite: bytes = b"01",
    wakuren_odds: bytes = b"00123",
    wakuren_favourite: bytes = b"02",
    horses: int = 3,
    brackets: int = 3,
    totals: bytes = b"00000123456" * 3,
) -> bytes:
    data = bytearray(b" " * O1Parser.RECORD_LENGTH)
    data[0:2] = b"O1"
    data[2:3] = data_kubun.encode("ascii")
    data[3:11] = b"20260101"
    data[11:15] = b"2026"
    data[15:19] = b"0101"
    data[19:21] = b"05"
    data[21:23] = b"01"
    data[23:25] = b"01"
    data[25:27] = b"11"
    data[27:35] = b"01011200"
    data[35:37] = b"18"
    data[37:39] = b"18"
    data[39:40] = b"7"
    data[40:41] = b"7"
    data[41:42] = b"7"
    data[42:43] = b"3"
    for index in range(horses):
        position = 43 + index * 8
        data[position:position + 2] = f"{index + 1:02d}".encode("ascii")
        data[position + 2:position + 6] = tan_odds
        data[position + 6:position + 8] = tan_favourite
        position = 267 + index * 12
        data[position:position + 2] = f"{index + 1:02d}".encode("ascii")
        data[position + 2:position + 6] = fuku_low
        data[position + 6:position + 10] = fuku_high
        data[position + 10:position + 12] = fuku_favourite
    for index in range(brackets):
        position = 603 + index * 9
        data[position:position + 2] = f"{index + 1}{index + 2}".encode("ascii")
        data[position + 2:position + 7] = wakuren_odds
        data[position + 7:position + 9] = wakuren_favourite
    data[927:960] = totals
    data[960:962] = b"\r\n"
    raw = bytes(data)
    assert len(raw) == O1Parser.RECORD_LENGTH
    return raw


def _o1_rows(**kwargs) -> list[dict]:
    parsed = O1Parser().parse(_o1_raw(**kwargs))
    assert parsed is not None
    return parsed


def test_o1_official_arrays_are_expanded() -> None:
    rows = _o1_rows()
    horses = [row for row in rows if row["Kumi"] == "00"]
    brackets = [row for row in rows if row["Kumi"] != "00"]
    assert [row["Umaban"] for row in horses] == ["01", "02", "03"]
    assert [row["Kumi"] for row in brackets] == ["12", "23", "34"]
    assert horses[0]["TanOdds"] == "0123"
    assert horses[0]["FukuOddsLow"] == "0011"
    assert horses[0]["FukuOddsHigh"] == "0022"
    assert brackets[0]["WakurenOdds"] == "00123"


def test_o1_no_vote_bracket_odds_are_preserved() -> None:
    """枠連の "00000":無投票 も提供値なので行を捨ててはならない。"""

    rows = _o1_rows(wakuren_odds=b"00000", wakuren_favourite=b"  ")
    brackets = [row for row in rows if row["Kumi"] != "00"]
    assert [row["Kumi"] for row in brackets] == ["12", "23", "34"]
    assert brackets[0]["WakurenOdds"] == "00000"


def test_o1_no_vote_win_odds_are_preserved() -> None:
    rows = _o1_rows(tan_odds=b"0000", tan_favourite=b"  ")
    horses = [row for row in rows if row["Kumi"] == "00"]
    assert [row["TanOdds"] for row in horses] == ["0000"] * 3


@pytest.mark.parametrize("marker", ("-", "*"))
def test_o1_cancellation_markers_are_preserved(marker: str) -> None:
    rows = _o1_rows(
        tan_odds=(marker * 4).encode("ascii"),
        tan_favourite=(marker * 2).encode("ascii"),
        fuku_low=(marker * 4).encode("ascii"),
        fuku_high=(marker * 4).encode("ascii"),
        fuku_favourite=(marker * 2).encode("ascii"),
        wakuren_odds=(marker * 5).encode("ascii"),
        wakuren_favourite=(marker * 2).encode("ascii"),
    )
    horses = [row for row in rows if row["Kumi"] == "00"]
    brackets = [row for row in rows if row["Kumi"] != "00"]
    assert horses[0]["TanOdds"] == marker * 4
    assert horses[0]["TanNinki"] == marker * 2
    assert horses[0]["FukuOddsLow"] == marker * 4
    assert horses[0]["FukuNinki"] == marker * 2
    assert brackets[0]["WakurenOdds"] == marker * 5
    assert brackets[0]["WakurenNinki"] == marker * 2


def test_o1_official_totals_are_preserved() -> None:
    rows = _o1_rows(totals=b"00000000001" + b"00000000022" + b"00000000333")
    assert rows[0]["TanVote"] == "00000000001"
    assert rows[0]["FukuVote"] == "00000000022"
    assert rows[0]["WakurenVote"] == "00000000333"


def test_o1_records_without_any_odds_keep_the_official_totals() -> None:
    rows = _o1_rows(data_kubun="9", horses=0, brackets=0)
    assert len(rows) == 1
    assert rows[0]["Umaban"] == O1Parser.BRACKET_ROW_HORSE_NUMBER
    assert rows[0]["Kumi"] == O1Parser.TOTAL_COMBINATION
    assert rows[0]["TanVote"] == "00000123456"


def test_o1_valid_rows_pass_validation() -> None:
    for row in _o1_rows():
        O1Parser.validate_current_fields(row)


@pytest.mark.parametrize(
    "overrides",
    (
        pytest.param({"DataKubun": "8"}, id="unofficial-status"),
        pytest.param({"MakeDate": "20260230"}, id="impossible-make-date"),
        pytest.param({"MonthDay": "0230"}, id="impossible-race-day"),
        pytest.param({"TanFlag": "9"}, id="unofficial-win-flag"),
        pytest.param({"FukuFlag": "9"}, id="unofficial-place-flag"),
        pytest.param({"WakurenFlag": "9"}, id="unofficial-bracket-flag"),
        pytest.param({"FukuChakubaraiKey": "1"}, id="unofficial-place-payout-key"),
        pytest.param({"TanOdds": "012"}, id="short-win-odds"),
        pytest.param({"TanNinki": "1"}, id="short-win-favourite"),
        pytest.param({"FukuOddsHigh": "01234"}, id="long-place-odds"),
        pytest.param({"TanVote": "1"}, id="short-win-total"),
    ),
)
def test_o1_domain_violations_are_rejected(overrides: dict) -> None:
    row = {**_o1_rows()[0], **overrides}
    with pytest.raises(ValueError):
        O1Parser.validate_current_fields(row)


def test_o1_official_place_payout_keys_are_accepted() -> None:
    for key in ("0", "2", "3"):
        row = {**_o1_rows()[0], "FukuChakubaraiKey": key}
        O1Parser.validate_current_fields(row)


NATIVE_TABLES = {
    "O1": "NL_O1",
    "O2": "NL_O2",
    "O3": "NL_O3",
    "O4": "NL_O4",
    "O5": "NL_O5",
    "O6": "NL_O6",
}
STANDARD_TABLES = {
    "O1": ("ODDS_TANPUKUWAKU_HEAD", "ODDS_TANPUKU", "ODDS_WAKU"),
    "O2": ("ODDS_UMAREN_HEAD", "ODDS_UMAREN"),
    "O3": ("ODDS_WIDE_HEAD", "ODDS_WIDE"),
    "O4": ("ODDS_UMATAN_HEAD", "ODDS_UMATAN"),
    "O5": ("ODDS_SANREN_HEAD", "ODDS_SANREN"),
    "O6": ("ODDS_SANRENTAN_HEAD", "ODDS_SANRENTAN"),
}
IMPORTERS = (DataImporter, OptimizedDataImporter)


def totals_only_rows(record_type: str) -> list[dict]:
    """One official snapshot whose odds part carries no combination."""

    if record_type == "O1":
        rows = _o1_rows(data_kubun="9", horses=0, brackets=0)
    else:
        rows = LAYOUTS[record_type].rows(data_kubun="9", filled=0, sale_flag=b"1")
    assert len(rows) == 1
    return [dict(rows[0])]


def _canonical(table_name: str) -> str:
    return SCHEMAS.get(table_name) or JRAVAN_SCHEMAS[table_name]


def _create(database, tables) -> None:
    for table_name in tables:
        database.execute(_canonical(table_name))
    database.commit()


@pytest.mark.parametrize("record_type", ("O1", *ALL_RECORD_TYPES))
@pytest.mark.parametrize("importer_class", IMPORTERS)
def test_sqlite_native_storage_keeps_the_totals_only_snapshot(
    tmp_path: Path,
    record_type: str,
    importer_class: type,
) -> None:
    table_name = NATIVE_TABLES[record_type]
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"native-{record_type}-{importer_class.__name__}.db")}
    )
    with database:
        _create(database, (table_name,))
        stats = importer_class(database, batch_size=1).import_records(
            iter(totals_only_rows(record_type))
        )
        assert stats["records_failed"] == 0
        assert stats["records_imported"] == 1
        stored = database.fetch_all(f"SELECT Kumi FROM {table_name}")
        assert stored == [{"Kumi": O1Parser.TOTAL_COMBINATION}]


@pytest.mark.parametrize("record_type", ("O1", *ALL_RECORD_TYPES))
@pytest.mark.parametrize("importer_class", IMPORTERS)
def test_sqlite_standard_storage_keeps_totals_without_a_child_row(
    tmp_path: Path,
    record_type: str,
    importer_class: type,
) -> None:
    """合計行は公式の子表に該当する組合せを持たないので header だけを残す。"""

    tables = STANDARD_TABLES[record_type]
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"standard-{record_type}-{importer_class.__name__}.db")}
    )
    with database:
        _create(database, tables)
        importer = importer_class(database, batch_size=1, use_jravan_schema=True)
        stats = importer.import_records(iter(totals_only_rows(record_type)))
        assert stats["records_failed"] == 0
        owner, *children = tables
        assert database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {owner}")["cnt"] == 1
        for child in children:
            assert database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {child}")["cnt"] == 0


@pytest.mark.parametrize("record_type", ("O1", *ALL_RECORD_TYPES))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("auto-commit", "caller-owned"))
def test_sqlite_single_record_path_keeps_the_totals_only_snapshot(
    tmp_path: Path,
    record_type: str,
    auto_commit: bool,
) -> None:
    table_name = NATIVE_TABLES[record_type]
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"single-{record_type}-{auto_commit}.db")}
    )
    with database:
        _create(database, (table_name,))
        importer = DataImporter(database)
        for row in totals_only_rows(record_type):
            assert importer.import_single_record(row, auto_commit=auto_commit) is True
        if not auto_commit:
            database.commit()
        assert database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")["cnt"] == 1


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_odds_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            try:
                database.rollback()
            except Exception:
                pass
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


@pytest.mark.parametrize("record_type", ("O1", *ALL_RECORD_TYPES))
@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_postgresql_keeps_the_totals_only_snapshot(
    postgresql_db,
    record_type: str,
    use_standard: bool,
) -> None:
    tables = STANDARD_TABLES[record_type] if use_standard else (NATIVE_TABLES[record_type],)
    for table_name in tables:
        postgresql_db.execute(_canonical(table_name))
    postgresql_db.commit()
    importer = DataImporter(postgresql_db, batch_size=1, use_jravan_schema=use_standard)
    stats = importer.import_records(iter(totals_only_rows(record_type)))
    postgresql_db.commit()

    assert stats["records_failed"] == 0
    owner, *children = tables
    assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {owner}")["cnt"] == 1
    for child in children:
        assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {child}")["cnt"] == 0


def live_rows(record_type: str) -> list[dict]:
    """One official snapshot that sells three combinations."""

    if record_type == "O1":
        return [dict(row) for row in _o1_rows(data_kubun="4", horses=3, brackets=3)]
    return [dict(row) for row in LAYOUTS[record_type].rows(data_kubun="4", filled=3)]


def erase_rows(record_type: str) -> list[dict]:
    """The official status-0 command carries the race key and no body."""

    if record_type == "O1":
        return [dict(row) for row in _o1_rows(data_kubun="0", horses=0, brackets=0)]
    return [
        dict(row)
        for row in LAYOUTS[record_type].rows(data_kubun="0", filled=0, sale_flag=b"0")
    ]


@pytest.mark.parametrize("record_type", ("O1", *ALL_RECORD_TYPES))
@pytest.mark.parametrize("importer_class", IMPORTERS)
@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_sqlite_status_zero_erases_the_snapshot_without_a_tombstone(
    tmp_path: Path,
    record_type: str,
    importer_class: type,
    use_standard: bool,
) -> None:
    """公式の削除指示は合計行 sentinel を残さず対象レースを物理削除する。"""

    tables = STANDARD_TABLES[record_type] if use_standard else (NATIVE_TABLES[record_type],)
    database = SQLiteDatabase(
        {
            "path": str(
                tmp_path
                / f"erase-{record_type}-{importer_class.__name__}-{use_standard}.db"
            )
        }
    )
    with database:
        _create(database, tables)
        importer = importer_class(database, batch_size=1, use_jravan_schema=use_standard)
        assert importer.import_records(iter(live_rows(record_type)))["records_failed"] == 0
        assert database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {tables[-1]}")["cnt"] > 0

        assert importer.import_records(iter(erase_rows(record_type)))["records_failed"] == 0

        for table_name in tables:
            assert (
                database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")["cnt"] == 0
            )


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_realtime_keeps_every_official_no_vote_combination(
    tmp_path: Path,
    record_type: str,
) -> None:
    """速報経路でも無投票（`0` の並び）の組合せを捨てない。"""

    layout = LAYOUTS[record_type]
    table_name = f"RT_{record_type}"
    assert RealtimeUpdater.RECORD_TYPE_TABLE[record_type] == table_name
    database = SQLiteDatabase({"path": str(tmp_path / f"realtime-{record_type}.db")})
    with database:
        _create(database, (table_name,))
        updater = RealtimeUpdater(database)
        raw = layout.raw(
            data_kubun="1",
            filled=3,
            odds={name: b"0" * width for name, width in layout.odds_fields},
            favourite=b"-" * layout.favourite_width,
        )
        results = updater.process_record(raw)
        assert results and all(result["success"] for result in results)
        assert database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")["cnt"] == 3


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
@pytest.mark.parametrize("data_kubun", OFFICIAL_DATA_KUBUN)
@pytest.mark.parametrize(
    "announced",
    (
        pytest.param(b"00000000", id="official-initial-zeros"),
        pytest.param(b"        ", id="blank"),
    ),
)
def test_unset_announced_time_is_accepted(
    record_type: str, data_kubun: str, announced: bytes
) -> None:
    """発表月日時分 is set for 中間 odds only; final odds carry the initial value.

    Live JV-Link RACE data sends the zero-filled form for every final O1-O6
    snapshot, so rejecting it rejects the whole feed.
    """

    layout = LAYOUTS[record_type]
    raw = bytearray(layout.raw(data_kubun=data_kubun))
    raw[27:35] = announced
    rows = layout.parser_class().parse(bytes(raw))
    assert rows
    for row in rows:
        layout.parser_class.validate_current_fields(row)


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
@pytest.mark.parametrize(
    "announced",
    (
        pytest.param(b"01321200", id="impossible-day"),
        pytest.param(b"01012500", id="impossible-hour"),
        pytest.param(b"0101120x", id="non-digit"),
    ),
)
def test_malformed_announced_time_is_still_rejected(
    record_type: str, announced: bytes
) -> None:
    layout = LAYOUTS[record_type]
    raw = bytearray(layout.raw())
    raw[27:35] = announced
    rows = layout.parser_class().parse(bytes(raw))
    assert rows
    with pytest.raises(ValueError):
        for row in rows:
            layout.parser_class.validate_current_fields(row)
