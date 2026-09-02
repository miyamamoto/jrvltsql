"""``fetch`` は複数 dataspec を 1 JV-Link セッションで指定順に処理する。

公式仕様は「dataspec を複数指定すると対象ファイル数が多い場合に JVRead が遅く
なる」を既知障害として挙げ、回避策に「dataspec を個別に指定」を挙げている。
したがって連結して 1 回の JVOpen にはせず、**JVOpen は dataspec ごと・セッション
だけ 1 本**にする。並べ替えは呼び出し側の持ち物なので jltsql では行わない。
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import NamedTuple
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.main import (
    FETCH_NOTE_DATE_FIELDS,
    FETCH_NOTE_TO_CLIENT_FILTER,
    FETCH_NOTE_TO_RANGE_CHUNKED,
    FETCH_NOTE_TO_SINGLE_OPEN,
    cli,
)
from src.fetcher.base import FetcherError

EXAMPLE_CONFIG = Path(__file__).resolve().parents[1] / "config" / "config.yaml.example"

STATS = {
    "records_fetched": 10,
    "records_parsed": 9,
    "records_imported": 8,
    "records_failed": 1,
    "batches_processed": 2,
}

# option=1 のガードレール注記そのものは #290 の対象外なので、文言は定数から組む。
# ここで転記すると、注記を直しただけでこのテストが無関係な差分で落ちる。
# RACE は範囲形式を使う dataspec なので、刻む側の注記が出る（#246）。
_OPTION1_NOTES = "\n".join(
    f"Note: {note}"
    for note in (
        FETCH_NOTE_TO_CLIENT_FILTER,
        FETCH_NOTE_TO_RANGE_CHUNKED,
        FETCH_NOTE_DATE_FIELDS,
    )
)

# 単一 --spec の出力は #290 の前後で一字一句変わってはいけない。rich の折り返しを
# 固定するため COLUMNS を固定した上で丸ごと突き合わせる。
SINGLE_SPEC_GOLDEN = f"""\
Fetching historical data from JRA-VAN DataLab...

  Data source: JRA (中央競馬)
  Date range: 20260820 -- 20260821
  Data spec:  RACE
  Option:     1 (通常データ)
  Database:   sqlite
{_OPTION1_NOTES}

Processing data...

[OK] Fetch complete!

Statistics:
  Fetched:  10
  Parsed:   9
  Imported: 8
  Failed:   1
  Batches:  2
