#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""異常レース・エッジケース E2E 検証

既存の keiba.db に格納済みのデータを SQL クエリで検証し、
異常レース（中止、出走取消、競走除外、少頭数等）が正しく格納されているか確認する。

実行方法 (A6 上):
  cd C:\\Users\\mitsu\\work\\jrvltsql
  C:\\Users\\mitsu\\AppData\\Local\\Programs\\Python\\Python312-32\\python.exe tests\\e2e\\e2e_edge_cases.py

データベース: data\\keiba.db (既存の本番DB、読み取り専用)
"""

import io
import os
import sqlite3
import sys
from pathlib import Path

if sys.platform == "win32":
    for sn in ("stdout", "stderr"):
        s = getattr(sys, sn)
        if hasattr(s, "buffer"):
            setattr(sys, sn, io.TextIOWrapper(s.buffer, encoding="utf-8", errors="replace"))

project_root = Path(__file__).resolve().parent.parent.parent


# ─────────────────────────────────────────────────
# IJyoCD (異常区分コード) 定義
# ─────────────────────────────────────────────────
IJYO_CODES = {
    "0": "正常",
    "1": "出走取消",
    "2": "発走除外",
    "3": "競走中止",
    "4": "失格",
    "5": "落馬(再騎乗)",
    "6": "落馬",
    "7": "その他",
}


def main():
    db_path = project_root / "data" / "keiba.db"
    if not db_path.exists():
        print(f"ERROR: {db_path} が見つかりません")
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    results = {"pass": 0, "fail": 0, "skip": 0}

    def check(name, condition, detail=""):
        if condition is None:
            results["skip"] += 1
            print(f"  SKIP: {name} {detail}")
        elif condition:
            results["pass"] += 1
            print(f"  PASS: {name} {detail}")
        else:
            results["fail"] += 1
            print(f"  FAIL: {name} {detail}")

    print("=" * 70)
    print("異常レース・エッジケース E2E 検証")
    print(f"DB: {db_path} ({db_path.stat().st_size / 1024 / 1024:.0f} MB)")
    print("=" * 70)

    # ═══════════════════════════════════════════════
    # 1. IJyoCD (異常区分) の分布確認
    # ═══════════════════════════════════════════════
    print("\n━━━ 1. IJyoCD (異常区分) 分布 ━━━")
    cur.execute("SELECT IJyoCD, COUNT(*) as cnt FROM NL_SE GROUP BY IJyoCD ORDER BY IJyoCD")
    rows = cur.fetchall()
    total_se = sum(r["cnt"] for r in rows)
    for r in rows:
        code = r["IJyoCD"]
        label = IJYO_CODES.get(code, "不明")
        print(f"  {code} ({label}): {r['cnt']:,} ({r['cnt']/total_se*100:.2f}%)")

    has_cancel = any(r["IJyoCD"] == "1" and r["cnt"] > 0 for r in rows)
    has_exclude = any(r["IJyoCD"] == "2" and r["cnt"] > 0 for r in rows)
    has_stop = any(r["IJyoCD"] == "3" and r["cnt"] > 0 for r in rows)
    check("出走取消データ存在 (IJyoCD=1)", has_cancel)
    check("発走除外データ存在 (IJyoCD=2)", has_exclude)
    check("競走中止データ存在 (IJyoCD=3)", has_stop)

    # ═══════════════════════════════════════════════
    # 2. 出走取消馬の検証 (IJyoCD=1)
    # ═══════════════════════════════════════════════
    print("\n━━━ 2. 出走取消馬 (IJyoCD=1) の検証 ━━━")

    # 取消馬は着順・タイムが空/0であるべき
    cur.execute("""
        SELECT COUNT(*) as cnt,
               SUM(CASE WHEN KakuteiJyuni = '0' OR KakuteiJyuni = '' OR KakuteiJyuni IS NULL THEN 1 ELSE 0 END) as no_rank,
               SUM(CASE WHEN Time = '0000' OR Time = '' OR Time IS NULL THEN 1 ELSE 0 END) as no_time
        FROM NL_SE WHERE IJyoCD = '1'
    """)
    r = cur.fetchone()
    cancel_total = r["cnt"]
    no_rank = r["no_rank"]
    no_time = r["no_time"]
    check("取消馬: 着順なし", no_rank == cancel_total,
          f"({no_rank}/{cancel_total} 着順なし)")
    check("取消馬: タイムなし", no_time == cancel_total,
          f"({no_time}/{cancel_total} タイムなし)")

    # 取消馬がいるレースの他の馬は正常か
    print("\n  --- 取消馬を含むレースの正常馬チェック ---")
    cur.execute("""
        SELECT s2.Year, s2.MonthDay, s2.JyoCD, s2.RaceNum,
               COUNT(*) as normal_count,
               SUM(CASE WHEN s2.KakuteiJyuni != '0' AND s2.KakuteiJyuni != '' THEN 1 ELSE 0 END) as has_rank
        FROM NL_SE s2
        WHERE s2.IJyoCD = '0'
          AND EXISTS (
            SELECT 1 FROM NL_SE s1
            WHERE s1.Year = s2.Year AND s1.MonthDay = s2.MonthDay
              AND s1.JyoCD = s2.JyoCD AND s1.RaceNum = s2.RaceNum
              AND s1.IJyoCD = '1'
          )
        GROUP BY s2.Year, s2.MonthDay, s2.JyoCD, s2.RaceNum
        LIMIT 100
    """)
    mixed_races = cur.fetchall()
    if mixed_races:
        # 正常馬には着順があるべき
        all_ranked = all(r["has_rank"] > 0 for r in mixed_races)
        check("取消馬含むレースの正常馬に着順あり", all_ranked,
              f"({len(mixed_races)} races checked)")
    else:
        check("取消馬含むレースの正常馬", None, "(該当データなし)")

    # ═══════════════════════════════════════════════
    # 3. 発走除外 (IJyoCD=2) の検証
    # ═══════════════════════════════════════════════
    print("\n━━━ 3. 発走除外 (IJyoCD=2) の検証 ━━━")
    cur.execute("""
        SELECT COUNT(*) as cnt,
               SUM(CASE WHEN KakuteiJyuni = '0' OR KakuteiJyuni = '' OR KakuteiJyuni IS NULL THEN 1 ELSE 0 END) as no_rank
        FROM NL_SE WHERE IJyoCD = '2'
    """)
    r = cur.fetchone()
    check("除外馬: 着順なし", r["no_rank"] == r["cnt"],
          f"({r['no_rank']}/{r['cnt']})")

    # ═══════════════════════════════════════════════
    # 4. 中止レース (DataKubun=9) の検証
    # ═══════════════════════════════════════════════
    print("\n━━━ 4. 中止レース (DataKubun=9) の検証 ━━━")
    cur.execute("SELECT COUNT(*) as cnt FROM NL_RA WHERE DataKubun = '9'")
    cancel_races = cur.fetchone()["cnt"]
    check("中止レース存在", cancel_races > 0, f"({cancel_races} races)")

    if cancel_races > 0:
        # 中止レースのサンプル
        cur.execute("""
            SELECT Year, MonthDay, JyoCD, RaceNum, Hondai
            FROM NL_RA WHERE DataKubun = '9'
            ORDER BY Year DESC, MonthDay DESC
            LIMIT 5
        """)
        print("  サンプル中止レース:")
        for r in cur.fetchall():
            name = r["Hondai"].strip() if r["Hondai"] else "(不明)"
            print(f"    {r['Year']}/{r['MonthDay']} {r['JyoCD']} R{r['RaceNum']} {name}")

        # 中止レースの HR (払戻) は空/0 であるべき
        cur.execute("""
            SELECT COUNT(*) as cnt,
                   SUM(CASE WHEN h.TanPay = '' OR h.TanPay = '0' OR h.TanPay IS NULL THEN 1 ELSE 0 END) as no_pay
            FROM NL_HR h
            JOIN NL_RA r ON h.Year = r.Year AND h.MonthDay = r.MonthDay
                         AND h.JyoCD = r.JyoCD AND h.RaceNum = r.RaceNum
            WHERE r.DataKubun = '9'
        """)
        r = cur.fetchone()
        if r["cnt"] > 0:
            check("中止レースの払戻なし", r["no_pay"] == r["cnt"],
                  f"({r['no_pay']}/{r['cnt']} 払戻なし)")
        else:
            check("中止レースの払戻", None, "(HR レコードなし - 正常)")

    # ═══════════════════════════════════════════════
    # 5. 大量取消レース（7頭取消: 2005/10/05 B6 R10）
    # ═══════════════════════════════════════════════
    print("\n━━━ 5. 大量取消レース (2005/10/05 B6 R10, 7頭取消) ━━━")
    cur.execute("""
        SELECT IJyoCD, COUNT(*) as cnt, GROUP_CONCAT(Bamei, ', ') as names
        FROM NL_SE
        WHERE Year='2005' AND MonthDay='1005' AND JyoCD='B6' AND RaceNum='10'
        GROUP BY IJyoCD
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            label = IJYO_CODES.get(r["IJyoCD"], "?")
            print(f"  IJyoCD={r['IJyoCD']} ({label}): {r['cnt']}頭")
        cancel_count = sum(r["cnt"] for r in rows if r["IJyoCD"] == "1")
        normal_count = sum(r["cnt"] for r in rows if r["IJyoCD"] == "0")
        check("7頭取消レース: 取消馬数", cancel_count == 7, f"({cancel_count})")
        check("7頭取消レース: 正常出走馬あり", normal_count > 0, f"({normal_count}頭)")

        # 払戻データ整合性
        cur.execute("""
            SELECT TanPay, FukuPay, HenkanFlag1, TokubaraiFlag1, FuseirituFlag1
            FROM NL_HR
            WHERE Year='2005' AND MonthDay='1005' AND JyoCD='B6' AND RaceNum='10'
        """)
        hr = cur.fetchone()
        if hr:
            print(f"  HR: 単勝={hr['TanPay']}, 複勝={hr['FukuPay']}")
            print(f"      返還Flag={hr['HenkanFlag1']}, 特払Flag={hr['TokubaraiFlag1']}, 不成立Flag={hr['FuseirituFlag1']}")
            check("大量取消レースの払戻データ存在", True)
        else:
            check("大量取消レースの払戻", None, "(HR なし)")
    else:
        check("大量取消レース", None, "(該当データなし)")

    # ═══════════════════════════════════════════════
    # 6. 少頭数レース（1頭立て）
    # ═══════════════════════════════════════════════
    print("\n━━━ 6. 少頭数レース (1頭のみ正常出走) ━━━")
    cur.execute("""
        SELECT s.Year, s.MonthDay, s.JyoCD, s.RaceNum,
               COUNT(*) as total,
               SUM(CASE WHEN s.IJyoCD = '0' THEN 1 ELSE 0 END) as normal
        FROM NL_SE s
        WHERE s.Year >= '2000'
        GROUP BY s.Year, s.MonthDay, s.JyoCD, s.RaceNum
        HAVING normal = 1
        ORDER BY s.Year DESC
        LIMIT 5
    """)
    solo_races = cur.fetchall()
    check("1頭立てレース存在", len(solo_races) > 0, f"({len(solo_races)}+ races)")

    if solo_races:
        for r in solo_races[:3]:
            print(f"  {r['Year']}/{r['MonthDay']} {r['JyoCD']} R{r['RaceNum']} (全{r['total']}頭中{r['normal']}頭正常)")

        # 1頭立てレースの HR
        sample = solo_races[0]
        cur.execute("""
            SELECT TanPay, FukuPay, FuseirituFlag1, TokubaraiFlag1
            FROM NL_HR
            WHERE Year=? AND MonthDay=? AND JyoCD=? AND RaceNum=?
        """, (sample["Year"], sample["MonthDay"], sample["JyoCD"], sample["RaceNum"]))
        hr = cur.fetchone()
        if hr:
            print(f"  HR: 単勝={hr['TanPay']}, 不成立Flag={hr['FuseirituFlag1']}, 特払Flag={hr['TokubaraiFlag1']}")
            check("1頭立てレースの払戻データ存在", True)

    # ═══════════════════════════════════════════════
    # 7. 東日本大震災期間 (2011/03/11 前後)
    # ═══════════════════════════════════════════════
    print("\n━━━ 7. 東日本大震災期間 (2011/03) ━━━")

    # 震災直後のレース数推移
    cur.execute("""
        SELECT MonthDay, COUNT(*) as races
        FROM NL_RA
        WHERE Year = '2011' AND MonthDay BETWEEN '0305' AND '0410'
        GROUP BY MonthDay ORDER BY MonthDay
    """)
    rows = cur.fetchall()
    print("  日付  | レース数")
    print("  ------|--------")
    for r in rows:
        md = r["MonthDay"]
        marker = " ← 震災" if md == "0311" else ""
        print(f"  {md[:2]}/{md[2:]}  | {r['races']:3d}{marker}")

    # 3/12-3/13 は開催中止のはず → DataKubun=9 ?
    cur.execute("""
        SELECT DataKubun, COUNT(*) as cnt
        FROM NL_RA
        WHERE Year = '2011' AND MonthDay BETWEEN '0312' AND '0325'
        GROUP BY DataKubun
    """)
    dk_rows = cur.fetchall()
    print("\n  震災直後 (3/12-3/25) DataKubun分布:")
    for r in dk_rows:
        print(f"    DataKubun={r['DataKubun']}: {r['cnt']} races")

    check("震災期間のレコード存在", len(rows) > 0)

    # ═══════════════════════════════════════════════
    # 8. NL_NU テーブル (出走取消・競走除外)
    # ═══════════════════════════════════════════════
    print("\n━━━ 8. NL_NU テーブル (出走取消・競走除外専用) ━━━")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = 'NL_NU'")
    has_nu = cur.fetchone()
    if has_nu:
        cur.execute("SELECT COUNT(*) as cnt FROM NL_NU")
        nu_count = cur.fetchone()["cnt"]
        check("NL_NU レコード数", nu_count > 0, f"({nu_count} records)")

        if nu_count > 0:
            cur.execute("PRAGMA table_info(NL_NU)")
            nu_cols = [r[1] for r in cur.fetchall()]
            print(f"  カラム: {', '.join(nu_cols[:15])}...")

            cur.execute("SELECT * FROM NL_NU LIMIT 3")
            print("  サンプル:")
            for r in cur.fetchall():
                print(f"    {dict(r)}")
    else:
        check("NL_NU テーブル", None,
              "(テーブル未作成 — RACE spec に含まれない可能性。DIFF spec での取得を推奨)")
        print("  ※ NU レコードは DIFF データ仕様に含まれます。")
        print("  ※ quickstart で DIFF spec を取得すれば NL_NU テーブルが作成されるはずです。")

    # ═══════════════════════════════════════════════
    # 9. RA-SE-HR クロス整合性
    # ═══════════════════════════════════════════════
    print("\n━━━ 9. RA-SE-HR クロス整合性 ━━━")

    # RA にあって SE にない（孤立RA）
    cur.execute("""
        SELECT COUNT(*) as cnt FROM NL_RA r
        WHERE NOT EXISTS (
            SELECT 1 FROM NL_SE s
            WHERE s.Year = r.Year AND s.MonthDay = r.MonthDay
              AND s.JyoCD = r.JyoCD AND s.RaceNum = r.RaceNum
        )
        AND r.DataKubun != '9'
    """)
    orphan_ra = cur.fetchone()["cnt"]
    check("孤立RA (SE なし、非中止)", orphan_ra == 0,
          f"({orphan_ra} orphan races)" if orphan_ra > 0 else "")

    # SE にあって RA にない（孤立SE）
    cur.execute("""
        SELECT COUNT(*) as cnt FROM NL_SE s
        WHERE NOT EXISTS (
            SELECT 1 FROM NL_RA r
            WHERE r.Year = s.Year AND r.MonthDay = s.MonthDay
              AND r.JyoCD = s.JyoCD AND r.RaceNum = s.RaceNum
        )
    """)
    orphan_se = cur.fetchone()["cnt"]
    check("孤立SE (RA なし)", orphan_se == 0,
          f"({orphan_se} orphan entries)" if orphan_se > 0 else "")

    # ═══════════════════════════════════════════════
    # 10. NULL / 空文字の妥当性
    # ═══════════════════════════════════════════════
    print("\n━━━ 10. NULL・空文字チェック ━━━")

    # 正常馬 (IJyoCD=0) で馬名が空
    cur.execute("SELECT COUNT(*) as cnt FROM NL_SE WHERE IJyoCD = '0' AND (Bamei IS NULL OR Bamei = '')")
    empty_name = cur.fetchone()["cnt"]
    check("正常馬の馬名非空", empty_name == 0, f"({empty_name} empty)" if empty_name > 0 else "")

    # RA の Year が空
    cur.execute("SELECT COUNT(*) as cnt FROM NL_RA WHERE Year IS NULL OR Year = ''")
    empty_year = cur.fetchone()["cnt"]
    check("RA の Year 非空", empty_year == 0, f"({empty_year} empty)" if empty_year > 0 else "")

    # 正常完走馬 (IJyoCD=0, KakuteiJyuni > 0) で Time が空
    cur.execute("""
        SELECT COUNT(*) as cnt FROM NL_SE
        WHERE IJyoCD = '0'
          AND CAST(KakuteiJyuni AS INTEGER) > 0
          AND (Time IS NULL OR Time = '' OR Time = '0000')
    """)
    empty_time = cur.fetchone()["cnt"]
    check("完走馬のタイム非空", empty_time == 0,
          f"({empty_time} missing)" if empty_time > 0 else "")

    conn.close()

    # ─── 結果サマリ ───
    print("\n" + "=" * 70)
    total = results["pass"] + results["fail"] + results["skip"]
    print(f"結果: {results['pass']} PASS / {results['fail']} FAIL / {results['skip']} SKIP (計 {total})")
    if results["fail"] == 0:
        print("✓ PASS")
    else:
        print("✗ FAIL")
    print("=" * 70)

    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
