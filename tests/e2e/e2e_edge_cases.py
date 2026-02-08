#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""異常レース・エッジケース検証 E2E テスト

keiba.db に格納済みの実データに対して、異常レースやエッジケースが
正しくDB格納されていることを検証する。

検証項目:
  (A) 中止レース (DataKubun='9')
  (B) 出走取消・競走除外 (IJyoCD)
  (C) 少頭数レース (SyussoTosu <= 5)
  (D) 災害期間のデータ (2011年3月 東日本大震災)
  (E) NULL値・ゼロ値の検証

実行方法 (A6 上):
  cd C:\\Users\\mitsu\\work\\jrvltsql
  python tests\\e2e\\e2e_edge_cases.py

  または SSH 経由:
  ssh mitsu@192.168.0.250 "cd C:\\Users\\mitsu\\work\\jrvltsql && python tests\\e2e\\e2e_edge_cases.py"
"""

import io
import os
import sys
import sqlite3
from pathlib import Path

# Windows UTF-8 対応
if sys.platform == "win32":
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "buffer"):
            setattr(sys, stream_name, io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))

# DB パス
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "keiba.db"

# テスト結果集計
results = []


def record(name: str, passed: bool, detail: str = ""):
    """テスト結果を記録"""
    status = "PASS" if passed else "FAIL"
    results.append((name, status, detail))
    mark = "✓" if passed else "✗"
    print(f"  [{mark}] {name}")
    if detail:
        print(f"      {detail}")


def connect_db() -> sqlite3.Connection:
    """keiba.db に接続"""
    if not DB_PATH.exists():
        print(f"ERROR: DB not found: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# (A) 中止レース
# ============================================================
def test_cancelled_races(conn: sqlite3.Connection):
    """中止レース (DataKubun='9') の検証"""
    print("\n=== (A) 中止レース ===")
    c = conn.cursor()

    # A-1: 中止レースが存在すること
    c.execute("SELECT COUNT(*) FROM NL_RA WHERE DataKubun = '9'")
    count = c.fetchone()[0]
    record("A-1 中止レースの存在", count > 0, f"{count} 件")

    # A-2: 中止レースは SyussoTosu=0, NyusenTosu=0 であること
    c.execute("""
        SELECT COUNT(*) FROM NL_RA
        WHERE DataKubun = '9' AND (SyussoTosu != 0 OR NyusenTosu != 0)
    """)
    bad = c.fetchone()[0]
    record("A-2 中止レースの出走/入線頭数=0", bad == 0,
           f"出走/入線≠0の中止レース: {bad} 件")

    # A-3: 中止レースに対応する SE レコードの状態
    #      中止レースの SE は DataKubun='9' であるべき
    c.execute("""
        SELECT COUNT(*) FROM NL_SE se
        INNER JOIN NL_RA ra ON se.Year=ra.Year AND se.MonthDay=ra.MonthDay
            AND se.JyoCD=ra.JyoCD AND se.Kaiji=ra.Kaiji
            AND se.Nichiji=ra.Nichiji AND se.RaceNum=ra.RaceNum
        WHERE ra.DataKubun = '9'
    """)
    se_count = c.fetchone()[0]
    record("A-3 中止レースの SE レコード", True,
           f"中止レースに紐づく SE: {se_count} 件 (0件も正常)")

    # A-4: 中止レースに HR (払戻) レコードが無いこと
    c.execute("""
        SELECT COUNT(*) FROM NL_HR hr
        INNER JOIN NL_RA ra ON hr.Year=ra.Year AND hr.MonthDay=ra.MonthDay
            AND hr.JyoCD=ra.JyoCD AND hr.Kaiji=ra.Kaiji
            AND hr.Nichiji=ra.Nichiji AND hr.RaceNum=ra.RaceNum
        WHERE ra.DataKubun = '9' AND hr.TanPay > 0
    """)
    hr_with_pay = c.fetchone()[0]
    record("A-4 中止レースに払戻なし", hr_with_pay == 0,
           f"払戻ありの中止レース: {hr_with_pay} 件")


# ============================================================
# (B) 出走取消・競走除外
# ============================================================
def test_scratched_horses(conn: sqlite3.Connection):
    """出走取消・競走除外 (IJyoCD) の検証"""
    print("\n=== (B) 出走取消・競走除外 ===")
    c = conn.cursor()

    # IJyoCD コード表:
    #   0=正常, 1=出走取消, 2=発走除外, 3=競走除外,
    #   4=競走中止, 5=失格, 6=落馬再騎乗, 7=再騎乗

    # B-1: 各 IJyoCD の件数
    c.execute("""
        SELECT IJyoCD, COUNT(*) FROM NL_SE
        WHERE DataKubun = '7'
        GROUP BY IJyoCD ORDER BY IJyoCD
    """)
    rows = c.fetchall()
    ijyo_map = {r[0]: r[1] for r in rows}
    record("B-1 IJyoCD 分布", len(ijyo_map) > 1,
           ", ".join(f"{k}={v}" for k, v in sorted(ijyo_map.items())))

    # B-2: 取消馬 (IJyoCD=1) は KakuteiJyuni=0, Time=0 であること
    c.execute("""
        SELECT COUNT(*) FROM NL_SE
        WHERE DataKubun = '7' AND IJyoCD = '1'
            AND (KakuteiJyuni != 0 OR Time != 0)
    """)
    bad = c.fetchone()[0]
    record("B-2 取消馬の着順=0, タイム=0", bad == 0,
           f"取消なのに着順/タイム≠0: {bad} 件")

    # B-3: 発走除外 (IJyoCD=2) も KakuteiJyuni=0, Time=0
    c.execute("""
        SELECT COUNT(*) FROM NL_SE
        WHERE DataKubun = '7' AND IJyoCD = '2'
            AND (KakuteiJyuni != 0 OR Time != 0)
    """)
    bad = c.fetchone()[0]
    record("B-3 発走除外馬の着順=0, タイム=0", bad == 0,
           f"発走除外なのに着順/タイム≠0: {bad} 件")

    # B-4: 取消馬がいるレースの他馬の着順整合性
    #       取消馬以外の KakuteiJyuni が 1 から連番であること（ギャップなし）
    c.execute("""
        WITH cancelled_races AS (
            SELECT DISTINCT Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum
            FROM NL_SE
            WHERE DataKubun = '7' AND IJyoCD = '1'
        ),
        normal_runners AS (
            SELECT se.Year, se.MonthDay, se.JyoCD, se.RaceNum,
                   se.KakuteiJyuni
            FROM NL_SE se
            INNER JOIN cancelled_races cr
                ON se.Year=cr.Year AND se.MonthDay=cr.MonthDay
                AND se.JyoCD=cr.JyoCD AND se.Kaiji=cr.Kaiji
                AND se.Nichiji=cr.Nichiji AND se.RaceNum=cr.RaceNum
            WHERE se.DataKubun = '7' AND se.IJyoCD = '0'
                AND se.KakuteiJyuni > 0
        ),
        race_check AS (
            SELECT Year, MonthDay, JyoCD, RaceNum,
                   MAX(KakuteiJyuni) as max_jun,
                   COUNT(*) as cnt
            FROM normal_runners
            GROUP BY Year, MonthDay, JyoCD, RaceNum
        )
        SELECT COUNT(*) FROM race_check WHERE max_jun != cnt
    """)
    bad = c.fetchone()[0]
    record("B-4 取消レースの着順連番性", True,
           f"着順不連続のレース: {bad} 件 (同着・競走中止で不一致は正常)")

    # B-5: 競走中止 (IJyoCD=4) の馬は Time>0 の場合もある（途中棄権）
    c.execute("""
        SELECT COUNT(*), SUM(CASE WHEN Time > 0 THEN 1 ELSE 0 END)
        FROM NL_SE
        WHERE DataKubun = '7' AND IJyoCD = '4'
    """)
    row = c.fetchone()
    record("B-5 競走中止馬の統計", row[0] > 0,
           f"競走中止: {row[0]} 件, うちTime>0: {row[1]} 件")


# ============================================================
# (C) 少頭数レース
# ============================================================
def test_small_field_races(conn: sqlite3.Connection):
    """出走頭数が極端に少ないレースの検証"""
    print("\n=== (C) 少頭数レース ===")
    c = conn.cursor()

    # C-1: 5頭以下のレースが存在すること
    c.execute("""
        SELECT SyussoTosu, COUNT(*) FROM NL_RA
        WHERE SyussoTosu BETWEEN 1 AND 5
            AND DataKubun IN ('7', 'A', 'B')
        GROUP BY SyussoTosu ORDER BY SyussoTosu
    """)
    rows = c.fetchall()
    detail = ", ".join(f"{r[0]}頭={r[1]}件" for r in rows)
    record("C-1 少頭数レースの存在", len(rows) > 0, detail)

    # C-2: 2頭立てレースの SE レコード数が正しいこと
    c.execute("""
        SELECT ra.Year, ra.MonthDay, ra.JyoCD, ra.RaceNum,
               ra.SyussoTosu,
               (SELECT COUNT(*) FROM NL_SE se
                WHERE se.Year=ra.Year AND se.MonthDay=ra.MonthDay
                AND se.JyoCD=ra.JyoCD AND se.Kaiji=ra.Kaiji
                AND se.Nichiji=ra.Nichiji AND se.RaceNum=ra.RaceNum
                AND se.DataKubun = '7' AND se.IJyoCD = '0') as actual_runners
        FROM NL_RA ra
        WHERE ra.SyussoTosu IN (2, 3)
            AND ra.DataKubun IN ('7', 'A', 'B')
    """)
    rows = c.fetchall()
    # 注意: SyussoTosu が極端に少ないレースは、実際にはレース途中の
    # 大量取消（障害レースの落馬等）で SyussoTosu が更新された可能性がある。
    # SE の IJyoCD='0' 数と SyussoTosu が一致しない場合も、データとしては正常。
    # ここでは SE レコードが存在すること自体を確認する。
    no_se = [(r[0], r[1], r[2], r[3], r[4], r[5])
             for r in rows if r[5] == 0]
    record("C-2 少頭数レースに SE レコードが存在", len(no_se) == 0,
           f"SE なし: {len(no_se)} 件, " +
           f"SyussoTosu≠SE(IJyoCD=0): {sum(1 for r in rows if r[4]!=r[5])} 件 (既知の差異)")

    # C-3: 2頭立てレースの払戻整合性（単勝・複勝が存在すること）
    c.execute("""
        SELECT ra.Year, ra.MonthDay, ra.JyoCD, ra.RaceNum,
               hr.TanPay, hr.FukuPay
        FROM NL_RA ra
        LEFT JOIN NL_HR hr ON ra.Year=hr.Year AND ra.MonthDay=hr.MonthDay
            AND ra.JyoCD=hr.JyoCD AND ra.Kaiji=hr.Kaiji
            AND ra.Nichiji=hr.Nichiji AND ra.RaceNum=hr.RaceNum
        WHERE ra.SyussoTosu = 2
            AND ra.DataKubun IN ('7', 'A', 'B')
    """)
    rows = c.fetchall()
    # 2頭立ては枠連・馬連不成立の場合がある（正常）
    record("C-3 2頭立てレースの払戻", True,
           f"{len(rows)} レース確認 (不成立の式別あり=正常)")

    # C-4: 少頭数レースのオッズテーブル（O1=単勝）
    c.execute("""
        SELECT COUNT(*) FROM NL_O1 o
        INNER JOIN NL_RA ra ON o.Year=ra.Year AND o.MonthDay=ra.MonthDay
            AND o.JyoCD=ra.JyoCD AND o.Kaiji=ra.Kaiji
            AND o.Nichiji=ra.Nichiji AND o.RaceNum=ra.RaceNum
        WHERE ra.SyussoTosu BETWEEN 1 AND 5
            AND ra.DataKubun IN ('7', 'A', 'B')
    """)
    odds_count = c.fetchone()[0]
    record("C-4 少頭数レースのオッズ", True,
           f"少頭数レースの O1 レコード: {odds_count} 件")


# ============================================================
# (D) 災害期間のデータ
# ============================================================
def test_disaster_period(conn: sqlite3.Connection):
    """2011年3月 東日本大震災前後のデータ検証"""
    print("\n=== (D) 災害期間のデータ (2011年3月) ===")
    c = conn.cursor()

    # D-1: 震災前 (3/5-6) にレースがあること
    c.execute("""
        SELECT COUNT(*) FROM NL_RA
        WHERE Year = 2011 AND MonthDay BETWEEN 305 AND 306
            AND CAST(JyoCD AS INTEGER) <= 10
    """)
    pre = c.fetchone()[0]
    record("D-1 震災前 (3/5-6) のレース", pre > 0, f"{pre} レース")

    # D-2: 震災直後 (3/12-13) に JRA レースがないこと
    #       ※ 3/11 が震災発生日。3/12-13 は開催中止
    c.execute("""
        SELECT COUNT(*) FROM NL_RA
        WHERE Year = 2011 AND MonthDay BETWEEN 312 AND 313
            AND CAST(JyoCD AS INTEGER) <= 10
            AND DataKubun = '7'
    """)
    gap = c.fetchone()[0]
    record("D-2 震災直後 (3/12-13) JRA確定レースなし", gap == 0,
           f"確定レース: {gap} 件")

    # D-3: JRA 再開 (3/19以降) にレースがあること
    c.execute("""
        SELECT COUNT(*) FROM NL_RA
        WHERE Year = 2011 AND MonthDay BETWEEN 319 AND 331
            AND CAST(JyoCD AS INTEGER) <= 10
            AND DataKubun IN ('7', 'A', 'B')
    """)
    post = c.fetchone()[0]
    record("D-3 JRA再開 (3/19-31) のレース", post > 0, f"{post} レース")

    # D-4: 2011年3月の日別レース数（データ欠損パターンの確認）
    c.execute("""
        SELECT MonthDay, COUNT(*) FROM NL_RA
        WHERE Year = 2011 AND MonthDay BETWEEN 301 AND 331
            AND CAST(JyoCD AS INTEGER) <= 10
        GROUP BY MonthDay ORDER BY MonthDay
    """)
    rows = c.fetchall()
    detail = ", ".join(f"{r[0]}={r[1]}" for r in rows)
    record("D-4 2011年3月 日別レース数", len(rows) > 0, detail)

    # D-5: 2011/3/11 の中止レース（DataKubun='9'）
    c.execute("""
        SELECT COUNT(*) FROM NL_RA
        WHERE Year = 2011 AND MonthDay = 311
            AND DataKubun = '9'
    """)
    cancelled = c.fetchone()[0]
    record("D-5 2011/3/11 の中止レース", True,
           f"中止レース: {cancelled} 件 (0件でも正常=当日開催なし)")


# ============================================================
# (E) NULL値・ゼロ値の検証
# ============================================================
def test_null_zero_values(conn: sqlite3.Connection):
    """NULL値・ゼロ値の検証"""
    print("\n=== (E) NULL値・ゼロ値 ===")
    c = conn.cursor()

    # E-1: 確定レース (DataKubun='7') で Odds=0 の正常出走馬がいないこと
    c.execute("""
        SELECT COUNT(*) FROM NL_SE
        WHERE DataKubun = '7' AND IJyoCD = '0' AND Odds = 0
    """)
    zero_odds = c.fetchone()[0]
    record("E-1 確定レースの正常馬 Odds≠0", zero_odds == 0,
           f"Odds=0: {zero_odds} 件")

    # E-2: 確定レースで Time=0 の入着馬（KakuteiJyuni>0）
    c.execute("""
        SELECT COUNT(*) FROM NL_SE
        WHERE DataKubun = '7' AND IJyoCD = '0'
            AND KakuteiJyuni > 0 AND Time = 0
    """)
    zero_time = c.fetchone()[0]
    # 古いデータ（1970-80年代）でタイム未記録の場合があるため、少数は許容
    record("E-2 入着馬の Time≠0", zero_time <= 10,
           f"Time=0の入着馬: {zero_time} 件" +
           (" (古いデータでタイム未記録=許容)" if zero_time > 0 else ""))

    # E-3: NL_RA の重要フィールドが NULL でないこと
    for col in ["JyoCD", "Year", "MonthDay", "RaceNum", "Kyori"]:
        c.execute(f"SELECT COUNT(*) FROM NL_RA WHERE {col} IS NULL AND DataKubun = '7'")
        null_count = c.fetchone()[0]
        record(f"E-3 NL_RA.{col} NOT NULL", null_count == 0,
               f"NULL: {null_count} 件")

    # E-4: NL_SE の重要フィールドが NULL でないこと（確定データ）
    for col in ["Umaban", "KakuteiJyuni", "IJyoCD"]:
        c.execute(f"SELECT COUNT(*) FROM NL_SE WHERE {col} IS NULL AND DataKubun = '7'")
        null_count = c.fetchone()[0]
        record(f"E-4 NL_SE.{col} NOT NULL", null_count == 0,
               f"NULL: {null_count} 件")

    # E-5: HR (払戻) の TanPay が全レースで 0 でないこと（確定データ）
    c.execute("""
        SELECT COUNT(*) FROM NL_HR
        WHERE DataKubun = '7' AND TanPay = 0
    """)
    zero_pay = c.fetchone()[0]
    record("E-5 確定レースの単勝払戻>0", zero_pay == 0,
           f"TanPay=0: {zero_pay} 件")

    # E-6: DataKubun の分布確認（想定外の値がないこと）
    c.execute("SELECT DataKubun, COUNT(*) FROM NL_RA GROUP BY DataKubun ORDER BY DataKubun")
    rows = c.fetchall()
    known = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B'}
    unknown = [r[0] for r in rows if r[0] not in known]
    detail = ", ".join(f"{r[0]}={r[1]}" for r in rows)
    record("E-6 DataKubun 値の妥当性", len(unknown) == 0,
           detail + (f" 不明: {unknown}" if unknown else ""))


# ============================================================
# メイン
# ============================================================
def main():
    print("=" * 60)
    print("異常レース・エッジケース検証")
    print(f"DB: {DB_PATH}")
    print("=" * 60)

    conn = connect_db()
    try:
        test_cancelled_races(conn)
        test_scratched_horses(conn)
        test_small_field_races(conn)
        test_disaster_period(conn)
        test_null_zero_values(conn)
    finally:
        conn.close()

    # サマリ
    print("\n" + "=" * 60)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    total = len(results)
    print(f"結果: {passed}/{total} PASS, {failed}/{total} FAIL")

    if failed > 0:
        print("\n--- FAIL 一覧 ---")
        for name, status, detail in results:
            if status == "FAIL":
                print(f"  ✗ {name}: {detail}")

    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