"""


def _runner():
    # rich の折り返し幅を固定して出力を決定的にする。
    return CliRunner(env={"COLUMNS": "200", "TERM": "dumb"})


class Invocation(NamedTuple):
    """``fetch`` の 1 回の実行と、その途中で使われたモック。"""

    result: object  # click の Result（exit_code / output）
    batch_processor: MagicMock  # BatchProcessor クラスのモック（生成回数を見る）
    processor: MagicMock  # その戻り値（process_date_range の呼ばれ方を見る）
    create_database: MagicMock  # DB 生成に到達したかを見る


def _invoke(specs, *, option=1, side_effect=None, progress=False) -> Invocation:
    """``fetch`` を実行し、結果と関与したモックを返す。"""
    processor = MagicMock()
    if side_effect is not None:
        processor.process_date_range.side_effect = side_effect
    else:
        processor.process_date_range.return_value = STATS

    factory = MagicMock(return_value=processor)
    create_database = MagicMock(return_value=MagicMock())

    args = ["--config", "config.yaml", "fetch", "--from", "20260820", "--to", "20260821"]
    for spec in specs:
        args += ["--spec", spec]
    args += ["--option", str(option), "--db", "sqlite", "--no-cache"]
    args.append("--progress" if progress else "--no-progress")

    runner = _runner()
    previous_cwd = Path.cwd()
    with TemporaryDirectory() as temp_dir:
        try:
            os.chdir(temp_dir)
            Path("config.yaml").write_text(
                EXAMPLE_CONFIG.read_text(encoding="utf-8"), encoding="utf-8"
            )
            with (
                patch("src.importer.batch.BatchProcessor", factory),
                patch("src.database.create_database_from_config", create_database),
                patch("src.database.schema.create_all_tables"),
            ):
                result = runner.invoke(cli, args)
        finally:
            os.chdir(previous_cwd)
    return Invocation(result, factory, processor, create_database)


def _processed_specs(processor):
    return [call.kwargs["data_spec"] for call in processor.process_date_range.call_args_list]


def test_single_spec_output_is_unchanged():
    run = _invoke(["RACE"])

    assert run.result.exit_code == 0, run.result.output
    assert run.result.output == SINGLE_SPEC_GOLDEN
    assert _processed_specs(run.processor) == ["RACE"]


def test_guardrail_notes_cover_the_whole_run_without_repeating():
    """注記は実走に 1 回。刻める spec と刻めない spec が混ざれば両方 1 回ずつ出る。

    RACE は暦年で刻み、DIFN は start-only（#246）。dataspec ごとに注記を
    出し直すと、同じ文が dataspec の数だけ並ぶ。
    """
    run = _invoke(["RACE", "DIFN"])

    assert run.result.exit_code == 0, run.result.output
    # rich は 1 行が幅を超えると折り返すので、改行を畳んでから数える。
    output = run.result.output.replace("\n", "")
    assert output.count(FETCH_NOTE_TO_RANGE_CHUNKED) == 1
    assert output.count(FETCH_NOTE_TO_SINGLE_OPEN) == 1
    assert output.count(FETCH_NOTE_DATE_FIELDS) == 1
    assert _processed_specs(run.processor) == ["RACE", "DIFN"]


def test_one_jvlink_session_serves_every_spec():
    """BatchProcessor は 1 個だけ。spec ごとに作り直すと #287 の効果が消える。

    ``BatchProcessor.__init__`` が ``HistoricalFetcher`` を 1 個作り、その生成時に
    JVInit が走る。spec ごとに作り直すと option=4 の取得元ダイアログが spec 数ぶん
    出てしまい、このチケットの前提そのものが崩れる。
    """
    run = _invoke(["DIFN", "WOOD", "SLOP"])

    assert run.result.exit_code == 0, run.result.output
    assert run.batch_processor.call_count == 1
    assert run.processor.process_date_range.call_count == 3


def test_specs_are_processed_in_the_order_given():
    """並べ替えは keibaai_cloud の持ち物（ADR-0025）。指定順をそのまま守る。"""
    run = _invoke(["WOOD", "BLDN", "DIFN", "RACE"])

    assert run.result.exit_code == 0, run.result.output
    assert _processed_specs(run.processor) == ["WOOD", "BLDN", "DIFN", "RACE"]


def test_each_spec_repeats_the_header_and_statistics_block():
    """出力の口は増やさない。既存ブロックを dataspec ごとに繰り返すだけ。"""
    run = _invoke(["DIFN", "WOOD", "SLOP"])

    assert run.result.exit_code == 0, run.result.output
    assert run.result.output.count("[OK] Fetch complete!") == 3
    assert run.result.output.count("Statistics:") == 3
    for spec in ("DIFN", "WOOD", "SLOP"):
        assert f"  Data spec:  {spec}" in run.result.output


def test_the_date_range_and_option_are_the_same_for_every_spec():
    run = _invoke(["DIFN", "RACE"], option=4)

    assert run.result.exit_code == 0, run.result.output
    for call in run.processor.process_date_range.call_args_list:
        assert call.kwargs["from_date"] == "20260820"
        assert call.kwargs["to_date"] == "20260821"
        assert call.kwargs["option"] == 4


def test_a_failing_spec_stops_the_run_before_the_next_one():
    """ADR-0023「止めて人に見せる」。以降を実行せず、終了コードで分かる。"""
    run = _invoke(
        ["DIFN", "WOOD", "SLOP"],
        side_effect=[STATS, FetcherError("Historical fetch failed: boom"), STATS],
    )

    assert run.result.exit_code != 0
    assert _processed_specs(run.processor) == ["DIFN", "WOOD"]
    assert "boom" in run.result.output


def test_setup_dialog_cancel_stops_the_whole_run():
    """取得元の選択が拒否された以上、後続も初回の選択を引き継げない。"""
    run = _invoke(
        ["DIFN", "WOOD"],
        option=4,
        side_effect=[
            FetcherError(
                "Historical fetch failed: JVOpen setup dialog was cancelled"
            ),
            STATS,
        ],
    )

    assert run.result.exit_code != 0
    assert _processed_specs(run.processor) == ["DIFN"]
    assert "cancel" in run.result.output


def test_a_retired_spec_anywhere_is_rejected_before_the_database():
    # DIFF は廃止済み（DIFN が後継）。2 番目に置いても DB より先に落ちる。
    run = _invoke(["RACE", "DIFF"])

    assert run.result.exit_code == 1, run.result.output
    run.create_database.assert_not_called()
    run.batch_processor.assert_not_called()


def test_an_invalid_option_combination_anywhere_is_rejected_before_the_database():
    # DIFN は option=2（今週データ）では取得できない。
    run = _invoke(["RACE", "DIFN"], option=2)

    assert run.result.exit_code == 1, run.result.output
    assert "DIFN" in run.result.output
    run.create_database.assert_not_called()
    run.batch_processor.assert_not_called()


@pytest.mark.parametrize("specs", [["RACE", "RACE"], ["DIFN", "RACE", "DIFN"]])
def test_a_repeated_spec_is_processed_once_per_occurrence(specs):
    """重複の除去も呼び出し側の判断。jltsql は指定された回数だけ回す。"""
    run = _invoke(specs)

    assert run.result.exit_code == 0, run.result.output
    assert _processed_specs(run.processor) == specs


def test_the_run_summary_uses_a_plural_label_so_it_is_not_read_as_a_spec_name():
    """前置きの一覧行が dataspec 見出しと同じラベルだと、driver が spec 名として読む。

    単数形 ``Data spec:`` は「いま処理している dataspec」だけを指すようにし、
    実走全体の一覧は複数形にして分ける。
    """
    run = _invoke(["DIFN", "WOOD", "SLOP"])

    assert run.result.exit_code == 0, run.result.output
    assert "  Data specs: DIFN, WOOD, SLOP" in run.result.output
    # 単数形は dataspec ごとの見出しとしてだけ、spec 数ぶん出る。
    assert run.result.output.count("  Data spec:  ") == 3


def test_a_single_spec_keeps_the_singular_label():
    run = _invoke(["RACE"])

    assert "  Data spec:  RACE" in run.result.output
    assert "Data specs:" not in run.result.output


def test_the_retired_reason_wins_over_the_option_combination_error():
    """廃止済み種別の理由を option 組み合わせより先に返す順序は複数指定でも保つ。

    DIFF は廃止済み、DIFN は option=2 では取得できない。両方に引っかかる要求で
    先に出るのは廃止済みの理由でなければならない（単一指定のときと同じ）。
    """
    run = _invoke(["DIFN", "DIFF"], option=2)

    assert run.result.exit_code == 1, run.result.output
    assert "DIFF" in run.result.output
    assert "option=2 では取得できません" not in run.result.output
    run.create_database.assert_not_called()


def test_progress_display_owns_the_per_spec_header_when_it_is_enabled():
    """progress 有効時は JVLinkProgressDisplay が dataspec 見出しを出す。

    CLI 側でも出すと 1 dataspec につき見出しが 2 つ並ぶので、そちらへ任せる。
    """
    run = _invoke(["DIFN", "WOOD"], progress=True)

    assert run.result.exit_code == 0, run.result.output
    assert "  Data spec:  DIFN" not in run.result.output
    assert "  Data specs: DIFN, WOOD" in run.result.output
    # Statistics ブロックは progress の有無によらず dataspec ごとに出る。
    assert run.result.output.count("[OK] Fetch complete!") == 2
